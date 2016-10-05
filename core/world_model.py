
import logger.logger as log
import params
import semanticnet as sn
import networkx as nx
import matplotlib.pyplot as plt
#from owlready import * #WORKS ONLY WITH Python 3.0... azz
from itertools import chain
from copy import deepcopy
import rdflib
from rdflib.namespace import RDF, RDFS, OWL, XSD, Namespace
import numpy as np

ontology=rdflib.Graph()
ontology.load('/home/francesco/ros_ws/base_ws/src/skiros/skiros/skiros/owl/stamina.owl')
PREFIX="""
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX stmn: <http://www.semanticweb.org/francesco/ontologies/2014/9/stamina#>
"""
STMN = Namespace('http://www.semanticweb.org/francesco/ontologies/2014/9/stamina#')

def getSubClasses(name, recursive=False):
    to_ret = list(ontology.subjects(RDFS["subClassOf"], rdflib.URIRef(name)))
    if recursive:
        for c in to_ret:
            to_ret += getSubClasses(c, recursive)
    return to_ret
    
def getSubProperties(name, recursive=False):
    to_ret = list(ontology.subjects(RDFS["subPropertyOf"], rdflib.URIRef(name)))
    if recursive:
        for c in to_ret:
            to_ret += getSubProperties(c, recursive)
    return to_ret
    
class Element(object):
    """
    """     
    def printState(self, verbose=False):
        to_ret = self._type + "-" + str(self._id) + ":" + self._label #+ self._properties
        if verbose:
            for _, p in self._properties.iteritems():
                to_ret += "\n" + p.printState()
            for r in self._relations:
                to_ret += "\n" + str(r)
        return to_ret
        
    def __init__(self, etype="Unknown", elabel="", eid=-1): 
        # Description
        self._type=etype
        self._label=elabel  
        self._id=eid      
        self._properties={}  
        self._relations=[] 
        
    def __str__(self):
        return self.printState()
        
    def addRelation(self, subj_id, predicate, obj_id, state=True):
        self._relations.append({'src': subj_id, 'type': predicate, 'dst': obj_id, 'state': state})
        
    def hasProperty(self, key):
        return self._properties.has_key(key)        
        
    def addProperty(self, key, value):
        self._properties[key] = params.Param(key, "", value, params.ParamTypes.Discrete)
                    
    def removeProperty(self, key):
        del self._properties[key]
        
    def appendProperty(self, key, value):
        if self.hasProperty(key):
            self._properties[key].append(value)
        else:
            self.addProperty(key, value)
    
    def hasValue(self, key, value):
        if self.hasProperty(key):
            return self._properties[key].find(value) >= 0
        return False
        
    def getProperty(self, key):
        return self._properties[key]
        
    def removePropertyValue(self, key, value):
        if self.hasProperty(key):
            index = self._properties[key].find(value)
            self._properties[key].remove(index)
        else:
            log.warn("removePropertyValue", 'Property {} is not in the map.'.format(key))
            
    def setPropertyValues(self, key, value):
        if self.hasProperty(key):
            self._properties[key].setValues(value)
        else:
            log.warn("setPropertyValues", 'Property {} is not in the map.'.format(key))
            
    def getPropertyValue(self, key):
        t = self._properties[key]
        return t.getValues()
             
    def isInstance(self, abstract, wmi):
        """
        Compare the element to an abstract description
        Return true if this is a valid instance, false otherwise
        """
        #Filter by type
        if not self._type==abstract._type and not (STMN[self._type] in getSubClasses(STMN[abstract._type], True)):
            return False
        #Filter by label
        if not (abstract._label=="" or abstract._label=="Unknown" or self._label==abstract._label):
            return False
        #Filter by properties
        for k, p in abstract._properties.iteritems():
            if not self.hasProperty(k):
                return False
            for v in p.getValues(): 
                if not v in self.getPropertyValue(k):
                    return False
        #Filter by relations
        for r in abstract._relations:
            if r["src"]==-1:#-1 is the special autoreferencial value
                if not wmi.getRelations(self._id, r["type"], -1):
                    return False
            else:
                if not wmi.getRelations(-1, r["type"], self._id):
                    return False
        return True
#class Ontology:
#    def setWorkspacePath(self, path):
#        onto_path.appen(path)
#    
#    def loadOntology(self, filename):
#        self._ontology = get_ontology(path+filename).load()

class DiscreteReasoner(object):
    def getAssociatedRelations(self):
        """ Not implemented in abstract class. """
        raise NotImplementedError("Not implemented in abstract class")
        
    def getAssociatedProperties(self):
        """ Not implemented in abstract class. """
        raise NotImplementedError("Not implemented in abstract class")
        
    def computeRelations(self, sub, obj):
        """ Not implemented in abstract class. """
        raise NotImplementedError("Not implemented in abstract class")

class SpatialReasoner(DiscreteReasoner):
    def getAssociatedRelations(self):
        return ['fitsIn']
        
    def getAssociatedProperties(self):
        return ['Position']
    
    def computeRelations(self, sub, obj):
        to_ret = []
        edge = {'src': sub._id, 'dst': obj._id}
        edge['type'] = 'fitsIn'
        to_ret.append(edge)
        return to_ret

class WorldModel:
    _id=0
    _graph=sn.Graph()

    def __init__(self, scene_name=None):
        self._verbose=False
        if scene_name:
            self.reset(scene_name)
    
    def __copy__(self):
        wm = WorldModel()
        wm._verbose=self._verbose
        wm._id = self._id
        wm._graph = self._graph
        return wm
    
    def __deepcopy__(self, memo):
        result = self.__copy__()
        memo[id(self)] = result
        return result
        
    def generateId(self, desired_id):
        if desired_id>=0:
            self._id = desired_id
        while self._graph.has_node(self._id):
            self._id += 1
        return self._id
        
    def reset(self, scene_name):
        self._id=0
        self._graph=sn.Graph()
        root = Element("Scene", scene_name, 0)
        props = { "type" : root._type, "label" : root._label}
        self._graph.add_node(dict(chain(props.items(),root._properties.items())), root._id)
        
    def _printRecursive(self, root, indend):
        s = root.printState()
        print indend + s
        indend = "-"*(len(indend)+len(s))+"->"
        for e in self.getChildren(root._id):
            self._printRecursive(e, indend)
        
    def printModel(self):
        root = self.getElement(0)
        #print str(self._graph) 
        self._printRecursive(root, "")
        #nx.draw(self._graph.networkx_graph())
        return
        
    def getAbstractElement(self, etype, elabel):
        e = Element(etype, elabel)
        self.addElement(e, 0, 'hasAbstract')
        return e
    
    def resolveElements(self, keys, ph):
        """
        Return all elements matching the profile in input (type, label, properties and relations)
        """
        first = {}
        couples = {}
        for key in keys:
            first[key] = np.array(self.resolveElement(ph.getParamValue(key)))
        all_keys = [key for key, _ in ph._params.iteritems()]
        #print keys
        #for key, p in ph._params.iteritems():
        #    print p.getValue().printState(True)
        #Solve the relations
        coupled_keys = []
        overlap_keys = []
        for i in range(len(all_keys)):#Loop over all keys
            key_base = all_keys[i]
            if not isinstance(ph.getParamValue(key_base), Element): continue
            for j in ph.getParamValue(key_base)._relations:#Loop over relation constraints
                #print j
                if j["src"]==-1:#-1 is the special autoreferencial value
                    key2 = j["dst"]  
                    key = key_base
                    if all_keys.index(key2)<i:#Skip relation with previous indexes, already considered
                        continue
                else:
                    key2 = key_base
                    key = j["src"]     
                    if all_keys.index(key)<i:#Skip relation with previous indexes, already considered
                        continue
                this = ph.getParamValue(key)
                other = ph.getParamValue(key2)
                if this._id>=0 and other._id>=0:#If both parameters are already set, no need to resolve..
                    continue
                if this._id>=0: set1 = [this]
                else: 
                    if ph.getParam(key).paramType()==params.ParamTypes.Optional: continue 
                    else: set1 = first[key]
                if other._id>=0: set2 = [other]
                else:
                    if ph.getParam(key2).paramType()==params.ParamTypes.Optional: continue 
                    else: set2 = first[key2]
                if (key, key2) in couples:
                    couples[(key, key2)] = np.concatenate((couples[(key, key2)], np.array([np.array([e1, e2]) for e1 in set1 for e2 in set2 if self.getRelations(e1._id, j["type"], e2._id)])))
                else:
                    if key in coupled_keys: overlap_keys.append(key)
                    else: coupled_keys.append(key)
                    if key2 in coupled_keys: overlap_keys.append(key2)
                    else: coupled_keys.append(key2)
                    couples[(key, key2)] = np.array([np.array([e1, e2]) for e1 in set1 for e2 in set2 if self.getRelations(e1._id, j["type"], e2._id)])
        
        if overlap_keys:
            loop = True
            iters = 5
            while loop:#Iterate until no shared keys are found
                iters-=1
                if iters==0:
                    raise
                loop = False
                coupled_keys = []
                merged = {}
                #print 'qui:'
                #print couples         
                for k1, s1 in couples.iteritems():
                    for k2, s2 in couples.iteritems():
                        shared_k = [k for k in k1 if k in k2]
                        if k1==k2 or not shared_k:
                            continue
                        loop = True
                        skip = True
                        for i in k1:
                            if not i in coupled_keys:
                                coupled_keys.append(i)
                                skip=False
                        for i in k2:
                            if not i in coupled_keys:
                                coupled_keys.append(i)
                                skip=False
                        if skip: continue#If it was already considered, skip
                        rk, rs = self._intersect2(k1,k2,s1,s2, shared_k)
                        merged[rk] = rs
                for key in keys:#Add back not merged couples
                    if not key in coupled_keys:
                        for k1, s1 in couples.iteritems():
                            if key in k1:
                                merged[k1] = s1 
                couples = merged   
            #log.error("", "Not solving the overlap!")
        for key in keys:#Add back not merged keys
            if not key in coupled_keys:
                couples[key] = first[key]
        #print couples
        return couples
        
    def _checkEqual(self, lst):
        b = lst[0]
        for i in range(1, len(lst)):
            if lst[i]._id!=b._id:
                return False
        return True
        
    def _checkEqual2(self, lst):
        return lst[1:] == lst[:-1]
        
    def _removeConstants(self, k1, s1, shared_i):
        r, c = s1.shape
        if r<=1:
            return k1, s1
        c_index = np.ones(c)
        c_index[shared_i] = 1
        for i in range(c):
            if i==shared_i:
                continue
            if not self._checkEqual(s1[:,i]):
                c_index[i] = 0
        if np.count_nonzero(c_index)<=0:
            return k1, s1
        k1 = [k1[i] for i in range(r) if c_index[i]==1]
        s1 = [s1[:, i] for i in range(r) if c_index[i]==1]
        #print 'new keys ' + str(k1)
        #for i in range(size):
        #    if r_index[i]:
        return k1, s1
       
    def _concatenate(self, a, b):
        if not isinstance(a, np.ndarray):
            a = np.array([a])
        if not isinstance(b, np.ndarray):
            b = np.array([b])
        return np.concatenate((a,b))
       
    def _intersect2(self, k1, k2, s1, s2, shared_k):
        #k1, s1 = self._removeConstants(k1, s1, k1.index(shared_k[0]))
        #k2, s2 = self._removeConstants(k2, s2, k2.index(shared_k[0]))
        #print k1
        #print k2
        a = [k1.index(k) for k in shared_k]
        b = [k2.index(k) for k in shared_k]
        c = np.arange(len(k1))
        d = np.arange(len(k2))
        d = np.delete(d, b)
        keys = []
        #Remove constant sets
        for k in k1:
            keys.append(k)
        for k in k2:
            if not k in shared_k:
                keys.append(k)
        #print keys
        sets = []
        #print c
        #print d
        for v1 in s1:
            for v2 in s2:
                append=True
                for i in range(len(shared_k)):
                    #print str(v1[a[i]].printState()) + 'vs' + str(v1[b[i]].printState()) + '=' + str(v1[a[i]]!=v2[b[i]])
                    if v1[a[i]]!=v2[b[i]]:
                        append=False
                if append:
                    sets.append(np.array(self._concatenate(v1[c], v2[d])))
        return tuple(keys), np.array(sets)
        
    def _intersect(self, *d):
        sets = iter(map(set, d))
        result = sets.next()
        for s in sets:
            result = result.intersection(s)
        return result
       
    def isOfType(self, element, etype):
        return element._type==etype or (STMN[element._type] in getSubClasses(STMN[etype], True))
       
    def resolveElement(self, description):
        """
        Return all elements matching the profile in input (type, label, properties)
        """
        first = []
        to_ret = []
        #print 'description ' + description.printState(True)
        #Get all nodes matching type and label
        #print getSubClasses(STMN[description._type], True)
        for _, e in self._graph.get_nodes().items():
            type_match = e['type']==description._type or (STMN[e['type']] in getSubClasses(STMN[description._type], True))
            if type_match and (description._label=="" or description._label=="Unknown" or e['label']==description._label):
                first.append(self._makeElement(e))
        #Filter by properties
        for e in first:
            add = True
            for k, p in description._properties.iteritems():
                if not e.hasProperty(k):
                    add = False
                    break
                for v in p.getValues(): 
                    if not v in e.getPropertyValue(k):
                        add = False
                        break
                if not add:
                    break
            if add:
                to_ret.append(e)
        #print to_ret
        return to_ret

    def _makeElement(self, props):
        e = Element()
        copy = deepcopy(props)
        e._id = copy.pop("id")
        e._type = copy.pop("type")
        e._label = copy.pop("label")
        e._properties = copy
        return e
    
    def getElement(self, eid):
        eprops = self._graph.get_node(eid)
        if not eprops:
            log.error("getElement", "{} not found.".format(eid))
            return Element()
        return self._makeElement(eprops)
        
    def addElement(self, element, parent_id, relation):
        if not self._graph.has_node(parent_id):
            log.warn("addElement", "No parent element found with key {}".format(parent_id))
            return
        eid = self.generateId(element._id)
        if self._verbose:
            log.debug('add', str(eid))
        element._id = eid
        props = { "type" : element._type, "label" : element._label}
        self._graph.add_node(dict(chain(props.items(),element._properties.items())), element._id)
        self.setRelation(parent_id, relation, eid, True)
        return eid
        
    def updateElement(self, element):
        if not self._graph.has_node(element._id):
            log.warn("updateElement", "No element found with key {}".format(element._id))
            return
        props = { "type" : element._type, "label" : element._label}
        self._graph.add_node(dict(chain(props.items(),element._properties.items())), element._id)
        
    def removeElement(self, eid):
        if self._verbose:
            log.debug('remove', str(eid))
        #self._id=0
        self._graph.remove_node(eid)
        
    def _checkRelation(self, esubject, relation, eobject, value):
        """
        Remove the old contain relation, to maintain the tree structure
        """
        if(relation=="contain" and value):  
            self.setRelation(-1, relation, eobject, False)
            
        
    def setRelation(self, esubject, relation, eobject, value=True):
        self._checkRelation(esubject, relation, eobject, value)
        try:
            if value:
                self._graph.add_edge(esubject, eobject, { "type" : relation })
            else:
                for e in self.getRelations(esubject, relation, eobject, True):
                    self._graph.remove_edge(e)
        except:
            self.printModel()
            raise
        return True
        
    def getAssociatedReasoner(self, relation):
        for cls in DiscreteReasoner.__subclasses__():
            instance = cls()
            if relation in instance.getAssociatedRelations():
                return instance
        return None
        
    def getRelations(self, esubject, relation, eobject, getId=False):
        rel = []
        for _, edge in self._graph.get_edges().items():
            if (esubject<0 or edge['src']==esubject) and (eobject<0 or edge['dst']==eobject) and (not relation or edge['type']==relation or STMN[edge['type']] in getSubProperties(relation, True)):
                if getId:
                    rel.append(edge['id'])
                else:
                    new_edge = deepcopy(edge)
                    rel.append(new_edge)
        reasoner = self.getAssociatedReasoner(relation)
        if reasoner and esubject>=0 and eobject>=0:
            rel += reasoner.computeRelations(self.getElement(esubject), self.getElement(eobject))
        return rel
        
    def getChildren(self, eid):
        to_ret=[]
        for edge in self.getRelations(eid, "contain", -1):
            e = self.getElement(edge['dst'])
            to_ret.append(e)
        return to_ret
        
    def getParent(self, eid):
        for edge in self.getRelations(-1, "contain", eid):
            return self.getElement(edge['dst'])   


if __name__ == '__main__':

   # g.namespaces
    #g.parse(file='/home/francesco/ros_ws/base_ws/src/skiros/skiros/owl/stamina.owl')
    #g.bind("stmn", STMN)    
    #print( g.serialize(format='n3') )
    #print XSD
    if STMN["GraspingPose"] in getSubClasses(STMN["Spatial"], True): 
        print STMN["GraspingPose"]
    #for x in getSubProperties(STMN["sceneProperty"], True): print x
    #for x in set(g.objects(STMN["compressor"], RDF["type"])): print x
    #for x in set(ontology.subjects(RDFS["subClassOf"], rdflib.URIRef(STMN["Product"]))): print x
    #for row in g.query(PREFIX+'SELECT ?x WHERE { ?x rdf:type :Compressor .}'):
     #   print row
    #initNs={ 'xsd': XSD , 'owl': OWL , 'rdfs': RDFS, 'rdf': RDF , 'stmn': STMN}):
        
    #for s,p,o in g:
      #  print s,p,o