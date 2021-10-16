from abc import abstractmethod, ABC 



class A():
    def __init__(self, a):
        self.a = a 

class B():
    def __init__(self, b):
        self.b = b 

class C(A,B):
    def __init__(self, a, b):
        A.__init__(self,a)
        B.__init__(self,b)
    
    def print(self):
        print(f'a: {self.a}, b: {self.b}')
        
    

    

x = C(1,3)
x.print()
