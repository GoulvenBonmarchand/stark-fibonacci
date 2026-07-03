from polynomial import Polynomial
from field import Field,add, rmult,truevalue,mult,power

def uneétape(b,cp,H):
    N=len(H)
    L=[]
    for k in range(N//2):
        pair=mult(add(cp[k],cp[N//2+k]),power(Field(2),-1))
        impair=mult(add(cp[k],rmult(-1,cp[N//2+k])),power(rmult(2,H[k]),-1))
        L.append(add(pair,rmult(b,impair)))
    return(L)


def fri(listb,cp,H):
    L=[uneétape(listb[0],cp,H)]
    i=1
    while len(L[-1])!=1:
        N=len(H)
        y=uneétape(listb[i],L[-1],H[:N//2])
        H=H[:N//2]
        i=i+1
        L.append(y)
    return(L)

