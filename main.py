#!/usr/bin/env python

# Author: Francesco Rovida

"""The main 

Requires:
pip install rdflib
pip install semanticnet
"""

import core as skiros
from data import *
import os

#Set output verbosity
verbose = False

class SkillManager():
    """
    This class contains functions to initialize the scene, create a plan and manipulate the eBT
    """
    def __init__(self, wmi):
        """
        Register the robot on the scene and initialize skills
        """
        self.wm = wmi
        self._instanciator = skiros.procedure.NodeInstanciator(wmi)
        self.registerRobot()
        self.initSkills()
        
    def initSkills(self):
        """
        Retrieve all defined skills in data/skills.py
        """
        for cls in skiros.procedure.ProcedureDescription.__subclasses__():
            self._instanciator.createDescription(cls)
        for cls in skiros.procedure.ProcedureInstance.__subclasses__():
            skill = self._instanciator.createInstance(cls)
            self.wm.addElement(skill.toElement(), self.robot._id, "hasSkill")
        self._instanciator.expandAll()
    
    def registerRobot(self):
        """
        Add the robot description to the scene.
            Location-2:unknown
            Agent:aau_stamina_robot
            ------------------------>TransformNode-9:home
            ------------------------>Camera-5:workspace_camera_front
            ------------------------>Kit-6:kitting_box
            ------------------------------------------>Cell-10:cell_a
            ------------------------------------------>Cell-11:cell_b
            ------------------------>Camera-4:workspace_camera_right
            ------------------------>Arm-3:ur10
            ---------------------------------->Gripper-8:rq3
            ---------------------------------->Camera-7:wrist_camera
        """
        self.robot = skiros.wm.Element("Agent", "aau_stamina_robot")
        self.wm.addElement(self.robot, 0, "contain")
        location = skiros.wm.Element("Location", "unknown")
        self.wm.addElement(location, 0, "contain")
        self.wm.setRelation(self.robot._id, "robotAt", location._id, True)
        arm = skiros.wm.Element("Arm", "ur10")
        arm.addProperty("StateProperty", "Idle")
        self.wm.addElement(arm, self.robot._id, "contain")
        camera = skiros.wm.Element("Camera", "workspace_camera_right")
        camera.addProperty("StateProperty", "Idle")
        self.wm.addElement(camera, self.robot._id, "contain")
        camera = skiros.wm.Element("Camera", "workspace_camera_front")
        camera.addProperty("StateProperty", "Idle")
        self.wm.addElement(camera, self.robot._id, "contain")
        kit = skiros.wm.Element("Kit", "kitting_box")
        self.wm.addElement(kit, self.robot._id, "contain")
        self.wm.setRelation(camera._id, "hasViewOn", kit._id, True)
        camera = skiros.wm.Element("Camera", "wrist_camera")
        camera.addProperty("StateProperty", "Idle")
        self.wm.addElement(camera, arm._id, "contain")
        gripper = skiros.wm.Element("Gripper", "rq3")
        gripper.addProperty("ContainerState", "Empty")
        gripper.addProperty("StateProperty", "Idle")
        self.wm.addElement(gripper, arm._id, "contain")
        home = skiros.wm.Element("TransformNode", "home")
        home.addProperty("Position", 0)
        self.wm.addElement(home, self.robot._id, "contain")
        self.wm.setRelation(gripper._id, "at", home._id, True)
        cell = skiros.wm.Element("Cell", "cell_a")
        cell.addProperty("ContainerState", "Empty")
        self.wm.addElement(cell, kit._id, "contain")
        cell = skiros.wm.Element("Cell", "cell_b")
        cell.addProperty("ContainerState", "Empty")
        self.wm.addElement(cell, kit._id, "contain")
    
    def taskPlan(self):
        """
        Adds some containers to the scene, then creates and returns a test plan
        
        Note: in a std operation this plan should come from a classical planner
        """
        p = skiros.procedure.Root("root", self.wm)
        e = skiros.wm.Element("SmallBox", "largebox_compressors")
        self.wm.addElement(e, 0, "contain")
        p.addChild(skiros.procedure.ProcedureWrapper("Drive", "drive_aau", 0, self._instanciator))
        p.last().specify("TargetLocation", e)
        p.addChild(skiros.procedure.ProcedureWrapper("Pick", "pick_aau", 0, self._instanciator))
        p.last().specify("Container", e)
        p.addChild(skiros.procedure.ProcedureWrapper("Place", "place_aau", 0, self._instanciator))
        p.last().specify("PlacingCell", self.wm.resolveElement(skiros.wm.Element('Cell','cell_b'))[0])
        e = skiros.wm.Element("LargeBox", "largebox_alternators")
        self.wm.addElement(e, 0, "contain") 
        p.addChild(skiros.procedure.ProcedureWrapper("Drive", "drive_aau", 0, self._instanciator))
        p.last().specify("TargetLocation", e)
        p.addChild(skiros.procedure.ProcedureWrapper("Pick", "pick_aau", 0, self._instanciator))
        p.last().specify("Container", e)
        p.addChild(skiros.procedure.ProcedureWrapper("Place", "place_aau", 0, self._instanciator))
        p.last().specify("PlacingCell", self.wm.resolveElement(skiros.wm.Element('Cell','cell_a'))[0])
        return p
                
    def taskPrint(self, p):
        if not p:
            print("None")
            return
        self.visitor = skiros.visitors.VisitorPrint(self.wm, self._instanciator)
        self.visitor.setVerbose(verbose)
        self.visitor.traverse(p)
        return self.visitor.getPrint()
        
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
        if self.visitor.traverse(p):
            self.taskPrint(self.visitor.getExecutionRoot())
        
    def taskOptimize(self, p):
        self.visitor = skiros.visitors_optimizer.VisitorOptimizer(self.wm, self._instanciator)
        self.visitor.setVerbose(False)
        #self.visitor.trackParam("PlacingKit")
        if self.visitor.traverse(p):
            result = self.visitor.getExecutionRoot()
            return result
            
if __name__ == '__main__':
    #Creates the results directory
    if not os.path.exists("results"):
        os.makedirs("results")
    #Creates a world model
    wmi = skiros.wm.WorldModel("aau_lab")
    #Creates a skill manager
    sm = SkillManager(wmi)
    #Runs the test
    with open('results/results.txt', 'w') as file:
        p = sm.taskPlan()
        p2 = sm.taskOptimize(p)
        file.write("Initial scene:\n")
        print "Initial scene:"
        print wmi.printModel()
        file.write(wmi.printModel())
        print "Standard sequence:"
        file.write("Standard sequence:\n")
        file.write(sm.taskPrint(p))
        print sm.taskPrint(p)
        file.write("Optimized sequence:\n")
        print "Optimized sequence:"
        file.write(sm.taskPrint(p2))
        print sm.taskPrint(p2)
    
