import params
import world_model as wm
import logger.logger as log
from behavior_trees import *
from copy import deepcopy
from copy import copy
import conditions as cond
from collections import defaultdict 
from sets import Set


class ProcedurePreempted(Exception):
     def __init__(self, value):
         self.value = value
     def __str__(self):
         return repr(self.value)

class ProcedureBase:
    def getDescription(self):
        return (self._type, self._params, self._pre_conditions, self._hold_conditions, self._post_conditions)
        
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
                    self._pre_conditions += [self.getPropCond(key+'Idle', "deviceState", key, "Idle", True)]
                    self._hold_conditions += [self.getPropCond(key+'Busy', "deviceState", key, "Idle", False)]
                    self._post_conditions += [self.getPropCond(key+'Idle', "deviceState", key, "Idle", True)]
           
    def generateDefParams(self):
        """
        Some default params are added automatically
        """
        if not self._params.hasParam('Robot'):
            self._params.addParam("Robot", wm.Element("Agent"), params.ParamTypes.System)
        #self._params.addParam("Skill", self.toElement(), params.ParamTypes.System)
        
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
        s = "{}\n".format(self._type) 
        if verbose:
            s += self._params.printState() + '\n'
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
        
                
        
class ProcedureInterface(ProcedureBase):
    """
    """    
    #--------Class functions--------   
    def __init__(self, children_processor=Serial):
        #Description
        self._type=""
        self._label=""
        self._description = ProcedureDescription()
        #Params
        self._params=params.ParamHandler()
        #Conditions
        self._pre_conditions=[]
        self._hold_conditions=[]
        self._post_conditions=[]
        #Connections
        self._parent = None
        self._children=[]  
        #Execution
        self._priority=0
        self._state=State.Uninitialized
        self._state_change = CEvent()
        self._progress=0
        self._preempt_request = CEvent()
        self._has_instance = False
        self._params_cache = []
        self._input_cache = []
        self._max_cache = 2
        self._was_simulated = False
        self._children_processor = children_processor
        self._remaps={}
                   
    def step(self):
        if self.verifyPreempt():
            raise ProcedurePreempted("")
        self._progress += 1
        print '[{}:{}]'.format(self._label, self._progress)
                   
    def setState(self, state):
        self._state = state  
        self._state_change.set()

    def clearRemaps(self):
        """
        Clear remaps
        """
        for remap in self._remaps:
            self.remap(remap[1], remap[0])
        self._remaps={}
            
    def copyRemaps(self, procedure):
        """
        Copy the remaps of another procedure. Called automatically when the procedure is added as a child
        """
        for r1, r2 in procedure._remaps.iteritems():
            self.remap(r1, r2)
        
    def remap(self, initial_key, target_key):
        """
        Remap a parameter to a new key
        """
        self._remaps[initial_key] = target_key
        self._params.remap(initial_key, target_key)
        for c in self._pre_conditions:
            c.remap(initial_key, target_key)
        for c in self._hold_conditions:
            c.remap(initial_key, target_key)
        for c in self._post_conditions:
            c.remap(initial_key, target_key)
        for c in self._children:
            c.remap(initial_key, target_key)
        
            
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
        for c in self._post_conditions:
            #print c.getDescription()
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
        if self._state==State.Active:
            print 'Waiting idle mode..'
            self.waitState(State.Active, False)
        if input_params != None:          
            self._params.setParams(input_params)
        self.setState(State.Active)
        self._progress = 0
        try:
            result = self.execute()
            if not result:
                self.setState(State.Error)
        except RuntimeError:
            self.setState(State.Error)
            log.error(self._label, "Runtime error during execution.")
            result = False
        except ProcedurePreempted:
            self.setState(State.Preempted)
            log.warn(self._label, "Preempted start")
            result = False
        finally:
            if input_params != None:          
                input_params.setParams(self._params)
            return result
                
    def end(self, input_params=None):
        try:
            if self.verifyPreempt():
                raise ProcedurePreempted("")
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
            if input_params != None:          
                input_params.setParams(self._params)
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
        s = "{}-{}\n".format(self._type,self._label) 
        if verbose:
            s += self._params.printState() + '\n'
            s += self.printConditions()
        return s
        
    def printState(self, verbose=False):
        s = "{}".format(self._label)
        if verbose:
            if self.hasInstance(): 
                if self._children:
                    s += "({})".format(self._children_processor.printType()) 
                #s += "({})".format(self._state) 
                #s += "[{}]".format(self._params.printState()) 
                #s += "[{}]".format(self.getModifiedParams()) 
            else:
                s += "({})".format('abstract') 
        return s
        
    def specify(self, key, values):
        """
        Specify a value and set it as default value too
        """
        self._params.specifyDefault(key, values)
                 
    def getParent(self):
        return self._parent
        
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
        
    def specifyInput(self, key, values):
        """
        Specify a parameter and update the input cache
        """
        self.specify(key, values)
        if self._input_cache:
            if key in self._input_cache[-1]:
                self._input_cache[-1][key].setValues(values)
        
    def setInput(self, input_params):
        self._params_cache.append(self._params.getCopy())
        self._input_cache.append(input_params.getCopy())
        #Online params already specified are preserved
        for k, p in self._params.getParamMap().iteritems():
            v = p.getDefaultValue()
            #if(k=='PlacingCell'): print '{} {}'.format(p.valueType(), isinstance(p.getValue(), wm.Element))
            if isinstance(v, wm.Element) and input_params.hasParam(k):
                #if(k=='PlacingCell'): print '{}: {} {}'.format(k, p.getValue()._id, input_params.getParamValue(k)._id)
                if v._id>0 and p.getValue()._id!=input_params.getParamValue(k)._id:
                    input_params.specify(k, v)                
        self._params.setParams(input_params)
        #Erase the oldest cache if the max lenght is reached
        if len(self._params_cache)>self._max_cache:
            self._params_cache.pop(0)
    
    def revertInput(self):
        if not self._params_cache:
            log.warn("revertInput", "No cache available, can't revert input.")
            return None
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
        
    def resetDescription(self):
        self._params = deepcopy(self._description._params)
        self._pre_conditions = deepcopy(self._description._pre_conditions)
        self._hold_conditions = deepcopy(self._description._hold_conditions)
        self._post_conditions = deepcopy(self._description._post_conditions)
        self._children = []
                       
    def addPreCondition(self, condition):
        self._pre_conditions.append(condition)
        for remap in self._remaps:
            self._pre_conditions[-1].remap(remap[0], remap[1])
        
    def addHoldCondition(self, condition):
        self._hold_conditions.append(condition)
        for remap in self._remaps:
            self._hold_conditions[-1].remap(remap[0], remap[1])
            
    def addPostCondition(self, condition):
        self._post_conditions.append(condition)
        for remap in self._remaps:
            self._post_conditions[-1].remap(remap[0], remap[1])        
        
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
        return self._has_instance
        
    def setInstance(self, instance):
        """
        instance must be a function. This will be executed when calling execute()
        """
        self._instance = instance
        self._has_instance = True     
    
        
class ProcedureInstance(ProcedureInterface, object):                
    def init(self, wmi, instanciator):
        self._wm = wmi
        self._instanciator = instanciator
        self.createDescription()
        self.generateDefParams()
        self._children_processor = Serial()
        self._remaps={}
        if self.onInit():
            self.setState(State.Idle)
            self.generateDefConditions()
                    
    def hasInstance(self):
        return True
        
    def toElement(self):
        to_ret = wm.Element(self._type, self._label)
        #Todo:add params, etc.
        return to_ret
        
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
            self._available_descriptions[procedure._type] = procedure
        self._available_instances[procedure._type].append(procedure)
        return procedure
        
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
        
    def printState(self, verbose=True):
        s = 'Procedures:\n'
        for t, p in self._available_descriptions.iteritems():
            s += p.printInfo(verbose)
        s += 'Instances:\n'
        for k, l in self._available_instances.iteritems():
            for p in l:
                s += p.printInfo(verbose)
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
        self._params_cache = []
        self._input_cache = []
        self._max_cache = 2
        self._children_processor = Serial()
        instanciator.assignDescription(self)
                    
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
        
    def execute(self):
        #print '{}:{}'.format(self._label, self._instance)
        result = self._instance.start(self._params)
        if not result:
            self.setState(self._instance._state)
        return result
    
    def postExecute(self):
        result = self._instance.end(self._params)
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
        if wm:
            self.init(wm)
        
    def createDescription(self):
        return        
        
    def hasInstance(self):
        return True
        
    def execute(self):
        return True
        
class Operator(ProcedureInterface): 
    def __init__(self, wmi=None):
        #Connections
        self._parent = None
        self._children=[]  
        #Description
        self._priority=0
        #Params
        self._params=params.ParamHandler()
        self._remaps={}
        #Conditions
        self._pre_conditions=[]
        self._hold_conditions=[]
        self._post_conditions=[]
        #Execution
        self._state=State.Uninitialized
        self._has_instance = False
        self._params_cache = []
        self._input_cache = []
        self._max_cache = 2
        self._children_processor = Serial()
        if wmi:
            self.init(wmi)
                  
    def simulate(self):
        self._was_simulated = True
        return self.execute()
            
    def revertSimulation(self):
        if not self._was_simulated:
            log.warn("revert", "No simulation was made, can't revert.")
            return False
        return self.revertExecute()
        
    def hasInstance(self):
        return True
        
    def createDescription(self):
        return        
        
    def execute(self):
        """ Not implemented in abstract class. """
        raise NotImplementedError("Not implemented in abstract class")
        
    def revertExecute(self):
        """ Not implemented in abstract class. """
        raise NotImplementedError("Not implemented in abstract class")
    
class ground(Operator):
    def __init__(self, wmi, parameters, conditions):
        #Connections
        self._parent = None
        self._children=[]  
        #Description
        self._type="Function"
        self._label='ground'
        self._priority=0
        #Params
        self._params=params.ParamHandler()
        self._params.reset(parameters.getCopy())
        self._remaps={}
        #Conditions
        self._pre_conditions=[]
        self._post_conditions=[]
        #Execution
        self._state=State.Uninitialized
        self._has_instance = False
        self._params_cache = []
        self._input_cache = []
        self._max_cache = 2
        self._children_processor = Serial()
        if wmi:
            self.init(wmi)
        #More
        self._conditions = conditions
        self._copy = params.ParamHandler()
            
    def createDescription(self):
        return        
        
    def execute(self):        
        to_resolve = [key for key, param in self._params.getParamMap().iteritems() if param.paramType()!=params.ParamTypes.Optional and param.valueType()==type(wm.Element()) and param.getValue()._id < 0]
        if not to_resolve:
            return        
        self._copy.reset(self._params.getCopy())
        for c in self._conditions:
            c.setDesiredState(self._params) 
        matches = self._wm.resolveElements(to_resolve, self._params)
        grounded = ''
        for key, match in matches.iteritems():
            if match.any():
                if isinstance(key, tuple):
                    for i, key2 in enumerate(key):
                        self._params.specify(key2, match[0][i]) 
                        grounded += match[0][i].printState() + ' '
                else:
                    self._params.specify(key, match[0])
                    grounded += match[0].printState() + ' '
            else: 
                log.warn("ground", "Can t ground param {} with {}.".format(key, self._params.getParamValue[key].printState()))
                return False
        log.info("Grounding: " + str(to_resolve) + grounded)
        return True
        
    def revertExecute(self):
        self._params.reset(self._copy.getCopy())
        return True
                   
class swap(Operator):
    def createDescription(self):
        self._type="Function"
        self._label='swap'
        self._params.addParam("Left", wm.Element("Thing"), params.ParamTypes.Online)
        self._params.addParam("Right", wm.Element("Thing"), params.ParamTypes.Online)
        return        
        
    def execute(self):
        key1=self._remaps["Left"]
        key2=self._remaps["Right"]
        left = self._params.getParamValues(key1)
        right = self._params.getParamValues(key2)
        self._params.specify(key1, right)
        self._params.specify(key2, left)
        return True
        
    def revertExecute(self):
        key1=self._remaps["Left"]
        key2=self._remaps["Right"]
        left = self._params.getParamValues(key1)
        right = self._params.getParamValues(key2)
        self._params.specify(key1, right)
        self._params.specify(key2, left)
        return True
        
class copy(Operator):
    def createDescription(self):
        self._type="Function"
        self._label='copy'
        self._params.addParam("From", wm.Element("Thing"), params.ParamTypes.Online)
        self._params.addParam("To", wm.Element("Thing"), params.ParamTypes.Online)
        return        
        
    def execute(self):
        key1=self._remaps["From"]
        key2=self._remaps["To"]
        copy = self._params.getParamValues(key1)
        self.old = self._params.getParamValues(key2)
        self._params.specify(key2, copy)
        return True
        
    def revertExecute(self):
        key2=self._remaps["To"]
        self._params.specify(key2, self.old)
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
        self._children_processor = children_processor
        if wm:
            self.init(wm)
        
    def createDescription(self):
        return        
        
    def hasInstance(self):
        return True
        
    def execute(self):
        return True