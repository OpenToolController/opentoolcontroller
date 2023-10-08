#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt5 import QtCore, QtGui, QtXml, QtWidgets
import sys
import re
import xml.etree.ElementTree as ET
import json
import os.path
import numpy as np
import queue

from opentoolcontroller.bt_model import BTModel
from opentoolcontroller.strings import defaults, col, typ
from opentoolcontroller.message_box import MessageBox
from opentoolcontroller.calibration_table_model import CalibrationTableModel


def clamp(n, smallest, largest): return max(smallest, min(n, largest))

def str2bool(v):
  return v.lower() in ("yes", "true", "t", "1")

#Sending a list ['one','two','etc'] so we don't use *enumerated
def enum(enumerated):
    enums = dict(zip(enumerated, range(len(enumerated))))
    enums["names"] = enumerated
    return type('enum', (), enums)


class Node:
    def __init__(self, parent=None):
        super().__init__()

        self._parent = parent
        self._children = []
        self._name = "unknown"
        self._description = ''

        if parent is not None:
            parent.addChild(self)


    def attrs(self):
        kv = {}
        my_classes = self.__class__.__mro__

        for cls in my_classes:
            for key, val in sorted(iter(cls.__dict__.items())):
                if isinstance(val, property):
                    kv[key] = val.fget(self)
        return kv

    def loadAttrs(self, data):
        try:
            #Get all the attributes of the node
            attrs = iter(self.attrs().items())
            for key, value in attrs:
                if key in data:
                    setattr(self, key, data[key])

        except Exception as e:
            MessageBox("Error loading attribute", e)#, key, value)



    def convertToDict(self, o):
        #Need to manually add type_info and children since they aren't properties
        data = {"type_info": o.typeInfo(),
                "children" : o.children()}

        attrs = iter(o.attrs().items())
        for key, value in attrs:
            data[key] = value

        return data

    def asJSON(self):
        data = json.dumps(self, default=self.convertToDict,  sort_keys=True, indent=4)
        return data

    def typeInfo(self):
        return 'root'

    def parent(self):
        return self._parent

    def child(self, row):
        return self._children[row]

    def addChild(self, child):
        self._children.append(child)
        child._parent = self
        child.name = child.name #Force the name to be unique

    def insertChild(self, position, child):
        if position < 0 or position > len(self._children):
            return False

        self._children.insert(position, child)
        child._parent = self
        child.name = child.name #Force the name to be unique
        return True


    def children(self):
        return self._children

    def childCount(self):
        return len(self._children)

    def removeChild(self, position):
        if position < 0 or position >= len(self._children):
            return False

        child = self._children.pop(position)
        child._parent = None

        return True


    def row(self):
        if self._parent is not None:
            return self._parent._children.index(self)
        else:
            return 0


    def data(self, c):
        if   c is col.NAME: return self.name
        elif c is col.TYPE_INFO: return self.typeInfo()
        elif c is col.DESCRIPTION: return self.description

    def setData(self, c, value):
        if   c is col.NAME: self.name = value
        elif c is col.TYPE_INFO: pass
        elif c is col.DESCRIPTION: self.description = value

    def name():
        def fget(self):
            return self._name

        def fset(self,value):
            #Sibling names must be unique, only allowing alpha numeric, _ and -
            value = str(value)
            value = re.sub(r'[^a-zA-Z0-9_-]', '',value)

            if self.parent() == None:
                self._name = value

            else:
                sibling_names = []

                for child in self.parent().children():
                    if child != self:
                        sibling_names.append(child.name)

                while value in sibling_names:
                    value = value + "_new"

                self._name = value

        return locals()
    name = property(**name())

    def description():
        def fget(self): return self._description
        def fset(self, value): self._description = str(value)
        return locals()
    description = property(**description())

'''
Things you might want to do with a behavior:
  - Run it
  - See what it's reporting out
  - Abort it (forced and controled)
  - send it an endpoint signal? (for behaviors with files with steps)

  parts that routh through the model for display
    - list of behaviors to make buttons
    - currently running behaviors name
    - currently running behavior
    - currently running behaviors info text (or nodes status???)

.... so we're gonna generate text from the behavior nodes then display it

'''

class BehaviorNode(Node):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = 'unknown'
        self._behaviors = []
        self._behavior_files = []
        self._states = []
        self._running_behavior = None
        self._running_behavior_name = ''
        self._behavior_info_text = ''

    def data(self, c):
        r = super().data(c)
        if   c is col.STATE     : r = self._state
        elif c is col.BEHAVIORS : r = self._behaviors
        elif c is col.STATES    : r = self._states
        elif c is col.RUNNING_BEHAVIOR_NAME : r = self._running_behavior_name
        elif c is col.RUNNING_BEHAVIOR : r = self._running_behavior
        elif c is col.BEHAVIOR_INFO_TEXT : r = self._behavior_info_text
        return r

    def setData(self, c, value):
        super().setData(c, value)
        if   c is col.STATE     : self._state = str(value)
        elif c is col.BEHAVIORS : pass #needs to be handled by the model to sync
        elif c is col.STATES    : self._states = value
        elif c is col.RUNNING_BEHAVIOR_NAME : self._running_behavior_name = value
        elif c is col.RUNNING_BEHAVIOR :
            print("HMM: ", value)
            self._running_behavior = value
        elif c is col.BEHAVIOR_INFO_TEXT : self._behavior_info_text = value

    def state(self):
        return self._state

    #TODO the system needs the same interfaces as the user for aborting and keeping track of what behavior is running 
    # maybe make a flat display of running behaviors? and allow visibilty of tool /system / device levels?
    # or make that display part of the tree?
    # Should be able to abort behaviros, orat least tool and system ones?
    # Abort button? should that just be a tool behavior?
    # Idle tool? (or similar) that's just a tool behavior?
    # When we can run device behaviors by hand then must disable system / tool behaviors
    # # Get a list of running behaviors with abort option of the category you can start?

    # - probably make a runningBehavior() function? hmm

    '''
    should device behaviors be abortable? ~~ probably, but only when you can manually operate devices
    system can be either in manual or auto (maintenance / online)?
    online systems can by used by tool behaviors, need system behaviors to be able to check that state
    
    SystemOperationMode
        what if this is a switch on the system graphic?
        - Online for process
            This is full auto, user can't run system or device behaviors, the tool Behaviors can start system behaviors
        - Manual
            User is allowed to start system behaviors
        - Manual
            User is allowed to start device behaviors
            User is allowed to start system and device behaviors


    actually 3 states
        - online for process
        - offline for maintenance
        - manual



    '''

    def behaviors(self):
        return self._behaviors

    def setBehaviors(self, value):
        self._behaviors = value

    def runningBehavior(self):
        return self._running_behavior

    def loadBehaviors(self):
        self._behaviors = []
        for file in self._behavior_files:
            bt_model = BTModel()
            bt_model.setFile(file)
            self._behaviors.append(bt_model)

    def behaviorFiles():
        def fget(self):
            files = []
            for behavior in self._behaviors:
                files.append(behavior.file())

            return files

        def fset(self, behavior_files):
            self._behavior_files = behavior_files

        return locals()
    behaviorFiles = property(**behaviorFiles())

    def states():
        def fget(self): return self._states
        def fset(self,value): self._states = value
        return locals()
    states = property(**states())



class ToolNode(BehaviorNode):
    def __init__(self, parent=None):
        super().__init__(parent)

    def typeInfo(self):
        return typ.TOOL_NODE


class SystemNode(BehaviorNode):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._background_svg = defaults.SYSTEM_BACKGROUND
        self._movable_icons = False
        self._system_is_online = False
        self._device_manual_control = False

    def typeInfo(self):
        return typ.SYSTEM_NODE

    def data(self, c):
        r = super().data(c)
        if   c is col.BACKGROUND_SVG        : r = self.backgroundSVG
        elif c is col.MOVABLE_ICONS         : r = self.movableIcons()
        elif c is col.SYSTEM_IS_ONLINE      : r = self.systemIsOnline
        elif c is col.DEVICE_MANUAL_CONTROL : r = self.deviceManualControl
        return r

    def setData(self, c, value):
        super().setData(c, value)
        if   c is col.BACKGROUND_SVG        : self.backgroundSVG = value
        elif c is col.MOVABLE_ICONS         : self._movable_icons = value
        elif c is col.SYSTEM_IS_ONLINE      : self.systemIsOnline = value
        elif c is col.DEVICE_MANUAL_CONTROL : self.deviceManualControl = value

    def movableIcons(self):
        return self._movable_icons

    def backgroundSVG():
        def fget(self): return self._background_svg
        def fset(self, value):
            if isinstance(value, str) and os.path.isfile(value):
                self._background_svg = value
            else:
                self._background_svg =  defaults.SYSTEM_BACKGROUND
        return locals()
    backgroundSVG = property(**backgroundSVG())


    def systemIsOnline():
        def fget(self): return self._system_is_online
        def fset(self, value): self._system_is_online = bool(value)
        return locals()
    systemIsOnline = property(**systemIsOnline())

    def deviceManualControl():
        def fget(self): return self._device_manual_control
        def fset(self, value): self._device_manual_control = bool(value)
        return locals()
    deviceManualControl = property(**deviceManualControl())





# This has to be fixed after the IO nodes are fixed
class DeviceNode(BehaviorNode):
    def __init__(self, parent=None):
        super().__init__(parent)

    def typeInfo(self):
        return typ.DEVICE_NODE

    def data(self, c):
        r = super().data(c)
        return r

    def setData(self, c, value):
        super().setData(c, value)




#TODO: Add background and font color and left/right align
class DeviceIconNode(Node):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._name     = 'Icon'
        self._x        = 50.0
        self._y        = 50.0
        self._rotation = 0.0
        self._scale    = 1.0
        self._default_layer = None

        self._layer = None
        self._layers = []

        self._has_text = False
        self._text = ''
        self._text_x = 0
        self._text_y = 0

        self._font_size = 12
        self._min_font_size = 6
        self._max_font_size = 72
        self._font_color = QtGui.QColor(0xFFFFFF) 

        self.svg = defaults.DEVICE_ICON        #'opentoolcontroller/resources/icons/general/unknown.svg'

    def typeInfo(self):
        return typ.DEVICE_ICON_NODE

    def layer(self):
        if self._layer is None:
            return self._default_layer
        return self._layer #the name of the current layer
    
    def setLayer(self, value):
        if value in self._layers:
            self._layer = value
        else:
            self._layer = self._layers[0]

    def layers(self):
        return self._layers #a list of layer names

    def fontColor(self):
        return self._font_color

    def data(self, c):
        r = super().data(c)

        if   c is col.SVG           : r = self.svg
        elif c is col.LAYER         : r = self.layer()
        elif c is col.DEFAULT_LAYER : r = self.defaultLayer
        elif c is col.X             : r = self.x
        elif c is col.Y             : r = self.y
        elif c is col.SCALE         : r = self.scale
        elif c is col.ROTATION      : r = self.rotation

        elif c is col.HAS_TEXT      : r = self.hasText
        elif c is col.TEXT          : r = self._text
        elif c is col.TEXT_X        : r = self.textX
        elif c is col.TEXT_Y        : r = self.textY
        elif c is col.FONT_SIZE     : r = self.fontSize
        elif c is col.FONT_COLOR    : r = self._font_color

        elif c is col.POS      : r = QtCore.QPointF(self.x, self.y)

        return r

    def setData(self, c, value):
        super().setData(c, value)


        if   c is col.SVG           : self.svg            = value
        elif c is col.LAYER         : self.setLayer(value)
        elif c is col.DEFAULT_LAYER : self.defaultLayer   = value
        elif c is col.X             : self.x              = value
        elif c is col.Y             : self.y              = value
        elif c is col.SCALE         : self.scale          = value
        elif c is col.ROTATION      : self.rotation       = value

        elif c is col.HAS_TEXT      : self.hasText        = value
        elif c is col.TEXT          : self._text          = str(value)
        elif c is col.TEXT_X        : self.textX          = value
        elif c is col.TEXT_Y        : self.textY          = value
        elif c is col.FONT_SIZE     : self.fontSize       = value
        elif c is col.FONT_COLOR    : self._font_color = value

        elif c is col.POS:
            self.x = value.x()
            self.y = value.y()


    def text(self):
        return self._text


   #All of these properties get saved
    def svg():
        def fget(self):
            return self._svg

        def fset(self, value):
            try:
                self._svg = value
                self._layers = []
                xml = ET.parse(self._svg)
                svg = xml.getroot()

                for child in svg:
                    self._layers.append(child.attrib['id'])

            except:
                self._svg = 'opentoolcontroller/resources/icons/general/unknown.svg'
                xml = ET.parse(self._svg)
                svg = xml.getroot()

                for child in svg:
                    self._layers.append(child.attrib['id'])

        return locals()
    svg = property(**svg())

    def pos(self):
        return QtCore.QPoint(self._x, self._y)

    def x():
        def fget(self): return self._x
        def fset(self,value): self._x = float(value)
        return locals()
    x = property(**x())

    def y():
        def fget(self): return self._y
        def fset(self,value): self._y = float(value)
        return locals()
    y = property(**y())

    def scale():
        def fget(self): return self._scale
        def fset(self,value): self._scale = float(value)
        return locals()
    scale = property(**scale())

    def rotation():
        def fget(self): return self._rotation
        def fset(self,value): self._rotation = float(value)
        return locals()
    rotation = property(**rotation())

    def hasText():
        def fget(self): return self._has_text
        def fset(self,value): self._has_text = bool(value)
        return locals()
    hasText = property(**hasText())

    def textX():
        def fget(self): return self._text_x
        def fset(self,value): self._text_x = float(value)
        return locals()
    textX = property(**textX())

    def textY():
        def fget(self): return self._text_y
        def fset(self,value): self._text_y = float(value)
        return locals()
    textY = property(**textY())

    def fontSize():
        def fget(self): return self._font_size
        def fset(self,value):
            self._font_size = clamp( int(value) , self._min_font_size, self._max_font_size)
        return locals()
    fontSize = property(**fontSize())

    def fontColorHex():
        def fget(self): return self._font_color.name()
        def fset(self, value): self._font_color = QtGui.QColor(value)
        return locals()
    fontColorHex = property(**fontColorHex())

    def defaultLayer():
        def fget(self): return self._default_layer
        def fset(self, value): self._default_layer = value
        return locals()
    defaultLayer = property(**defaultLayer())





'''
All Hal nodes have a Queue
  - Devices have a BT
  - The device BT puts values into a queue for the HalNode
  - System Auto: It's BT sends commnads to the device BT via Bool/Float var nodes
  - System Manual: Device manual view gets buttons/variables for the Bool/Float var nodes


Do we need this queue thing or can we just have the BT control loop also edit the Streamer ???

 - each device has a behavior tree
 - need a controller that run through each and builds a set of changes for the streamer


 a thread just processing behavior trees?
 .... for device in system
 ........ do stuff and set the values in the halQueue


 Then in the hardware thread
 .... for pin in pins
 ........ build new stream via queue
 .... if stream != prev_stream --> set streamer
'''

class HalNode(Node):
    '''Common to all IO nodes
        All IO Nodes have:
            - name           : The nodes name is used for the hal pin name, for >1 bit name_0, name_1, etc.  This is unique within a device
    '''
    hal_pins = []  # Format (pin_name, direction, type)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._name = 'HAL_Node'
        self._hal_pin = ''
        self._hal_pin_type = None
        self._hal_queue = queue.Queue()


    def typeInfo(self):
        raise NotImplementedError("Nodes that inherit HalNode must implement typeInfo")

    def data(self, c):
        r = super().data(c)
        if c is col.HAL_PIN:
            try:
                r = self.halPins().names.index(self._hal_pin) #Connected to a QComboBox which passes an index
            except:
                self.halPin = ''
                r = ''
        elif c is col.HAL_PIN_TYPE: r = self._hal_pin_type

        return r

    def setData(self, c, value):
        super().setData(c, value)

        if c is col.HAL_PIN:
            try:
                self.halPin = self.halPins().names[value] #Connected to a QComboBox so we use an index
            except:
                self.halPin = ''
        elif c is col.HAL_PIN_TYPE: pass

    def signalName(self):
        return self.parent().parent().name + '.' + self.parent().name + '.' + self.name + '.'

    def halQueueGet(self):
        try:
            return self._hal_queue.get_nowait()
        except queue.Empty:
            return None

    def halQueuePut(self, value):
        print("halQueuePut - ", value)
        self._hal_queue.put_nowait(value)

    def halQueueManualPut(self, value):
        with self._hal_queue.mutex:
            self._hal_queue.queue.clear()

        self._hal_queue.put_nowait(value)


    def halPinType(self):
        return self._hal_pin_type

    def halPin():
        def fget(self): return self._hal_pin
        def fset(self, value):
            try:
                pin = [item for item in HalNode.hal_pins if item[0] == value]
                self._hal_pin = pin[0][0]
                self._hal_pin_type = pin[0][1]
            except:
                self._hal_pin = ""
                self._hal_pin_type = None
        return locals()
    halPin = property(**halPin())



class DigitalInputNode(HalNode):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._name = 'Digital_Input_Node'
        self._hal_val = False
        self._off_name = ''
        self._on_name = ''

    def typeInfo(self):
        return typ.D_IN_NODE

    def data(self, c):
        r = super().data(c)
        if   c is col.HAL_VALUE : r = self._hal_val
        elif c is col.VALUE     : r = self._hal_val #self._on_name if self._hal_val else self._off_name
        elif c is col.OFF_NAME  : r = self.offName
        elif c is col.ON_NAME   : r = self.onName

        return r

    def setData(self, c, value):
        super().setData(c, value)
        if   c is col.HAL_VALUE : self._hal_val = True if bool(value) == True else False
        #elif c is col.VALUE     : self._hal_val = True if bool(value) == True else False #
        elif c is col.OFF_NAME  : self.offName = value
        elif c is col.ON_NAME   : self.onName  = value

    def halValue(self):
        return self._hal_val

    def value(self):
        return self._hal_val

    def halPins(self):
        all_pins = HalNode.hal_pins #list of (name, type, dir)
        sub_pins = [item for item in all_pins if item[1] == 'bit']
        pins = [item[0] for item in sub_pins if item[2] == 'OUT']
        pins.insert(0, '')
        return enum(pins)

    def offName():
        def fget(self): return self._off_name
        def fset(self,value): self._off_name = str(value)
        return locals()
    offName = property(**offName())

    def onName():
        def fget(self): return self._on_name
        def fset(self,value): self._on_name = str(value)
        return locals()
    onName = property(**onName())


class DigitalOutputNode(DigitalInputNode):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._name = 'Digital_Output_Node'
        self._enable_manual = True
        self._view_only = True

    def typeInfo(self):
        return typ.D_OUT_NODE

    def halPins(self):
        all_pins = HalNode.hal_pins #list of (name, type, dir)
        sub_pins = [item for item in all_pins if item[1] == 'bit']
        pins = [item[0] for item in sub_pins if item[2] == 'IN']
        pins.insert(0, '')

        return enum(pins)


    def data(self, c):
        r = super().data(c)


        return r

    def setData(self, c, value):
        super().setData(c, value)
        if   c is col.VALUE:
            value = True if value == True else False
            self.halQueuePut(value)



#TODO figure out the number type part
class AnalogInputNode(HalNode):
    '''
        Represents an analog input (i.e. 0-10 VDC) for a device
            - calibration_table_model : Calibration of analog signal to HAL numbers
            - calibration_table_data : This property is used to load and save cal data
            - display_digits : number of digits to display on default
            - display_scientific : If true use scientific notation
    '''
    def __init__(self, parent=None):
        super().__init__(parent)
        self._name = 'Analog_Input_Node'

        self._hal_val = 0
        self._val = 0
        self._units = ''

        self._display_digits = defaults.A_DISPLAY_DIGITS
        self._display_scientific = False

        self._calibration_table_model = CalibrationTableModel()
        self._calibration_table_model.dataChanged.connect(self.updateScaleFactor)
        self._calibration_table_model.modelReset.connect(self.updateScaleFactor)

        self._xp = [0,0]
        self._yp = [0,0]


    def typeInfo(self):
        return typ.A_IN_NODE

    def calibrationTableModel(self):
        return self._calibration_table_model

    def data(self, c):
        r = super().data(c)

        if   c is col.HAL_VALUE               : r = self._hal_val
        elif c is col.VALUE                   : r = self.value()
        elif c is col.UNITS                   : r = self.units
        elif c is col.DISPLAY_DIGITS          : r = self.displayDigits
        elif c is col.DISPLAY_SCIENTIFIC      : r = self.displayScientific
        elif c is col.CALIBRATION_TABLE_MODEL : r = self._calibration_table_model

        return r


    def setData(self, c, value):
        super().setData(c, value)

        if   c is col.HAL_VALUE          : self._hal_val = value
        elif c is col.VALUE              : pass
        elif c is col.UNITS              : self.units = value
        elif c is col.DISPLAY_DIGITS     : self.displayDigits = value
        elif c is col.DISPLAY_SCIENTIFIC : self.displayScientific = value

    def value(self):
        return float(np.interp(self._hal_val, self._xp, self._yp))

    def displayToHal(self, val):
        return np.interp(val, self._yp, self._xp)

    def updateScaleFactor(self):
        try:
            self._xp = self._calibration_table_model.halValues()
            self._yp = self._calibration_table_model.guiValues()
        except:
            self._xp = [0,10]
            self._yp = [0,10]

    def halPins(self):
        all_pins = HalNode.hal_pins #list of (name, type, dir)
        sub_pins = [item for item in all_pins if item[1] in ['s32','u32','float']]
        pins = [item[0] for item in sub_pins if item[2] == 'OUT']
        pins.insert(0, '')
        return enum(pins)

    def units():
        def fget(self): return self._units
        def fset(self, value): self._units = str(value)
        return locals()
    units = property(**units())

    def displayDigits():
        def fget(self): return self._display_digits
        def fset(self, value):
            self._display_digits = clamp(int(value), 0, defaults.A_DISPLAY_DIGITS_MAX)
            self.updateScaleFactor()
        return locals()
    displayDigits = property(**displayDigits())

    def displayScientific():
        def fget(self): return self._display_scientific
        def fset(self, value):
            if value == True or value == 'True':
                self._display_scientific = True
            else:
                self._display_scientific = False

        return locals()
    displayScientific = property(**displayScientific())

    def calibrationTableData():
        def fget(self):
            return self.calibrationTableModel().dataArray()

        def fset(self, value):
            try:
                self.calibrationTableModel().setDataArray(value)
                self.updateScaleFactor()
            except Exception as e:
                MessageBox("Malformed calibration table data", e, value)

        return locals()
    calibrationTableData = property(**calibrationTableData())


class AnalogOutputNode(AnalogInputNode):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._name = 'Analog_Output_Node'
        self._max = 0
        self._min = 0

    def typeInfo(self):
        return typ.A_OUT_NODE

    def data(self, c):
        r = super().data(c)
        if   c is col.MIN  : r = self.min
        elif c is col.MAX  : r = self.max
        return r

    def setData(self, c, value):
        super().setData(c, value)
        if   c is col.MIN  : self.min = value
        elif c is col.MAX  : self.max = value

    def halPins(self):
        all_pins = HalNode.hal_pins #list of (name, type, dir)
        sub_pins = [item for item in all_pins if item[1] in ['s32','u32','float']]
        pins = [item[0] for item in sub_pins if item[2] == 'IN']
        pins.insert(0, '')
        return enum(pins)

    def min():
        def fget(self): return self._min
        def fset(self, value): self._min = float(value)
        return locals()
    min = property(**min())

    def max():
        def fget(self): return self._max
        def fset(self, value): self._max = float(value)
        return locals()
    max = property(**max())


class BoolVarNode(Node):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._name = 'Bool_Var_Node'
        self._val = False
        self._off_name = ''
        self._on_name = ''
        self._user_manual_set = True

    def typeInfo(self):
        return typ.BOOL_VAR_NODE

    def data(self, c):
        r = super().data(c)
        if   c is col.VALUE           : r = self._val
        elif c is col.OFF_NAME        : r = self.offName
        elif c is col.ON_NAME         : r = self.onName
        elif c is col.USER_MANUAL_SET : r = self.userManualSet

        return r

    def setData(self, c, value):
        super().setData(c, value)
        if   c is col.VALUE           : self._val = True if value == True else False
        elif c is col.OFF_NAME        : self.offName = value
        elif c is col.ON_NAME         : self.onName = value
        elif c is col.USER_MANUAL_SET : self.userManualSet = value

    def value(self):
        return self._val

    def offName():
        def fget(self): return self._off_name
        def fset(self, value): self._off_name = str(value)
        return locals()
    offName = property(**offName())

    def onName():
        def fget(self): return self._on_name
        def fset(self, value): self._on_name = str(value)
        return locals()
    onName = property(**onName())

    def userManualSet():
        def fget(self): return self._user_manual_set
        def fset(self, value):
            if value == True or value == 'True':
                self._user_manual_set = True
            else:
                self._user_manual_set = False

        return locals()
    userManualSet = property(**userManualSet())

class IntVarNode(Node):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._name = 'Int_Var_Node'
        self._val = 0
        self._min = 0
        self._max = 0
        self._units = ''
        self._user_manual_set = True

    def typeInfo(self):
        return typ.INT_VAR_NODE

    def data(self, c):
        r = super().data(c)
        if   c is col.VALUE           : r = self._val
        elif c is col.MIN             : r = self.min
        elif c is col.MAX             : r = self.max
        elif c is col.UNITS           : r = self.units
        elif c is col.USER_MANUAL_SET : r = self.userManualSet
        return r

    def setData(self, c, value):
        super().setData(c, value)
        if c is col.VALUE             : self._val = int(clamp(int(value), self.min, self.max))
        elif c is col.MIN             : self.min = value
        elif c is col.MAX             : self.max = value
        elif c is col.UNITS           : self.units = value
        elif c is col.USER_MANUAL_SET : self.userManualSet = value

    def value(self):
        return self._val

    def min():
        def fget(self): return self._min
        def fset(self, value): self._min = int(value)
        return locals()
    min = property(**min())

    def max():
        def fget(self): return self._max
        def fset(self, value): self._max = int(value)
        return locals()
    max = property(**max())

    def units():
        def fget(self): return self._units
        def fset(self, value): self._units = str(value)
        return locals()
    units = property(**units())

    def userManualSet():
        def fget(self): return self._user_manual_set
        def fset(self, value):
            if value == True or value == 'True':
                self._user_manual_set = True
            else:
                self._user_manual_set = False

        return locals()
    userManualSet = property(**userManualSet())

class FloatVarNode(Node):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._name = 'Float_Var_Node'
        self._val = 0.0
        self._min = 0.0
        self._max = 0.0
        self._units = ''
        self._display_digits = defaults.A_DISPLAY_DIGITS
        self._display_scientific = False
        self._user_manual_set = True

    def typeInfo(self):
        return typ.FLOAT_VAR_NODE

    def data(self, c):
        r = super().data(c)
        if   c is col.VALUE              : r = self._val
        elif c is col.MIN                : r = self.min
        elif c is col.MAX                : r = self.max
        elif c is col.UNITS              : r = self.units
        elif c is col.DISPLAY_DIGITS     : r = self.displayDigits
        elif c is col.DISPLAY_SCIENTIFIC : r = self.displayScientific
        elif c is col.USER_MANUAL_SET    : r = self.userManualSet
        return r

    def setData(self, c, value):
        super().setData(c, value)
        if c is col.VALUE                : self._val = clamp(float(value), self.min, self.max)
        elif c is col.MIN                : self.min = value
        elif c is col.MAX                : self.max = value
        elif c is col.UNITS              : self.units = value
        elif c is col.DISPLAY_DIGITS     : self.displayDigits = value
        elif c is col.DISPLAY_SCIENTIFIC : self.displayScientific = value
        elif c is col.USER_MANUAL_SET    : self.userManualSet = value

    def value(self):
        return self._val

    def min():
        def fget(self): return self._min
        def fset(self, value): self._min = float(value)
        return locals()
    min = property(**min())

    def max():
        def fget(self): return self._max
        def fset(self, value): self._max = float(value)
        return locals()
    max = property(**max())

    def units():
        def fget(self): return self._units
        def fset(self, value): self._units = str(value)
        return locals()
    units = property(**units())

    def displayDigits():
        def fget(self): return self._display_digits
        def fset(self, value):
            self._display_digits = clamp(int(value), 0, defaults.A_DISPLAY_DIGITS_MAX)
        return locals()
    displayDigits = property(**displayDigits())

    def displayScientific():
        def fget(self): return self._display_scientific
        def fset(self, value):
            if value == True or value == 'True':
                self._display_scientific = True
            else:
                self._display_scientific = False

        return locals()
    displayScientific = property(**displayScientific())

    def userManualSet():
        def fget(self): return self._user_manual_set
        def fset(self, value):
            if value == True or value == 'True':
                self._user_manual_set = True
            else:
                self._user_manual_set = False

        return locals()
    userManualSet = property(**userManualSet())
