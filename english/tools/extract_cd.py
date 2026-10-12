import os, struct, sys
binp, out = sys.argv[1], sys.argv[2]
f = open(binp,'rb'); SS=2352
def raw(lba): f.seek(lba*SS); return f.read(SS)
def ud(lba): return raw(lba)[24:24+2048]
pvd = ud(16); assert pvd[1:6]==b'CD001'
root = pvd[156:156+34]
listing=[]
def walk(lba, size, path):
    data=b''.join(ud(lba+i) for i in range((size+2047)//2048))
    p=0
    while p < len(data):
        l=data[p]
        if l==0: p=(p//2048+1)*2048; continue
        rec=data[p:p+l]; p+=l
        elba=struct.unpack('<I',rec[2:6])[0]; esz=struct.unpack('<I',rec[10:14])[0]
        flags=rec[25]; nl=rec[32]; name=rec[33:33+nl]
        if name in (b'\x00',b'\x01'): continue
        name=name.decode('ascii','replace').split(';')[0]
        full=os.path.join(path,name)
        if flags&2:
            os.makedirs(os.path.join(out,full),exist_ok=True); walk(elba,esz,full)
        else:
            n=(esz+2047)//2048
            sub=raw(elba)[18] if n else 0
            form2 = bool(sub & 0x20)
            with open(os.path.join(out,full),'wb') as o:
                if form2:
                    for i in range(n): o.write(raw(elba+i))
                else:
                    d=b''.join(ud(elba+i) for i in range(n)); o.write(d[:esz])
            listing.append((full,elba,esz,'XA/STR(raw2352)' if form2 else 'data'))
os.makedirs(out,exist_ok=True)
walk(struct.unpack('<I',root[2:6])[0], struct.unpack('<I',root[10:14])[0], '')
with open(os.path.join(out,'_lista.txt'),'w') as o:
    for r in listing: o.write('%-40s LBA=%-7d %10d  %s\n'%r)
print(open(os.path.join(out,'_lista.txt')).read())
