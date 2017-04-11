import core.procedure as proc
import core.params as params
import core.world_model as wm
import core.logger.logger as log

"""The skills and primitives library """
        
    
class Drive(proc.ProcedureDescription):
    def createDescription(self):
        self._type = "Drive"
        #=======Params=========
        self.addParam("StartLocation", wm.Element("Location"), params.ParamTypes.Online)
        self.addParam("TargetLocation", wm.Element("Location"), params.ParamTypes.Online)
        self.addParam("Camera", wm.Element("Camera"), params.ParamTypes.Hardware)
        #=======PreConditions=========
        self.addPreCondition(self.getRelationCond("RobotAt", "robotAt", "Robot", "StartLocation", True))
        #=======HoldConditions=========
        #=======PostConditions=========
        self.addPostCondition(self.getRelationCond("NoRobotAt", "robotAt", "Robot", "StartLocation", False))
        self.addPostCondition(self.getRelationCond("RobotAt", "robotAt", "Robot", "TargetLocation", True))
        #=======Subtree=========
        
class drive_aau(proc.ProcedureInstance):
    def createDescription(self):
        self.setType(Drive())
        self._label = "drive_aau"
        
    def onInit(self):
        return True
        
    def expand(self, procedure):
        #=======PostConditions=========
        procedure.addPostCondition(procedure.getRelationCond("NoView", "hasViewOn", "Camera", "StartLocation", False))
        procedure.addPostCondition(procedure.getRelationCond("HasView", "hasViewOn", "Camera", "TargetLocation", True))
        pass
    
    def execute(self):
        robot = self._params.getParamValue("Robot")
        skill = self._label
        res = skillExecute(robot, skill, self._params.getParamMap())
        if not res:
            log.error("[{}]".format(skill), "Failed to execute.")
            return False
        else:
            result = getResult(robot, skill)
            updateRoutine(self, result)
        return True
    
class drive_fake(proc.ProcedureInstance):
    def createDescription(self):
        self.setType(Drive())
        self._label = "drive_fake"
        
    def onInit(self):
        return True
        
    def execute(self):
        robot = self._params.getParamValue("Robot")
        skill = self._label
        res = skillExecute(robot, skill, self._params.getParamMap())
        if not res:
            log.error("[{}]".format(skill), "Failed to execute.")
            return False
        else:
            result = getResult(robot, skill)
            updateRoutine(self, result)
        return True
        
class Pick(proc.ProcedureDescription):
    def createDescription(self):
        self._type = "Pick"
        #=======Params=========
        self.addParam("Container", wm.Element("Location"), params.ParamTypes.Online)
        self.addParam("Object", wm.Element("Product"), params.ParamTypes.Optional)
        self.addParam("Arm", wm.Element("Arm"), params.ParamTypes.Hardware)
        self.addParam("Gripper", wm.Element("Gripper"), params.ParamTypes.Hardware)
        #=======PreConditions=========
        #self.addPreCondition(self.getRelationCond("HasSkill", "hasSkill", "Robot", "Skill", True))
        self.addPreCondition(self.getPropCond("EmptyHanded", "ContainerState", "Gripper", "Empty", True))
        self.addPreCondition(self.getRelationCond("RobotAtLocation", "robotAt", "Robot", "Container", True))
        self.addPreCondition(self.getRelationCond("ObjectInContainer", "contain", "Container", "Object", True))
        #=======PostConditions=========
        self.addPostCondition(self.getPropCond("EmptyHanded", "ContainerState", "Gripper", "Empty", False))
        self.addPostCondition(self.getRelationCond("RobotAtLocation", "robotAt", "Robot", "Container", True))
        self.addPostCondition(self.getRelationCond("Holding", "contain", "Gripper", "Object", True))
            
        
class pick_aau(proc.ProcedureInstance):
    def createDescription(self):
        self.setType(Pick())
        self._label = "pick_aau"
        
    def expand(self, procedure):
        #procedure.addPreCondition(self.getOnTypeCond("IsType", "Container","LargeBox"))
        #Locate object
        procedure.addChild(self.getProcedure("CleanParam", "clean_param"))
        procedure._children[-1].remap('Param', 'ObservationPose') 
        procedure.addChild(self.getProcedure("LocateModule", "locate_fake"))
        procedure.addChild(self.getProcedure("ObservationBuilder", "build_observation_pose"))
        #Open gripper
        procedure.addChild(self.getProcedure("GripperControlModule", "gripper_oc", 0))
        procedure._children[-1].specify("Close", False)
        procedure._children[-1].addPostCondition(self.getPropCond("Open", "ContainerState", "Gripper", "Open", True));
        procedure._children[-1].addPostCondition(self.getPropCond("NotClosed", "ContainerState", "Gripper", "Close", False));
        #Move to observe
        procedure.addChild(self.getProcedure("MotionModule", "arm_motion", 0), latch=True)
        procedure._children[-1].remap('DestinationObject', 'ObservationPose')
        procedure._children[-1].remap('Trajectory', 'ObserveTrajectory') 
        #Register
        procedure.addChild(self.getProcedure("CleanParam", "clean_param"))
        procedure._children[-1].remap('Param', 'GraspingPose') 
        procedure.addChild(self.getProcedure("Registration", "registration"))
        procedure._children[-1].remap('PriorInfo', 'Object') 
        procedure.addChild(self.getProcedure("GraspBuilder", "build_grasping_pose"))
        #Move to grasp
        procedure.addChild(self.getProcedure("MotionModule", "arm_motion", 0))
        procedure._children[-1].remap('Initial', 'ObservationPose') 
        procedure._children[-1].specify("ApproachDistance", -0.0)
        procedure._children[-1].remap('DestinationObject', 'GraspingPose') 
        procedure._children[-1].remap('Trajectory', 'GraspTrajectory') 
        #Grasp
        procedure.addChild(self.getProcedure("HoldCheckModule", "holding", 0), latch=True)
        procedure.addChild(self.getProcedure("MotionModule", "arm_motion", 0), latch=True)
        procedure._children[-1].specify("DestinationObject", wm.Element("TransformNode", "home"))
        procedure._children[-1].specify("ApproachDistance", -0.0)
        procedure._children[-1].specify("Reverse", True)
        procedure._children[-1].remap('DestinationObject', 'Home')
        procedure._children[-1].remap('Initial', 'GraspingPose')
        procedure._children[-1].remap('Trajectory', 'HomeTrajectory') 
        #arm_motion = self.getProcedure("ArmObjectMotion", "arm_move_to_kinematic", 0)
        #arm_motion._params.specify('Kinematic', self._wm.getAbstractElement("Kinematic", 'Home'))
        #procedure.addChild(arm_motion)
        
    def onInit(self):
        return True
        
    def execute(self):
        return True
                 
class place_aau(proc.ProcedureInstance):
    def createDescription(self):
        self._type = "Place"
        self._label = "place_aau"
        #=======Params=========
        self.addParam("PlacingCell", wm.Element("Cell"), params.ParamTypes.Online)
        self.addParam("PlacingKit", wm.Element("Kit"), params.ParamTypes.Online)
        self.addParam("Object", wm.Element("Product"), params.ParamTypes.Online)
        self.addParam("Arm", wm.Element("Arm"), params.ParamTypes.Hardware)
        self.addParam("Gripper", wm.Element("Gripper"), params.ParamTypes.Hardware)
        self.addParam("Skill", self.toElement(), params.ParamTypes.System)#TODO will move to std params
        #=======PreConditions=========
        self.addPreCondition(self.getRelationCond("HasSkill", "hasSkill", "Robot", "Skill", True))
        self.addPreCondition(self.getRelationCond("Holding", "contain", "Gripper", "Object", True));
        self.addPreCondition(self.getRelationCond("Carrying", "contain", "Robot", "PlacingKit", True));
        self.addPreCondition(self.getRelationCond("FitsIn", "fitsIn", "Object", "PlacingCell", True));
        self.addPreCondition(self.getPropCond("LocationEmpty", "ContainerState", "PlacingCell", "Empty", True));
        self.addPreCondition(self.getRelationCond("CellInKit", "contain", "PlacingKit", "PlacingCell", True));
        #=======PostConditions=========
        self.addPostCondition(self.getRelationCond("NotHolding", "contain", "Gripper", "Object", False));
        self.addPostCondition(self.getPropCond("LocationEmpty", "ContainerState", "PlacingCell", "Empty", False));
        self.addPostCondition(self.getPropCond("EmptyHanded", "ContainerState", "Gripper", "Empty", True));
        self.addPostCondition(self.getRelationCond("ObjectInCell", "contain", "PlacingCell", "Object", True));
        self.addPostCondition(self.getRelationCond("InKit", "inKit", "PlacingKit", "Object", True));
        
    def expand(self, procedure):
        #Locate kit box
        procedure.addChild(self.getProcedure("VisionModule", "kittingbox_registration", 0))
        procedure._children[-1].remap('Kit', 'PlacingKit')
        procedure._children[-1].remap('Camera', 'KitCamera')
        #Build placing pose
        procedure.addChild(self.getProcedure("CleanParam", "clean_param"))
        procedure._children[-1].remap('Param', 'PlacingPose') 
        procedure.addChild(self.getProcedure("PlacingPoseBuilder", "build_placing_pose", 0))
        #Move to place
        procedure.addChild(self.getProcedure("MotionModule", "arm_motion", 0))
        procedure._children[-1].specify("ApproachDistance", -0.0)
        procedure._children[-1].remap('DestinationObject', 'PlacingPose')
        #Open Gripper
        procedure.addChild(self.getProcedure("ReleaseCheckModule", "release", 0), latch=True)
        procedure.addChild(self.getProcedure("MotionModule", "arm_motion", 0), latch=True)
        procedure._children[-1].specify("DestinationObject", wm.Element("TransformNode", "home"))
        procedure._children[-1].specify("ApproachDistance", -0.0)
        procedure._children[-1].specify("Reverse", True)
        procedure._children[-1].remap('DestinationObject', 'Home')
        #procedure.addChild(proc.copy(self._wm), latch=True)
        #procedure._children[-1].remap('From', 'PlacingKit')
        #procedure._children[-1].remap('To', 'Initial')
    def onInit(self):
        return True
        
    def execute(self):
        return True
        
class arm_motion(proc.ProcedureInstance):
    def createDescription(self):
        self._type = "MotionModule"
        self._label = "arm_motion"
        self.addParam("DestinationObject", wm.Element("Spatial"), params.ParamTypes.Online)
        self.addParam("Arm", wm.Element("Arm"), params.ParamTypes.Hardware)
        self.addParam("ApproachDistance", 0.0, params.ParamTypes.Offline)
        self.addParam("Reverse", False, params.ParamTypes.Offline)
        #=======PreConditions=========
        self.addPreCondition(self.getHasPropCond("HasPosition", "Position", "DestinationObject", True))
        self.addPreCondition(self.getRelationCond("RobotHasArm", "contain", "Robot", "Arm", True))
        #=======PostConditions=========
        
    def expand(self, procedure):
        #procedure.addChild(self.getProcedure("InverseKinematic", "ik"))
        procedure.addChild(self.getProcedure("TrajectoryPlanModule", "plan_trajectory"))
        #log.warn("SET", "{}".format(self._params.getParamValue("Reverse")))
        procedure._children[-1].specify("ApproachDistance", procedure._params.getParamValue("ApproachDistance"))
        procedure._children[-1].specify("Reverse", procedure._params.getParamValue("Reverse"))
        procedure.addChild(self.getProcedure("MotionExecutionModule", "motion_execution"))
        pass
        
    def onInit(self):
        return True
        
    def execute(self):
        return True
                       
class plan_trajectory(proc.ProcedureInstance):
    def createDescription(self):
        self._type = "TrajectoryPlanModule"
        self._label = "plan_trajectory"
        #=======Params=========
        #self.addParam("Initial", wm.Element("Spatial"), params.ParamTypes.Online)
        self.addParam("DestinationObject", wm.Element("Product"), params.ParamTypes.Online)
        self.addParam("Trajectory", wm.Element("Trajectory"), params.ParamTypes.Optional)
        self.addParam("Arm", wm.Element("Arm"), params.ParamTypes.Hardware)
        self.addParam("ApproachDistance", 0.0, params.ParamTypes.Offline)
        self.addParam("Reverse", False, params.ParamTypes.Offline)
        self.addParam("ApproachAxis", "y", params.ParamTypes.Offline)
        self.addParam("Module", self.toElement(), params.ParamTypes.System)#TODO will move to std params
        #=======PreConditions=========
        #self.addPreCondition(self.getRelationCond("HasModule", "hasModule", "Robot", "Module", True))
        #self.addPreCondition(self.getIsSpecifiedCond("HasKinematic", "TargetKinematic", True))
        #=======PostConditions=========
        #self.addPostCondition(self.getIsSpecifiedCond("HasTrajectory", "Trajectory", True))
        
    def onInit(self):
        return True
        
    def execute(self):
        robot = self._params.getParamValue("Robot")
        skill = self._label
       # axis = self._params.getParamValue("Gripper").getProperty("FrontAxis").getValue()
        #self._params.specify("ApproachAxis", str(axis))        
        res = moduleExecute(robot, skill, self._params.getParamMap())
        if not res:
            log.error("[{}]".format(skill), "Failed to execute.")
            return False
        else:
            result = getResult(robot, skill)
            updateRoutine(self, result)
        return True
        
class motion_execution(proc.ProcedureInstance):
    def createDescription(self):
        self._type = "MotionExecutionModule"
        self._label = "motion_execution"
        #=======Params=========
        self.addParam("Trajectory", wm.Element("Trajectory"), params.ParamTypes.Online, [params.ParamOptions.Consume])
        self.addParam("Arm", wm.Element("Arm"), params.ParamTypes.Hardware, [params.ParamOptions.Lock])
        self.addParam("Initial", wm.Element("Spatial"), params.ParamTypes.Online)
        self.addParam("DestinationObject", wm.Element("Product"), params.ParamTypes.Online)
        self.addParam("Gripper", wm.Element("Gripper"), params.ParamTypes.Hardware)
        self.addParam("Module", self.toElement(), params.ParamTypes.System)#TODO will move to std params
        #=======PreConditions=========
        #self.addPreCondition(self.getRelationCond("HasModule", "hasModule", "Robot", "Module", True))
        self.addPreCondition(self.getRelationCond("GripperAt", "at", "Gripper", "Initial", True))
        #=======PostConditions=========
        self.addPostCondition(self.getRelationCond("GripperAt", "at", "Gripper", "Initial", False))
        self.addPostCondition(self.getRelationCond("GripperAt", "at", "Gripper", "DestinationObject", True))
        
    def onInit(self):
        return True
        
    def execute(self):
        robot = self._params.getParamValue("Robot")
        skill = self._label
        res = moduleExecute(robot, skill, self._params.getParamMap())
        if not res:
            log.error("[{}]".format(skill), "Failed to execute.")
            return False
        else:
            result = getResult(robot, skill)
            updateRoutine(self, result)
        return True    
                     
                     
class Locate(proc.ProcedureDescription):
    def createDescription(self):
        self._type = "LocateModule"
        #=======Params=========
        self.addParam("Container", wm.Element("Location"), params.ParamTypes.Online)
        self.addParam("Object", wm.Element("Product"), params.ParamTypes.Optional)
        self.addParam("Camera", wm.Element("Camera"), params.ParamTypes.Hardware, [params.ParamOptions.Lock])
        self.addParam("Module", self.toElement(), params.ParamTypes.System)#TODO will move to std params
        #=======PreConditions=========
        self.addPreCondition(self.getRelationCond("RobotAt", "robotAt", "Robot", "Container", True))
        #self.addPreCondition(self.getRelationCond("HasModule", "hasModule", "Robot", "Module", True))
        self.addPreCondition(self.getRelationCond("HasView", "hasViewOn", "Camera", "Container", True))
        #=======PostConditions=========
        self.addPostCondition(self.getRelationCond("InContainer", "contain", "Container", "Object", True));
        self.addPostCondition(self.getHasPropCond("HasPosition", "Position", "Object", True))
        
class locate_bonn(proc.ProcedureInstance):
    def createDescription(self):
        self.setType(Locate())
        self._label = "locate_bonn"
        
    def onInit(self):
        return True
        
    def execute(self):
        robot = self._params.getParamValue("Robot")
        skill = self._label
        res = moduleExecute(robot, skill, self._params.getParamMap())
        if not res:
            log.error("[{}]".format(skill), "Failed to execute.")
            return False
        else:
            result = getResult(robot, skill)
            updateRoutine(self, result)
        return True
          
class locate_fake(proc.ProcedureInstance):
    def createDescription(self):
        self.setType(Locate())
        self._label = "locate_fake"
        
    def onInit(self):
        return True
        
    def expand(self, procedure):
        #=======PostConditions=========
        #procedure.addPostCondition(self.getHasPropCond("HasRegisteredShot", "hasRegisteredShot", "Object", True))
        pass
        
    def execute(self):
        robot = self._params.getParamValue("Robot")
        skill = self._label
        res = moduleExecute(robot, skill, self._params.getParamMap())
        if not res:
            log.error("[{}]".format(skill), "Failed to execute.")
            return False
        else:
            result = getResult(robot, skill)
            updateRoutine(self, result)
        return True
        
class clean_param(proc.ProcedureInstance):
    def createDescription(self):
        self._type = "CleanParam"
        self._label = "clean_param"
        #=======Params=========
        self.addParam("Param", wm.Element("Spatial"), params.ParamTypes.Optional, [params.ParamOptions.Consume])
        
    def onInit(self):
        return True
        
    def execute(self):
        with self._wm:
            return self.simulate()
        
class KitLocalizationModule(proc.ProcedureDescription):
    def createDescription(self):
        self._type = "KitLocalizationModule"
        #=======Params=========
        self.addParam("Kit", wm.Element("Kit"), params.ParamTypes.Online)
        self.addParam("Camera", wm.Element("Camera"), params.ParamTypes.Hardware, [params.ParamOptions.Lock])
        #=======PreConditions=========
        #=======PostConditions=========
        self.addPostCondition(self.getHasPropCond("HasPosition", "StateProperty", "Kit", True))
        
class kittingbox_registration_std(proc.ProcedureInstance):
    def createDescription(self):
        self.setType(KitLocalizationModule())
        self._label = "kittingbox_registration_std"
        
    def onInit(self):
        return True
        
    def expand(self, procedure):
        procedure.addPreCondition(procedure.getRelationCond("HasView", "hasViewOn", "Camera", "Kit", True))
        procedure.addChild(self.getProcedure("VisionModule", "kittingbox_registration", 0))
        return True
                
    def postExecute(self):
        with self._wm:
            return self.simulate()  
        
class kittingbox_registration_arm_camera(proc.ProcedureInstance):
    def createDescription(self):
        self.setType(KitLocalizationModule())
        self._label = "kittingbox_registration_arm_camera"
        
    def onInit(self):
        return True
        
    def expand(self, procedure):
        procedure.addChild(self.getProcedure("MotionModule", "arm_motion", 0))
        procedure._children[-1].specify("DestinationObject", wm.Element("TransformNode", "kit_observation_pose"))
        procedure._children[-1].remap('DestinationObject', 'KitObservation') 
        procedure._children[-1].specify("ApproachDistance", 0.0)
        procedure.addChild(self.getProcedure("VisionModule", "kittingbox_registration", 0))
        procedure._children[-1].addParam("Gripper", wm.Element("Gripper"), params.ParamTypes.Online)
        procedure._children[-1].addParam("KitObservation", wm.Element("TransformNode"), params.ParamTypes.Online)
        procedure._children[-1].addPreCondition(self.getRelationCond("AtObservation", "at", "Gripper", "KitObservation", True))
        return True
        
    def execute(self):
        return True
        
    def postExecute(self):
        with self._wm:
            return self.simulate()  
       
class kittingbox_registration(proc.ProcedureInstance):
    def createDescription(self):
        self._type = "VisionModule"
        self._label = "kittingbox_registration"
        #=======Params=========
        self.addParam("Kit", wm.Element("Kit"), params.ParamTypes.Online)
        self.addParam("Camera", wm.Element("Camera"), params.ParamTypes.Hardware, [params.ParamOptions.Lock])
        #=======PreConditions=========
        self.addPreCondition(self.getRelationCond("HasView", "hasViewOn", "Camera", "Kit", True))
        #=======PostConditions=========
        self.addPostCondition(self.getHasPropCond("HasPosition", "StateProperty", "Kit", True))
        
    def onInit(self):
        return True
        
    def execute(self):
        return True
        
    def postExecute(self):
        with self._wm:
            return self.simulate()  
            
class gripper_oc(proc.ProcedureInstance):
    def createDescription(self):
        self._type = "GripperControlModule"
        self._label = "gripper_oc"
        #=======Params=========
        self.addParam("Modality", -1, params.ParamTypes.Offline)
        self.addParam("Close", True, params.ParamTypes.Offline)
        self.addParam("Gripper", wm.Element("Gripper"), params.ParamTypes.Hardware)
        self.addParam("Module", self.toElement(), params.ParamTypes.System)#TODO will move to std params
        #=======PreConditions=========
        #self.addPreCondition(self.getRelationCond("HasModule", "hasModule", "Robot", "Module", True))
        #=======PostConditions=========
        
    def onInit(self):
        return True
        
    def execute(self):
        robot = self._params.getParamValue("Robot")
        skill = self._label
        res = moduleExecute(robot, skill, self._params.getParamMap())
        if not res:
            log.error("[{}]".format(skill), "Failed to execute.")
            return False
        else:
            result = getResult(robot, skill)
            updateRoutine(self, result)
        return True
              
class holding(proc.ProcedureInstance):
    def createDescription(self):
        self._type = "HoldCheckModule"
        self._label = "holding"
        #=======Params=========
        self.addParam("Object", wm.Element("Product"), params.ParamTypes.Online)
        self.addParam("GraspingPose", wm.Element("GraspingPose"), params.ParamTypes.Online)
        self.addParam("Gripper", wm.Element("Gripper"), params.ParamTypes.Hardware)
        #=======PreConditions=========
        self.addPreCondition(self.getRelationCond("GripperAt", "at", "Gripper", "GraspingPose", True))
        #=======PostConditions=========
        self.addPostCondition(self.getPropCond("GripperFull", "ContainerState", "Gripper", "Empty", False))
        self.addPostCondition(self.getRelationCond("Holding", "contain", "Gripper", "Object", True))
        self.addPostCondition(self.getPropCond("NotOpen", "ContainerState", "Gripper", "Open", False))
        self.addPostCondition(self.getPropCond("Close", "ContainerState", "Gripper", "Close", True))
        
    def onInit(self):
        return True
        
    def execute(self):
        return True
        
    def postExecute(self):
        with self._wm:
            return self.simulate()  
        
    def expand(self, procedure):
        procedure.addChild(self.getProcedure("GripperControlModule", "gripper_oc", 0))
        procedure._children[-1].specify("Close", True)
        
class release(proc.ProcedureInstance):
    def createDescription(self):
        self._type = "ReleaseCheckModule"
        self._label = "release"
        #=======Params=========
        self.addParam("PlacingCell", wm.Element("Cell"), params.ParamTypes.Online)
        self.addParam("Object", wm.Element("Product"), params.ParamTypes.Online)
        self.addParam("PlacingPose", wm.Element("PlacingPose"), params.ParamTypes.Online)
        self.addParam("Gripper", wm.Element("Gripper"), params.ParamTypes.Hardware)
        #=======PreConditions=========
        self.addPreCondition(self.getRelationCond("GripperAt", "at", "Gripper", "PlacingPose", True))
        self.addPreCondition(self.getRelationCond("PlacingPoseOfCell", "contain", "PlacingCell", "PlacingPose", True))
        self.addPreCondition(self.getRelationCond("Holding", "contain", "Gripper", "Object", True))
        #=======PostConditions=========
        self.addPostCondition(self.getPropCond("GripperEmpty", "ContainerState", "Gripper", "Empty", True))
        self.addPostCondition(self.getPropCond("LocationFull", "ContainerState", "PlacingCell", "Empty", False))
        self.addPostCondition(self.getRelationCond("NotHolding", "contain", "Gripper", "Object", False))
        self.addPostCondition(self.getRelationCond("Release", "contain", "PlacingCell", "Object", True))
        self.addPostCondition(self.getPropCond("Open", "ContainerState", "Gripper", "Open", True))
        self.addPostCondition(self.getPropCond("NotClosed", "ContainerState", "Gripper", "Close", False))
        
    def onInit(self):
        return True
        
    def execute(self):
        return True
        
    def postExecute(self):
        with self._wm:
            return self.simulate()  
        
    def expand(self, procedure):
        procedure.addChild(self.getProcedure("GripperControlModule", "gripper_oc", 0))
        procedure._children[-1]._params.specify("Close", False)
        
class registration(proc.ProcedureInstance):
    def createDescription(self):
        self._type = "Registration"
        self._label = "registration"
        #=======Params=========
        self.addParam("ObservationPose", wm.Element("ObservationPose"), params.ParamTypes.Online)
        self.addParam("Container", wm.Element("Location"), params.ParamTypes.Online)
        self.addParam("PriorInfo", wm.Element("Product"), params.ParamTypes.Online)
        self.addParam("Arm", wm.Element("Arm"), params.ParamTypes.Hardware)
        self.addParam("Camera", wm.Element("Camera"), params.ParamTypes.Hardware, [params.ParamOptions.Lock])
        self.addParam("Gripper", wm.Element("Gripper"), params.ParamTypes.Hardware)
        self.addParam("Register", True, params.ParamTypes.Offline)
        #=======PreConditions=========
        self.addPreCondition(self.getRelationCond("HasCloseView", "at", "Gripper", "ObservationPose", True))
        self.addPreCondition(self.getRelationCond("UseArmCamera", "contain", "Arm", "Camera", True))
        #=======PostConditions=========
        self.addPostCondition(self.getHasPropCond("HasRegisteredShot", "hasRegisteredShot", "PriorInfo", True))
        
    def onInit(self):
        return True
        
    def execute(self):
        robot = self._params.getParamValue("Robot")
        skill = self._label
        res = moduleExecute(robot, skill, self._params.getParamMap())
        if not res:
            log.error("[{}]".format(skill), "Failed to execute.")
            return False
        else:
            result = getResult(robot, skill)
            updateRoutine(self, result)
        return True
        
class build_grasping_pose(proc.ProcedureInstance):
    def createDescription(self):
        self._type = "GraspBuilder"
        self._label = "build_grasping_pose"
        #=======Params=========
        self.addParam("Object", wm.Element("Product"), params.ParamTypes.Online)
        self.addParam("Gripper", wm.Element("Gripper"), params.ParamTypes.Hardware)
        self.addParam("GraspingPose", wm.Element("GraspingPose"), params.ParamTypes.Optional)
        self.addParam("Module", self.toElement(), params.ParamTypes.System)#TODO will move to std params
        #=======PreConditions=========
        #self.addPreCondition(self.getRelationCond("HasModule", "hasModule", "Robot", "Module", True))
        self.addPreCondition(self.getHasPropCond("HasRegisteredShot", "hasRegisteredShot", "Object", True))
        #=======PostConditions=========
        self.addPostCondition(self.getRelationCond("HasGraspingPose", "contain", "Object", "GraspingPose", True));
        self.addPostCondition(self.getHasPropCond("HasPosition", "Position", "GraspingPose", True));
        
    def onInit(self):
        return True
        
    def execute(self):
        robot = self._params.getParamValue("Robot")
        skill = self._label
        res = moduleExecute(robot, skill, self._params.getParamMap())
        if not res:
            log.error("[{}]".format(skill), "Failed to execute.")
            return False
        else:
            result = getResult(robot, skill)
            updateRoutine(self, result)
        return True
               
class build_observation_pose(proc.ProcedureInstance):
    def createDescription(self):
        self._type = "ObservationBuilder"
        self._label = "build_observation_pose"
        #=======Params=========
        self.addParam("Object", wm.Element("Product"), params.ParamTypes.Online)
        self.addParam("Arm", wm.Element("Arm"), params.ParamTypes.Hardware)
        self.addParam("ObservationPose", wm.Element("ObservationPose"), params.ParamTypes.Optional)
        self.addParam("Module", self.toElement(), params.ParamTypes.System)#TODO will move to std params
        #=======PreConditions=========
        #self.addPreCondition(self.getRelationCond("HasModule", "hasModule", "Robot", "Module", True))
        self.addPreCondition(self.getHasPropCond("HasPosition", "Position", "Object", True))
        #=======PostConditions=========
        self.addPostCondition(self.getRelationCond("HasObservationPose", "contain", "Object", "ObservationPose", True));
        self.addPostCondition(self.getHasPropCond("HasPosition", "Position", "ObservationPose", True));
        
    def onInit(self):
        return True
        
    def execute(self):
        robot = self._params.getParamValue("Robot")
        skill = self._label
        res = moduleExecute(robot, skill, self._params.getParamMap())
        if not res:
            log.error("[{}]".format(skill), "Failed to execute.")
            return False
        else:
            result = getResult(robot, skill)
            updateRoutine(self, result)
        return True
        
class build_placing_pose(proc.ProcedureInstance):
    def createDescription(self):
        self._type = "PlacingPoseBuilder"
        self._label = "build_placing_pose"
        #=======Params=========
        self.addParam("PlacingKit", wm.Element("Kit"), params.ParamTypes.Online)
        self.addParam("PlacingCell", wm.Element("Cell"), params.ParamTypes.Online)
        self.addParam("Object", wm.Element("Product"), params.ParamTypes.Online)
        self.addParam("Gripper", wm.Element("Gripper"), params.ParamTypes.Hardware)
        self.addParam("PlacingPose", wm.Element("PlacingPose"), params.ParamTypes.Optional)
        self.addParam("Module", self.toElement(), params.ParamTypes.System)#TODO will move to std params
        #=======PreConditions=========
       #self.addPreCondition(self.getRelationCond("HasModule", "hasModule", "Robot", "Module", True))
        self.addPreCondition(self.getHasPropCond("HasPosition", "StateProperty", "PlacingKit", True));
        #=======PostConditions=========
        self.addPostCondition(self.getRelationCond("HasPlacingPose", "contain", "PlacingCell", "PlacingPose", True));
        self.addPostCondition(self.getHasPropCond("HasPosition", "Position", "PlacingPose", True));
        
    def onInit(self):
        return True
        
    def execute(self):
        robot = self._params.getParamValue("Robot")
        skill = self._label
        res = moduleExecute(robot, skill, self._params.getParamMap())
        if not res:
            log.error("[{}]".format(skill), "Failed to execute.")
            return False
        else:
            result = getResult(robot, skill)
            updateRoutine(self, result)
        return True