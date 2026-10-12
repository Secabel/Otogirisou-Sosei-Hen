"""Cargador de escenas por demanda (estrategia B) para Otogirisou - Sosei Hen (PSX).
Genera (con keystone) el blob de datos+codigo MIPS y los parches al exe.  Ver docs/06_cargador_implementacion.md

Diseno resumido
  - La tabla RAM de bases de escena (0x8007AEC0, 46 u32) pasa a contener 0 para escenas NO residentes.
  - 14 sitios del exe hacen `lw D,(tabla+S*4)`. Cada uno se sustituye por `j tramp_i`; la trampolin:
      1) apaga interrupciones (el handler del BIOS destruye k0/k1), 2) calcula &tabla[S],
      3) lee la base; si != 0 -> vuelve; si == 0 -> slow_common: guarda TODOS los registros, carga la
         escena del CD (CdRead + CdReadSync bloqueante de libcd), la coloca en un slot del pool (victima = la mas antigua
         no fijada por gp+0x3E0/0x3F0/0x528), actualiza la tabla, restaura y vuelve.
  - 0x8001ED00 (relleno de tabla al arrancar) salta a my_init (tabla = 0, slots vacios)."""
import struct, keystone, capstone

TABLA = 0x8007AEC0
EXE_BASE = 0x80010000
EXE_HDR = 0x800

# sitios: (direccion del lw, D, modo, fuente, keep, salto)
#  modo 'T': &tabla[S] esta en el registro `fuente`;  'S': S esta en `fuente`;  'A': S = fuente & 0xff
#  keep=True: A+4 queda en el delay slot del j;  False: A+4 se repite en la cola
#  salto: destino del `j` original en A+4 (sitios 3 y 11), A+8 es su delay slot
SITIOS = [
    (0x80015ED8, '$v1', 'S', '$a1', True,  None),
    (0x80017E38, '$a1', 'T', '$v1', False, None),
    (0x80018A54, '$a1', 'T', '$v0', False, 0x800189CC),
    (0x80019920, '$v0', 'T', '$v1', True,  None),
    (0x80019A08, '$v0', 'T', '$v1', True,  None),
    (0x8001AEF0, '$v1', 'S', '$a1', True,  None),
    (0x8001CFE8, '$v0', 'T', '$v1', True,  None),
    (0x8001F66C, '$v0', 'S', '$a1', True,  None),
    (0x8001F70C, '$v0', 'S', '$a3', True,  None),
    (0x8001FC38, '$v0', 'A', '$a0', True,  None),
    (0x80030BE4, '$a1', 'T', '$v0', False, 0x80030B5C),
    (0x80030DD4, '$v0', 'S', '$a1', True,  None),
    (0x80030E34, '$v0', 'S', '$a2', True,  None),
    (0x800319AC, '$v0', 'T', '$v1', True,  None),
]
ESPERADO = {0x80015ED8: ('lw', '$v1', '$v0'), 0x80017E38: ('lw', '$a1', '$v1'), 0x80018A54: ('lw', '$a1', '$v0'),
            0x80019920: ('lw', '$v0', '$v1'), 0x80019A08: ('lw', '$v0', '$v1'), 0x8001AEF0: ('lw', '$v1', '$v0'),
            0x8001CFE8: ('lw', '$v0', '$v1'), 0x8001F66C: ('lw', '$v0', '$v0'), 0x8001F70C: ('lw', '$v0', '$v0'),
            0x8001FC38: ('lw', '$v0', '$v1'), 0x80030BE4: ('lw', '$a1', '$v0'), 0x80030DD4: ('lw', '$v0', '$v0'),
            0x80030E34: ('lw', '$v0', '$v0'), 0x800319AC: ('lw', '$v0', '$v1')}

# --- disposicion del blob (offsets desde su base) ---
O_SCTAB = 0x000   # 45 x {u32 lba, u16 nsect, u16 off}
O_SLOTSC = 0x180  # 16 bytes: escena de cada slot (0xFF vacio)
O_STAMP = 0x1A0   # 16 words
O_CLOCK = 0x1E0
O_LOC = 0x1E4
O_RES = 0x1E8
O_SLOTAD = 0x1F0  # 16 words: direccion RAM de cada slot
O_STACK = 0x600   # tope de la pila privada (0x400 bytes hacia abajo)
O_CODE = 0x600
MAXSLOT = 16
TR_SIZE = 0x80    # bytes por trampolin


def LA(r, v):
    return f"  lui {r},{(v >> 16) & 0xffff}\n  ori {r},{r},{v & 0xffff}\n"


def SYNC(tag, D_RES):
    """CdReadSync NO bloqueante en bucle (la version del juego con modo 0 solo espera el ack del comando, no el fin de la lectura):
    devuelve cuando quedan 0 sectores (v0==0) o error (v0<0). Entre sondeos cede un VSync."""
    return (f"sy_{tag}:\n  addiu $a0,$zero,1\n" + LA('$a1', D_RES) + "  jal 0x80058358\n  nop\n"
            f"  blez $v0,sy_{tag}_e\n  nop\n  jal 0x8004cc78\n  move $a0,$zero\n  b sy_{tag}\n  nop\nsy_{tag}_e:\n")


def asm_comun(base, nslot, slotsz, logaddr, ls_addr=0):
    # logaddr: registro de depuracion en RAM libre (0x8015F000 lo pisan los creditos/FMV)
    D_SLOTAD = base + O_SLOTAD
    D_SCTAB, D_SLOTSC, D_STAMP = base + O_SCTAB, base + O_SLOTSC, base + O_STAMP
    D_CLOCK, D_LOC, D_RES, STK = base + O_CLOCK, base + O_LOC, base + O_RES, base + O_STACK
    regs = [('$at', 0x00), ('$v0', 0x04), ('$v1', 0x08), ('$a0', 0x0c), ('$a1', 0x10), ('$a2', 0x14), ('$a3', 0x18),
            ('$t0', 0x1c), ('$t1', 0x20), ('$t2', 0x24), ('$t3', 0x28), ('$t4', 0x2c), ('$t5', 0x30), ('$t6', 0x34), ('$t7', 0x38),
            ('$s0', 0x3c), ('$s1', 0x40), ('$s2', 0x44), ('$s3', 0x48), ('$s4', 0x4c), ('$s5', 0x50), ('$s6', 0x54), ('$s7', 0x58),
            ('$t8', 0x5c), ('$t9', 0x60), ('$fp', 0x68), ('$ra', 0x6c)]
    s = ".set noreorder\n.set noat\nslow_common:\n  addiu $sp,$sp,-0x90\n"
    for r, o in regs: s += f"  sw {r},{o}($sp)\n"
    s += "  mfhi $t0\n  sw $t0,0x70($sp)\n  mflo $t0\n  sw $t0,0x74($sp)\n  sw $k1,0x78($sp)\n  sw $k0,0x7c($sp)\n"
    s += LA('$t0', TABLA) + "  subu $a0,$k0,$t0\n  srl $a0,$a0,2\n" + LA('$t1', base + O_CODE) + "  subu $a1,$k1,$t1\n  srl $a1,$a1,7\n  move $s0,$sp\n" + LA('$sp', STK)
    s += f"  jal {ls_addr}\n  nop\n  sw $v0,0x7c($s0)\n  move $sp,$s0\n"
    s += "  mfc0 $t0,$12\n  nop\n  ori $t0,$t0,1\n  addiu $t0,$t0,-1\n  mtc0 $t0,$12\n  nop\n"
    s += "  lw $t0,0x70($sp)\n  nop\n  mthi $t0\n  lw $t0,0x74($sp)\n  nop\n  mtlo $t0\n"
    for r, o in regs: s += f"  lw {r},{o}($sp)\n"
    s += "  lw $k1,0x78($sp)\n  lw $k0,0x7c($sp)\n  nop\n  jr $k1\n  addiu $sp,$sp,0x90\n"
    s1 = s
    s = ".set noreorder\n.set noat\n"
    # ---- load_scene(a0=escena) -> v0 = base ----
    s += "load_scene:\n  addiu $sp,$sp,-0x48\n  sw $ra,0x44($sp)\n"
    for i in range(8): s += f"  sw $s{i},{0x20 + 4 * i}($sp)\n"
    s += "  sw $a1,0x10($sp)\n  sltiu $t0,$a0,45\n  beqz $t0,ls_ret0\n  move $s0,$a0\n"
    s += "  mfc0 $t0,$12\n  nop\n  ori $t0,$t0,1\n  mtc0 $t0,$12\n  nop\n"          # interrupciones ON
    s += LA('$s1', D_SLOTSC) + LA('$s2', D_STAMP) + LA('$fp', D_SLOTAD) + "  addiu $s3,$zero,-1\n  addiu $s4,$zero,-1\n  move $s5,$zero\n"
    s += "ls_loop:\n  addu $t0,$s1,$s5\n  lbu $t0,0($t0)\n  nop\n  addiu $t1,$zero,255\n  beq $t0,$t1,ls_empty\n  nop\n"
    s += "  sll $t0,$s5,2\n  addu $t0,$t0,$fp\n  lw $s6,0($t0)\n" + LA('$t2', slotsz) + "  addu $s7,$s6,$t2\n"
    for n, off in enumerate((0x3e0, 0x3f0, 0x528)):
        s += f"  lw $t3,{off}($gp)\n  nop\n  sltu $t4,$t3,$s6\n  bnez $t4,ls_p{n + 1}\n  nop\n  sltu $t4,$t3,$s7\n  bnez $t4,ls_next\n  nop\nls_p{n + 1}:\n"
    s += "  sll $t5,$s5,2\n  addu $t5,$t5,$s2\n  lw $t6,0($t5)\n  nop\n  sltu $t7,$t6,$s4\n  beqz $t7,ls_next\n  nop\n  move $s4,$t6\n  move $s3,$s5\n"
    s += "ls_next:\n  addiu $s5,$s5,1\n"
    s += f"  sltiu $t0,$s5,{nslot}\n  bnez $t0,ls_loop\n  nop\n  b ls_chosen\n  nop\n"
    s += "ls_empty:\n  move $s3,$s5\nls_chosen:\n  bgez $s3,ls_go\n  nop\n  move $s3,$zero\nls_go:\n"
    s += "  addu $t0,$s1,$s3\n  lbu $t1,0($t0)\n  nop\n  move $s4,$t1\n  addiu $t2,$zero,255\n  beq $t1,$t2,ls_noev\n  nop\n"
    s += "  sll $t1,$t1,2\n" + LA('$t3', TABLA) + "  addu $t1,$t1,$t3\n  sw $zero,0($t1)\n"
    # registro circular (resto libre del pool, sobrevive a un reinicio): [0]=magia [4]=arranques [0xC]=indice; entradas de 8 bytes desde +0x10: escena, slot, desalojada, sitio, gp+0x3E0
    s += "ls_noev:\n" + LA('$t0', logaddr) + "  lw $t1,0xc($t0)\n  nop\n  andi $t2,$t1,255\n  sll $t2,$t2,3\n  addu $t2,$t2,$t0\n  addiu $t2,$t2,0x10\n"
    s += "  sb $s0,0($t2)\n  sb $s3,1($t2)\n  sb $s4,2($t2)\n  lw $t3,0x10($sp)\n  nop\n  sb $t3,3($t2)\n  lw $t3,0x3e0($gp)\n  nop\n  sw $t3,4($t2)\n  addiu $t1,$t1,1\n  sw $t1,0xc($t0)\n"
    s += "  sll $t0,$s3,2\n  addu $t0,$t0,$fp\n  lw $s7,0($t0)\n  nop\n"
    s += "  sll $t0,$s0,3\n" + LA('$t1', D_SCTAB) + "  addu $t0,$t0,$t1\n  lw $s4,0($t0)\n  lhu $s5,4($t0)\n  lhu $s6,6($t0)\n"
    s += "  move $a0,$s4\n" + LA('$a1', D_LOC) + "  jal 0x80057cb8\n  nop\n"                                # CdIntToPos(lba, loc)
    s += "  addiu $s1,$zero,3000\nls_rd:\n"
    # 1) drenar la cola de CD del juego (flag 0x8007A873 != 0 => lectura en curso): llamar al sondeo 0x8001D448 + VSync(0) hasta que quede libre
    s += "ls_q:\n  lui $t0,0x8008\n  lbu $t0,-0x578d($t0)\n  nop\n  beqz $t0,ls_qok\n  nop\n  jal 0x8001d448\n  nop\n  jal 0x8004cc78\n  move $a0,$zero\n  b ls_q\n  nop\nls_qok:\n"
    s += SYNC("a", D_RES)                                                                        # drena libcd (sondeo)
    s += LA('$a0', D_LOC) + "  move $a1,$s5\n  move $a2,$s7\n  addiu $a3,$zero,0x80\n  jal 0x80057fa8\n  nop\n"   # CdRead
    s += "  bnez $v0,ls_wait\n  nop\n  jal 0x8004cc78\n  move $a0,$zero\n  b ls_again\n  nop\nls_wait:\n"
    s += SYNC("b", D_RES)
    s += "  bgez $v0,ls_done\n  nop\nls_again:\n  addiu $s1,$s1,-1\n  bnez $s1,ls_rd\n  nop\nls_done:\n"
    s += "  addu $v0,$s7,$s6\n  sll $t0,$s0,2\n" + LA('$t1', TABLA) + "  addu $t0,$t0,$t1\n  sw $v0,0($t0)\n"
    s += LA('$t1', D_SLOTSC) + "  addu $t1,$t1,$s3\n  sb $s0,0($t1)\n"
    s += LA('$t1', D_CLOCK) + "  lw $t2,0($t1)\n  nop\n  addiu $t2,$t2,1\n  sw $t2,0($t1)\n" + LA('$t3', D_STAMP) + "  sll $t4,$s3,2\n  addu $t4,$t4,$t3\n  sw $t2,0($t4)\n"
    s += "  b ls_end\n  nop\nls_ret0:\n  move $v0,$zero\nls_end:\n"
    for i in range(8): s += f"  lw $s{i},{0x20 + 4 * i}($sp)\n"
    s += "  lw $ra,0x44($sp)\n  nop\n  jr $ra\n  addiu $sp,$sp,0x48\n"
    return s1, s


def asm_init(base, logaddr):
    D_SLOTSC, D_CLOCK = base + O_SLOTSC, base + O_CLOCK
    s = ".set noreorder\n.set noat\nmy_init:\n" + LA('$t0', TABLA)
    s += "  addiu $t1,$zero,45\nmi_l:\n  sw $zero,0($t0)\n  addiu $t0,$t0,4\n  addiu $t1,$t1,-1\n  bnez $t1,mi_l\n  nop\n"
    s += LA('$t2', 0x80124800) + "  sw $t2,0($t0)\n"          # entrada 45 = fin del script (centinela != 0)
    s += LA('$t3', D_SLOTSC) + f"  addiu $t1,$zero,{MAXSLOT}\n  addiu $t4,$zero,255\nmi_l2:\n  sb $t4,0($t3)\n  addiu $t3,$t3,1\n  addiu $t1,$t1,-1\n  bnez $t1,mi_l2\n  nop\n"
    s += LA('$t3', D_CLOCK) + "  sw $zero,0($t3)\n"
    s += LA('$t0', logaddr) + LA('$t2', 0x4C4F4731) + "  lw $t1,0($t0)\n  nop\n  beq $t1,$t2,mi_keep\n  nop\n  sw $t2,0($t0)\n  sw $zero,4($t0)\n  sw $zero,8($t0)\n  sw $zero,0xc($t0)\n  b mi_fin\n  nop\n"
    s += "mi_keep:\n  lw $t1,4($t0)\n  nop\n  addiu $t1,$t1,1\n  sw $t1,4($t0)\nmi_fin:\n  jr $ra\n  nop\n"
    return s


def asm_tramp(i, sitio, a4, a8, tr_addr, slow_addr):
    A, D, modo, src, keep, salto = sitio
    L = [f"mfc0 {D},$12", "nop", f"ori {D},{D},1", f"addiu {D},{D},-1", f"mtc0 {D},$12", "nop"]
    if modo == 'T': L += [f"move $k0,{src}"]
    else:
        if modo == 'A': L += [f"andi $k0,{src},255", "sll $k0,$k0,2"]
        else: L += [f"sll $k0,{src},2"]
        L += [f"lui $k1,{TABLA >> 16}", f"ori $k1,$k1,{TABLA & 0xffff}", "addu $k0,$k0,$k1"]
    L += [f"lw {D},0($k0)", "nop", f"bnez {D},ok", "nop"]
    ret = tr_addr + 4 * (len(L) + 4)
    L += [f"lui $k1,{ret >> 16}", f"ori $k1,$k1,{ret & 0xffff}", f"j {slow_addr}", "nop", f"move {D},$k0", "ok:"]
    if salto is None and not keep: L += [a4]
    if salto is not None: L += [a8]
    L += ["mfc0 $k0,$12", "nop", "ori $k0,$k0,1", "mtc0 $k0,$12", "nop"]
    L += [f"j {salto if salto is not None else A + 8}", "nop"]
    return ".set noreorder\n.set noat\n" + "\n".join(("" if x.endswith(':') else "  ") + x for x in L) + "\n"


def ensamblar(src, addr):
    ks = keystone.Ks(keystone.KS_ARCH_MIPS, keystone.KS_MODE_MIPS32 + keystone.KS_MODE_LITTLE_ENDIAN)
    enc, n = ks.asm(src, addr)
    return bytes(enc)


def j_word(dest):
    return 0x08000000 | ((dest >> 2) & 0x3ffffff)


def construir(exe, base, slots, slotsz, logaddr, escenas):
    """exe: bytearray (se modifica).  base: direccion RAM del blob.  slots: lista de direcciones RAM de los slots (cada uno de `slotsz` bytes).
    escenas: 45 x (lba, nsect, off).  Devuelve (blob:bytes, simbolos:dict)."""
    nslot = len(slots)
    assert 1 <= nslot <= MAXSLOT and len(escenas) == 45
    md = capstone.Cs(capstone.CS_ARCH_MIPS, capstone.CS_MODE_MIPS32 + capstone.CS_MODE_LITTLE_ENDIAN)

    def word(a): return struct.unpack_from('<I', exe, a - EXE_BASE + EXE_HDR)[0]

    def dis(a):
        i = next(md.disasm(struct.pack('<I', word(a)), a)); return i.mnemonic, i.op_str
    TR0 = base + O_CODE
    COMUN = TR0 + len(SITIOS) * TR_SIZE
    blob = bytearray(O_CODE)
    for k, (lba, ns, off) in enumerate(escenas):
        assert ns * 2048 <= slotsz, ('escena mayor que el slot', k, ns * 2048, slotsz)
        struct.pack_into('<IHH', blob, O_SCTAB + 8 * k, lba, ns, off)
    for k, a in enumerate(slots): struct.pack_into('<I', blob, O_SLOTAD + 4 * k, a)
    tramps = bytearray()
    for i, st in enumerate(SITIOS):
        A = st[0]
        m, ops = dis(A)
        e = ESPERADO[A]
        assert m == 'lw' and ops.replace(' ', '') in (f"{e[1]},({e[2]})", f"{e[1]},0({e[2]})"), (hex(A), m, ops)
        a4 = a8 = None
        if st[5] is None:
            if not st[4]:
                m4, o4 = dis(A + 4); a4 = f"{m4} {o4}"
        else:
            m4, o4 = dis(A + 4); assert m4 == 'j' and int(o4, 16) == st[5], (hex(A), m4, o4)
            m8, o8 = dis(A + 8); a8 = f"{m8} {o8}"
        ta = TR0 + i * TR_SIZE
        b = ensamblar(asm_tramp(i, st, a4, a8, ta, COMUN), ta)
        assert len(b) <= TR_SIZE, (i, len(b))
        tramps += b + b'\x00' * (TR_SIZE - len(b))
    p1, p2 = asm_comun(base, nslot, slotsz, logaddr)
    n1 = len(ensamblar(p1, COMUN)); LS = COMUN + n1
    p1, p2 = asm_comun(base, nslot, slotsz, logaddr, LS)
    comun = ensamblar(p1, COMUN) + ensamblar(p2, LS)
    INIT = COMUN + len(comun)
    init = ensamblar(asm_init(base, logaddr), INIT)
    total = bytes(blob) + bytes(tramps) + comun + init
    for i, st in enumerate(SITIOS):
        struct.pack_into('<I', exe, st[0] - EXE_BASE + EXE_HDR, j_word(TR0 + i * TR_SIZE))
        if not st[4]: struct.pack_into('<I', exe, st[0] + 4 - EXE_BASE + EXE_HDR, 0)   # delay slot = nop (la instruccion se repite en la cola)
    struct.pack_into('<II', exe, 0x8001ED00 - EXE_BASE + EXE_HDR, j_word(INIT), 0)
    sim = dict(base=base, tr0=TR0, comun=COMUN, init=INIT, size=len(total), stack=base + O_STACK)
    return total, sim
