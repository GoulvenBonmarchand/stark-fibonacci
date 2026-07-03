import random
from field import Field
prime=3*2**30+1
N=10
valeurN=89
def puissance2N(x):
    c=0
    while N-2**c>0:
        c+=1
    return(c)

def troisrng():
    a=random.randint(1,prime-1)
    b=random.randint(1,prime-1)
    c=random.randint(1,prime-1)
    return(a,b,c)

def listb(l):
    L=[]
    for k in range(l):
        L.append(random.randint(1,prime-1))
    return(L)

taille=2**(puissance2N(N)+3)
print(taille)
def query(l):
    L=[]
    for k in range(l):
        L.append(random.randint(0,taille-6))
    return(L)