
class bt():
    SUCCESS = 'SUCCESS' #1
    FAILURE = 'FAILURE' #2
    RUNNING = 'RUNNING' #3


    NO_SET             = 0x00
    VAL                = 0x01
    VAR                = 0x02

    EQUAL              = 0x10
    NOT_EQUAL          = 0x20
    GREATER_THAN       = 0x30
    GREATER_THAN_EQUAL = 0x40
    LESS_THAN          = 0x50
    LESS_THAN_EQUAL    = 0x60

    def set_type(num):
        n = 0
        return (num // 0x10**n % 0x10) << 4*n

    def equality(num):
        n = 1
        return (num // 0x10**n % 0x10) << 4*n

    #The different types of nodes
    LEAF = 0
    BRANCH = 1
    PROPERTY = 2




class col():
    SET_OUTPUT_TEST = 111

    #NODE
    NAME = 0
    TYPE_INFO = 1
    DESCRIPTION = 2

    #SystemNode
    BACKGROUND_SVG = 3
    MOVABLE_ICONS = 4

    #BehaviorNode
    STATE = 5
    BEHAVIORS = 6
    STATES = 7

    #DeviceNode

    #DeviceIconNode
    SVG = 8
    LAYER = 9
    DEFAULT_LAYER = 10
    X = 11
    Y = 12
    SCALE = 13
    ROTATION = 14

    HAS_TEXT = 15
    TEXT = 16
    TEXT_X = 17
    TEXT_Y = 18
    FONT_SIZE = 19
    FONT_COLOR = 20

    POS = 21

    #HalNode
    HAL_PIN = 22
    HAL_PIN_TYPE = 23

    #FIXME
    HAL_VALUE = 24 #True/False
    VALUE = 25 #Value used in the gui

    #DigitalInputNode
    VALUE_OFF = 26
    VALUE_ON = 27

    #AnalogInputNode
    UNITS = 28
    DISPLAY_DIGITS = 29
    DISPLAY_SCIENTIFIC = 30
    CALIBRATION_TABLE_MODEL = 31

    #All var nodes
    USER_MANUAL_SET = 32

    #BoolVarNode
    OFF_NAME = 33
    ON_NAME = 34

    #IntVarNode and FloatVarNode
    MIN = 35
    MAX = 36

    ######################
    ### Behavior Model ###
    BT_STATUS = 100
    WAIT_TIME = 101
    VAR_NODE_NAME = 102

    #Message, Dialog, and Alert Nodes
    SUCCESS_TEXT = 103
    FAIL_TEXT = 104
    TICK_RATE_MS = 105

    DEVICE_STATE = 106
    NEW_LINE = 107
    MAN_BTN_NEW_LINE = 108
    MAN_BTN_SPAN_COL_END = 109
    
    TIMEOUT_SEC = 110
    NUMBER_REPEATS = 111 
    IGNORE_FAILURE = 112 

    ALERT_TYPE = 113
    SET_TYPE = 114

    COMPARE_2_NAME = 115
    TOLERANCE_SCALE_VALUE = 116
    TOLERANCE_SCALE_NAME = 117
    TOLERANCE_OFFSET_VALUE = 118
    TOLERANCE_OFFSET_NAME = 119
    SET_TYPE_SCALE = 120
    SET_TYPE_OFFSET = 121
    

    #Run Behavior Node
    DEVICE_NAME = 122
    BEHAVIOR_NAME = 123


class typ():
    TOOL_NODE = 'Tool_Node'
    SYSTEM_NODE = 'System_Node'
    DEVICE_NODE = 'Device_Node'
    DEVICE_ICON_NODE =  'Device_Icon_Node'

    D_IN_NODE  = 'Digital_Input_Node'
    A_IN_NODE  = 'Analog_Input_Node'
    D_OUT_NODE = 'Digital_Output_Node'
    A_OUT_NODE = 'Analog_Output_Node'
    HAL_NODES = [D_IN_NODE, D_OUT_NODE, A_IN_NODE, A_OUT_NODE]
    BOOL_VAR_NODE = 'Bool_Var_Node'
    INT_VAR_NODE = 'Int_Var_Node'
    FLOAT_VAR_NODE = 'Float_Var_Node'

    #Behavior Tree Nodes
    ROOT_SEQUENCE_NODE = 'Root_Sequence'
    SEQUENCE_NODE = 'Sequence'
    REPEAT_NODE = 'Repeat'
    SELECTOR_NODE = 'Selector'
    WAIT_TIME_NODE = 'Wait_Time'
    WHILE_NODE = 'While'
    SET_NODE = 'Set'
    WAIT_NODE = 'Wait'
    TOLERANCE_NODE = 'Tolerance'
    MESSAGE_NODE = 'Message'
    DIALOG_NODE = 'Dialog'
    ALERT_NODE = 'Alert'
    ALERT_SEQUENCE_NODE = 'Alert_Sequence'
    SUCCESS_NODE = 'Success'
    FAILURE_NODE = 'Failure'
    SET_ICON_NODE = 'Set_Icon'
    SET_DEVICE_STATE_NODE = 'Set_Device_State'
    RUN_BEHAVIOR_NODE = 'Run_Behavior'
    WAIT_STATE_NODE = 'Wait_State'

    SETPOINT = 'Setpoint'
    RUN_BEHAVIOR_SETPOINT = 'Run_Behavior_Setpoint'
    WAIT_STATE_SETPOINT = 'Wait_State_Setpoint'
    TOLERANCEPOINT = 'Tolerancepoint'
    PROPERTY_SETPOINT = 'Property_Setpoint'
    BEHAVIOR_INPUT = 'Behavior_Input'









class defaults():
    SYSTEM_BACKGROUND    =  'opentoolcontroller/resources/icons/general/generic_system_background.svg'
    DEVICE_ICON          = 'opentoolcontroller/resources/icons/general/unknown.svg'
    A_DISPLAY_DIGITS     = 2
    A_DISPLAY_DIGITS_MAX = 10

