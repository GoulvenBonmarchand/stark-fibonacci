from field import Field,power,truevalue,add,mult,rmult

prime=3*2**30+1
class Polynomial:
    def __init__(self,coeffs,ratio=[1]):
        self.coeffs=coeffs #coeffs[0] elt constant
        self.ratio=ratio

def réduction(poly,f):
    s=0
    denom=0
    if [0]*len(poly.coeffs)==poly.coeffs:
        return(Field(0))
    while s==0:
        #changement coeffs poly
        new_poly=Polynomial([])
        if truevalue(f)==0:
            poly.coeffs=poly.coeffs[1::]
            poly.ratio=poly.ratio[1::]
        else:
            fopp=rmult(-1,power(f,-1))
            new_poly.coeffs.append(truevalue(rmult(poly.coeffs[0],fopp)))
            new_poly.ratio[0]=truevalue(rmult(poly.ratio[0],fopp))
            for k in range(1,len(poly.coeffs)):
                sub=poly.coeffs[k]-new_poly.coeffs[-1]
                new_poly.coeffs.append(sub*truevalue(fopp))
            for k in range(1,len(poly.ratio)):
                sub=poly.ratio[k]-new_poly.ratio[-1]
                new_poly.ratio.append(sub*truevalue(fopp))
            poly.coeffs,poly.ratio=new_poly.coeffs,new_poly.ratio
        for k in range(len(poly.coeffs)):
            s+=poly.coeffs[k]*truevalue(power(f,k))
            s=s%prime
        for k in range(len(poly.ratio)):
            denom+=poly.ratio[k]*truevalue(power(f,k))
            denom=denom%prime
    if denom==0:
        return("error")
    return(Field((truevalue(rmult(s,power(Field(denom),-1))))%f.prime,f.prime))

def eval_at(poly,f):
    s=0
    denom=0
    for k in range(len(poly.coeffs)):
        s+=poly.coeffs[k]*truevalue(power(f,k))
        s=s%prime
    for k in range(len(poly.ratio)):
        denom+=poly.ratio[k]*truevalue(power(f,k))
        denom=denom%prime
    if denom==0:
        if s!=0:
            return("error")
        else:
            return(réduction(poly,f))
    return(Field((truevalue(rmult(s,power(Field(denom),-1))))%f.prime,f.prime))


def poly_add(P, Q):
    n = max(len(P), len(Q))
    R = [0]*n
    for i in range(n):
        if i < len(P):
            R[i] += P[i]
        if i < len(Q):
            R[i] += Q[i]
        R[i] %= prime
    return R

def poly_mult(P, Q):
    R = [0]*(len(P)+len(Q)-1)
    for i in range(len(P)):
        for j in range(len(Q)):
            R[i+j] = (R[i+j] + P[i]*Q[j]) % prime
    return R

def lagrange(fx, fy):
    p = fx[0].prime
    resultat = [0]
    n = len(fx)
    for i in range(n):
        Li = [1]
        denom = Field(1, p)
        for j in range(n):
            if i != j:
                Li = poly_mult(Li, [(-truevalue(fx[j])) % p, 1])
                diff = add(fx[i], Field(-truevalue(fx[j]), p))
                denom = mult(denom, diff)
        coeff = mult(fy[i], power(denom,-1))
        Li = [(c * truevalue(coeff)) % p for c in Li]
        resultat = poly_add(resultat, Li)
    print(0)
    return Polynomial(resultat)

