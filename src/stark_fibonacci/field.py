prime=3*2**30+1
class Field:
    def __init__(self,value,prime=prime):
        self.prime=prime
        self.value=value

def truevalue(f):
    return(int(f.value%f.prime))
def add(left,right):
    if left.prime!=right.prime:
        return( "error les éléments doivent appartenir au même corps")
    else:
        s=(truevalue(left)+truevalue(right))%left.prime
        return(Field(s,left.prime))
    
def mult(a,b):
    if a.prime!=b.prime:
        return( "error les éléments doivent appartenir au même corps")
    else:
        m=(truevalue(a)*truevalue(b))%a.prime
        return(Field(m,a.prime))

def rmult(r,a):
    return(Field((r*truevalue(a))%a.prime,a.prime))

def power(a, n):
    return Field(pow(truevalue(a), n, a.prime), a.prime)
