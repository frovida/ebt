#!/usr/bin/env python

# Author: Francesco Rovida

"""The main 

Requires:
pip install rdflib
pip install semanticnet
"""

import core as skiros
from lib import *

class SkillManager():
    def __init__(self, wmi):
        self.wm = wmi
        self._instanciator = skiros.procedure.NodeInstanciator(wmi)
        self.registerRobot()
        self.initSkills()
        
    def initSkills(self):
        for cls in skiros.procedure.ProcedureDescription.__subclasses__():
            self._instanciator.createDescription(cls)
        for cls in skiros.procedure.ProcedureInstance.__subclasses__():
            skill = self._instanciator.createInstance(cls)
            self.wm.addElement(skill.toElement(), self.robot._id, "hasSkill")
        self._instanciator.expandAll()
        #print self._instanciator.printState(False)
    
    def registerRobot(self):
        self.robot = skiros.wm.Element("Agent", "aau_stamina_robot")
        self.wm.addElement(self.robot, 0, "contain")
        location = skiros.wm.Element("Location", "Home")
        self.wm.addElement(location, 0, "contain")
        self.wm.setRelation(self.robot._id, "robotAt", location._id, True)
        arm = skiros.wm.Element("Arm", "ur10")
        arm.addProperty("deviceState", "Idle")
        self.wm.addElement(arm, self.robot._id, "contain")
        camera = skiros.wm.Element("Camera", "workspace_camera_right")
        camera.addProperty("deviceState", "Idle")
        self.wm.addElement(camera, self.robot._id, "contain")
        camera = skiros.wm.Element("Camera", "wrist_camera")
        camera.addProperty("deviceState", "Idle")
        self.wm.addElement(camera, arm._id, "contain")
        gripper = skiros.wm.Element("Gripper", "rq3")
        gripper.addProperty("containerState", "Empty")
        gripper.addProperty("deviceState", "Idle")
        self.wm.addElement(gripper, arm._id, "contain")
        location = skiros.wm.Element("TransformNode", "Home")
        self.wm.addElement(location, 0, "contain")
        self.wm.setRelation(gripper._id, "at", location._id, True)
        kit = skiros.wm.Element("Kit", "kitting_box")
        self.wm.addElement(kit, self.robot._id, "contain")
        cell = skiros.wm.Element("Cell", "cell_a")
        cell.addProperty("containerState", "Empty")
        self.wm.addElement(cell, kit._id, "contain")
        cell = skiros.wm.Element("Cell", "cell_b")
        cell.addProperty("containerState", "Empty")
        self.wm.addElement(cell, kit._id, "contain")
    
    def planProcedure(self):
        p = skiros.procedure.Root("root", self.wm)
        e = skiros.wm.Element("SmallBox", "largebox_compressors")
        wmi.addElement(e, 0, "contain")
        p.addChild(skiros.procedure.ProcedureWrapper("Drive", "drive_aau", 0, self._instanciator))
        p.last().specify("TargetLocation", e)
        p.addChild(skiros.procedure.ProcedureWrapper("Pick", "pick_aau", 0, self._instanciator))
        p.last().specify("Container", e)
        p.addChild(skiros.procedure.ProcedureWrapper("Place", "place_aau", 0, self._instanciator))
        p.last().specify("PlacingCell", wmi.resolveElement(wm.Element('Cell','cell_b'))[0])
        e = skiros.wm.Element("LargeBox", "largebox_alternators")
        wmi.addElement(e, 0, "contain") 
        #Add achievement and mantainment Goals. Allow to define Goals expansions
        #On failures of pre-conditions, look for a defined goal to satisfy them. Or just create a goal and ask the strip planner..
        #FOrse ho bisogno di effetti condizionali... No, e un piu
        p.addChild(skiros.procedure.ProcedureWrapper("Drive", "drive_aau", 0, self._instanciator))
        p.last().specify("TargetLocation", e)
        p.addChild(skiros.procedure.ProcedureWrapper("Pick", "pick_aau", 0, self._instanciator))
        p.last().specify("Container", e)
        p.addChild(skiros.procedure.ProcedureWrapper("Place", "place_aau", 0, self._instanciator))
        p.last().specify("PlacingCell", wmi.resolveElement(wm.Element('Cell','cell_a'))[0])
        #aarm_motion = self.getProcedure("ArmMotion", "arm_move_to_kinematic", 0)
        #arm_motion._params.specify('Kinematic', self._wm.getAbstractElement("Kinematic", 'Home'))
        #procedure.addChild(arm_motion)
        return p
        
    def planProcedure2(self):
        p = skiros.procedure.Root("root", self.wm)
        e = skiros.wm.Element("SmallBox", "largebox_compressors")
        wmi.addElement(e, 0, "contain")
        p.addChild(skiros.procedure.ProcedureWrapper("Test", "test2", 0, self._instanciator))
        p.addChild(skiros.procedure.ProcedureWrapper("Test", "test", 0, self._instanciator))
        return p
        
    def taskPrint(self, p):
        self.visitor = skiros.visitors.VisitorPrint(self.wm, self._instanciator)
        self.visitor.setVerbose(False)
        self.visitor.traverse(p)
        
    def taskExecute(self, p):
        self.visitor = skiros.visitors.VisitorExecutor(self.wm, self._instanciator)
        self.visitor.setSimulate()
        #self.visitor.trackParam("ObservationPose")
        self.visitor.setVerbose(False)
        self.visitor.traverse(p)
        
    def taskSimulate(self, p):
        self.visitor = skiros.visitors.VisitorReversibleSimulator(self.wm, self._instanciator)
        self.visitor.setVerbose(False)
        #self.visitor.trackParam("Initial")
        #self.visitor.trackParam("Gripper")
        if self.visitor.traverse(p):
            self.taskPrint(self.visitor.getExecutionRoot())
        
    def taskOptimize(self, p):
        self.visitor = skiros.visitors_optimizer.VisitorOptimizer(self.wm, self._instanciator)
        self.visitor.setVerbose(False)
        #self.visitor.trackParam("PlacingKit")
        if self.visitor.traverse(p):
            self.visitor.getExecutionSequence().printMemory()
           
    def taskOptimize2(self, p):
        self.visitor = skiros.visitors_optimizer.VisitorOptimizer2(self.wm, self._instanciator)
        self.visitor.setVerbose(False)
        #self.visitor.trackParam("PlacingKit")
        #self.visitor.trackParam("ObservationPose")
        if self.visitor.traverse(p):
            result = self.visitor.getExecutionRoot()
            return result
            
if __name__ == '__main__':
    wmi = skiros.wm.WorldModel("aau_lab")
    sm = SkillManager(wmi)
    wmi.printModel()
    p = sm.planProcedure()
    p2 = sm.taskOptimize2(p)
    #sm.taskExecute(p2)
    #time.sleep(3)
    print "Standard sequence:"
    sm.taskPrint(p)
    print "Optimized sequence:"
    sm.taskPrint(p2)
    #wmi.printModel()
    
