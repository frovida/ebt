import core.procedure as proc
import core.params as params
import core.world_model as wm

"""The skills and primitives library """
        
class drive_aau(proc.ProcedureInstance):
    def createDescription(self):
        self._type = "Drive"
        self._label = "drive_aau"
        #=======Params=========
        self.addParam("StartLocation", wm.Element("Location"), params.ParamTypes.Online)
        self.addParam("TargetLocation", wm.Element("Location"), params.ParamTypes.Online)
        self.addParam("Camera", wm.Element("Camera"), params.ParamTypes.Hardware)
        #=======PreConditions=========
        self.addPreCondition(self.getRelationCond("RobotAt", "robotAt", "Robot", "StartLocation", True))
        #=======HoldConditions=========
        #=======PostConditions=========
        self.addPostCondition(self.getRelationCond("RobotAt", "robotAt", "Robot", "StartLocation", False))
        self.addPostCondition(self.getRelationCond("HasView", "hasViewOn", "Camera", "StartLocation", False))
        self.addPostCondition(self.getRelationCond("HasView", "hasViewOn", "Camera", "TargetLocation", True))
        self.addPostCondition(self.getRelationCond("RobotAt", "robotAt", "Robot", "TargetLocation", True))
        #=======Subtree=========
        
    def onInit(self):
        return True
        
    def execute(self):
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
        self.addPreCondition(self.getPropCond("EmptyHanded", "containerState", "Gripper", "Empty", True))
        self.addPreCondition(self.getRelationCond("RobotAtLocation", "robotAt", "Robot", "Container", True))
        self.addPreCondition(self.getRelationCond("ObjectInContainer", "contain", "Container", "Object", True))
        #=======PostConditions=========
        self.addPostCondition(self.getPropCond("EmptyHanded", "containerState", "Gripper", "Empty", False))
        self.addPostCondition(self.getRelationCond("RobotAtLocation", "robotAt", "Robot", "Container", True))
        self.addPostCondition(self.getRelationCond("Holding", "contain", "Gripper", "Object", True))
            
        
class pick_aau(proc.ProcedureInstance):
    def createDescription(self):
        self.setType(Pick())
        self._label = "pick_aau"
        
    def expand(self, procedure):
        procedure.addPreCondition(self.getOnTypeCond("IsType", "Container","LargeBox"))
        #Locate object
        procedure.addChild(self.getProcedure("CleanParam", "clean_param"))
        procedure._children[-1].remap('Param', 'ObservationPose') 
        procedure.addChild(self.getProcedure("Locate", "locate_aau"))
        #Open gripper
        procedure.addChild(self.getProcedure("GripperControlModule", "gripper_oc", 0))
        procedure._children[-1].specify("Close", False)
        procedure._children[-1].addPostCondition(self.getPropCond("Open", "containerState", "Gripper", "Open", True));
        procedure._children[-1].addPostCondition(self.getPropCond("NotClosed", "containerState", "Gripper", "Closed", False));
        #Move to observe
        procedure.addChild(self.getProcedure("ArmObjectMotion", "arm_move_to_object", 0), latch=True)
        procedure._children[-1].remap('Target', 'ObservationPose')
        #Register
        procedure.addChild(self.getProcedure("CleanParam", "clean_param"))
        procedure._children[-1].remap('Param', 'GraspingPose') 
        procedure.addChild(self.getProcedure("Registration", "registration"))
        #Move to grasp
        procedure.addChild(self.getProcedure("ArmObjectMotion", "arm_move_to_object", 0))
        procedure._children[-1].remap('Target', 'GraspingPose') 
        #Grasp
        gripper = self.getProcedure("GripperControlModule", "gripper_oc", 0)
        gripper.specify("Close", True)
        gripper.addPostCondition(self.getPropCond("NotOpen", "containerState", "Gripper", "Open", False))
        gripper.addPostCondition(self.getPropCond("Closed", "containerState", "Gripper", "Closed", True))
        procedure.addChild(gripper, latch=True)
        #arm_motion = self.getProcedure("ArmObjectMotion", "arm_move_to_kinematic", 0)
        #arm_motion._params.specify('Kinematic', self._wm.getAbstractElement("Kinematic", 'Home'))
        #procedure.addChild(arm_motion)
        
    def onInit(self):
        return True
        
    def execute(self):
        return True
         
class pick_aau_simple(proc.ProcedureInstance):
    def createDescription(self):
        self.setType(Pick())
        self._label = "pick_aau_simple"
        
    def expand(self, procedure):
        procedure.addPreCondition(self.getOnTypeCond("IsType", "Container","SmallBox"))
        #Locate object
        procedure.addChild(self.getProcedure("CleanParam", "clean_param"))
        procedure._children[-1].remap('Param', 'ObservationPose') 
        procedure.addChild(self.getProcedure("Locate", "locate_aau"))
        #Open gripper
        procedure.addChild(self.getProcedure("GripperControlModule", "gripper_oc", 0))
        procedure._children[-1].specify("Close", False)
        procedure._children[-1].addPostCondition(self.getPropCond("Open", "containerState", "Gripper", "Open", True));
        procedure._children[-1].addPostCondition(self.getPropCond("NotClosed", "containerState", "Gripper", "Closed", False));
        #Move to observe
        procedure.addChild(self.getProcedure("ArmObjectMotion", "arm_move_to_object", 0), latch=True)
        procedure._children[-1].remap('Target', 'ObservationPose')
        #Register
        procedure.addChild(self.getProcedure("CleanParam", "clean_param"))
        procedure._children[-1].remap('Param', 'GraspingPose') 
        procedure.addChild(self.getProcedure("Registration", "registration"))
        #Move to grasp
        procedure.addChild(self.getProcedure("ArmObjectMotion", "arm_move_to_object", 0))
        procedure._children[-1].remap('Target', 'GraspingPose') 
        #Grasp
        gripper = self.getProcedure("GripperControlModule", "gripper_oc", 0)
        gripper.specify("Close", True)
        gripper.addPostCondition(self.getPropCond("NotOpen", "containerState", "Gripper", "Open", False))
        gripper.addPostCondition(self.getPropCond("Closed", "containerState", "Gripper", "Closed", True))
        procedure.addChild(gripper, latch=True)
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
        #=======PreConditions=========
        self.addPreCondition(self.getRelationCond("Holding", "contain", "Gripper", "Object", True));
        self.addPreCondition(self.getRelationCond("Carrying", "contain", "Robot", "PlacingKit", True));
        self.addPreCondition(self.getRelationCond("FitsIn", "fitsIn", "Object", "PlacingCell", True));
        self.addPreCondition(self.getPropCond("LocationEmpty", "containerState", "PlacingCell", "Empty", True));
        self.addPreCondition(self.getRelationCond("CellInKit", "contain", "PlacingKit", "PlacingCell", True));
        #=======PostConditions=========
        self.addPostCondition(self.getRelationCond("Holding", "contain", "Gripper", "Object", False));
        self.addPostCondition(self.getPropCond("LocationEmpty", "containerState", "PlacingCell", "Empty", False));
        self.addPostCondition(self.getPropCond("EmptyHanded", "containerState", "Gripper", "Empty", True));
        self.addPostCondition(self.getRelationCond("ObjectInCell", "contain", "PlacingCell", "Object", True));
        self.addPostCondition(self.getRelationCond("InKit", "inKit", "PlacingKit", "Object", True));
        
    def expand(self, procedure):
        #Locate kit box
        procedure.addChild(self.getProcedure("LocateKit", "locate_kit", 0))
        procedure._children[-1].remap('Kit', 'PlacingKit')
        #Move to place
        procedure.addChild(self.getProcedure("ArmObjectMotion", "arm_move_to_object", 0))
        procedure._children[-1].remap('Target', 'PlacingKit')
        #Open Gripper
        procedure.addChild(self.getProcedure("GripperControlModule", "gripper_oc", 0), latch=True)
        procedure._children[-1]._params.specify("Close", False)
        procedure._children[-1].addPostCondition(self.getPropCond("Open", "containerState", "Gripper", "Open", True));
        procedure._children[-1].addPostCondition(self.getPropCond("NotClosed", "containerState", "Gripper", "Closed", False));
        #
        #procedure.addChild(proc.copy(self._wm), latch=True)
        #procedure._children[-1].remap('From', 'PlacingKit')
        #procedure._children[-1].remap('To', 'Initial')
    def onInit(self):
        return True
        
    def execute(self):
        return True
        
class arm_move_to_kinematic(proc.ProcedureInstance):
    def createDescription(self):
        self._type = "ArmKinematicMotion"
        self._label = "arm_move_to_kinematic"
        self._params.addParam("Kinematic", wm.Element("Kinematic"), params.ParamTypes.Online)
        self._params.addParam("Arm", wm.Element("Arm"), params.ParamTypes.Hardware)
        self._params.addParam("Gripper", wm.Element("Gripper"), params.ParamTypes.Hardware)
        #=======PreConditions=========
        #=======PostConditions=========
        self.addPostCondition(self.getRelationCond("ArmAt", "at", "Arm", "Kinematic", True));
        
    def expand(self, procedure):
        procedure.addChild(self.getProcedure("ArmMotionPlan", "plan_aau"))
        procedure.addChild(self.getProcedure("ArmMotionExe", "move_exe"))
        
    def onInit(self):
        return True
        
    def execute(self):
        return True
        
class arm_move_to_object(proc.ProcedureInstance):
    def createDescription(self):
        self._type = "ArmObjectMotion"
        self._label = "arm_move_to_object"
        self.addParam("Initial", wm.Element("Spatial"), params.ParamTypes.Online)
        self.addParam("Target", wm.Element("Spatial"), params.ParamTypes.Online)
        self.addParam("Arm", wm.Element("Arm"), params.ParamTypes.Hardware)
        self.addParam("Gripper", wm.Element("Gripper"), params.ParamTypes.Hardware)
        #=======PreConditions=========
        self.addPreCondition(self.getRelationCond("GripperAt", "at", "Gripper", "Initial", True))
        self.addPreCondition(self.getHasPropCond("HasPosition", "Position", "Target", True))
        #=======PostConditions=========
        self.addPostCondition(self.getRelationCond("GripperAt", "at", "Gripper", "Initial", False))
        self.addPostCondition(self.getRelationCond("GripperAt", "at", "Gripper", "Target", True))
        
    def expand(self, procedure):
        procedure.addChild(self.getProcedure("InverseKinematic", "ik"))
        procedure.addChild(self.getProcedure("ArmMotionPlan", "plan_aau"))
        procedure.addChild(self.getProcedure("ArmMotionExe", "move_exe"))
        return
        
    def onInit(self):
        return True
        
    def execute(self):
        return True
                
class ik(proc.ProcedureInstance):
    def createDescription(self):
        self._type = "InverseKinematic"
        self._label = "ik"
        #=======Params=========
        self.addParam("Target", wm.Element("Product"), params.ParamTypes.Online)
        self.addParam("InitialKinematic", wm.Element("Kinematic"), params.ParamTypes.Optional)
        self.addParam("TargetKinematic", wm.Element("Kinematic"), params.ParamTypes.Optional)
        self.addParam("Arm", wm.Element("Arm"), params.ParamTypes.Hardware)
        #=======PreConditions=========
        self.addPreCondition(self.getHasPropCond("HasPosition", "Position", "Target", True))
        #=======PostConditions=========
        #self.addPostCondition(self.getIsSpecifiedCond("HasKinematic", "TargetKinematic", True))
        
    def onInit(self):
        return True
        
    def execute(self):
        return True
        
class plan_aau(proc.ProcedureInstance):
    def createDescription(self):
        self._type = "ArmMotionPlan"
        self._label = "plan_aau"
        #=======Params=========
        self.addParam("InitialKinematic", wm.Element("Kinematic"), params.ParamTypes.Online, [params.ParamOptions.Consume])
        self.addParam("TargetKinematic", wm.Element("Kinematic"), params.ParamTypes.Online, [params.ParamOptions.Consume])
        self.addParam("Trajectory", wm.Element("Trajectory"), params.ParamTypes.Optional)
        self.addParam("Arm", wm.Element("Arm"), params.ParamTypes.Hardware)
        #=======PreConditions=========
        #self.addPreCondition(self.getIsSpecifiedCond("HasKinematic", "TargetKinematic", True))
        #=======PostConditions=========
        #self.addPostCondition(self.getIsSpecifiedCond("HasTrajectory", "Trajectory", True))
        
    def onInit(self):
        return True
        
    def execute(self):
        return True
        
class move_exe(proc.ProcedureInstance):
    def createDescription(self):
        self._type = "ArmMotionExe"
        self._label = "move_exe"
        #=======Params=========
        self.addParam("Trajectory", wm.Element("Trajectory"), params.ParamTypes.Online, [params.ParamOptions.Consume])
        self.addParam("Arm", wm.Element("Arm"), params.ParamTypes.Hardware, [params.ParamOptions.Lock])
        self.addParam("Gripper", wm.Element("Gripper"), params.ParamTypes.Hardware)
        #=======PreConditions=========
        #=======PostConditions=========
        
    def onInit(self):
        return True
        
    def execute(self):
        return True    
                            
class locate_aau(proc.ProcedureInstance):
    def createDescription(self):
        self._type = "Locate"
        self._label = "locate_aau"
        #=======Params=========
        self.addParam("Container", wm.Element("Location"), params.ParamTypes.Online)
        self.addParam("Object", wm.Element("Product"), params.ParamTypes.Optional)
        self.addParam("ObservationPose", wm.Element("ObservationPose"), params.ParamTypes.Optional)
        self.addParam("Camera", wm.Element("Camera"), params.ParamTypes.Hardware)
        #=======PreConditions=========
        self.addPreCondition(self.getRelationCond("HasView", "hasViewOn", "Camera", "Container", True))
        #=======PostConditions=========
        self.addPostCondition(self.getRelationCond("InContainer", "contain", "Container", "Object", True));
        self.addPostCondition(self.getHasPropCond("HasPosition", "Position", "Object", True));
        self.addPostCondition(self.getRelationCond("HasObservationPose", "contain", "Object", "ObservationPose", True));
        self.addPostCondition(self.getHasPropCond("HasPosition", "Position", "ObservationPose", True));
        
    def onInit(self):
        return True
        
    def execute(self):
        obj = self._params.getParamValue("Object")
        obj.addProperty("Position", [0,0,0])
        self._params.specify("Object", obj)
        return True
          
class clean_param(proc.ProcedureInstance):
    def createDescription(self):
        self._type = "CleanParam"
        self._label = "clean_param"
        #=======Params=========
        self.addParam("Param", wm.Element("Thing"), params.ParamTypes.Optional, [params.ParamOptions.Consume])
        
    def onInit(self):
        return True
        
    def execute(self):
        return True
        
class locate_kit(proc.ProcedureInstance):
    def createDescription(self):
        self._type = "LocateKit"
        self._label = "locate_kit"
        #=======Params=========
        self.addParam("Kit", wm.Element("Kit"), params.ParamTypes.Online)
        self.addParam("Camera", wm.Element("Camera"), params.ParamTypes.Hardware)
        #=======PreConditions=========
        #self.addPreCondition(self.getRelationCond("HasView", "hasViewOn", "Camera", "Kit", True));
        #=======PostConditions=========
        self.addPostCondition(self.getHasPropCond("HasPosition", "Position", "Kit", True));
        
    def onInit(self):
        return True
        
    def execute(self):
        return True
       
class gripper_oc(proc.ProcedureInstance):
    def createDescription(self):
        self._type = "GripperControlModule"
        self._label = "gripper_oc"
        #=======Params=========
        self.addParam("Modality", -1, params.ParamTypes.Offline)
        self.addParam("Close", True, params.ParamTypes.Offline)
        self.addParam("Gripper", wm.Element("Gripper"), params.ParamTypes.Hardware)
        #=======PreConditions=========
        #=======PostConditions=========
        
    def onInit(self):
        return True
        
    def execute(self):
        return True    
        
class registration(proc.ProcedureInstance):
    def createDescription(self):
        self._type = "Registration"
        self._label = "registration"
        #=======Params=========
        self.addParam("ObservationPose", wm.Element("ObservationPose"), params.ParamTypes.Online)
        self.addParam("GraspingPose", wm.Element("GraspingPose"), params.ParamTypes.Optional)
        self.addParam("Object", wm.Element("Product"), params.ParamTypes.Online)
        self.addParam("Camera", wm.Element("Camera"), params.ParamTypes.Hardware)
        self.addParam("Gripper", wm.Element("Gripper"), params.ParamTypes.Hardware)
        #=======PreConditions=========
        self.addPreCondition(self.getRelationCond("HasCloseView", "at", "Gripper", "ObservationPose", True))
        #=======PostConditions=========
        self.addPostCondition(self.getRelationCond("HasGraspingPose", "contain", "Object", "GraspingPose", True));
        self.addPostCondition(self.getHasPropCond("HasPosition", "Position", "GraspingPose", True));
        
    def onInit(self):
        return True
        
    def execute(self):
        return True