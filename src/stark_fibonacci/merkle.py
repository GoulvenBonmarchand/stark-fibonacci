import hashlib as hashlib
from field import Field,truevalue

class merkletree:
    def __init__(self,root,leaves=[]):
        self.root=root
        self.leaves=leaves


def hashage(n):
    a = n.to_bytes(8, "big")
    return hashlib.sha256(a).digest()

def create_merkle_from_list(list):
    L=[]
    for k in range(len(list)):
        L.append(merkletree(hashage(truevalue(list[k]))))
    while len(L)!=1:
        h1,h2=L[0],L[1]
        has=hashlib.sha256(h1.root+h2.root).digest()
        L.append(merkletree(has,[h1,h2]))
        L=L[2:]
    return(L[0])


def taille_arbre(arbre):
    n=0
    while len(arbre.leaves)>0:
        n+=1
        arbre=arbre.leaves[0]
    return(n)

def inttobinary(n,m):
    max=m
    L=[0]*max
    while max>-1:
        if n>=2**max:
            n=n-2**max
            L[max]=1
        max=max-1
    return(L)


#n est donnée par le verifier l'indice de l'élement dans la liste
def authentification_path(arbre,n):
    position=inttobinary(n,taille_arbre(arbre))
    taille=taille_arbre(arbre)
    L=[]
    for k in range(1,taille+1):
        L.append(arbre.leaves[1-position[-k]].root)
        arbre=arbre.leaves[position[-k]]
    return(L)

#m est la valeur du nième élément de la liste
def retrouverroot(path,m,n):
    m=truevalue(m)
    h=hashage(m)
    position=inttobinary(n,len(path))
    for k in range(1,len(path)+1):
        if position[k-1]==0:
            h=hashlib.sha256(h+path[-k]).digest()
        else:
            h=hashlib.sha256(path[-k]+h).digest()
    return(h)   
    
merkle=create_merkle_from_list([Field(0),Field(1),Field(2),Field(3),Field(3),Field(5),Field(6),Field(7)])
for k in range(8):
    r=retrouverroot(authentification_path(merkle,k),Field(k),k)
    print(merkle.root==r)
# def position(arbre,m):
#     arbre_bis=arbre
#     h=hashage(truevalue(m))
#     n=taille_arbre(arbre)
#     position=[0]*n
#     for k in range(2**n):
#         L=inttobinary(k,arbre)
#         print(L)
#         i=1
#         while arbre_bis.leaves!=[]:
#             arbre_bis=arbre_bis.leaves[L[-i]]
#             i=i+1
#         print(arbre_bis.root)
#         print(h)
#         if arbre_bis.root==h:
#             return(L)
