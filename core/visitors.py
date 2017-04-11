from procedure_utils import *

class VisitorInterface:
    """
    Base interface for visitors
    """    
    #--------Class functions--------   
    def __init__(self):
        #Execution
        self._state=State.Idle
        self._preempt_request = Event()
 
    def preempt(self):
        self._preempt_request.set()
        
    def verifyPreempt(self, procedure):
        if self._preempt_request.is_set():
            self._preempt_request.clear()
            procedure.preempt()
            self.setState(State.Preempted)
            return True
        return False                
        
    def setState(self, state):
        self._state = state  
        
    def traverse(self, root):
        self.onStart(root)
        self.setState(State.Active)
        if not root.visit(self):
            self.processingDone(root)
            self.setState(State.Error)
            return False
        if not self.processingDone(root):
            self.setState(State.Error)
            return False
        self.setState(State.Completed)
        return True
    
    def process(self, procedure):
        #Process node
        if self.verifyPreempt(procedure):
            return False
        if not self.processNode(procedure):
            self.setState(State.Error)
            return False
        #Process children
        if self.verifyPreempt(procedure):
            return False
        if not self.processChildren(procedure):
            self.setState(State.Error)
            return False
        if self.verifyPreempt(procedure):
            return False
        #Post-process node
        if not self.postProcessNode(procedure):
            self.setState(State.Error)
            return False
        #End
        self.setState(State.Completed)
        return True            
        
    def processNode(self, procedure):
        """ Not implemented in abstract class. """
        raise NotImplementedError("Not implemented in abstract class")

    def processChildren(self, procedure):
        """ Use the processor embedded in the procedure """
        return procedure.processChildren(self)
        
    def postProcessNode(self, procedure):
        """ Not implemented in abstract class. """
        raise NotImplementedError("Not implemented in abstract class")
        
    def onStart(self, procedure):
        """ Optional - Not implemented in abstract class. """
        return True
        
    def processingDone(self, procedure):
        """ Optional - Not implemented in abstract class. """
        return True
       
class VisitorPrint(VisitorInterface, NodePrinter, NodeExecutor):
    """
    Print the whole procedure tree
    """    
    def __init__(self, wmi, instanciator):
        #Execution
        self._state=State.Idle
        self._preempt_request = Event()  
        self._verbose=False
        self._wm = wmi
        self._instanciator = instanciator
        self._processor = Serial()
        self._prefix = "->"
        self._indend = 0        
        
    def setVerbose(self, verbose):
        self._verbose=verbose
        
    def processNode(self, procedure):
        self.init(procedure)
        self._procedure_printed = self._procedure_printed + self.printProcedure(procedure, self._verbose) + "\n"
        self.indend()
        return True
        
    def processChildren(self, procedure):
        """ Use serial processor always """
        return self._processor.processChildren(procedure._children, self)
        
    def postProcessNode(self, procedure):
        self.unindend()
        return True
        
    def onStart(self, procedure):
        self._procedure_printed = ""
        return True
    
    def getPrint(self):
        return self._procedure_printed
    
class VisitorExecutor(VisitorInterface, NodePrinter, NodeExecutor):
    """
    Simulate the procedure execution
    """
    def __init__(self, wmi, instanciator):
        #Execution
        self._simulate=False
        self._verbose=False
        self._state=State.Idle
        self._preempt_request = Event()
        self._prefix = "->"
        self._indend = 0       
        self._wm = wmi
        self._stack = []
        self._tracked_params = []
        self._instanciator = instanciator
        self._params=params.ParamHandler()
        
    def setVerbose(self, verbose):
        self._verbose=verbose
              
    def processNode(self, procedure):
        if not self.execute(procedure):
            self.printProcedure(procedure)
            log.error(procedure._label, "Failed")
            return False  
        self.printProcedure(procedure)      
        self.indend()
        return True
        
    def postProcessNode(self, procedure):
        self.postExecute(procedure)
        self.unindend()
        return True
                      
class VisitorReversibleSimulator(VisitorInterface, NodePrinter, NodeReversibleSimulator):
    """
    Simulate the procedure execution and revert the simulation
    """
    def __init__(self, wmi, instanciator):
        #Execution
        self._simulate=True
        self._verbose=False
        self._stack = []
        self._tracked_params = []
        self._state=State.Idle
        self._preempt_request = Event()
        self._prefix = "->"
        self._indend = 0       
        self._wm = wmi
        self._instanciator = instanciator
        self._params=params.ParamHandler()
        self.forward = NodeMemorizer('Forward')
        self.back = NodeMemorizer('Backward')
        self._execution_branch = []
        self._forget_branch = []
        self.visitor = VisitorPrint(self._wm, self._instanciator)
        self._bound = {}
              
    def setVerbose(self, verbose):
        self._verbose=verbose
        
    def processNode(self, procedure):
        if not self.execute(procedure):
            return False
        self.printProcedure(procedure)
        self.indend()
        return True
        
    def postProcessNode(self, procedure):
        if not self.postExecute(procedure):
            return False
        self.unindend()
        self.visitor.traverse(self.getExecutionRoot())
        return True
    
    def processingDone(self, procedure):
        if not self.undoAll():
            return False
        self.back.printMemory()
        return True
        
