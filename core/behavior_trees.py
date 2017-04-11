from multiprocessing.dummy import Process, Value, Event, Lock
from flufl.enum import Enum 
from copy import copy, deepcopy

State = Enum('State', 'Uninitialized Idle Active Preempted Error Completed') 

class CEvent:
    """
    An event that can be copied
    """
    def __init__(self):
        self.event = Event()
        
    def set(self):
        self.event.set()
        
    def is_set(self):
        return self.event.is_set()
        
    def clear(self):
        self.event.clear()
        
    def wait(self, timeout=None):
        self.event.wait(timeout)
        
    def __copy__(self):
        c = CEvent()
        if self.event.is_set():
            c.event.set()
        return c
    
    def __deepcopy__(self, memo):
        result = self.__copy__()
        memo[id(self)] = result
        return result

class Barrier:
    def __init__(self):
        self.mutex = Lock()
        self.event = Event()
        self.target = 1
        self.counter = 0
    
    def reset(self, target):
        self.target = target
        self.counter = 0
    
    def signal(self):
        self.mutex.acquire()
        print self.counter
        self.counter += 1
        self.mutex.release()
        self.event.set()
    
    def wait(self, timeout=None):
        self.event.wait(timeout)
        self.event.clear()
        return self.counter >= self.target

class Serial():
    def printType(self):
        return '->'
        
    def processChildren(self, children, visitor):
        """
        Serial executor - return on first fail, or return success
        """
        for c in children:
            if not c.visit(visitor):
                return False
        return True
         
    
class Parallel():
    def printType(self):
        return '||'
        
    def processChildren(self, children, visitor):
        """
        Parallel executor - return on first fail, or return success
        """
        result = Value('b', True)
        barrier = Barrier()
        processes = []
        barrier.reset(len(children))
        for c in children:
            processes.append(Process(target=Parallel.processChild, args=(self, c, visitor, result, barrier,)))
            processes[-1].daemon = True
            processes[-1].start()
        try:
            while not barrier.wait():
                pass
        except KeyboardInterrupt:
            return self.stop(children)
        return result.value
    
    def stop(self, children): 
        for c in children:
            c.preempt()
        #for c in children:
        #    c.waitState(State.Active, False)
        return False   
    
    def processChild(self, child, visitor, result, barrier):
        if not child.visit(visitor):
            result.value = False
        barrier.signal() 
        
class Selector():         
    def processChildren(self, children, visitor):
        """
        Selector executor - return on first success, or return fail
        """
        for c in children:
            if c.visit(visitor):
                return True
        return False
        
#Decorators
        
class Loop():    
    def __init__(self, processor):
        self._processor = processor
        
    def printType(self):
        return 'Loop({})'.format(self._processor.printType())
        
    def processChildren(self, children, visitor):
        """
        Repeat execution
        """
        while True:
            if not self._processor.processChildren(children, visitor):
                return False
        return True
        
class NoFail():   
    def __init__(self, processor):
        self._processor = processor
        
    def printType(self):
        return 'NoFail({})'.format(self._processor.printType())
        
    def processChildren(self, children, visitor):
        """
        Ignore failed execution
        """
        self._processor.processChildren(children, visitor)
        return True

class DecoratorSync():  
    def __init__(self, processor):
        self._processor = processor
        
    def processChildren(self, children, visitor):
        """
        Repeat execution
        """
        self._processor.processChildren(children, visitor)
        return True
      