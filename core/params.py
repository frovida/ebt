        
from enum import Enum 
import numpy as np
from copy import deepcopy
import logger.logger as log

"""
Online: are specified in input at run-time
Offline: are specified in input a-priory
Hardware: are specified in input at run-time
Config: like offline, but constant
Optional: not mandatory in input, get specified in output
System: added automatically
"""
ParamTypes = Enum('ParamTypes', 'Online Offline Hardware Config Optional System Discrete')
"""
Consume: (postCondition) unspecify and remove from world model 
Unspecify: (postCondition) unspecify
"""
ParamOptions = Enum('ParamOptions', 'Consume Unspecify Lock')  

class Param:
    """
    """
    def __init__(self, key, description, value_type, param_type):            
        self._key=key          
        self._description=description   
        self._param_type=param_type
        if isinstance(value_type, list):
            self._default = value_type
            self._values = value_type
            self._value_type = type(value_type[0])
        else:
            self._default = [value_type]
            self._value_type=type(value_type)
            self._values = [value_type]
    
    def getDefaultValue(self, index=0):
        return self._default[index]
        
    def getDefaultValues(self):
        return self._default
        
    def hasDefaultValues(self):
        for v1, v2 in zip(self._default, self._values):
            if v1!=v2: return False
        return True
            
    def makeDefault(self, values):
        self._default = self._values
            
    def resetToDefault(self):
        #print 'Set to: ' + self._default[0].printState()
        self._values = self._default        
    
    def key(self):
        return self._key
        
    def description(self):
        return self._description
        
    def valueType(self):
        return self._value_type
        
    def valueTypeIs(self, vtype):
        return self._value_type == type(vtype)
        
    def paramType(self):
        return self._param_type  
        
    def paramTypeIs(self, ptype):
        return self._param_type == ptype
        
    def setValues(self, value):
        if isinstance(value, list):
            if isinstance(value[0], self._value_type):
                self._values = value
            else: 
                log.error("setValues", str(value[0])+"!="+str(self._value_type))
        elif isinstance(value, self._value_type):
            self._values = [value]
        else: 
            log.error("setValues", str(value)+"!="+str(self._value_type))

    def find(self, value):
        for v in enumerate(self._values):
            if v[1] == value:
                return v[0]
        return -1                
            
    def append(self, value):
        self._values.append(value)
        
    def remove(self, index):
        del self._values[index]
            
    def getValue(self, index=0):
        return self._values[index]
        
    def getValues(self):
        return self._values
        
    def getValuesStr(self):
        return str(self._values)
        
    def printState(self):
        to_ret = self._key + ":" 
        for s in self._values:
            to_ret += str(s)
        return to_ret
     
class ParamHandler:
    """
    """
    def __init__(self):
        self._params={}

    def reset(self, copy):
        self._params=copy

    def getCopy(self):
        return deepcopy(self._params)
        
    def getParamMap(self):
        return self._params

    def merge(self, other):
        """
        Return the parameter map, result of the merge between self and another ParameterHandler 
        """
        to_ret = self.getCopy()
        for key, param in other._params.iteritems():
            if self.hasParam(key):
                to_ret[key].setValues(param.getValues())
            else:
                to_ret[key] = param
        return to_ret
        
    def remap(self, initial_key, target_key):
        """
        Remap a parameter to a new key
        """
        if self.hasParam(initial_key):
            #print self.printState()
            temp = self._params[initial_key]
            temp._key = target_key
            self._params[target_key] = temp
            del self._params[initial_key]
            #print 'after ' + self.printState()

    def setParams(self, other, keep_offline=True):
        """
        Set the input params
        """
        for key, param in other._params.iteritems():
            if self.hasParam(key):
                t = self._params[key]
                if not keep_offline or (t.paramType()!=ParamTypes.Offline and t.paramType()!=ParamTypes.Config):
                    t.setValues(param.getValues())
        
    def hasParam(self, key):
        """
        Check that a key exists and return false otherwise
        """
        if key in self._params:
            return True
        else:
            return False

    def setDefault(self, key):
        """
        Set the param (or the params, if key is a list) to the default value
        """
        if isinstance(key, list):
            for k in key:
                self._params[k].resetToDefault()
        else:
            self._params[key].resetToDefault()
        
    def addParam(self, key, value, param_type, description=""):
        self._params[key] = Param(key, description, value, param_type)
                    
    def getParam(self, key):
        if self.hasParam(key):
            return self._params[key]
        else:
            log.error('getParam', 'Param {} is not in the map.'.format(key))
            print self.printState()
        
    def specifyDefault(self, key, values):
        self.specify(key, values)
        self._params[key].makeDefault(values)
    
    def specify(self, key, values):
        if self.hasParam(key):
            self._params[key].setValues(values)
        else:
            log.error('specify', 'Param {} is not in the map.'.format(key))
            print self.printState()
            
    def getParamValue(self, key):
        if self.hasParam(key):
            return self._params[key].getValues()[0]
        else:
            log.error('getParamValue', 'Param {} is not in the map.'.format(key))
        
    def getParamValues(self, key):
        if self.hasParam(key):
            return self._params[key].getValues()
        else:
            log.error('getParamValues', 'Param {} is not in the map.'.format(key))
        
    def getParamMapFiltered(self, type_filter):
        to_ret = {}
        for key, param in self._params.iteritems():
            if isinstance(type_filter, list):
                if param.paramType() in type_filter:
                    to_ret[key] = param
            else:
                if param.paramType() == type_filter:
                    to_ret[key] = param                
        return to_ret
        
    def printState(self):
        to_ret = ""
        for _, p in self._params.iteritems():
            #if not p.hasDefaultValues():
            if p.paramTypeIs(ParamTypes.Online):
                to_ret += p.printState() + " "
        return to_ret
        
        
if __name__ == '__main__':
    ph = ParamHandler()
    ph.addParam("ciao", 10, ParamTypes.Online)
    print ph.printState()
    ph.specify("ciao", 5)
    print ph.printState()