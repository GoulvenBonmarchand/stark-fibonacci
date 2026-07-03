from field import Field,add,power,mult,truevalue
from polynomial import lagrange,eval_at,Polynomial,poly_mult
from fri import fri
from utils import troisrng,listb
from merkle import create_merkle_from_list,authentification_path
from utils import puissance2N

prime=3*2**30+1
N=10
valeurN=89
a=[]
def vec1023(u0,u1):
    a.append(u0)
    a.append(u1)
    for k in range(N-1):
        a.append(add(a[-1],a[-2]))
    return(a)
a=vec1023(Field(1),Field(1))


générateur=Field(5)
w=générateur
g=power(w,(3*2**(30-puissance2N(N))))

def Ggroup(g):
    G=[Field(1)]
    for k in range(1,2**puissance2N(N)):
        G.append(mult(G[-1],g))
    return(G)
G=Ggroup(g)

def importG():
    return(G)

h=power(w,3*2**(30-puissance2N(N)-3))
def Hgroup(h):
    H=[w]
    for k in range(1,2**(puissance2N(N)+3)):
        H.append(mult(H[-1],h))
    return(H)
H=Hgroup(h)

def importH():
    return(H)

poly=lagrange(G[:N+1],a)
print(poly.coeffs)
print(poly.ratio)
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
p1.ratio=[-truevalue(G[N]),1]

p2=poly
for k in range(1,len(p2.coeffs)):
    p2.coeffs[k]=p2.coeffs[k]*truevalue(g)**(2*k)-p2.coeffs[k]*truevalue(g)**(k)-p2.coeffs[k]
for k in range(N-1,2**puissance2N(N)):
    p2.coeffs=poly_mult(p2.coeffs,[-truevalue(G[k]),1])
p2.ratio=[0]*2**puissance2N(N)
p2.ratio[0]=-1
p2.ratio[-1]=1

def importpol():
    return(p0,p1,p2)

a,b,c=troisrng()
def valéatoire():
    return(a,b,c)
Cp0=[]
for k in range(len(H)):
    Cp0.append(a*truevalue(eval_at(p0,H[k]))+b*truevalue(eval_at(p1,H[k]))+c*truevalue(eval_at(p2,H[k])))
    Cp0[k]=Field(Cp0[k])

listeb=listb(puissance2N(N)+3)
def importlistb():
    return(listeb)
fry=fri(listeb,Cp0,H)

cp0merkle=create_merkle_from_list(Cp0)
Roots.append(cp0merkle.root)
cpmerkle=[]
for k in range(len(fry)):
    cpmerkle.append(create_merkle_from_list(fry[k]))
    Roots.append(cpmerkle[-1].root)

def commitroot():
    return(Roots)


def decommitment(elt):
    pack=[]
    pack.append((eval_at(poly,H[elt]),authentification_path(merkledomain,elt)))
    pack.append((eval_at(poly,mult(g,H[elt])),authentification_path(merkledomain,elt+3)))
    pack.append((eval_at(poly,mult(g,mult(g,H[elt]))),authentification_path(merkledomain,elt+6)))
    pack.append((Cp0[elt],authentification_path(cp0merkle,elt)))
    if elt<len(H)//2:
        pack.append((Cp0[elt+len(H)//2],authentification_path(cp0merkle,elt+len(H)//2)))
    else:
        pack.append((Cp0[elt-len(H)//2],authentification_path(cp0merkle,elt-len(H)//2)))
        elt=elt-len(H)//2
    N=len(H)//2
    for k in range(len(cpmerkle)-1):
        pack.append((fry[k][elt],authentification_path(cpmerkle[k],elt)))
        if elt<N//2:
            pack.append((fry[k][elt+N//2],authentification_path(cpmerkle[k],elt+N//2)))
        else:
            pack.append((fry[k][elt-N//2],authentification_path(cpmerkle[k],elt-N//2)))
            elt=elt-N//2
        N=N//2
    pack.append((fry[-1][elt],authentification_path(cpmerkle[-1],elt)))
    return(pack)