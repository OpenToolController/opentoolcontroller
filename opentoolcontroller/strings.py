
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
    NAME          = 0
    TYPE_INFO     = 1
    DESCRIPTION   = 2

    #SystemNode
    BACKGROUND_SVG = 10
    MOVABLE_ICONS = 11

    #DeviceNode
    STATE = 10
    BEHAVIORS = 11
    STATES = 12

    #DeviceIconNode
    SVG       = 10
    LAYER     = 11
    X         = 12
    Y         = 13
    SCALE     = 14
    ROTATION  = 15
    DEFAULT_LAYER = 16
    HAS_TEXT  = 17
    TEXT      = 18
    TEXT_X    = 19
    TEXT_Y    = 20
    FONT_SIZE = 21
    FONT_COLOR = 22
    POS       = 23

    ICON_POS = 27
    ICON_SCALE = 28
    ICON_ROTATION  = 29

    #SET_ICON_LAYER = 30
    SET_ICON_X = 31
    SET_ICON_Y = 32
    SET_ICON_SCALE = 33
    SET_ICON_ROTATION  = 34

    SET_TYPE = 35
    VAR_NODE_NAME = 36


    #Value is always the value in terms of the GUI, where as there's also HAL_VALUE
    #The variables use VALUE but the Hal nodes use display_value since it's a convertred number
    #Need to keep the same (30) because we use the same display code for read only HAL and variables
    VALUE = 30
    #DISPLAY_VALUE = VALUE

    HAL_VALUE = 20 #True/False

    #HalNode
    HAL_PIN      = 40
    HAL_PIN_TYPE = 41

    #DigitalInputNode
    VALUE_OFF = 23
    VALUE_ON  = 24

    #AnalogInputNode
    UNITS                   = 22
    DISPLAY_DIGITS          = 23
    DISPLAY_SCIENTIFIC      = 24
    CALIBRATION_TABLE_MODEL = 25



    #All var nodes
    USER_MANUAL_SET = 10

    #BoolVarNode
    OFF_NAME      = 11
    ON_NAME       = 12

    #IntVarNode and FloatVarNode
    MIN           = 11
    MAX           = 12



    #?
    BT_STATUS = 1
    WAIT_TIME = 30
    HAL_NODE = 31

    POS       = 220 #move all the pos things to this
    XY         = 221

    SET_NODE_SETPOINTS = 222

    WAIT_NODE_WAITPOINTS = 223
    WAIT_NODE_WAIT_TYPE = 224
    WAIT_NODE_BUFFER_TYPE = 225
    WAIT_NODE_TIMEOUT = 226

    #used on Message, Dialog, and Alert Nodes
    POSSIBLE_NODES = 227
    MESSAGE_DATA = 228
    SUCCESS_TEXT = 229
    FAIL_TEXT = 230
    ICON_LAYER = 231

    TICK_RATE_MS = 232


    #new message node stuff
    POST_TO_ALERTS = 234
    POST_TO_MESSAGE = 235

    DEVICE_STATE = 236
    NEW_LINE = 237
    MAN_BTN_NEW_LINE = 238
    MAN_BTN_SPAN_COL_END = 239
    

    TIMEOUT_SEC = 240
    NUMBER_REPEATS = 241
    IGNORE_FAILURE = 242

    ALERT_TYPE = 243

    COMPARE_2_NAME = 244
    TOLERANCE_SCALE_VALUE = 245
    TOLERANCE_SCALE_NAME = 246
    TOLERANCE_OFFSET_VALUE = 247
    TOLERANCE_OFFSET_NAME = 248
    SET_TYPE_SCALE = 249
    SET_TYPE_OFFSET = 250

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

    SETPOINT = 'Setpoint'
    TOLERANCEPOINT = 'Tolerancepoint'
    PROPERTY_SETPOINT = 'Property_Setpoint'
    BEHAVIOR_INPUT = 'Behavior_Input'









class defaults():
    SYSTEM_BACKGROUND    =  'opentoolcontroller/resources/icons/general/generic_system_background.svg'
    DEVICE_ICON          = 'opentoolcontroller/resources/icons/general/unknown.svg'
    A_DISPLAY_DIGITS     = 2
    A_DISPLAY_DIGITS_MAX = 10

