from PyQt5 import QtCore, QtGui, QtXml, QtWidgets
import xml.etree.ElementTree as ET

from opentoolcontroller.strings import bt, col, typ
from opentoolcontroller.message_box import MessageBox
import json
from string import Formatter
import time

import pprint
pp = pprint.PrettyPrinter(width=82, compact=True)

class BaseNode:
    def __init__(self, parent=None):
        super().__init__()
        self._parent = parent
        self._children = []

        self._root_node = None

        '''Do we need this???'''
        if parent is not None:
            parent.addChild(self)
        
    def setInfoText(self, text):
        self._root_node.setInfoText(text)

    def infoText(self):
        return self._root_node.infoText()

    def setRootNode(self, node):
        self._root_node = node
    
    def rootNode(self):
        return self._root_node

    def reset(self):
        pass

    def loadAttrs(self, data):
        try:
            #Get all the attributes of the node
            attrs = iter(self.attrs().items())
            for key, value in attrs:
                if key in data:
                    setattr(self, key, data[key])

        except Exception as e:
            MessageBox("Error setting attribute", e)

    def convertToDict(self, o):
        data = {"type_info": o.typeInfo()}

        if len(o.children()) > 0:
            data["children"] =  o.children()

        attrs = iter(o.attrs().items())
        for key, value in attrs:
            data[key] = value

        return data

    def asJSON(self):
        data = json.dumps(self, default=self.convertToDict,  sort_keys=True, indent=4)
        return data

    def attrs(self):
        kv = {}

        my_classes = self.__class__.__mro__
        for cls in my_classes:
            for k, v in sorted(iter(cls.__dict__.items())):
                if isinstance(v, property):
                    kv[k] = v.fget(self)
        return kv

    def typeInfo(self):
        raise NotImplementedError("Nodes that inherit BaseNode must implement typeInfo")


    def treeType(self):
        return bt.LEAF

    def parent(self):
        return self._parent

    def child(self, row):
        return self._children[row]

    def addChild(self, child):
        self._children.append(child)
        child._parent = self

    def insertChild(self, position, child):
        if position < 0 or position > len(self._children):
            return False

        self._children.insert(position, child)
        child._parent = self
        child.setRootNode(self.rootNode())

        return True

    def children(self):
        return self._children

    def childrenByTreeType(self, value):
        children = []

        for child in self.children():
            if child.treeType() == value:
                children.append(child)

        return children

    def childCount(self):
        return len(self._children)

    def removeChild(self, position):
        if position < 0 or position >= len(self._children):
            return False

        child = self._children.pop(position)
        child._parent = None

        return child

    def row(self):
        if self._parent is not None:
            return self._parent._children.index(self)
        else:
            return 0

    def data(self, column):
        if   column is col.TYPE_INFO: return self.typeInfo()

    def setData(self, column, value):
        if   column is col.TYPE_INFO: pass


class Node(BaseNode):
    def __init__(self, parent=None):
        super().__init__()
        self._pos = (0,0)
        self._status = None #Success/Failure/Running

    def reset(self):
        self._status = None
        for child in self.children():
            child.reset()

    def data(self, column):
        if   column is col.TYPE_INFO: return self.typeInfo()
        elif column is col.POS: return self._pos

    def setData(self, column, value):
        if   column is col.TYPE_INFO: pass
        elif column is col.POS: self._pos = value

    def width(self):
        return 120

    def height(self):
        return 60

    def status(self):
        return self._status

    def x(self):
        return self._pos[0]

    def y(self):
        return self._pos[1]

    def iconvertToDict(self, o):
        data = {"type_info": o.typeInfo(),
                "children" : o.children()}

        attrs = iter(o.attrs().items())
        for key, value in attrs:
            data[key] = value

        return data

    #Properties get saved to JSON
    def pos():
        def fget(self): return self._pos
        def fset(self, value):
            x = float(value[0])
            y = float(value[1])
            self._pos = (x,y)
        return locals()
    pos = property(**pos())


# Runs each child until one fails, if one fails returns failure.  If all succeed return success
class SequenceNode(Node):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_child = 0

    def typeInfo(self):
        return typ.SEQUENCE_NODE

    def reset(self):
        super().reset()
        self._current_child = 0

    def treeType(self):
        return bt.BRANCH

    def tick(self):
        if self._status in [bt.SUCCESS, bt.FAILURE]:
            return self._status

        else:
            for i, child in enumerate(self._children[self._current_child:]):
                result = child.tick()

                if result in [bt.RUNNING, bt.FAILURE]:
                    self._status = result
                    return self._status

                self._current_child = i

            self._status = bt.SUCCESS
            return self._status



class SelectorNode(Node):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_child = 0

    def typeInfo(self):
        return typ.SELECTOR_NODE

    def reset(self):
        super().reset()
        self._current_child = 0

    def treeType(self):
        return bt.BRANCH

    def tick(self):
        if self._status in [bt.SUCCESS, bt.FAILURE]:
            return self._status

        else:
            for i, child in enumerate(self._children[self._current_child:]):
                result = child.tick()

                if result == bt.RUNNING:
                    self._status = bt.RUNNING
                    return self._status

                elif result == bt.SUCCESS:
                    self._status = bt.SUCCESS
                    return self._status

                self._current_child = i

            self._status = bt.FAILURE
            return self._status


class RootSequenceNode(SequenceNode):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tick_rate_ms = 1000
        self._name = "Behavior Name"
        self._file = "" 
        self._manual_button_new_line = False
        self._manual_button_span_col_end = False

        self._info_text = '' #Nodes that wait display a text to the user
        self.setRootNode(self)

    def setInfoText(self, text):
        self._info_text = text

    def infoText(self):
        return self._info_text


    def typeInfo(self):
        return typ.ROOT_SEQUENCE_NODE

    def file(self):
        return self._file

    def setFile(self, value):
        print("RootSquence file: ", value)
        self._file = value

    def treeType(self):
        return bt.BRANCH

    def data(self, column):
        r = super().data(column)
        if   column is col.NAME                 : return self._name
        elif column is col.TICK_RATE_MS         : return self._tick_rate_ms
        elif column is col.MAN_BTN_NEW_LINE     : return self.manualButtonNewLine
        elif column is col.MAN_BTN_SPAN_COL_END : return self.manualButtonSpanColEnd
        return r

    def setData(self, column, value):
        super().setData(column, value)
        if   column is col.NAME                 : self._name = str(value)
        elif column is col.TICK_RATE_MS         : self._tick_rate_ms = int(value)
        elif column is col.MAN_BTN_NEW_LINE     : self.manualButtonNewLine = value
        elif column is col.MAN_BTN_SPAN_COL_END : self.manualButtonSpanColEnd = value


    def tick_rate_ms():
        def fget(self): return self._tick_rate_ms
        def fset(self, value): self._tick_rate_ms = int(value)
        return locals()
    tick_rate_ms = property(**tick_rate_ms())

    def name():
        def fget(self): return self._name
        def fset(self, value): self._name = str(value)
        return locals()
    name = property(**name())

    def manualButtonNewLine():
        def fget(self): return self._manual_button_new_line
        def fset(self, value): self._manual_button_new_line = bool(value)
        return locals()
    manualButtonNewLine = property(**manualButtonNewLine())

    def manualButtonSpanColEnd():
        def fget(self): return self._manual_button_span_col_end
        def fset(self, value): self._manual_button_span_col_end = bool(value)
        return locals()
    manualButtonSpanColEnd = property(**manualButtonSpanColEnd())


class RepeatNode(Node):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._number_repeats = 0
        self._number_repeats_remaining = 0
        self._ignore_failure = False
        self._current_child = 0

    def typeInfo(self):
        return typ.REPEAT_NODE

    def treeType(self):
        return bt.BRANCH

    def reset(self):
        super().reset()
        self._current_child = 0
        self._number_repeats_remaining = self._number_repeats 

    def data(self, column):
        r = super().data(column)
        if   column is col.NUMBER_REPEATS : return self.numberRepeats
        elif column is col.IGNORE_FAILURE : return self.ignoreFailure
        return r

    def setData(self, column, value):
        super().setData(column, value)
        if   column is col.NUMBER_REPEATS : self.numberRepeats = value
        elif column is col.IGNORE_FAILURE : self.ignoreFailure = value

    def tick(self):
        if self._status in [bt.SUCCESS, bt.FAILURE]:
            return self._status

        else:
            self._status = bt.RUNNING
            for i, child in enumerate(self._children[self._current_child:]):
                result = child.tick()

                if result is bt.RUNNING:
                    self._status = result
                    return self._status

                elif result is bt.FAILURE:
                    if self._ignore_failure:
                        break
                    else:
                        self._status = result
                        return self._status

                self._current_child = i


            if self._number_repeats_remaining > 0:
                self._number_repeats_remaining -= 1
                for child in self.children():
                    child.reset()
                self._current_child = 0
            
            else:
                if result == bt.SUCCESS:
                    self._status = bt.SUCCESS
                elif result == bt.FAILURE:
                    self._status = bt.FAILURE

            return self._status


    def numberRepeats():
        def fget(self): return self._number_repeats
        def fset(self, value):
            self._number_repeats = int(value)
            self._number_repeats_remaining = self._number_repeats 
        return locals()
    numberRepeats = property(**numberRepeats())

    def ignoreFailure():
        def fget(self): return self._ignore_failure
        def fset(self, value): self._ignore_failure = bool(value)
        return locals()
    ignoreFailure = property(**ignoreFailure())



class FailureNode(Node):
    def __init__(self, parent=None):
        super().__init__(parent)

    def typeInfo(self):
        return typ.FAILURE_NODE

    def treeType(self):
        return bt.LEAF

    def tick(self):
        self._status = bt.FAILURE
        return self._status

class SuccessNode(Node):
    def __init__(self, parent=None):
        super().__init__(parent)

    def typeInfo(self):
        return typ.SUCCESS_NODE

    def treeType(self):
        return bt.LEAF

    def tick(self):
        self._status = bt.SUCCESS
        return self._status


class WaitTimeNode(Node):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._wait_time = 0
        self._timer = QtCore.QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.tmr)

    def typeInfo(self):
        return typ.WAIT_TIME_NODE

    def treeType(self):
        return bt.LEAF

    def data(self, column):
        r = super().data(column)
        if   column is col.WAIT_TIME: r = self.wait_time
        return r

    def setData(self, column, value):
        super().setData(column, value)
        if   column is col.WAIT_TIME: self.wait_time = value

    def tmr(self):
        self._status = bt.SUCCESS

    def setInfoText(self, value):
        text = "Wait: %0.1f sec" % value
        super().setInfoText(text)

    def tick(self):
        if self._status == None:
            self._timer.setInterval(self._wait_time * 1000)
            self._timer.start()
            self._status = bt.RUNNING
            self.setInfoText(self._wait_time)
            return self._status

        if self._status == bt.RUNNING:
            self.setInfoText(self._timer.remainingTime()*0.001)

        return self._status


    #Properties get saved to JSON
    def wait_time():
        def fget(self): return self._wait_time
        def fset(self, value):
            self._wait_time = float(value)
        return locals()
    wait_time = property(**wait_time())


'''
PropertySetpoint
    set_type  : no_set / equal / not equal / greater / less
    name      : name of the property that is set
    value     : a hard coded value that is used
    var_index : the tool index that is used to get a dynamic value
    var_name  : the name of the tool index, used for saving



SetpointBase
    set_type  : no_set / equal / not equal / greater / less
    set_index : the tool index that is being done to
    set_name  : save

Setpoint(SetpointBase)
    value     : a hard coded value that is used
    var_index : the tool index that is used to get a dynamic value
    var_name  : save

RunBehaviorSetpoint(SetpointBase)
    behavior      :
    behavior_name : save

WaitStateSetpoint(SetpointBase)  
    state_name    :

Tolerancepoint(SetpointBase)
    #abs(compare_1 - compare_2) < (compare_2*tol_scale + tol_offset)
    compare_1_index  : tool index of value that we compare to  
    compare_1_name   : save
    compare_2_index  : tool index of value that we compare to  
    compare_2_name   : save

    tolerance_scale_index :
    tolerance_scale_name  :  save
    tolerance_scale_value : hard coded value

    tolerance_offset_index : = None
    tolerance_offset_name  : save
    tolerance_offset_value : hard coded value 

'''


class SetpointBase(BaseNode):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._set_type = bt.NO_SET
        self._set_index = None
        self._set_name = ""

    def setSetIndex(self, index):
        self._set_index = index

    def setIndex(self):
        return self._set_index

    def data(self, column):
        r = super().data(column)
        if   column is col.SET_TYPE : r = self.setType
        return r

    def setData(self, column, value):
        super().setData(column, value)
        if   column is col.SET_TYPE : self.setType = value

    def setType():
        def fget(self): return self._set_type
        def fset(self, v): self._set_type = v
        return locals()
    setType = property(**setType())

    def setName():
        def fget(self):
            try:
                return self._set_index.internalPointer().name
            except:
                return self._set_name
        def fset(self, value):
            self._set_name = value
        return locals()
    setName = property(**setName())


#A set node has a setpoint for each IO that can be set
class Setpoint(SetpointBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self._var_index = None
        self._var_name = ""

    def typeInfo(self):
        return typ.SETPOINT

    def treeType(self):
        return bt.PROPERTY

    def setVarIndex(self, index):
        self._var_index = index

    def varIndex(self):
        return self._var_index

    def data(self, column):
        r = super().data(column)
        if   column is col.VALUE         : r = self.value
        elif column is col.VAR_NODE_NAME : r = self.varName
        return r

    def setData(self, column, value):
        super().setData(column, value)
        if   column is col.VALUE         : self.value = value
        elif column is col.VAR_NODE_NAME : self.varName = value

    def value():
        def fget(self): return self._value
        def fset(self,value): self._value = value
        return locals()
    value = property(**value())

    def varName():
        def fget(self):
            try:
                return self._var_index.internalPointer().name
            except:
                return self._var_name
        def fset(self, value):
            self._var_name = value
        return locals()
    varName = property(**varName())

class RunBehaviorSetpoint(SetpointBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        #Runs a behavior of a device
        #need to store device and behavior name in order to load and sync from file
        
        self._behavior = None
        self._behavior_name = ''

    def typeInfo(self):
        return typ.RUN_BEHAVIOR_SETPOINT

    def treeType(self):
        return bt.PROPERTY

    def setBehavior(self, value):
        self._behavior = value

    def behavior(self):
        return self._behavior

    def data(self, column):
        r = super().data(column)
        if column is col.BEHAVIOR_NAME : r = self.behaviorName
        return r

    def setData(self, column, value):
        super().setData(column, value)
        if column is col.BEHAVIOR_NAME : self.behaviorName = value

    def behaviorName():
        def fget(self):
            try:
                return self._behavior.name()
            except:
                return self._behavior_name
        def fset(self, value):
            self._behavior_name = value
        return locals()
    behaviorName = property(**behaviorName())

class WaitStateSetpoint(SetpointBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = ''

    def typeInfo(self):
        return typ.WAIT_STATE_SETPOINT

    def treeType(self):
        return bt.PROPERTY

    def data(self, column):
        r = super().data(column)
        if column is col.STATE_SETPOINT : r = self.state
        return r

    def setData(self, column, value):
        super().setData(column, value)
        if column is col.STATE_SETPOINT : self.state = value

    def state():
        def fget(self): return self._state
        def fset(self, value): self._state = value
        return locals()
    state = property(**state())

#Used to set properties instead of IO.  SetIcon node has a PropertySetpoint for each property that is set
#maybe use property as part of this class name? SetProperty?
class PropertySetpoint(BaseNode):
    def __init__(self, parent=None):
        super().__init__(parent)
        #Similar to Setpoint but has a fixed name
        self._set_type = bt.NO_SET
        self._name = ""
        self._value = 0
        self._var_index = None
        self._var_name = ""

    def typeInfo(self):
        return typ.PROPERTY_SETPOINT

    def treeType(self):
        return bt.PROPERTY

    def setVarIndex(self, index):
        self._var_index = index

    def varIndex(self):
        return self._var_index

    def data(self, column):
        r = super().data(column)
        if   column is col.SET_TYPE      : r = self.setType
        elif column is col.VALUE         : r = self.value
        elif column is col.VAR_NODE_NAME : r = self.varName
        return r

    def setData(self, column, value):
        super().setData(column, value)
        if   column is col.SET_TYPE      : self.setType = value
        elif column is col.VALUE         : self.value = value
        elif column is col.VAR_NODE_NAME : self.varName = value

    def setType():
        def fget(self): return self._set_type
        def fset(self, v): self._set_type = v
        return locals()
    setType = property(**setType())

    def value():
        def fget(self): return self._value
        def fset(self,value): self._value = value
        return locals()
    value = property(**value())

    def name():
        def fget(self): return self._name
        def fset(self, value): self._name = value
        return locals()
    name = property(**name())

    def varName():
        def fget(self):
            try:
                return self._var_index.internalPointer().name
            except:
                return self._var_name
        def fset(self, value):
            self._var_name = value
        return locals()
    varName = property(**varName())


#The SetNode gets a list of tool nodes then we check if any are in save_values, and if so use the setpoint
# Having the node reference lets it actually set the node
class SetNode(Node):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tool_model = None

    def typeInfo(self):
        return typ.SET_NODE

    def treeType(self):
        return bt.LEAF

    def toolTypes(self):
        return [typ.D_OUT_NODE, typ.BOOL_VAR_NODE, typ.A_OUT_NODE, typ.FLOAT_VAR_NODE]

    def toolModel(self):
        return  self._tool_model

    def setToolModel(self, model):
        self._tool_model = model

    def setInfoText(self, names):
        text = "Setting: " + names
        super().setInfoText(text)

    def tick(self):
        if self._status != bt.SUCCESS:
            info_names = ''

            for child in self.children():
                type_info = child.setIndex().internalPointer().typeInfo()
                tool_model = self.toolModel()
                child_name, value = None, None

                if child.setType == bt.VAL:
                    child_name = child.setName

                    if type_info in [typ.BOOL_VAR_NODE, typ.FLOAT_VAR_NODE]:
                        value = child.value
                        tool_model.setData(child.setIndex().siblingAtColumn(col.VALUE), value)

                    elif type_info == typ.D_OUT_NODE:
                        pass #FIXME  TODO HAL
                    elif type_info == typ.A_OUT_NODE:
                        pass #FIXME TODO HAL
                        #hal que stuff
                        #node.halQueuePut(setpoint)

                elif child.setType == bt.VAR:
                    child_name = child.setName

                    if type_info in [typ.BOOL_VAR_NODE, typ.FLOAT_VAR_NODE, typ.D_OUT_NODE, typ.A_OUT_NODE]:
                        value = child.varIndex().internalPointer().value() 
                        tool_model.setData(child.setIndex().siblingAtColumn(col.VALUE), value)#child.varIndex().internalPointer().value())

                #if child_name:
                #    if len(info_names) > 0:
                #        info_names += ', '
                #    info_names += str(child_name) + ': ' + str(value)

                #self.setInfoText(info_names)

        self._status = bt.SUCCESS
        return self._status

class WaitNode(Node): #This one is used by the device on IO
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tool_model = None
        self._timeout_sec = 0
        self._start_time = 0

    def typeInfo(self):
        return typ.WAIT_NODE

    def treeType(self):
        return bt.LEAF

    def toolTypes(self):
        return [typ.D_IN_NODE, typ.D_OUT_NODE, typ.BOOL_VAR_NODE, typ.A_IN_NODE, typ.A_OUT_NODE, typ.FLOAT_VAR_NODE]

    def toolModel(self):
        return  self._tool_model

    def setToolModel(self, model):
        self._tool_model = model

    def data(self, column):
        r = super().data(column)
        if   column is col.TIMEOUT_SEC: r = self.timeoutSec
        return r

    def setData(self, column, value):
        super().setData(column, value)
        if   column is col.TIMEOUT_SEC: self.timeoutSec = value

    def setInfoText(self, children_text):
        text = ''

        #children_text[child.setName] = (tool_value, text_compare, value)
        for name in children_text:
            (tool_value, text_compare, value) = children_text[name]
            if len(text) > 0:
                text += ", "
            #text += str(name) + ": " + str(tool_value) + str(text_compare) + str(value)
            #TODO make this fancier 
            text += str(name) 

        timeout_time = self._timeout_sec - (time.time() - self._start_time)
        full_text = "Waiting for: %s , timeout: %0.1f sec" % (text, timeout_time)
        super().setInfoText(full_text)

    def tick(self):
        if not self._status:
            self._start_time = time.time()
            self._status = bt.RUNNING


        if self._status == bt.RUNNING:
            children_results = {}
            children_text = {}
            info_names = ''

            for child in self.children():
                type_info = child.setIndex().internalPointer().typeInfo()
                tool_model = self.toolModel()

                #Decode the two column hex value
                wait_type = bt.set_type(child.setType)
                equal_type = bt.equality(child.setType)

                
                value = None
                if wait_type == bt.VAL:
                    value = child.value
                elif wait_type == bt.VAR:
                    value = child.varIndex().internalPointer().value()


                if wait_type in [bt.VAL, bt.VAR]:
                    tool_value = child.setIndex().internalPointer().value()
                    result = False
                    
                    if equal_type == bt.EQUAL:
                        text_compare = "="
                        if tool_value == value:
                            result = True
                    elif equal_type == bt.NOT_EQUAL:
                        text_compare = "!="
                        if tool_value != value:
                            result = True
                    elif equal_type == bt.GREATER_THAN:
                        text_compare = ">"
                        if tool_value > value:
                            result = True
                    elif equal_type == bt.GREATER_THAN_EQUAL:
                        text_compare = "≥"
                        if tool_value >= value:
                            result = True
                    elif equal_type == bt.LESS_THAN:
                        text_compare = "<"
                        if tool_value < value:
                            result = True
                    elif equal_type == bt.LESS_THAN_EQUAL:
                        text_compare = "≤"
                        if tool_value <= value:
                            result = True

                    children_results[child.setName] = result
                    if not result:
                        children_text[child.setName] = (tool_value, text_compare, value)



            if all(child_result == True for child_result in children_results.values()):
                self._status = bt.SUCCESS

            self.setInfoText(children_text)

                #if child.setType == bt.VAL:
                #    if type_info in [typ.BOOL_VAR_NODE, typ.FLOAT_VAR_NODE]:
                #        tool_model.setData(child.setIndex().siblingAtColumn(col.VALUE), child.value)

                #    elif type_info == typ.D_OUT_NODE:
                #        pass #FIXME TODO HAL
                #    elif type_info == typ.A_OUT_NODE:
                #        pass #FIXME TODO HAL
                #        #hal que stuff
                #        #node.halQueuePut(setpoint)

                #elif child.setType == bt.VAR:
                #    if type_info in [typ.BOOL_VAR_NODE, typ.FLOAT_VAR_NODE, typ.D_OUT_NODE, typ.A_OUT_NODE]:
                #        tool_model.setData(child.setIndex().siblingAtColumn(col.VALUE), child.varIndex().internalPointer().value())


        #Check timeout after incase it's at 0 so it doesn't fail the first round
        if self._status == bt.RUNNING:
            if (time.time() - self._start_time)  > self._timeout_sec:
                self._status = bt.FAILURE
                print("timed out: ", (time.time() - self._start_time))

        #self._status = bt.SUCCESS
        return self._status

    def timeoutSec():
        def fget(self): return self._timeout_sec
        def fset(self,value): self._timeout_sec = value
        return locals()
    timeoutSec = property(**timeoutSec())


class Tolerancepoint(BaseNode):
    def __init__(self, parent=None):
        super().__init__(parent)
        #We set a node (set_index) to either a value or to the value of another node (var_index)
        self._set_type = bt.NO_SET
        self._set_type_scale = bt.NO_SET
        self._set_type_offset = bt.NO_SET

        #abs(compare_1 - compare_2) < (compare_2*tol_scale + tol_offset)
        self._compare_1_index = None
        self._compare_1_name = ""
        self._compare_2_index = None
        self._compare_2_name = ""

        self._tolerance_scale_index = None
        self._tolerance_scale_name = None
        self._tolerance_scale_value = 0.10

        self._tolerance_offset_index = None
        self._tolerance_offset_name = None
        self._tolerance_offset_value = 1.0


    def typeInfo(self):
        return typ.TOLERANCEPOINT

    def treeType(self):
        return bt.PROPERTY

    def setCompare1Index(self, index):
        self._compare_1_index = index

    def compare1Index(self):
        return self._compare_1_index 

    def setCompare2Index(self, index):
        self._compare_2_index = index

    def compare2Index(self):
        return self._compare_2_index 

    def setToleranceScaleIndex(self, index):
        self._tolerance_scale_index = index

    def toleranceScaleIndex(self):
        return self._tolerance_scale_index

    def setToleranceOffsetIndex(self, index):
        self._tolerance_offset_index = index

    def toleranceOffsetIndex(self):
        return self._tolerance_offset_index



    def data(self, column):
        r = super().data(column)
        if   column is col.SET_TYPE               : r = self.setType
        elif column is col.SET_TYPE_SCALE         : r = self.setTypeScale
        elif column is col.SET_TYPE_OFFSET        : r = self.setTypeOffset
        elif column is col.COMPARE_2_NAME         : r = self.compare2Name
        elif column is col.TOLERANCE_SCALE_VALUE  : r = self.toleranceScaleValue
        elif column is col.TOLERANCE_SCALE_NAME   : r = self.toleranceScaleName
        elif column is col.TOLERANCE_OFFSET_VALUE : r = self.toleranceOffsetValue
        elif column is col.TOLERANCE_OFFSET_NAME  : r = self.toleranceOffsetName
        return r

    def setData(self, column, value):
        super().setData(column, value)
        if   column is col.SET_TYPE               : self.setType = value
        elif column is col.SET_TYPE_SCALE         : self.setTypeScale = value
        elif column is col.SET_TYPE_OFFSET        : self.setTypeOffset = value
        elif column is col.COMPARE_2_NAME         : self.compare2Name = value
        elif column is col.TOLERANCE_SCALE_VALUE  : self.toleranceScaleValue = value
        elif column is col.TOLERANCE_SCALE_NAME   : self.toleranceScaleName = value
        elif column is col.TOLERANCE_OFFSET_VALUE : self.toleranceOffsetValue = value
        elif column is col.TOLERANCE_OFFSET_NAME  : self.toleranceOffsetName = value

    def setType():
        def fget(self): return self._set_type
        def fset(self, v): self._set_type = v
        return locals()
    setType = property(**setType())

    def setTypeScale():
        def fget(self): return self._set_type_scale
        def fset(self, v): self._set_type_scale = v
        return locals()
    setTypeScale = property(**setTypeScale())

    def setTypeOffset():
        def fget(self): return self._set_type_offset
        def fset(self, v): self._set_type_offset = v
        return locals()
    setTypeOffset = property(**setTypeOffset())


    def toleranceScaleValue():
        def fget(self): return self._tolerance_scale_value
        def fset(self,value): self._tolerance_scale_value = value
        return locals()
    toleranceScaleValue = property(**toleranceScaleValue())

    def toleranceOffsetValue():
        def fget(self): return self._tolerance_offset_value
        def fset(self,value): self._tolerance_offset_value = value
        return locals()
    toleranceOffsetValue = property(**toleranceOffsetValue())

    def compare1Name():
        def fget(self):
            try:
                return self._compare_1_index.internalPointer().name
            except:
                return self._compare_1_name
        def fset(self, value):
            self._compare_1_name = value
        return locals()
    compare1Name= property(**compare1Name())

    def compare2Name():
        def fget(self):
            try:
                return self._compare_2_index.internalPointer().name
            except:
                return self._compare_2_name
        def fset(self, value):
            self._compare_2_name = value
        return locals()
    compare2Name= property(**compare2Name())

    def toleranceScaleName():
        def fget(self):
            try:
                return self._tolerance_scale_index.internalPointer().name
            except:
                return self._tolerance_scale_name
        def fset(self, value):
            self._tolerance_scale_name = value
        return locals()
    toleranceScaleName = property(**toleranceScaleName())

    def toleranceOffsetName():
        def fget(self):
            try:
                return self._tolerance_offset_index.internalPointer().name
            except:
                return self._tolerance_offset_name
        def fset(self, value):
            self._tolerance_offset_name = value
        return locals()
    toleranceOffsetName = property(**toleranceOffsetName())




#change to toleranceNode
class ToleranceNode(Node):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tool_model = None
        self._timeout_sec = 0
        self._start_time = 0


    def typeInfo(self):
        return typ.TOLERANCE_NODE

    def treeType(self):
        return bt.LEAF

    def toolTypes(self):
        return [typ.A_IN_NODE, typ.A_OUT_NODE, typ.FLOAT_VAR_NODE]

    def toolModel(self):
        return  self._tool_model

    def setToolModel(self, model):
        self._tool_model = model

    def data(self, column):
        r = super().data(column)
        if   column is col.TIMEOUT_SEC: r = self.timeoutSec
        return r

    def setData(self, column, value):
        super().setData(column, value)
        if   column is col.TIMEOUT_SEC: self.timeoutSec = value


    def setInfoText(self, children_text):
        text = ''

        for name in children_text:
            (compare1value, compare2value) = children_text[name]
            if len(text) > 0:
                text += ", "
            text += "%s: (%0.1f | %0.1f)" % (name, compare1value, compare2value)

        timeout_time = self._timeout_sec - (time.time() - self._start_time)
        full_text = "Waiting for tolernace: %s , timeout: %0.1f sec" % (text, timeout_time)
        super().setInfoText(full_text)

    def tick(self):
        if not self._status:
            self._start_time = time.time()
            self._status = bt.RUNNING


        if self._status == bt.RUNNING:
            children_results = {}
            children_text = {}

            for child in self.children():
                if child.setType == bt.VAL:
                    compare_1_value = child.compare1Index().internalPointer().value()
                    compare_2_value = child.compare2Index().internalPointer().value()
                    delta = compare_1_value - compare_2_value

                    tol = 0

                    #Scale
                    if child.setTypeScale == bt.VAL:
                        tol += child.toleranceScaleValue*compare_2_value
                    elif child.setTypeScale == bt.VAR:
                        tol += child.toleranceScaleIndex().internalPointer().value()*compare_2_value


                    #Offset
                    if child.setTypeOffset == bt.VAL:
                        tol += child.toleranceOffsetValue
                    elif child.setTypeOffset == bt.VAR:
                        tol += child.toleranceOffsetIndex().internalPointer().value()


                    if abs(delta) < tol:
                        children_results[child.compare1Name] = True
                    else:
                        children_results[child.compare1Name] = False
                        children_text[child.compare1Name] = (compare_1_value, compare_2_value)


            #keeping like this so its possible to log what one didn't hit tolerance?
            if all(child_result == True for child_result in children_results.values()):
                self._status = bt.SUCCESS

            self.setInfoText(children_text)

        #Check timeout after incase it's at 0 so it doesn't fail the first round
        if self._status == bt.RUNNING:
            if (time.time() - self._start_time)  > self._timeout_sec:
                self._status = bt.FAILURE

        return self._status

    def timeoutSec():
        def fget(self): return self._timeout_sec
        def fset(self,value): self._timeout_sec = value
        return locals()
    timeoutSec = property(**timeoutSec())



class SetIconNode(Node):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tool_model = None
        self._icon_index = None
        self._tool_value_methods = {} #Stores tool .value() methods so they can be called at runtime

    def typeInfo(self):
        return typ.SET_ICON_NODE

    def treeType(self):
        return bt.LEAF

    def toolTypes(self):
        return [typ.D_IN_NODE, typ.D_OUT_NODE, typ.BOOL_VAR_NODE, typ.A_IN_NODE, typ.A_OUT_NODE, typ.FLOAT_VAR_NODE]
        
    def toolModel(self):
        return  self._tool_model

    def setToolModel(self, model):
        self._tool_model = model

    def setIconIndex(self, index):
        self._icon_index = index

        if self._tool_model:
            self._tool_value_methods = {} 
            for index in self._tool_model.indexesOfTypes(self.toolTypes(), self._icon_index.parent()):
                self._tool_value_methods[index.internalPointer().name] = index.internalPointer().value

    def iconIndex(self):
        return self._icon_index

    def svg(self):
        return self._icon_index.internalPointer().svg

    def layers(self):
        return self._icon_index.internalPointer().layers()

    def tick(self):
        if self._status != bt.SUCCESS:
            for child in self.children():
                value = None

                if child.name == 'TEXT': 
                    try:
                        text = str(child.value)
                        evaled_dict = {}
                        needed_vars = [fn for _, fn, _, _ in Formatter().parse(text) if fn is not None]

                        for key in needed_vars:
                            if key in self._tool_value_methods:
                                method = self._tool_value_methods[key]
                                evaled_dict[key] = method()
                            else:
                                evaled_dict[key] = '?'

                        value = text.format(**evaled_dict)
                
                    except (ValueError, IndexError, KeyError) as error:
                        print(error)
                        value = "?"


                else:
                    if child.setType == bt.VAL:
                        value = child.value
                    elif child.setType == bt.VAR:
                        value = child.varIndex().internalPointer().value()


                if value is not None:
                    self.toolModel().setData(self.iconIndex().siblingAtColumn(getattr(col, child.name)), value)




        self._status = bt.SUCCESS
        return self._status

class RunBehaviorNode(Node):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tool_model = None
        self._icon_index = None

    def typeInfo(self):
        return typ.RUN_BEHAVIOR_NODE

    def treeType(self):
        return bt.LEAF

    def toolTypes(self):
        return [typ.SYSTEM_NODE, typ.DEVICE_NODE]
        
    def toolModel(self):
        return  self._tool_model

    def setToolModel(self, model):
        self._tool_model = model

    def setInfoText(self, behavior_names):
        text = ''

        for node_name, behavior_name in behavior_names:
            if len(text)>0:
                text += ', '
            text += node_name + ":" + behavior_name

        super().setInfoText(text)

    def tick(self):
        if self._status != bt.SUCCESS:
            behavior_names = []

            for child in self.children():
                if child.setType == bt.VAL:
                    try:
                        child.behavior().runAbortOthers()
                        behavior_names.append((child.behavior().toolIndex().internalPointer().name, child.behaviorName))
                    except:
                        print("run behavior failed")

            self.setInfoText(behavior_names)

        self._status = bt.SUCCESS
        return self._status

class WaitStateNode(Node):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tool_model = None
        self._timeout_sec = 0
        self._start_time = 0

    def typeInfo(self):
        return typ.WAIT_STATE_NODE

    def treeType(self):
        return bt.LEAF

    def toolTypes(self):
        return [typ.SYSTEM_NODE, typ.DEVICE_NODE]
        
    def toolModel(self):
        return  self._tool_model

    def setToolModel(self, model):
        self._tool_model = model

    def data(self, column):
        r = super().data(column)
        if   column is col.TIMEOUT_SEC: r = self.timeoutSec
        return r

    def setData(self, column, value):
        super().setData(column, value)
        if   column is col.TIMEOUT_SEC: self.timeoutSec = value

    def setInfoText(self, children_text):
        text = ''

        #children_text[child.setName] = (tool_value, text_compare, value)
        for name in children_text:
            state = children_text[name]
            if len(text) > 0:
                text += ", "
            text += str(name) + ":" + str(state) 

        timeout_time = self._timeout_sec - (time.time() - self._start_time)
        full_text = "Waiting for: %s , timeout: %0.1f sec" % (text, timeout_time)
        super().setInfoText(full_text)

    def tick(self):
        if not self._status:
            self._start_time = time.time()
            self._status = bt.RUNNING


        if self._status == bt.RUNNING:
            children_results = {}
            children_text = {}

            for child in self.children():
                type_info = child.setIndex().internalPointer().typeInfo()
                tool_model = self.toolModel()

                #Decode the two column hex value
                wait_type = bt.set_type(child.setType)
                equal_type = bt.equality(child.setType)

                result = False
                current_state = child.setIndex().internalPointer().state()
                state_setpoint = child.state

                if wait_type != bt.NO_SET:
                    if equal_type == bt.EQUAL and current_state == state_setpoint:
                        result = True
                    elif equal_type == bt.NOT_EQUAL and current_state != state_setpoint:
                        result = True
                else:
                    result = True

                children_results[child.setName] = result
                if not result:
                    children_text[child.setName] = state_setpoint

            if all(child_result == True for child_result in children_results.values()):
                self._status = bt.SUCCESS

            self.setInfoText(children_text)

        #Check timeout after incase it's at 0 so it doesn't fail the first round
        if self._status == bt.RUNNING:
            if (time.time() - self._start_time)  > self._timeout_sec:
                self._status = bt.FAILURE

        return self._status

    def timeoutSec():
        def fget(self): return self._timeout_sec
        def fset(self,value): self._timeout_sec = value
        return locals()
    timeoutSec = property(**timeoutSec())


class AlertNode(Node):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tool_model = None
        self._tool_index = None
        self._tool_value_methods = {} #Stores tool .value() methods so they can be called at runtime
        
        self._text = ''
        self._alert_type = 2 # 2 is alert
        self._alert_callback = None #This function gets called to send the alert message to
        self._system_name = "?"
        self._device_name = "?"

    def typeInfo(self):
        return typ.ALERT_NODE

    def treeType(self):
        return bt.LEAF

    def toolTypes(self):
        return [typ.D_IN_NODE, typ.D_OUT_NODE, typ.BOOL_VAR_NODE, typ.A_IN_NODE, typ.A_OUT_NODE, typ.FLOAT_VAR_NODE]

    def toolModel(self):
        return  self._tool_model

    def setToolModel(self, model):
        self._tool_model = model

    def toolIndex(self):
        return  self._tool_index

    def setToolIndex(self, index):
        self._tool_index = index
        self._device_name = index.internalPointer().name
        self._system_name = index.parent().internalPointer().name

        if self._tool_model:
            self._tool_value_methods = {} 
            for index in self._tool_model.indexesOfTypes(self.toolTypes(), self._tool_index.parent()):
                self._tool_value_methods[index.internalPointer().name] = index.internalPointer().value


    def setAlertCallback(self, callback):
        self._alert_callback = callback

    def message(self):
        try:
            text = str(self.text)
            evaled_dict = {}
            needed_vars = [fn for _, fn, _, _ in Formatter().parse(text) if fn is not None]

            for key in needed_vars:
                if key in self._tool_value_methods:
                    method = self._tool_value_methods[key]
                    evaled_dict[key] = method()
                else:
                    evaled_dict[key] = '?'

            return text.format(**evaled_dict)
    
        except (ValueError, IndexError, KeyError) as error:
            print(error)
            return "?"


    def data(self, column):
        r = super().data(column)
        if   column is col.TEXT       : return self.text
        elif column is col.ALERT_TYPE : return self.alertType
        return r

    def setData(self, column, value):
        super().setData(column, value)
        if   column is col.TEXT       : self.text = value
        elif column is col.ALERT_TYPE : self.alertType = value

    def tick(self):
        if self._status == None:
            self._status = bt.RUNNING

            message = self.message()

            if self._alert_callback is not None:
                self._alert_callback(alert_type=self._alert_type, system=self._system_name, device=self._device_name, alert=message)

        self._status = bt.SUCCESS
        return self._status

    def text():
        def fget(self): return self._text
        def fset(self, value): self._text = str(value)
        return locals()
    text = property(**text())

    def alertType():
        def fget(self): return self._alert_type
        def fset(self, value): self._alert_type = value
        return locals()
    alertType = property(**alertType())


#Clears its alert if children return success
class AlertSequenceNode(Node):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tool_model = None
        self._tool_index = None
        self._tool_value_methods = {} #Stores tool .value() methods so they can be called at runtime
        self._current_child = 0
        
        self._text = ''
        self._alert_type = 2 # 2 is alert
        self._alert_callback = None #This function gets called to send the alert message to
        self._clear_alert_callback = None #Call this to clear the generated alert
        self._set_user_clearable_callback = None
        self._system_name = "?"
        self._device_name = "?"

    def typeInfo(self):
        return typ.ALERT_SEQUENCE_NODE

    def treeType(self):
        return bt.BRANCH

    def toolTypes(self):
        return [typ.D_IN_NODE, typ.D_OUT_NODE, typ.BOOL_VAR_NODE, typ.A_IN_NODE, typ.A_OUT_NODE, typ.FLOAT_VAR_NODE]

    def toolModel(self):
        return  self._tool_model

    def setToolModel(self, model):
        self._tool_model = model

    def toolIndex(self):
        return  self._tool_index

    def reset(self):
        super().reset()
        self._current_child = 0
        #TODO set to user clearable???
        #if self._clear_alert_callback:
        #    self._clear_alert_callback()
        
        if self._set_user_clearable_callback:
            self._set_user_clearable_callback()
            

    def setToolIndex(self, index):
        self._tool_index = index
        self._device_name = index.internalPointer().name
        self._system_name = index.parent().internalPointer().name

        if self._tool_model:
            self._tool_value_methods = {} 
            for index in self._tool_model.indexesOfTypes(self.toolTypes(), self._tool_index.parent()):
                self._tool_value_methods[index.internalPointer().name] = index.internalPointer().value


    def setAlertCallback(self, callback):
        self._alert_callback = callback

    def message(self):
        try:
            text = str(self.text)
            evaled_dict = {}
            needed_vars = [fn for _, fn, _, _ in Formatter().parse(text) if fn is not None]

            for key in needed_vars:
                if key in self._tool_value_methods:
                    method = self._tool_value_methods[key]
                    evaled_dict[key] = method()
                else:
                    evaled_dict[key] = '?'

            return text.format(**evaled_dict)
    
        except (ValueError, IndexError, KeyError) as error:
            print(error)
            return "?"


    def data(self, column):
        r = super().data(column)
        if   column is col.TEXT       : return self.text
        elif column is col.ALERT_TYPE : return self.alertType
        return r

    def setData(self, column, value):
        super().setData(column, value)
        if   column is col.TEXT       : self.text = value
        elif column is col.ALERT_TYPE : self.alertType = value


    def tick(self):
        if self._status in [bt.SUCCESS, bt.FAILURE]:
            return self._status

        else:
            if self._status == None:
                message = self.message()

                if self._alert_callback is not None:
                    self._clear_alert_callback, self._set_user_clearable_callback = self._alert_callback(alert_type=self._alert_type, 
                                                                                system=self._system_name, device=self._device_name,
                                                                                                         alert=message, user_clear=False)


            for i, child in enumerate(self._children[self._current_child:]):
                result = child.tick()

                if result in [bt.RUNNING, bt.FAILURE]:
                    self._status = result
                    return self._status

                self._current_child = i

            self._status = bt.SUCCESS
            self._clear_alert_callback()
            return self._status


    def text():
        def fget(self): return self._text
        def fset(self, value): self._text = str(value)
        return locals()
    text = property(**text())

    def alertType():
        def fget(self): return self._alert_type
        def fset(self, value): self._alert_type = value
        return locals()
    alertType = property(**alertType())


#Displays a message, non-blocking
class MessageNode(Node):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tool_model = None
        self._tool_index = None
        self._tool_value_methods = {} #Stores tool .value() methods so they can be called at runtime
        
        self._text = ''
        self._system_name = None
        self._device_name = None

    def typeInfo(self):
        return typ.MESSAGE_NODE

    def treeType(self):
        return bt.LEAF

    def toolTypes(self):
        return [typ.D_IN_NODE, typ.D_OUT_NODE, typ.BOOL_VAR_NODE, typ.A_IN_NODE, typ.A_OUT_NODE, typ.FLOAT_VAR_NODE]

    def toolModel(self):
        return  self._tool_model

    def setToolModel(self, model):
        self._tool_model = model

    def toolIndex(self):
        return  self._tool_index

    def setToolIndex(self, index):
        self._tool_index = index
        self._device_name = index.internalPointer().name
        self._system_name = index.parent().internalPointer().name

        if self._tool_model:
            self._tool_value_methods = {} 
            for index in self._tool_model.indexesOfTypes(self.toolTypes(), self._tool_index.parent()):
                self._tool_value_methods[index.internalPointer().name] = index.internalPointer().value



    def message(self):
        try:
            text = str(self.text)
            evaled_dict = {}
            needed_vars = [fn for _, fn, _, _ in Formatter().parse(text) if fn is not None]

            for key in needed_vars:
                if key in self._tool_value_methods:
                    method = self._tool_value_methods[key]
                    evaled_dict[key] = method()
                else:
                    evaled_dict[key] = '?'

            return text.format(**evaled_dict)
    
        except (ValueError, IndexError, KeyError) as error:
            print(error)
            return "?"


    def data(self, column):
        r = super().data(column)
        if   column is col.TEXT           : return self.text
        return r

    def setData(self, column, value):
        super().setData(column, value)
        if   column is col.TEXT           : self.text = value

    def tick(self):
        if self._status == None:
            self._status = bt.SUCCESS
            message = self.message()

            #Shows the message but doesn't block anything
            dlg = QtWidgets.QMessageBox()
            dlg.setWindowModality(QtCore.Qt.NonModal)
            dlg.setText(message)

            title_text = ""
            if self._system_name:
                title_text += str(self._system_name)
            if self._device_name:
                title_text += str(self._device_name)

            dlg.setWindowTitle(title_text)

            button = dlg.exec()


        return self._status

    def text():
        def fget(self): return self._text
        def fset(self, value): self._text = str(value)
        return locals()
    text = property(**text())

#Displays a dialog box w/ two buttons, returns success/failure based on input
class DialogNode(MessageNode):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._success_text = ""
        self._fail_text = ""

    def typeInfo(self):
        return typ.DIALOG_NODE

    def data(self, column):
        r = super().data(column)
        if column is col.SUCCESS_TEXT : return self.successText
        elif column is col.FAIL_TEXT  : return self.failText
        return r

    def setData(self, column, value):
        super().setData(column, value)
        if column is col.SUCCESS_TEXT : self.successText = value
        elif column is col.FAIL_TEXT  : self.failText = value


    def tick(self):
        if self._status in [bt.SUCCESS, bt.FAILURE]:
            return self._status

        elif self._status == None:
            self._status = bt.RUNNING
            message = self.message()

            #Shows the message but doesn't block anything
            dlg = QtWidgets.QMessageBox()
            dlg.setWindowModality(QtCore.Qt.NonModal)
            dlg.setText(message)
            btn_1 = dlg.addButton(self.successText, dlg.AcceptRole)
            btn_2 = dlg.addButton(self.failText, dlg.RejectRole)

            title_text = ""
            if self._system_name:
                title_text += str(self._system_name)
            if self._device_name:
                title_text += str(self._device_name)

            dlg.setWindowTitle(title_text)

            button = dlg.exec()
        
            if button == dlg.AcceptRole:
                self._status = bt.SUCCESS
            else:
                self._status = bt.FAILURE

        return self._status


    def successText():
        def fget(self): return self._success_text
        def fset(self, value): self._success_text = str(value)
        return locals()
    successText = property(**successText())

    def failText():
        def fget(self): return self._fail_text
        def fset(self, value): self._fail_text = str(value)
        return locals()
    failText = property(**failText())


class SetDeviceStateNode(Node):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._device_state = ""
        self._device_state_callback = None
        self._device_state_index = None

    def typeInfo(self):
        return typ.SET_DEVICE_STATE_NODE

    def treeType(self):
        return bt.LEAF

    def setDeviceStateCallback(self, callback, index):
        self._device_state_callback = callback
        self._device_state_index = index

    def states(self):
        return self._device_state_index.internalPointer().states

    def data(self, column):
        r = super().data(column)
        if   column is col.DEVICE_STATE: r = self.device_state
        return r

    def setData(self, column, value):
        super().setData(column, value)
        if   column is col.DEVICE_STATE: self.device_state = value

    def tick(self):
        if self._status in [bt.SUCCESS, bt.FAILURE]:
            return self._status
        else:
            if self._device_state_callback and self._device_state_index:
                self._device_state_callback(self._device_state_index, self._device_state)
            self._status = bt.SUCCESS
            return self._status

    def device_state():
        def fget(self): return self._device_state
        def fset(self, value): self._device_state = str(value)
        return locals()
    device_state = property(**device_state())






#~~not used right now~~
class BehaviorInput(BaseNode):
    def __init__(self, name=None, parent=None):
        super().__init__(parent)
        self._set_type = bt.NO_SET
        self._text = ''
        self._new_line = False

        self._node = None
        self._node_name = ""

    def typeInfo(self):
        return typ.BEHAVIOR_INPUT

    def treeType(self):
        return bt.PROPERTY

    def node(self):
        return self._node

    def setNode(self, value):
        self._node = value

    def loadNode(self):
        for node in self.parent().toolNodes():
            if node.name == self._node_name:
                self._node = node

    def data(self, column):
        r = super().data(column)
        if   column is col.SET_TYPE : r = self.setType
        elif column is col.TEXT     : r = self.text
        elif column is col.NEW_LINE : r = self.newLine
        return r

    def setData(self, column, value):
        super().setData(column, value)
        if   column is col.SET_TYPE : self.setType = value
        elif column is col.TEXT     : self.text = value
        elif column is col.NEW_LINE : self.newLine = value

    def nodeName():
        def fget(self):
            if self._node is not None:
                return self._node.name
        def fset(self,value):
            self._node_name = value
            self.loadNode()
        return locals()
    nodeName = property(**nodeName())

    def setType():
        def fget(self): return self._set_type
        def fset(self, v): self._set_type = v
        return locals()
    setType = property(**setType())

    def text():
        def fget(self): return self._text
        def fset(self,value): self._text = str(value)
        return locals()
    text = property(**text())

    def newLine():
        def fget(self): return self._new_line
        def fset(self,value): self._new_line = bool(value)
        return locals()
    newLine = property(**newLine())





