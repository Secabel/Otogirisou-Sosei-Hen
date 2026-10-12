import sys
from capstone import *
d=open('extracted/SLPS_016.45','rb').read()
a=int(sys.argv[1],16);b=int(sys.argv[2],16)
md=Cs(CS_ARCH_MIPS,CS_MODE_MIPS32+CS_MODE_LITTLE_ENDIAN); md.skipdata=True
for i in md.disasm(d[a-0x80010000+0x800:b-0x80010000+0x800],a):
    print(f"{i.address:08x}  {i.mnemonic:7s} {i.op_str}")
