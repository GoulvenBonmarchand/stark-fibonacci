from main import commitroot,decommitment,valéatoire,importH,importG,importlistb
from field import truevalue, Field,add,mult,power,rmult
from polynomial import Polynomial,eval_at
from utils import query,puissance2N
from merkle import merkletree,retrouverroot

prime=3*2**30+1
N=10
valeurN=89

Root=commitroot()

nombre_query=puissance2N(N)
quer=query(nombre_query)
listb=importlistb()

def test_un_query(Root,preuve,elt,listb):
    flag=True
    H=importH()
    N=len(H)
    G=importG()
    x,pathx=preuve[0]
    gx,pathgx=preuve[1]
    ggx,pathggx=preuve[2]
    rootx=Root[0]
    cp0x,cp0xpath=preuve[3]
    cp0root=Root[1]
    if rootx!=retrouverroot(pathx,x,elt) or rootx!=retrouverroot(pathgx,gx,elt+3) or rootx!=retrouverroot(pathggx,ggx,elt+6):
        print(rootx)
        print(retrouverroot(pathx,x,elt))
        print(retrouverroot(pathgx,gx,elt+3))
        print(retrouverroot(pathggx,ggx,elt+6))
        return(False)
    a,b,c=valéatoire()
    p0x=(mult(add(x,Field(-1)),power(add(H[elt],Field(-1)),-1)))
    p1x=(mult(add(x,Field(-1)),power(add(H[elt],Field(-valeurN)),-1)))
    num1=add(add(ggx,rmult(-1,gx)),rmult(-1,x))
    num2=Field(1)
    for k in range(N-1,2**puissance2N(N)):
        num2=mult(num2,add(H[elt],rmult(-1,G[k])))
    num=mult(num1,num2)
    denom=power(add(power(H[elt],2**puissance2N(N)),Field(-1)),-1)
    p2x=mult(num,denom)
    cp0_calc=add(add(rmult(a,p0x),rmult(b,p1x)),rmult(c,p2x))
    if truevalue(cp0x)!=truevalue(cp0_calc) or cp0root!=retrouverroot(cp0xpath,cp0x,elt):
        return(False)
    cp0_x,cp0_x_path=preuve[4]
    if elt<N//2:
        if cp0root!=retrouverroot(cp0_x_path,cp0_x,N//2+elt):
            return(False)
        pair=mult(add(cp0x,cp0_x),power(Field(2),-1))
        impair=mult(add(cp0x,rmult(-1,cp0_x)),power(rmult(2,H[elt]),-1))
        valeur_avant=add(pair,rmult(listb[0],impair))
    else:
        if cp0root!=retrouverroot(cp0_x_path,cp0_x,elt-N//2):
            return(False)
        pair=mult(add(cp0x,cp0_x),power(Field(2),-1))
        impair=mult(add(cp0x,rmult(-1,cp0_x)),power(rmult(2,H[elt]),-1))
        valeur_avant=add(pair,rmult(listb[0],impair))
        elt=elt-N//2
    N=N//2
    for k in range(2,Root-1):
        root=Root[k]
        cpkx,cpkxpath=preuve[2*k+1]
        cpk_x,cpk_xpath=preuve[2*k+2]
        if truevalue(valeur_avant)!=truevalue(cpkx) or root!=retrouverroot(cpkxpath,cpkx,elt):
            return(False)
        if elt<N//2:
            if root!=retrouverroot(cpk_xpath,cpk_x,N//2+elt):
                return(False)
            pair=mult(add(cpkx,cpk_x),power(Field(2),-1))
            impair=mult(add(cpkx,rmult(-1,cpk_x)),power(rmult(2,H[elt]),-1))
            valeur_avant=add(pair,rmult(listb[k-1],impair))
        else:
            if root!=retrouverroot(cpk_xpath,cpk_x,elt-N//2):
                return(False)
            pair=mult(add(cpkx,cpk_x),power(Field(2),-1))
            impair=mult(add(cpkx,rmult(-1,cpk_x)),power(rmult(2,H[elt]),-1))
            valeur_avant=add(pair,rmult(listb[k-1],impair))
            elt=elt-N//2
        N=N//2
    return(flag)


def test_final(Root,quer):
    flag=True
    for elt in quer:
        preuve=decommitment(elt)
        if test_un_query(Root,preuve,elt,listb)==False:
            return(False)
    return(flag)

print(test_final(Root,quer))