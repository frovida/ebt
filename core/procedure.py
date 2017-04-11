import params
import world_model as wm
import logger.logger as log
from behavior_trees import *
from copy import deepcopy
from copy import copy
import conditions as cond
from collections import defaultdict 
from sets import Set
import sys


class ProcedurePreempted(Exception):
     def __init__(self, value):
         self.value = value
     def __str__(self):
         return repr(self.value)

class ProcedureBase:
    def getDescription(self):
        return (self._type, self._params, self._pre_conditions, self._hold_conditions, self._post_conditions)
        
    def setDescription(self, typein, paramsin, prein, holdin, postin):
        self._type = copy(typein) 
        self._params = deepcopy(paramsin)
        self._pre_conditions = deepcopy(prein)
        self._hold_conditions = deepcopy(holdin)
        self._post_conditions = deepcopy(postin)
        
    def createDescription(self):
        """ Not implemented in abstract class. """
        return
        
    def addParam(self, key, value, param_type, options=[], description=""):     
        self._params.addParam(key, value, param_type, description)
        if type(value) == type(wm.Element()):
            for o in options:
                if o == params.ParamOptions.Consume:
                    self._post_conditions += [self.getGenerateCond("Consume"+key, key, False)] 
                elif o == params.ParamOptions.Unspecify:
                    self._post_conditions += [self.getIsSpecifiedCond("Unset"+key, key, False)]
                elif o == params.ParamOptions.Lock:
                    self._pre_conditions += [self.getPropCond(key+'Idle', "StateProperty", key, "Idle", True)]
                    self._hold_conditions += [self.getPropCond(key+'Busy', "StateProperty", key, "Idle", False)]
                    self._post_conditions += [self.getPropCond(key+'Idle', "StateProperty", key, "Idle", True)]
           
    def generateDefParams(self):
        """
        Some default params are added automatically
        """
        if not self._params.hasParam('Robot'):
            self._params.addParam("Robot", wm.Element("Agent"), params.ParamTypes.System)
        #if not self._params.hasParam('Skill'):
        #    self._params.addParam("Skill", self.toElement(), params.ParamTypes.System)
        
    def generateDefConditions(self):
        """
        Some default preconditions are added automatically
        """
        #self.addPreCondition(self.getRelationCond("HasSkill", "hasSkill", "Robot", "Skill", True))
        #for key, param in self._params.getParamMapFiltered(params.ParamTypes.Hardware).iteritems():
        #    self.addPreCondition(self.getPropCond("DeviceIdle", "deviceState", key, "Idle", True))
        for key, param in self._params.getParamMapFiltered([params.ParamTypes.Online, params.ParamTypes.Offline]).iteritems():
            if param.valueType() == type(wm.Element()): 
                c1 = self.getIsSpecifiedCond("Has"+key, key, True)                   
                dont_add = False
                for c2 in self._pre_conditions:
                    if c1.isEqual(c2):
                        dont_add = True
                if not dont_add: self.addPreCondition(c1)
        for key, param in self._params.getParamMapFiltered(params.ParamTypes.Optional).iteritems():
            if param.valueType() == type(wm.Element()):
                c1 = self.getGenerateCond("Has"+key, key, True)                   
                dont_add = False
                for c2 in self._post_conditions:
                    if c1.isEqual(c2) or c1.hasConflict(c2):
                        dont_add = True
                if not dont_add: self._post_conditions = [c1] + self._post_conditions
        return True
        
    def addPreCondition(self, condition):
        self._pre_conditions.append(condition)
        
    def addHoldCondition(self, condition):
        self._hold_conditions.append(condition)
            
    def addPostCondition(self, condition):
        self._post_conditions.append(condition)
        
    def getIsSpecifiedCond(self, clabel, subj, desired_state):
        return cond.ConditionIsSpecified(clabel, subj, desired_state)
        
    def getGenerateCond(self, clabel, subj, desired_state):
        return cond.ConditionGenerate(clabel, subj, desired_state)
        
    def getHasPropCond(self, clabel, olabel, subj, desired_state):
        return cond.ConditionHasProperty(clabel, olabel, subj, desired_state)
        
    def getPropCond(self, clabel, olabel, subj, value, desired_state):
        return cond.ConditionProperty(clabel, olabel, subj, value, desired_state)
        
    def getRelationCond(self, clabel, olabel, subj, obj, desired_state):
        return cond.ConditionRelation(clabel, olabel, subj, obj, desired_state)
        
    def getOnTypeCond(self, clabel, subj, value):
        return cond.ConditionOnType(clabel, subj, value)
        
    def getModifiedParams(self):
        param_list = set([])
        for c in self._post_conditions:
            #if isinstance(c, cond.ConditionGenerate):
            param_list = param_list.union(set(c.getKeys()))
        return param_list
        
    def printInfo(self, verbose=False):
        s = "{}".format(self._type) 
        if verbose:
            s += "["
            s += self._params.printState() + ']\n'
            s += self.printConditions()
        return s
        
    def printConditions(self):
        s = "PreConditions:\n"
        for c in self._pre_conditions:
            s += '{}\n'.format(c._description)
        s += "PostConditions:\n"
        for c in self._post_conditions:
            s += '{}\n'.format(c._description)   
        return s
    
    def toElement(self):
        to_ret = wm.Element(self._type)
        return to_ret
    
class ProcedureDescription(ProcedureBase, object):
    def __init__(self):
        #Description
        self._type=""
        #Params
        self._params=params.ParamHandler()
        #Conditions
        self._pre_conditions=[]
        self._hold_conditions=[]
        self._post_conditions=[]
        self.createDescription()
        self.generateDefParams()
        self.generateDefConditions()
        
                
        
class ProcedureInterface(ProcedureBase):
    """
    """    
    #--------Class functions--------   
    def __init__(self, children_processor=Serial()):
        #Description
        self._type=""
        self._label=""
        self._description = ProcedureDescription()
        #Params
        self._params=params.ParamHandler()
        self._remaps={}
        #Conditions
        self._pre_conditions=[]
        self._hold_conditions=[]
        self._post_conditions=[]
        #Connections
        self._parent = None
        self._children=[] 
        self._children_processor = children_processor 
        #Execution
        self._priority=0
        self._state=State.Uninitialized
        self._state_change = CEvent()
        self._progress=0
        self._preempt_request = CEvent()
        self._was_simulated = False
        #Caches
        self._max_cache = 2
        self._params_cache = []
        self._input_cache = []
        self._remaps_cache = defaultdict(list)
                   
    def getLightCopy(self):
        """
        Makes a light copy (only description, params and state)
        """
        p = self.__class__(self._children_processor)
        p._children_processor = deepcopy(self._children_processor)
        p._type=copy(self._type)
        p._label=copy(self._label)
        p._params = deepcopy(self._params)
        p._remaps = deepcopy(self._remaps)
        p._description = deepcopy(self._description)
        p._pre_conditions = deepcopy(self._pre_conditions)
        p._hold_conditions = deepcopy(self._hold_conditions)
        p._post_conditions = deepcopy(self._post_conditions)
        if self._state!=State.Uninitialized:
            p._state = copy(self._state)
            p._wm = self._wm            
        return p
        
    def step(self):
        if self.verifyPreempt():
            raise ProcedurePreempted("")
        self._progress += 1
        #print '[{}:{}]'.format(self._label, self._progress)
                   
    def setState(self, state):
        self._state = state  
        self._state_change.set()

    def getParamsNoRemaps(self):
        ph = params.ParamHandler()
        ph.reset(self._params.getCopy())
        for r1, r2 in self._remaps.iteritems():
            ph.remap(r2, r1)
        return ph
            
    def clearRemaps(self):
        """
        Clear remaps
        """
        for r1, r2 in reversed(self._remaps.iteritems()):
            self.remap(r2, r1)
        self._remaps={}
        self._remaps_cache={}
            
    def copyRemaps(self, procedure):
        """
        Copy the remaps of another procedure. Called automatically when the procedure is added as a child
        """
        for r1, r2 in procedure._remaps.iteritems():
            self.remap(r1, r2)
        
    def remap(self, initial_key, target_key, record=True):
        """
        Remap a parameter to a new key
        """
        #log.error(self._label, "remap {} {} {}".format(self, initial_key, target_key))
        if self._remaps.has_key(initial_key):
            if self._remaps[initial_key]==target_key:#Redundant
                #log.warn(self._label, "Ignoring redundant remap {}->{}".format(initial_key, target_key))
                return
            else:
                #log.warn(self._label, "Key {} already remapped to {}. Can t remap to {}".format(initial_key, self._remaps[initial_key], target_key))
                return
        if self._remaps.has_key(target_key):
            #log.warn(self._label, "Ignoring circular remap {}->{}".format(initial_key, target_key))
            return
            
        if self._params.hasParam(target_key):
            log.error(self._label, "Key {} already present in the map, remapping can shadow a parameter.".format(target_key))
            return 
        for c in self._children:
            c.remap(initial_key, target_key)
        #Remaps
        self._params.remap(initial_key, target_key)
        for c in self._pre_conditions:
            c.remap(initial_key, target_key)
        for c in self._hold_conditions:
            c.remap(initial_key, target_key)
        for c in self._post_conditions:
            c.remap(initial_key, target_key)
        #Records
        if record:
            self._remaps[initial_key] = target_key
            remapid = len(self._params_cache)
            if remapid>0: #If I have params cached, I cache also the remap to revert it afterwards
                self._remaps_cache[remapid].append((initial_key, target_key))
            
            
    def _revertRemaps(self):
        """
        Revert remaps. Just used in revertInput
        """
        remapid = len(self._params_cache)
        try:
            if self._remaps_cache[remapid]:
                for remap in self._remaps_cache[remapid]:
                    log.warn("REMAP", "Revert {} {}".format(remap[0], remap[1]))
                    print self._remaps_cache
                    self._remaps.pop(remap[0])
                    self.remap(remap[1], remap[0], False)
                del self._remaps_cache[remapid]
        except:
            print self.printInfo(True)
            print self._remaps_cache
            raise
            
    def init(self, wm):
        self._wm = wm
        self.createDescription()
        self.setState(State.Idle)
                      
    def inSubtreeOf(self, procedure):
        if self in procedure._children:
            return True
        for c in procedure._children:
            if self.inSubtreeOf(c):
                return True
        return False
            
    def hold(self):
        for c in self._hold_conditions:
            if not c.setTrue(self._params, self._wm):
                log.error(c.getDescription(), "Hold failed.")
                return False
        return True
        
    def revertHold(self):
        for c in reversed(self._hold_conditions):
            #print c.getDescription()
            if not c.revert(self._params, self._wm):
                log.error(c.getDescription(), "Revert hold failed.")
                return False
        self._was_simulated = False
        return True
        
    def simulate(self):
        self._was_simulated = True
        #print "Simulate: {}".format(self.printInfo(True))
        for c in self._post_conditions:
            if not c.setTrue(self._params, self._wm):
                log.error(c.getDescription(), "Simulation failed.")
                return False
        return True
            
    def revertSimulation(self):
        if not self._was_simulated:
            log.warn("revert", "No simulation was made, can't revert.")
            return False
        for c in reversed(self._post_conditions):
            if not c.revert(self._params, self._wm):
                log.error(c.getDescription(), "Revert failed.")
                return False
        self._was_simulated = False
        return True
        
    def start(self, input_params=None):
        #if self._state==State.Active:
            #print 'Waiting idle mode..'
            #self.waitState(State.Active, False)
        if input_params != None:          
            self._params.setParams(input_params, False)
        self.setState(State.Active)
        self._progress = 0
        result = False
        #try:
        result = self.execute()
        if not result:
            self.setState(State.Error)
        #except RuntimeError:
        #    self.setState(State.Error)
        #    log.error(self._label, "Runtime error during execution.")
        #except ProcedurePreempted:
        #    self.setState(State.Preempted)
        #    log.warn(self._label, "Preempted start")
        #except:
        #    e = sys.exc_info()[0]
        #    log.error(self._label, e)
        #finally:
        if input_params != None:          
            input_params.setParams(self._params, False)
        return result
                
    def end(self, input_params=None):
        try:
            if self.verifyPreempt():
                raise ProcedurePreempted("")
            if input_params != None:          
                self._params.setParams(input_params, False)
            result = self.postExecute()
            if not result:
                self.setState(State.Error)
        except RuntimeError:
            self.setState(State.Error)
            log.error(self._label, "Runtime error during post-execution.")
            result = False
        except ProcedurePreempted:
            self.setState(State.Preempted)
            log.warn(self._label, "Preempted end")
            result = False
        finally:
            #if input_params != None:          
            #    input_params.setParams(self._params, False)
            self.setState(State.Completed) 
            return result
        
    def preempt(self):
        if self._state==State.Active:
            self._preempt_request.set()
            self.onPreempt()
            for c in self._children:
                c.preempt()

    def waitState(self, state, isset=True):
        if isset:#Xor?
            while self._state!=state:
                #print 'Waiting set.. {}'.format(self._state)
                self._state_change.clear()
                self._state_change.wait()
        else:
            while self._state==state:
                #print 'Waiting not set.. {}'.format(self._state)
                self._state_change.clear()
                self._state_change.wait()
        #print 'State changed {}'.format(self._state)
            
    
    def verifyPreempt(self):
        if self._preempt_request.is_set():
            self._preempt_request.clear()
            return True
        return False
        
    def visit(self, visitor):
        return visitor.process(self)
        
    def printInfo(self, verbose=False):
        s = "{}-{} ".format(self._type,self._label) 
        if verbose:
            s += "["
            s += self._params.printState() + ']\n'
            s += self.printConditions()
            s += "Remaps: \n"
            for r1, r2 in self._remaps.iteritems():
                s += r1+"->"+r2
        else:
            s += "\n"
        return s
        
    def printState(self, verbose=False):
        s = "{}".format(self._label)
        if verbose:
            if self.hasInstance(): 
                if self._children:
                    s += "({})".format(self._children_processor.printType()) 
                #s += "({})".format(self._state) 
                s += "[{}]".format(self._params.printState()) 
                #s += "\n[Remaps: {}]".format(self._remaps)  
                #s += "[Remaps cache: {}]".format(self._remaps_cache)
                #s += "[{}]".format(self.getModifiedParams()) 
            else:
                s += "({})".format('abstract') 
        return s
                         
    def getParent(self):
        return self._parent
        
    def hasChildren(self):
        return len(self._children)>0        
        
    def addChild(self, p, latch=False):
        if isinstance(p, list):
            for i in p:
                i._parent = self
                self._children.append(i)
                i.copyRemaps(self)
        else:
            p._parent = self
            self._children.append(p)
            p.copyRemaps(self)
        if latch and len(self._children)>1:
            for c in self._children[-2]._post_conditions:
                for key in c.getKeys():
                    if not p._params.hasParam(key):
                        p._params._params[key] = deepcopy(self._children[-2]._params._params[key])
            p._pre_conditions += deepcopy(self._children[-2]._post_conditions)
        return self
        
    def last(self):
        return self._children[-1]
          
    def popChild(self):
        child = self._children.pop()
        child._parent = None
        
    def specify(self, key, values):
        """
        Specify a value and set it as default value too
        """
        self._params.specifyDefault(key, values)
        
    def specifyInput(self, key, values):
        """
        Specify a parameter and update the input cache
        """
        self.specify(key, values)
        if self._input_cache:
            if key in self._input_cache[-1]:
                self._input_cache[-1][key].setValues(values)
                
    def specifyParams(self, input_params):
        """
        Set the parameters and makes them default (they will no more be overwritten by setInput)
        """
        self._params_cache.append(self._params.getCopy())
        self._input_cache.append(input_params.getCopy())             
        self._params.specifyParams(input_params)
        
    def setInput(self, input_params):
        """
        Set the parameters. Params already specified with specifyInputs are preserved
        """
        self._params_cache.append(self._params.getCopy())
        self._input_cache.append(input_params.getCopy())
        input_copy = params.ParamHandler()
        input_copy.reset(input_params.getCopy())
        for k, p in self._params.getParamMap().iteritems():
            v = p.getDefaultValue()
            if isinstance(v, wm.Element) and input_copy.hasParam(k):
                if v._id>0 and p.getValue()._id!=input_copy.getParamValue(k)._id:
                    input_copy.specify(k, v)                
        self._params.setParams(input_copy)
        #Erase the oldest cache if the max lenght is reached
        if len(self._params_cache)>self._max_cache:
            self._popCache()
            
    def _popCache(self):
        self._params_cache.pop(0)
        for i in range(self._max_cache+1):
            if not self._remaps_cache.has_key(i):     
                continue
            del self._remaps_cache[i]
            if self._remaps_cache.has_key(i+1):
                self._remaps_cache[i] = self._remaps_cache[i+1]
    
    def revertInput(self):
        if not self._params_cache:
            log.warn("revertInput", "No cache available, can't revert input.")
            return None
        self._revertRemaps()
        self._params.reset(deepcopy(self._params_cache.pop()))
        return deepcopy(self._input_cache.pop())
    
    def hasPreCond(self):
        if self._pre_conditions:
            return True
        else:
            return False
    
    def checkPreCond(self, verbose=False):
        """
        Check pre-conditions. Return a list of parameters that breaks the conditions, or an empty list if all are satisfied
        """
        to_ret = Set()
        for c in self._pre_conditions:
            if not c.evaluate(self._params, self._wm):
                if verbose:
                    log.error(c.getDescription(), "ConditionCheck failed")
                for key in c.getKeys():
                    to_ret.add(key)
        return list(to_ret)
         
    def hasPostCond(self):
        if self._post_conditions:
            return True
        else:
            return False
            
    def checkPostCond(self, verbose=False):
        """
        Check post-conditions. Return a list of parameters that breaks the conditions, or an empty list if all are satisfied
        """
        to_ret = []
        for c in self._post_conditions:
            if not c.evaluate(self._params, self._wm):
                if verbose:
                    log.error(c.getDescription(), "ConditionCheck failed")
                to_ret += c.getKeys()
        return to_ret
                
    #--------User functions--------
    def setChildrenProcessor(self, processor):
        self._children_processor = processor
        
    def setType(self, description):   
        """
        Description is a ProcedureDescription
        """
        self._description = description
        self._type = description._type        
        self.resetDescription()
        
    def resetDescription(self, other=None):
        if other:
            self._params.reset(self._description._params.merge(other._params))
        else:
            self._params = deepcopy(self._description._params)
        self._pre_conditions = deepcopy(self._description._pre_conditions)
        self._hold_conditions = deepcopy(self._description._hold_conditions)
        self._post_conditions = deepcopy(self._description._post_conditions)
        self._children = []
        
    def mergeDescription(self, other):
        self.resetDescription(other)
        for c in other._pre_conditions:
            if not c in self._pre_conditions:
                self.addPreCondition(c)
        for c in other._hold_conditions:
            if not c in self._hold_conditions:
                self.addHoldCondition(c)
        for c in other._post_conditions:
            if not c in self._post_conditions:
                self.addPostCondition(c)                
                       
    def addPreCondition(self, condition):
        self._pre_conditions.append(condition)
        for r1, r2 in self._remaps.iteritems():
            self._pre_conditions[-1].remap(r1, r2)
        
    def addHoldCondition(self, condition):
        self._hold_conditions.append(condition)
        for r1, r2 in self._remaps.iteritems():
            self._hold_conditions[-1].remap(r1, r2)
            
    def addPostCondition(self, condition):
        self._post_conditions.append(condition)
        for r1, r2 in self._remaps.iteritems():
            self._post_conditions[-1].remap(r1, r2)  
        
    def processChildren(self, visitor):
        """
        """
        if self._children_processor.processChildren(self._children, visitor):
            return True
        else:
            self.setState(State.Error)
            return False
        
    #--------Virtual functions--------        
    def execute(self):
        """ Override for different execution """
        return self._instance(self._params)
        
    def postExecute(self):
        """ Optional, Not implemented in abstract class. """
        return True
        
    def onPreempt(self):
        """ Optional, Not implemented in abstract class. """
        return True
        
    def hasInstance(self):
        """ Wrapper procedures override this """
        return True
                   
        
class ProcedureInstance(ProcedureInterface, object):     
    def getLightCopy(self):
        """
        Makes a light copy (only description, params and state)
        """
        p = self.__class__(self._children_processor)
        p._children_processor = deepcopy(self._children_processor)
        p._type=self._type
        p._label=self._label
        p._params = deepcopy(self._params)
        p._remaps = deepcopy(self._remaps)
        p._description = deepcopy(self._description)
        p._pre_conditions = deepcopy(self._pre_conditions)
        p._hold_conditions = deepcopy(self._hold_conditions)
        p._post_conditions = deepcopy(self._post_conditions)
        if self._state!=State.Uninitialized:
            p._state = self._state
            p._wm = self._wm       
            p._instanciator = self._instanciator  
        return p       
        
    def init(self, wmi, instanciator):
        self._wm = wmi
        self._instanciator = instanciator
        self.createDescription()
        self.generateDefParams()
        self._children_processor = Serial()
        if self.onInit():
            self.setState(State.Idle)
            self.generateDefConditions()
                                    
    def onInit(self):
        """ Optional, Not implemented in abstract class. """
        return True
       
    def createDescription(self):
        """ Not implemented in abstract class. """
        raise NotImplementedError("Not implemented in abstract class")
        
    def expand(self, procedure):
        """ 
            Optional, Not implemented in abstract class. 
            Expand the subtree. 
        """
        return
    
    def execute(self, input_params):
        """ Not implemented in abstract class. """
        raise NotImplementedError("Not implemented in abstract class")
        
    def getProcedure(self, ptype, plabel, priority=0, prec=[], postc=[]):
        """
        Return a procedure wrapper initialized.
        
        It is possible to add more pre and post conditions (that gets added to the initial ones)
        """
        p = ProcedureWrapper(ptype, plabel, priority, self._instanciator)
        for c in prec:
            p.addPreCondition(c)
        for c in postc:
            p.addPostCondition(c)
        return p
        
  
class NodeInstanciator():
    def __init__(self, wmi):
        self._available_descriptions={}  
        self._available_instances=defaultdict(list)   
        self._wm = wmi
        
    def createDescription(self, ptype):
        procedure = ptype()
        self._available_descriptions[procedure._type] = procedure
        return procedure
        
    def createInstance(self, pclass):
        procedure = pclass()
        procedure.init(self._wm, self)
        if not procedure._type in self._available_descriptions:
            self._available_descriptions[procedure._type] = self._makeDescription(procedure)
        self._available_instances[procedure._type].append(procedure)
        return procedure
        
    def _makeDescription(self, procedure):
        to_ret = ProcedureDescription()
        to_ret.setDescription(*procedure.getDescription())
        return to_ret
        
    def expandAll(self):
        for _, ps in self._available_instances.iteritems():
            for p in ps:
                p.expand(p)
            
    def assignDescription(self, procedure):
        """
        Assign a description to an abstract procedure.
        """
        if procedure._type in self._available_descriptions:
            procedure.init(self._wm)
            procedure.setType(self._available_descriptions[procedure._type])
        else:
            log.error("assignDescription", "No instances of type {} found.".format(procedure._type))
        
    def getInstances(self, ptype):
        return self._available_instances[ptype]
        
    def assignInstance(self, procedure):
        """
        Assign an instance to an abstract procedure. If an instance with same label is not found, assign the first instance of the type
        """
        to_set = None
        first_cycle = True
        for p in self._available_instances[procedure._type]:
            if first_cycle:
                first_cycle = False
                to_set = p
            if p._label == procedure._label:
                to_set = p
        if to_set != None:
            procedure.setInstance(to_set)
        else:
            log.error("assignInstance", "No instances of type {} found.".format(procedure._type))
        
    def printState(self, verbose=True, filter_type=""):
        s = 'Descriptions:\n'
        for t, p in self._available_descriptions.iteritems():
            if p._type==filter_type or filter_type=="":
                s += p.printInfo(verbose)
                s += '\n'
        s += '\nInstances:\n'
        for k, l in self._available_instances.iteritems():
            for p in l:
                if p._type==filter_type or filter_type=="":
                    s += p.printInfo(verbose)
                    s += '\n'
        return s

class ProcedureWrapper(ProcedureInterface):
    def __init__(self, ptype, plabel, priority=0, instanciator=None):
        #Connections
        self._parent = None
        self._children=[]  
        #Description
        self._type=ptype
        self._label=plabel
        self._priority=0
        #Params
        self._params=params.ParamHandler()
        self._remaps={}
        #Conditions
        self._pre_conditions=[]
        self._hold_conditions=[]
        self._post_conditions=[]
        #Execution
        self._preempt_request = CEvent()
        self._state=State.Uninitialized
        self._state_change = CEvent()
        self._has_instance = False
        self._children_processor = Serial()
        if instanciator:
            instanciator.assignDescription(self)
        #Caches
        self._max_cache = 2
        self._params_cache = []
        self._input_cache = []
        self._remaps_cache = defaultdict(list)
                               
    def getLightCopy(self):
        """
        Makes a light copy (only description and params)
        """
        p = ProcedureWrapper(self._type, self._label, self._priority)
        p._params = deepcopy(self._params)
        p._remaps = deepcopy(self._remaps)
        p._description = deepcopy(self._description)
        p._pre_conditions = deepcopy(self._pre_conditions)
        p._hold_conditions = deepcopy(self._hold_conditions)
        p._post_conditions = deepcopy(self._post_conditions)
        if self._has_instance:
            p._has_instance=self._has_instance
            p._instance=self._instance
        if self._state!=State.Uninitialized:
            p._state = copy(self._state)
            p._wm = self._wm            
        return p
        
    def hasInstance(self):
        return self._has_instance
        
    def setInstance(self, instance):
        """
        instance must be a ProcedureInstance
        
        All the execution parts get redirected to the instance.
        
        Instance can change at run-time, but the description will remain fixed
        """
        if self._has_instance:
            self.resetDescription()
        self._instance = instance
        self._has_instance = True   
        self._wm = instance._wm
        instance.expand(self)
                                    
    def getInstance(self):
        return self._instance
        
    def _copyInstanceParams(self):
        self._params.setParams(self._instance._params, False)
        for k, p in self._instance._params._params.iteritems():#Hack to get remapped key back
            if k in self._remaps:
                self._params.specify(self._remaps[k], p.getValues())
        
    def execute(self):
        #print '{}:{}'.format(self._label, self._instance)
        result = self._instance.start(self.getParamsNoRemaps())
        self._copyInstanceParams()
        if not result:
            self.setState(self._instance._state)
        return result
    
    def postExecute(self):
        result = self._instance.end(self.getParamsNoRemaps())
        self._copyInstanceParams()
        if not result:
            self.setState(self._instance._state)
        return result
        
    def onPreempt(self):
        self._instance.preempt()
        
      
class Root(ProcedureInterface): 
    def __init__(self, name, wm=None):
        #Connections
        self._parent = None
        self._children=[]  
        #Description
        self._type="Root"
        self._label=name
        self._priority=0
        self._description = ProcedureDescription()
        #Params
        self._params=params.ParamHandler()
        self._remaps={}
        #Conditions
        self._pre_conditions=[]
        self._hold_conditions=[]
        self._post_conditions=[]
        #Execution
        self._preempt_request = CEvent()
        self._state=State.Uninitialized
        self._state_change = CEvent()
        self._has_instance = False
        self._params_cache = []
        self._input_cache = []
        self._max_cache = 2
        self._children_processor = Serial()
        self._remaps_cache = defaultdict(list)
        if wm:
            self.init(wm)
        
    def createDescription(self):
        return        
        
    def hasInstance(self):
        return True
        
    def execute(self):
        return True
        
class Procedure(ProcedureInterface): 
    def __init__(self, name, children_processor=Serial(),wm=None):
        #Connections
        self._parent = None
        self._children=[]  
        #Description
        self._type="Procedure"
        self._label=name
        self._priority=0
        self._description = ProcedureDescription()
        #Params
        self._params=params.ParamHandler()
        self._remaps={}
        #Conditions
        self._pre_conditions=[]
        self._hold_conditions=[]
        self._post_conditions=[]
        #Execution
        self._preempt_request = CEvent()
        self._state=State.Uninitialized
        self._state_change = CEvent()
        self._has_instance = False
        self._max_cache = 2
        self._children_processor = children_processor
        if wm:
            self.init(wm)
        #Cache
        self._params_cache = []
        self._input_cache = []
        self._remaps_cache = defaultdict(list)
        
    def createDescription(self):
        return        
        
    def hasInstance(self):
        return True
        
    def execute(self):
        return True