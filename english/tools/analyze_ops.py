"""Ajusta longitudes de los ops desconocidos maximizando validez del parseo y saltos que caen en limites de token."""
import json, struct, sys, itertools
ram=open('analysis/ram_texto1.bin','rb').read()
BASE=0x8008D800; END=BASE+302*2048
starts=[]
for i in range(400):
    a=struct.unpack_from('<I',ram,0x7AEC0+4*i)[0]
    if not (BASE<=a<END) or (starts and a<=starts[-1]): break
    starts.append(a)
starts.append(END)
L={int(k):v for k,v in json.load(open('tables/ops_cmd.json'))['len'].items()}
L[21]=2
UNK=[3,9,10,19,20]
def parse(L):
    bad=0; jumps=[]; bounds=[]; ops=0
    for s in range(len(starts)-1):
        p=starts[s]-0x80000000; e=starts[s+1]-0x80000000; b=set(); base=p
        while p<e:
            b.add(p-base); c=ram[p]
            if c==0:
                op=ram[p+1]; n=L.get(op)
                if n is None: bad+=1; n=2
                if op==0x0e and p+6<=e: jumps.append((s,ram[p+2],ram[p+3]<<16|ram[p+4]<<8|ram[p+5]))
                if op==0x0d and p+9<=e: jumps.append((s,ram[p+5],ram[p+6]<<16|ram[p+7]<<8|ram[p+8]))
                p+=n; ops+=1
            elif 0xf0<=c<=0xf7: p+=2
            else: p+=1
        bounds.append(b)
    ok=sum(1 for (s,sc,off) in jumps if sc<len(bounds) and off in bounds[sc])
    return bad,ok,len(jumps),ops
if __name__=='__main__':
    for it in range(3):
        for op in UNK:
            best=None
            for n in range(1,12):
                L[op]=n; bad,ok,nj,ops=parse(L)
                sc=(ok-bad*0.5)
                if best is None or sc>best[0]: best=(sc,n,bad,ok,nj)
            L[op]=best[1]; print(it,op,best)
    print(L); print(parse(L))
    json.dump({'len':{str(k):v for k,v in L.items()}},open('tables/ops_cmd_v2.json','w'))
