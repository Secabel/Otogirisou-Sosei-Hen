import struct, sys
from capstone import *
d=open(sys.argv[1],'rb').read()
BASE=0x80010000; OFF=0x800
targets={int(x,16) for x in sys.argv[2:]}
code=d[OFF:]
md=Cs(CS_ARCH_MIPS,CS_MODE_MIPS32+CS_MODE_LITTLE_ENDIAN)
md.detail=False
md.skipdata=True
ins=list(md.disasm(code,BASE))
# track lui values per register (simple linear)
lui={}
for i in ins:
    ops=i.op_str
    if i.mnemonic=='lui':
        r,v=ops.split(', ');lui[r]=int(v,0)<<16
    elif i.mnemonic in('addiu','ori','lw','sw','lb','lbu','lh','lhu','sh','sb') :
        try:
            if i.mnemonic in('addiu','ori'):
                rd,rs,imm=ops.split(', ')
            else:
                rt,rest=ops.split(', ',1);imm,rs=rest.split('(');rs=rs.rstrip(')')
            if rs in lui:
                a=lui[rs]+(int(imm,0) if i.mnemonic!='ori' else int(imm,0)&0xffff)
                a&=0xffffffff
                if a in targets: print(hex(i.address),i.mnemonic,ops,hex(a))
        except Exception as e: pass
