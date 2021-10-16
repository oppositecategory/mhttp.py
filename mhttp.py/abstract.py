from abc import abstractmethod, ABC 



class Base():
    def __init__(self, a, b):
        self.a = a 
        self.b = b 

    def compute(self):
        print(self.a+self.b)

    
class Derived(Base):
    def __init__(self,a,b):
        super().__init__(a,b)
        
    def compute(self):
        super().compute()
        print("But in the derived class.")
    

x = Derived(1,1)
x.compute()


class mHTTPProtocol(ABC):
    def __init__(self):
        pass
    