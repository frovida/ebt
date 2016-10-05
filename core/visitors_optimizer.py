from visitors import *
            
class VisitorOptimizer(VisitorInterface, NodePrinter, NodeReversibleSimulator):
    """
    Simulate the execution back and fort to find an optimized execution sequence, then revert the simulation.
    
    The optimized execution sequence get stored, and can be retrieved with 'getExecutionSequence'
    """
    def __init__(self, wmi, instanciator):
        #Execution
        self._simulate=True
        self._verbose=False
        self._state=State.Idle
        self._preempt_request = Event()
        self._prefix = "->"
        self._indend = 0       
        self._wm = wmi
        self._instanciator = instanciator
        self._stack = []
        self._tracked_params = []
        self._params=params.ParamHandler()
        self._processor = Serial()
        self.forward = NodeMemorizer('Forward')
        self.back = NodeMemorizer('Backward')
              
    def setVerbose(self, verbose):
        self._verbose=verbose
        
    def checkRules(self, p1, p2):
        """
        Return true if the 3 rules are respected:
            Rule 1: preconditions have to hold
            Rule 2: can-t go before a procedure with inverse postconditions
            Rule 3: parent preconditions involving params of child have to hold
        """
        #Rule 1: preconditions have to hold
        if p1.checkPreCond(self._verbose):
            return False
        #Rule 2: can-t go before a procedure with conflicting conditions
        for c1 in p1._post_conditions:
            for c2 in p2._post_conditions:
                if c1.hasConflict(c2):
                    if self._verbose:
                        print c1.getDescription() + " has conflict with " + c2.getDescription()
                    return False
        for c1 in p1._hold_conditions:
            for c2 in p2._pre_conditions:
                if c1.hasConflict(c2):
                    if self._verbose:
                        print c1.getDescription() + " has conflict with " + c2.getDescription()
                    return False
        #Rule 3: parent preconditions involving params of child have to hold as well
        if p1.inSubtreeOf(p2):
            if self._verbose:
                print p1._label + ' is child of ' + p2._label 
            for c2 in p2._pre_conditions:
                if [key for key, _ in p1._params.getParamMap().iteritems() if key in c2.getKeys()]:
                    dont_add = False
                    for c1 in p1._pre_conditions:
                        if c1.isEqual(c2):
                            dont_add = True
                    if dont_add: continue
                    if self._verbose:
                        print 'Add precond: ' + c2.getDescription()
                    p1.addPreCondition(c2)
                    for key in c2.getKeys():
                        if not p1._params.hasParam(key):
                            p1._params.getParamMap()[key] = p2._params.getParamMap()[key]
        return True
                
        
    def processNode(self, procedure):
        if not self.execute(procedure, False): #Execute, without registering in the memory, to initialize the procedure
            log.error('Execute failed')
            print self.printParams(procedure._params)
            return False
        self.printProcedure(procedure)

        if not procedure.checkPostCond() and procedure.hasPostCond():
            log.info('discarded','Redundand procedure {}'.format(procedure._label))
            return True
        if self._verbose:
            print '==Undo until possible=='
        if procedure.hasPreCond():
            while self.undo():
                #log.info('',str(self._params.getParamMap()))
                procedure.setInput(self._params)
                #print self.printParams(procedure._params)
                if not self.checkRules(procedure, self.back.recall()[0]):
                    self.redo()
                    break
        if self._verbose:
            print '==Swap with neighbors parents=='
        while self.back.recall() and procedure.inSubtreeOf(self.back.recall()[0]):
            if not self.redo():
                log.error('Redo failed')
                print self.printParams(procedure._params)
                return False
        if self._verbose:
            print '==Insert procedure=='
        if not self.execute(procedure):
            log.error('Execute failed')
            print self.printParams(procedure._params)
            return False
        #if self._verbose:
        #    print '==Redo all=='
        #self.redoAll()   
        #self.forward.printMemory()     
        self.indend()
        return True
        
    def checkRule4(self, procedure):
        """
        Return true if the rule 4 is respected:
            Rule 4: procedure doesn-t interfere with subsequent procedure's preconditions
        """
        if not self.postExecute(procedure):
            raise
        if not self.back.hasMemory():
            return True
        if not self.redo():
            self.erase()
            return False
        return True
        
    def processChildren(self, procedure):
        """ Use serial processor always """
        return self._processor.processChildren(procedure._children, self)
        
    
    def postProcessNode(self, procedure):
        if not procedure.checkPostCond() and procedure.hasPostCond():
            log.info('discarded','Redundand procedure {}'.format(procedure._label))
            return True
        if self._verbose:
            print '==Redo until rule 4 is satisfied=='
        while not self.checkRule4(procedure):
            self.redo()
        if self._verbose:
            print '==Insert procedure end=='
        #if not self.postExecute(procedure):
        #    return False
        if self._verbose:
            print '==Redo all=='
        self.redoAll()   
        self.unindend()
        return True
    
    def processingDone(self, procedure):
        self._execution_sequence = deepcopy(self.forward)
        self._execution_sequence._name = "Optimized execution sequence"
        if not self.undoAll():
            return False
        return True
    
    def getExecutionSequence(self):
        return self._execution_sequence     
        
class VisitorOptimizer2(VisitorInterface, NodePrinter, NodeReversibleSimulator):
    """
    Simulate the execution back and fort to find an optimized execution sequence, then revert the simulation.
    
    The optimized execution sequence get stored in a new behaviour tree, and can be retrieved with 'getExecutionTree'
    """
    def __init__(self, wmi, instanciator):
        #Execution
        self._simulate=True
        self._verbose=False
        self._state=State.Idle
        self._preempt_request = Event()
        self._prefix = "->"
        self._indend = 0       
        self._wm = wmi
        self._instanciator = instanciator
        self._stack = []
        self._tracked_params = []
        self._params=params.ParamHandler()
        self._processor = Serial()
        self.forward = NodeMemorizer('Forward')
        self.back = NodeMemorizer('Backward')
        self._execution_branch = []
        self._forget_branch = []
        self.visitor = VisitorPrint(self._wm, self._instanciator)
        self._bound = {}
       
            
    def setVerbose(self, verbose):
        self._verbose=verbose
        
    def checkRules(self, p1, p2):
        """
        Return true if the 3 rules are respected:
            Rule 1: preconditions have to hold
            Rule 2: can-t go before a procedure with inverse postconditions
            Rule 3: parent preconditions involving params of child have to hold
        """
        #Rule 1: preconditions have to hold
        if p1.checkPreCond(self._verbose):
            return False
        #Rule 2: can-t go before a procedure with conflicting conditions
        for c1 in p1._post_conditions:
            for c2 in p2._post_conditions:
                if c1.hasConflict(c2):
                    if self._verbose:
                        print c1.getDescription() + " has conflict with " + c2.getDescription()
                    return False
        for c1 in p1._hold_conditions:
            for c2 in p2._pre_conditions:
                if c1.hasConflict(c2):
                    if self._verbose:
                        print c1.getDescription() + " has conflict with " + c2.getDescription()
                    return False
        #Rule 3: node moving out of its parent. preconditions involving params of child have to hold as well
        if p1.inSubtreeOf(p2):
            if self._verbose:
                print p1._label + ' is child of ' + p2._label 
            for c2 in p2._pre_conditions:
                if [key for key, _ in p1._params.getParamMap().iteritems() if key in c2.getKeys()]:
                    dont_add = False
                    for c1 in p1._pre_conditions:
                        if c1.isEqual(c2):
                            dont_add = True
                    if dont_add: continue
                    if self._verbose:
                        print 'Add precond: ' + c2.getDescription()
                    p1.addPreCondition(c2)
                    for key in c2.getKeys():
                        if not p1._params.hasParam(key):
                            p1._params.getParamMap()[key] = p2._params.getParamMap()[key]
        return True
                
        
    def processNode(self, procedure):
        if not self.execute(procedure, False): #Execute, without registering in the memory, to initialize the procedure
            log.error('Execute failed')
            print self.printParams(procedure._params)
            return False
        #self.printProcedure(procedure)

        if not procedure.checkPostCond() and procedure.hasPostCond():
            log.info('discarded','Redundand procedure {}'.format(procedure._label))
            return True
        if self._verbose:
            print '==Undo until possible=='
        processor=None
        if procedure.hasPreCond():
            while self.undo():
                #log.info('',str(self._params.getParamMap()))
                procedure.setInput(self._params)
                #print self.printParams(procedure._params)
                if not self.checkRules(procedure, self.back.recall()[0]):
                    self.redo()
                    #print self.printParams(self.forward.recall()[0]._params)                    
                    processor=Serial
                    break
        if self._verbose:
            print '==Swap with neighbors parents=='
        while True:
            if not self.back.recall():
                break
            if not procedure.inSubtreeOf(self.back.recall()[0]) and self.back.recall()[1]!='postExecute':
                break
            if not self.redo():
                log.error('Redo failed')
                print self.printParams(procedure._params)
                return False
            processor=None
        if self._verbose:
            print '==Insert procedure=='
        if not self.execute(procedure, processor=processor):
            log.error('Execute failed')
            print self.printParams(procedure._params)
            return False
        #if self._verbose:
        #    print '==Redo all=='
        #self.redoAll()   
        #self.forward.printMemory()     
        self.indend()
        return True
        
    def checkRule4(self, procedure):
        """
        Return true if the rule 4 is respected:
            Rule 4: procedure doesn-t interfere with subsequent procedure's preconditions
        """
        if not self.postExecute(procedure):
            raise
        if not self.back.hasMemory():
            return True
        if not self.redo(Parallel):
            self.erase()
            return False
        return True
        
    
    def processChildren(self, procedure):
        """ Use serial processor always """
        return self._processor.processChildren(procedure._children, self)
        
    def postProcessNode(self, procedure):
        if not procedure.checkPostCond() and procedure.hasPostCond():
            log.info('discarded','Redundand procedure {}'.format(procedure._label))
            return True
        if self._verbose:
            print '==Redo until rule 4 is satisfied=='
        while not self.checkRule4(procedure):
            self.redo()
        if self._verbose:
            print '==Insert procedure end=='
        #if not self.postExecute(procedure):
        #    return False
        if self._verbose:
            print '==Redo all=='
        self.redoAll()   
        self.unindend()
        #self.visitor.traverse(self.getExecutionRoot())
        return True
    
    def processingDone(self, procedure):
        self.freezeExecutionTree()
        if not self.undoAll():
            return False
        return True    