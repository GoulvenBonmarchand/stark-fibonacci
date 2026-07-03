from field import Field,add,power,mult,truevalue
from polynomial import lagrange,eval_at,Polynomial,poly_mult
from fri import fri
from stark import troisrng,listb
from merkle import create_merkle_from_list

prime=3*2**30+1
N=1022
valeurN=2338775057
a=[]
def vec1023(u0,u1):
    a.append(u0)
    a.append(u1)
    for k in range(N-1):
        a.append(add(a[-1],a[-2]))
    return(a)
a=vec1023(Field(0),Field(1))

def puissance2N(x):
    c=0
    while N-2**c>0:
        c+=1
    return(c)

générateur=Field(5)
w=générateur
g=power(w,(3*2**(30-puissance2N(N))))

def Ggroup(g):
    G=[Field(1)]
    for k in range(1,2**puissance2N(N)):
        G.append(mult(G[-1],g))
    return(G)
G=Ggroup(g)


h=power(w,3*2**(30-puissance2N(N)-3))
def Hgroup(h):
    H=[w]
    for k in range(1,2**(puissance2N(N)+3)):
        H.append(mult(H[-1],h))
    return(H)
H=Hgroup(h)

poly=lagrange(G[:N+1],a)
evaldomain=[]
for k in range(len(H)):
    evaldomain.append(eval_at(poly,H[k]))

merkledomain=create_merkle_from_list(evaldomain)
Roots=[merkledomain.root]
p0=poly
p0.coeffs[0]=poly.coeffs[0]-1
p0.ratio=[-1,1]

p1=poly
p1.coeffs[0]=poly.coeffs[0]-valeurN
p1.ratio=[-G[N],1]

p2=poly
for k in range(1,len(p2.coeffs)):
    p2.coeffs[k]=p2.coeffs[k]*g**(2*k)-p2.coeffs[k]*g**(k)-p2.coeffs[k]
for k in range(N-1,2**puissance2N(N)):
    p2.coeffs=poly_mult(p2.coeffs,[-G[k],1])
p2.ratio=[0]*2**puissance2N(N)
p2.ratio[0]=-1
p2.ratio[-1]=1

a,b,c=troisrng()
Cp0=[]
for k in range(len(h)):
    Cp0.append(a*truevalue(eval_at(p0,H[k]))+b*truevalue(eval_at(p1,H[k]))+c*truevalue(eval_at(p2,H[k])))
    Cp0[k]=Field(Cp0[k])

listeb=listb(puissance2N(N)+3)
fry=fri(listeb,Cp0,H)

cp0merkle=create_merkle_from_list(Cp0)
Roots.append(cp0merkle.root)
cpmerkle=[]
for k in range(len(fry)):
    cpmerkle.append(create_merkle_from_list(fry[k]))
    Roots.append(cpmerkle[-1].root)

def commitroot():
    return(Roots)
