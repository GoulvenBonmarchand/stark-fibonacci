import numpy as np
from numpy import galois

prime=17
GF = np.galois.GF(prime)

a=GF([])
def vec1023(u0,u1,n):
    a.append(u0,u1)
    for k in range(n):
        a.append(a[-1]+a[-2])
    print(a)
vec1023(0,1,35)