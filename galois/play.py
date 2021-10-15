from abc import ABC, abstractmethod


class A(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def func(self):
        print('yay')

    @abstractmethod 
    def func1(self):
        pass 

class B(A):
    def __init__(self):
        super().__init__()
    
    def func(self):
        pass

    def func1(self):
        print("B")

    
b = B()
b.func()




