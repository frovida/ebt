from procedure import *
import logger.logger as log
from sets import Set
import numpy as np

class NodePrinter():
    def __init__(self):
        self._prefix = "->"
        self._indend = 0
        
    def setPrefix(self, prefix):
        self._prefix = prefix + "->"
        
    def indend(self):
        self._indend += 2
        
    def unindend(self):
        self._indend -= 2
    
    def printProcedure(self, procedure, verbose=True):
        s = "-"*self._indend + self._prefix + procedure.printState(verbose)
        #s+=self.printParams(procedure._params)
        print s
        #procedure.printConditions()
        
    def printParams(self,  params):
        to_ret = "\n"
        for _, p in params.getParamMap().iteritems():
            if p.valueType() == type(wm.Element()):
                to_ret += p._key + ": "
                for e in p.getValues():
                    to_ret += e.printState() + "\n" 
            else:               
                to_ret += p.printState() + "\n"
        return to_ret
    
class NodeExecutor():
    def __init__(self, wmi, instanciator):
        self._wm = wmi
        self._simulate=False
        self._verbose=False
        self._tracked_params = []
        self._params=params.ParamHandler()
        self._instanciator = instanciator
    
    def trackParam(self, key):
        self._tracked_params.append(key)        

    def _printTracked(self): 
        for key in self._tracked_params:
            if self._params.hasParam(key):
                print key + ' ' + self._params.getParamValue(key).printState()
            else:
                print key + ' not available.'  
                
    def setSimulate(self, sim=True):
        self._simulate=sim
        
    def setParams(self, input_params):
        self._params.reset(input_params) 
        self._printTracked()
        
    def mergeParams(self, procedure):
        self._params.reset(self._params.merge(procedure._params)) 
        self._printTracked()
        
    def inferUnvalidParams(self, procedure):
        #print '{}: {} '.format(procedure._label, self.printParams(procedure._params))
        unvalid_params = procedure.checkPreCond()
        if unvalid_params:
            #log.info("[{}] Reset unvalid params {}".format(procedure._label, unvalid_params))
            procedure._params.setDefault(unvalid_params)
            return self.autoParametrizeBB(procedure) 
        return True
        
    def autoParametrizeBB(self, procedure):
        """
        Ground undefined parameters with parameters in the Black Board
        """              
        to_resolve = [key for key, param in procedure._params.getParamMap().iteritems() if param.paramType()!=params.ParamTypes.Optional and param.valueType()==type(wm.Element()) and param.getValue()._id < 0]
        if not to_resolve:
            return True
        remap = {}
        cp = params.ParamHandler()
        cp.reset(procedure._params.getCopy())
        for c in procedure._pre_conditions:
            c.setDesiredState(cp)
        for key in to_resolve:
            remap[key] = []
            for k, p in self._params._params.iteritems():
                if p.valueTypeIs(wm.Element()):
                    if p.getValue().isInstance(cp.getParamValue(key), self._wm):
                        remap[key].append(k)
                        
        l = np.zeros(len(to_resolve), dtype=int)
        unvalid_params = to_resolve
        loop = True
        while loop:
            loop = False
            #Set params and check preCond
            for index, key in enumerate(to_resolve):
                #print '{}: {}'.format(key, remap[key])
                if not remap[key]:
                    return self.autoParametrizeWm(procedure, to_resolve, cp)
                procedure._params.specify(key, self._params.getParamValues(remap[key][l[index]]))
            unvalid_params = procedure.checkPreCond()
            #If there are unvalid params, increment 1 of the counters. Loop breaks when all counters are at last element
            for key in unvalid_params:
                if key in to_resolve:
                    if l[to_resolve.index(key)]<len(remap[key])-1:
                        l[to_resolve.index(key)] += 1
                        loop = True
                        break
                    else:
                        l[to_resolve.index(key)] = 0
        if unvalid_params:
            return self.autoParametrizeWm(procedure, to_resolve, cp)
        remapped = ''
        for index, key in enumerate(to_resolve):
            if key != remap[key][l[index]]:
        #        procedure.remap(key, remap[key][l[index]])
                remapped += "[{}={}]".format(key, remap[key][l[index]])
        log.info("MatchBB","{}: {}".format(procedure._label, remapped))
        return True
        
    def autoParametrizeWm(self, procedure, to_resolve, cp):
        """
        Ground undefined parameters with elements in the world model
        """       
        matches = self._wm.resolveElements(to_resolve, cp)
        grounded = ''
        for key, match in matches.iteritems():
            if match.any():
                if isinstance(key, tuple):
                    for i, key2 in enumerate(key):
                        procedure._params.specify(key2, match[0][i]) 
                        grounded += '[{}:{}]'.format(key2, match[0][i].printState())
                else:
                    procedure._params.specify(key, match[0])
                    grounded += '[{}:{}]'.format(key, match[0].printState())
            else: 
                print '{}: {}'.format(procedure._label, to_resolve)
                log.error("autoParametrizeWm", "Can t autoparametrize param {}.".format(key))
                return False
        log.info("Ground", "{}: {}".format(procedure._label, grounded))
        return True
    
    def init(self, procedure):
        if not procedure.hasInstance():
            self._instanciator.assignInstance(procedure)
            
    def ground(self, procedure):
        self.autoParametrizeBB(procedure)
        if not self.inferUnvalidParams(procedure):
            return False
        if procedure.checkPreCond(True):
            return False
        return True
    
    def tryOther(self, procedure):
        used = [procedure._label]
        #if self._verbose:
        for i in self._instanciator.getInstances(procedure._type):
            if not i._label in used:
                log.info("Try different procedure {}".format(procedure._label))
                used.append(i._label)
                procedure._label = i._label
                procedure.setInstance(i)
                if self.ground(procedure):
                    return True
        return False
                
    def _execute(self, procedure):
        if self._simulate:
            return True
        else:
            return procedure.start()
        
    def execute(self, procedure):
        self.init(procedure)
        procedure.setInput(self._params)
        if self._verbose:
            log.info("Execute {}".format(procedure._label))
        if not self.ground(procedure):
            if not self.tryOther(procedure):
                return False
        procedure.hold()
        if not self._execute(procedure):
            return False
        self.mergeParams(procedure)#Update params
        return True
    
    def _postExecute(self, procedure):
        if self._simulate:
            return procedure.simulate()#Set post-cond to true
        else:
            return procedure.end()
        
    def postExecute(self, procedure):
        procedure.setInput(self._params)#Re-apply parameters, after processing the sub-tree.... Important!
        if self._verbose:
            log.info("postExecute {}".format(procedure._label))
        if not self._postExecute(procedure):
            return False
        self.mergeParams(procedure)#Update params
        return True

       
class NodeMemorizer:
    def __init__(self, name):
        self._name = name
        self._tree = []
        self._verbose = True

    def _debug(self, msg):
        if self._verbose:
            log.info(self._name, msg)

    def hasMemory(self):
        return len(self._tree)>0
    
    def memorize(self, procedure, tag):
        #self._debug("Memorize " + procedure.printInfo(False))
        self._tree.append((procedure, tag))
        
    def recall(self, index=None):
        if self._tree:
            if index and abs(index)<len(self._tree):
                return self._tree[index]
            return self._tree[-1]
            
    def forget(self):
        if self._tree:
            procedure = self._tree.pop()
            #self._debug("Forget " + procedure[0].printInfo(False))
            return procedure   
        
    def printMemory(self):
        print self._name + ":"
        for p in self._tree:
            print p[0].printState() + '-' + p[1]
        
class TreeBuilder:
    def __init__(self, wmi):
        self._wm = wmi
        self._execution_branch = []
        self._forget_branch = []
                  
    def removeExecutionNode(self):
        if self._execution_branch:
            parent = self._execution_branch[-1].getParent()
            if parent:
                parent.popChild()
            return self._execution_branch.pop()
        
    def restoreExecutionNode(self):
        if self._forget_branch:
            self._execution_branch.append(self._forget_branch.pop())
        
    def popExecutionNode(self):
        self._forget_branch.append(self._execution_branch.pop())
        
    def addExecutionNode(self, procedure):
        p = deepcopy(procedure)
        p._children = []
        parent = self.getExecutionParent()
        self._execution_branch.append(p)
        if parent:
            parent.addChild(p)
        
    def getExecutionParent(self):
        if self._execution_branch:
            return self._execution_branch[-1]
        
    def getPrevious(self):
        if not self._forget_branch:
            return None
        else:
            return self._forget_branch[-1]

    def previousParentIsSameWithWrongProcessor(self, processor):
        parent = self.getExecutionParent()
        previous = self.getPrevious()
        if previous:
            if previous.getParent() == parent:
                if not isinstance(parent._children_processor, processor):
                    return True
        return False
            
    def getExecutionRoot(self):
        return self._execution_root
        
    def freezeExecutionTree(self):
        self._forget_branch = []
            

class NodeReversibleSimulator(NodeExecutor, TreeBuilder):
    def __init__(self):
        self._simulate=True
        self.forward = NodeMemorizer('Forward')
        self.back = NodeMemorizer('Backward')
        self._execution_branch = []
        self._forget_branch = []
        self._bound = {}
        
    def addInExecutionTree(self, procedure, processor=Serial):        
        if not self._execution_branch:
            self.addExecutionNode(procedure)
            self._execution_root = self._execution_branch[0]
            return
        if processor!=None and self.previousParentIsSameWithWrongProcessor(processor):
            #Else wrap the previous and the current into a node with the right processor
            print '{} wants {}, parent is {}'.format(procedure._label, processor().printType(), self.getExecutionParent()._label)
            self.undoPrevious()
            pp = Procedure(processor().printType(), processor(), self._wm)
            self.execute(pp)
            self.redoPrevious()
            self.parametrize(procedure)
            self.addExecutionNode(procedure)
            self._bound[id(procedure)] = pp
        else:
            self.addExecutionNode(procedure)        
        
    def erase(self):
        self.undo()
        self.back.forget()

    def undoPrevious(self):        
        procedure = self.forward.recall()[0]
        self.undo()
        while procedure!=self.forward.recall()[0]:
            self.undo()
        self.undo()
        
    def redoPrevious(self):        
        procedure = self.back.recall()[0]
        self.redo()
        while procedure!=self.back.recall()[0]:
            self.redo()
        self.redo()
        
    def undo(self):
        if not self.forward.hasMemory():
            return False
        procedure, tag = self.forward.forget()
        if self._verbose:
            log.info("undo", "{}-{}".format(procedure._label, tag))
        if tag=='execute':
            self.revert(procedure)
        elif tag=='postExecute':
            self.postRevert(procedure)
        self.back.memorize(procedure, tag)
        return True
    
    def undoAll(self):
        while self.forward._tree:
            if not self.undo():
                return False
        return True
        
    def redo(self, processor=None):
        if not self.back.hasMemory():
            return False
        procedure, tag = self.back.recall()
        if tag=='execute':
            if self.execute(procedure, processor=processor):
                self.back.forget()
                return True
            else:
                return False
        elif tag=='postExecute':
            if self.postExecute(procedure):
                self.back.forget()
                return True
            else:
                return False
        
    def redoAll(self):
        while self.back.hasMemory():
            if not self.redo():
                return False
        return True
    
    def parametrize(self, procedure):
        procedure.setInput(self._params)#No execution...
        if not self.ground(procedure):
            if not self.tryOther(procedure):
                return False
        if not self._execute(procedure):
            return False    
        return True
    
    def execute(self, procedure, remember=True, processor=Serial):
        self.init(procedure)
        procedure.setInput(self._params)#No execution...
        if not self.parametrize(procedure):
            return False
        if remember:
            self.addInExecutionTree(procedure, processor) 
            procedure.hold()
            self.mergeParams(procedure)#Update params
            self.forward.memorize(procedure, "execute")
        if self._verbose:
            log.info("Execute {}".format(procedure._label))
        return True
    
    def revert(self, procedure):
        procedure.revertHold()
        self.setParams(procedure.revertInput())
        self.removeExecutionNode()
        return True
    
    
    def postExecute(self, procedure):
        procedure.setInput(self._params)#Re-apply parameters, after processing the sub-tree.... Important, thay have been modified by the subtree!
        if self._verbose:
            log.info("postExecute {}".format(procedure._label))
        if not self._postExecute(procedure):
            return False
        self.mergeParams(procedure)#Update params
        self.forward.memorize(procedure, "postExecute")
        self.popExecutionNode()
        if id(procedure) in self._bound:
            self.postExecute(self._bound.pop(id(procedure)))
        return True
    
    def postRevert(self, procedure):
        if not procedure.revertSimulation():
            log.error("undo", "Can't revert {}".format(procedure.printState()))
            return False 
        self.setParams(procedure.revertInput())
        self.restoreExecutionNode() 
        #print 'miei ' + self.printParams(procedure._params)
        return True
         
        
               