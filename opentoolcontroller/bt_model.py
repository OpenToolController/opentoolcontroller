from PyQt5 import QtCore, QtGui

from opentoolcontroller.strings import bt, col, typ
from opentoolcontroller.bt_data import *
from opentoolcontroller.message_box import MessageBox
from opentoolcontroller.strings import defaults

import json
import os.path
import time
import pickle



import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas


class BehaviorRunner():
    def __init__(self, period_ms, i):
        self._tick_rate_ms = int(period_ms)
        self._behavior_runner_number = i

        self._timer = QtCore.QTimer()
        self._timer.timeout.connect(self.tick)
        self._timer.start(self._tick_rate_ms)

        self._running_behaviors = []
        self._max_elapsed_ms = 0
        self._histogram_window = None


    def behaviorRunnerNumber(self):
        return self._behavior_runner_number
    
    def tickRateMS(self):
        return self._tick_rate_ms

    def launchHistogram(self):
        self._histogram_window = LiveHistogramWindow()
        self._histogram_window.show()


    def runAbortSiblings(self, new_behavior):
        #Remove and reset siblings of the one we're starting
        self._tmp_running = []
        for behavior in self._running_behaviors:
            if new_behavior.toolIndex() == behavior.toolIndex():
                behavior.setStopped()
            else:
                self._tmp_running.append(behavior)
        self._running_behaviors = self._tmp_running

        new_behavior.setRunning()
        self._running_behaviors.append(new_behavior)


    def stopBehavior(self, behavior):
        self._running_behaviors = [x for x in self._running_behaviors if x != behavior]
        behavior.setStopped()


    def tick(self):
        behaviors_to_stop = []

        start_time = time.time()

        for behavior in self._running_behaviors:
            try:
                result = behavior.tick()
                if result in {bt.SUCCESS, bt.FAILURE}:
                    behaviors_to_stop.append(behavior)

            except Exception as e:
                print("failed to run behavior")
                print(e)
                behaviors_to_stop.append(behavior)

        for behavior in behaviors_to_stop:
            self.stopBehavior(behavior)


        elapsed_sec = time.time() - start_time
        elapsed_ms = elapsed_sec * 1e3
        
        if self._histogram_window:
            self._histogram_window.update([elapsed_ms])


                
class LiveHistogramWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.max_points = 50

        self.setWindowTitle("Tick Time")
        self.setGeometry(100, 100, 400, 400)

        self._layout = QtWidgets.QVBoxLayout()
        self.setLayout(self._layout)

        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)
        self._layout.addWidget(self.canvas)

        self.data = []  # List to store the data points for the histogram

        # Create the initial histogram
        self.bins = np.arange(1, 11)
        self.bars = self.ax.bar(self.bins[:-1], np.zeros_like(self.bins[:-1]), align='edge', edgecolor='black')

       
        # Set labels and title
        self.ax.set_xlabel('Time (ms)')
        self.ax.set_ylabel('Frequency')
        self.ax.set_title('Tick Time')


    def update(self, new_values=None):
        if new_values is None:
            new_values = []

        # Add new values to the data
        self.data.extend(new_values)

        if len(self.data) > self.max_points:
            self.data = self.data[-self.max_points:]


        # Calculate bins dynamically based on the range of the data
        min_value = min(self.data)
        max_value = max(self.data)
        self.bins = np.linspace(min_value, max_value, 11)

        # Update the existing bars in the histogram
        hist, _ = np.histogram(self.data, bins=self.bins)
        for bar, h, bin_left, bin_right in zip(self.bars, hist, self.bins[:-1], self.bins[1:]):
            bin_width = bin_right - bin_left
            bin_center = (bin_left + bin_right) / 2
            bar.set_height(h)
            bar.set_x(bin_left)
            bar.set_width(bin_width)


        self.ax.set_ylim(0, max(hist))
        self.ax.set_xlim(0, max_value)
        self.canvas.draw()






class BTModel(QtCore.QAbstractItemModel):
    #behaviorRunner = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self._root_node = RootSequenceNode()
        self._root_index = self.createIndex(0, 0, self._root_node) #There's a empty index w/out a valid parent above this

        self._tool_callback = None
        self._index_icon = None

        self._tool_model = None
        self._tool_index = None

        self._behavior_runner = None


    '''The tool needs a single timer that all the behaviors use, or maybe per System?
        if we run the behavior then we need to add ourselvs to our timers tick loop?
        Probs subclass Qtimer and add a tick thing that we loop through

        Once the behavior finishes then we eject ourselves from the timer, or if it fails

        The timer should track how long all its ticks take

    '''

    def setToolModel(self, tool_model):
        self._tool_model = tool_model

    def toolModel(self):
        return self._tool_model

    def setToolIndex(self, tool_index):
        self._tool_index = tool_index

    def toolIndex(self):
        return self._tool_index

    def behaviorRunner(self):
        return self._behavior_runner
    
    def setBehaviorRunner(self, runner):
        self._behavior_runner = runner

    def syncMessageIndex(self, index):
        message_node = index.internalPointer()
        message_node.setToolModel(self.toolModel())
        message_node.setToolIndex(self.toolIndex())

    def syncAlertIndex(self, index):
        alert_node = index.internalPointer()
        alert_node.setToolModel(self.toolModel())
        alert_node.setToolIndex(self.toolIndex())
        alert_node.setAlertCallback(self.toolModel().alertCallback())



    def syncLeafSetpointBase(self, leaf_index, setpoint_type):
        leaf_node = leaf_index.internalPointer()
        leaf_node.setToolModel(self.toolModel())

        names = []

        # Add ones we don't have
        for tool_index in self.toolModel().indexesOfTypes(leaf_node.toolTypes(), self.toolIndex(), 1):
            tool_node = tool_index.internalPointer()
            names.append(tool_node.name)

            for setpoint_index in self.indexesOfType(setpoint_type, leaf_index):
                setpoint_node = setpoint_index.internalPointer()

                if setpoint_node.setName == tool_node.name:
                    setpoint_node.setSetIndex(tool_index)
                    break

            else:
                new_setpoint_index = self.insertChild(leaf_index, setpoint_type)
                setpoint_node = new_setpoint_index.internalPointer()
                setpoint_node.setSetIndex(tool_index)


        #Remove the ones that arent part of the tool model
        for setpoint_index in self.indexesOfType(setpoint_type, leaf_index):
            setpoint_node = setpoint_index.internalPointer()
            if not setpoint_node.setName in names:
                self.removeRows(setpoint_index.row(), 1, setpoint_index.parent())




    def syncLeafSetpoints(self, leaf_index):
        self.syncLeafSetpointBase(leaf_index, typ.SETPOINT)

        #Sync the varNodeIndexes
        for setpoint_index in self.indexesOfType(typ.SETPOINT, leaf_index):
            setpoint_node = setpoint_index.internalPointer()

            for tool_index in self.toolModel().childrenIndexes(self.toolIndex()):
                if tool_index.internalPointer().name == setpoint_node.varName:
                    setpoint_node.setVarIndex(tool_index)




    def syncLeafRunBehaviorSetpoints(self, leaf_index):
        self.syncLeafSetpointBase(leaf_index, typ.RUN_BEHAVIOR_SETPOINT)

        #Now set the behavior via the saved behavior name
        for runpoint_index in self.indexesOfType(typ.RUN_BEHAVIOR_SETPOINT, leaf_index):
            runpoint_node = runpoint_index.internalPointer()

            #Check if we have a behavior that matches
            for behavior in runpoint_node.setIndex().internalPointer().behaviors():
                if behavior.name() == runpoint_node.behaviorName:
                    runpoint_node.setBehavior(behavior)



    def syncLeafWaitStateSetpoints(self, leaf_index):
        self.syncLeafSetpointBase(leaf_index, typ.WAIT_STATE_SETPOINT)

        #Now set the behavior via the saved behavior name
        for setpoint_index in self.indexesOfType(typ.WAIT_STATE_SETPOINT, leaf_index):
            setpoint_node = setpoint_index.internalPointer()

            #Check if we have a state that matches
            #if state in setpoint_node.setIndex().internalPointer().states:
            #    setpoint_node.state = state




    def syncLeafTolerancepoints(self, leaf_index):
        leaf_node = leaf_index.internalPointer()
        leaf_node.setToolModel(self.toolModel())
        names = []

        # Add ones we don't have and set the models
        for tool_index in self.toolModel().indexesOfTypes(leaf_node.toolTypes(), self.toolIndex(), 1):
            tool_node = tool_index.internalPointer()
            names.append(tool_node.name)

            for point_index in self.indexesOfType(typ.TOLERANCEPOINT, leaf_index):
                point_node = point_index.internalPointer()

                if point_node.compare1Name == tool_node.name:
                    point_node.setCompare1Index(tool_index)
                    break

            else:
                new_point_index = self.insertChild(leaf_index, typ.TOLERANCEPOINT)
                new_point_index.internalPointer().setCompare1Index(tool_index)



        #Remove the ones that arent part of the tool model
        for point_index in self.indexesOfType(typ.TOLERANCEPOINT, leaf_index):
            point_node = point_index.internalPointer()
            if not point_node.compare1Name in names:
                self.removeRows(point_index.row(), 1, point_index.parent())


        #After all the sets are usable then we need to sync the compare2Index and toleranceIndex
        for point_index in self.indexesOfType(typ.TOLERANCEPOINT, leaf_index):
            point_node = point_index.internalPointer()

            for tool_index in self.toolModel().childrenIndexes(self.toolIndex()):
                if tool_index.internalPointer().name == point_node.compare2Name:
                    point_node.setCompare2Index(tool_index)

                if tool_index.internalPointer().name == point_node.toleranceScaleName:
                    point_node.setToleranceScaleIndex(tool_index)

                if tool_index.internalPointer().name == point_node.toleranceOffsetName:
                    point_node.setToleranceOffsetIndex(tool_index)








    def syncLeafBehaviorInputs(self, leaf_index):
        leaf_node = leaf_index.internalPointer()
        names = []

        #Add ones we don't have and set the models
        for tool_index in self.toolModel().indexesOfTypes(leaf_node.toolTypes(), self.toolIndex(), 1):
            has_setpoint = False
            tool_node = tool_index.internalPointer()
            names.append(tool_node.name)

            for setpoint_index in self.indexesOfType(typ.SETPOINT, leaf_index):
                setpoint_node = setpoint_index.internalPointer()

                if setpoint_node.setName == tool_node.name:
                    has_setpoint = True
                    setpoint_node.setToolModel(self.toolModel())
                    setpoint_node.setSetIndex(tool_index)


            if not has_setpoint:
                new_setpoint_index = self.insertChild(leaf_index, typ.SETPOINT)
                setpoint_node = new_setpoint_index.internalPointer()
                setpoint_node.setToolModel(self.toolModel())
                setpoint_node.setSetIndex(tool_index)

        #Remove ones we don't need
        for setpoint_index in self.indexesOfType(typ.SETPOINT, leaf_index):
            setpoint_node = setpoint_index.internalPointer()
            if not setpoint_node.setName in names:
                self.removeRows(setpoint_index.row(), 1, setpoint_index.parent())


    def syncIconIndex(self, icon_index):
        icon_node = icon_index.internalPointer()
        icon_properties = ['LAYER', 'X', 'Y', 'SCALE', 'ROTATION', 'HAS_TEXT', 'TEXT', 'TEXT_X', 'TEXT_Y', 'FONT_SIZE']

        tool_icon_index = self._tool_model.indexesOfType(typ.DEVICE_ICON_NODE, self._tool_index)
        tool_icon_index = tool_icon_index[0] if tool_icon_index else None

        icon_node.setToolModel(self.toolModel())
        icon_node.setIconIndex(tool_icon_index)


        for row, name in enumerate(icon_properties):

            if (row < len(icon_node.children()) and icon_node.child(row).typeInfo() == typ.PROPERTY_SETPOINT and
                        icon_node.child(row).name == name):
                named_setpoint_node = icon_node.child(row)

            else:
                named_setpoint_index = self.insertChild(icon_index, typ.PROPERTY_SETPOINT)
                named_setpoint_node = named_setpoint_index.internalPointer()
                named_setpoint_node.name = name


            #sync the varNodeVariable
            for tool_index in self.toolModel().childrenIndexes(self.toolIndex()):
                if tool_index.internalPointer().name == named_setpoint_node.varName:
                    named_setpoint_node.setVarIndex(tool_index)


        #Remove excess children
        row = len(icon_properties)
        count = len(icon_node.children()) - len(icon_properties)
        if count > 0:
            self.removeRows(row, count, icon_index)


    def syncDeviceStateIndex(self, index):
        node = index.internalPointer()
        node.setDeviceStateCallback(self._tool_model.setData, self.toolIndex().siblingAtColumn(col.STATE))


    def syncToTool(self):

        for index in self.indexesOfType(typ.SET_DEVICE_STATE_NODE):
            self.syncDeviceStateIndex(index)

        for index in self.indexesOfType(typ.SET_NODE):
            self.syncLeafSetpoints(index)

        for index in self.indexesOfType(typ.RUN_BEHAVIOR_NODE):
            self.syncLeafRunBehaviorSetpoints(index)

        for index in self.indexesOfType(typ.WAIT_STATE_NODE):
            self.syncLeafWaitStateSetpoints(index)

        for index in self.indexesOfType(typ.WAIT_NODE):
            self.syncLeafSetpoints(index)

        for index in self.indexesOfType(typ.TOLERANCE_NODE):
            self.syncLeafTolerancepoints(index)

        for icon_index in self.indexesOfType(typ.SET_ICON_NODE):
            self.syncIconIndex(icon_index)
        
        for index in self.indexesOfType(typ.MESSAGE_NODE):
            self.syncMessageIndex(index)

        for index in self.indexesOfType(typ.ALERT_NODE):
            self.syncAlertIndex(index)

        for index in self.indexesOfType(typ.ALERT_SEQUENCE_NODE):
            self.syncAlertIndex(index)







    def name(self):
        return str(self._root_node.name)

    def fileFullPath(self):
        return defaults.TOOL_DIR + "/" + self._root_node.file()

    def file(self):
        return str(self._root_node.file())

    def setFile(self, file_name):
        self._root_node.setFile(file_name)


    #Behavior tree stuff
    def asJSON(self):
        return self._root_node.asJSON()

    def loadJSON(self, json):
        try:
            if json['type_info'] == typ.ROOT_SEQUENCE_NODE:
                self._root_node.loadAttrs(json)

                if 'children' in json:
                    for child in json['children']:
                        index = self.insertChild(self._root_index, child['type_info'], None, True)
                        index.internalPointer().loadAttrs(child)
                        self._recurseJSON(index, child)


        except Exception as e:
            MessageBox("Failed to behavior from JSON", e)
            return False


    def _recurseJSON(self, parent_index, json):
        if 'children' in json:
            for child in json['children']:
                index = self.insertChild(parent_index, child['type_info'], None, True)
                index.internalPointer().loadAttrs(child)
                self._recurseJSON(index, child)



    def rootIndex(self):
        return self._root_index

    def rowCount(self, parent):
        '''Returns the number of children'''
        if not parent.isValid():
            return 1
        else:
            parentNode = parent.internalPointer()

        return parentNode.childCount()

    def columnCount(self, parent):
        return 1 #number of columns a QTreeView displays


    #doesn't make a new node
    def insertExistingChild(self, parent_index, node, insert_row = None):
        parent_node  = parent_index.internalPointer()

        if insert_row is None:
            insert_row = parent_index.internalPointer().childCount()

        if insert_row is not False:
            self.beginInsertRows(parent_index, insert_row, insert_row) #parent, first, last
            parent_node.insertChild(insert_row, node)
            self.endInsertRows()


    def insertChildAtPos(self, parent_index, child_type, pos = (0,0)):
        insert_row = 0
        x = pos[0]

        for child in parent_index.internalPointer().children():
            if hasattr(child, 'pos'):
                if x > child.x():
                    insert_row += 1

        new_child_index = self.insertChild(parent_index, child_type, insert_row)
        self.setData(new_child_index.siblingAtColumn(col.POS), pos)
        #self.sortChildrenByXPos(parent_index)
        ###self.modelReset.emit()

        return new_child_index


    def insertChild(self, parent_index, child_type, insert_row = None, from_load = False):
        parent_node  = parent_index.internalPointer()

        if insert_row is None:
            insert_row = parent_index.internalPointer().childCount()

        if insert_row is not False:
            self.beginInsertRows(parent_index, insert_row, insert_row) #(parent, first, last)

            if    child_type == typ.SEQUENCE_NODE         : parent_node.insertChild(insert_row, SequenceNode())
            elif  child_type == typ.REPEAT_NODE           : parent_node.insertChild(insert_row, RepeatNode())
            elif  child_type == typ.REPEAT_NUMBER_NODE    : parent_node.insertChild(insert_row, RepeatNumberNode())
            elif  child_type == typ.SELECTOR_NODE         : parent_node.insertChild(insert_row, SelectorNode())
            elif  child_type == typ.WHILE_NODE            : parent_node.insertChild(insert_row, WhileNode())
            elif  child_type == typ.SET_NODE              : parent_node.insertChild(insert_row, SetNode())
            elif  child_type == typ.RUN_BEHAVIOR_NODE     : parent_node.insertChild(insert_row, RunBehaviorNode())
            elif  child_type == typ.WAIT_STATE_NODE       : parent_node.insertChild(insert_row, WaitStateNode())
            elif  child_type == typ.WAIT_NODE             : parent_node.insertChild(insert_row, WaitNode())
            elif  child_type == typ.TOLERANCE_NODE        : parent_node.insertChild(insert_row, ToleranceNode())
            elif  child_type == typ.ALERT_NODE            : parent_node.insertChild(insert_row, AlertNode())
            elif  child_type == typ.ALERT_SEQUENCE_NODE   : parent_node.insertChild(insert_row, AlertSequenceNode())
            elif  child_type == typ.MESSAGE_NODE          : parent_node.insertChild(insert_row, MessageNode())
            elif  child_type == typ.DIALOG_NODE           : parent_node.insertChild(insert_row, DialogNode())
            elif  child_type == typ.WAIT_TIME_NODE        : parent_node.insertChild(insert_row, WaitTimeNode())
            elif  child_type == typ.SET_DEVICE_STATE_NODE : parent_node.insertChild(insert_row, SetDeviceStateNode())
            elif  child_type == typ.SUCCESS_NODE          : parent_node.insertChild(insert_row, SuccessNode())
            elif  child_type == typ.FAILURE_NODE          : parent_node.insertChild(insert_row, FailureNode())
            elif  child_type == typ.SET_ICON_NODE         : parent_node.insertChild(insert_row, SetIconNode())
            elif  child_type == typ.SETPOINT              : parent_node.insertChild(insert_row, Setpoint())
            elif  child_type == typ.RUN_BEHAVIOR_SETPOINT : parent_node.insertChild(insert_row, RunBehaviorSetpoint())
            elif  child_type == typ.WAIT_STATE_SETPOINT   : parent_node.insertChild(insert_row, WaitStateSetpoint())
            elif  child_type == typ.TOLERANCEPOINT        : parent_node.insertChild(insert_row, Tolerancepoint())
            elif  child_type == typ.PROPERTY_SETPOINT     : parent_node.insertChild(insert_row, PropertySetpoint())
            elif  child_type == typ.BEHAVIOR_INPUT        : parent_node.insertChild(insert_row, BehaviorInput())

            else: MessageBox('Attempting to insert unknown node of type', child_type)

            new_child_index = self.index(insert_row, 0, parent_index)
            new_child_node = new_child_index.internalPointer()





            if from_load == False:
                if child_type == typ.SET_DEVICE_STATE_NODE:
                    self.syncDeviceStateIndex(new_child_index)

                elif child_type == typ.SET_ICON_NODE:
                    self.syncIconIndex(new_child_index)

                elif child_type == typ.MESSAGE_NODE:
                    self.syncMessageIndex(new_child_index)

                elif child_type == typ.ALERT_NODE:
                    self.syncAlertIndex(new_child_index)

                elif child_type == typ.ALERT_SEQUENCE_NODE:
                    self.syncAlertIndex(new_child_index)

                elif child_type == typ.SET_NODE:
                    self.syncLeafSetpoints(new_child_index)

                elif child_type == typ.RUN_BEHAVIOR_NODE:
                    self.syncLeafRunBehaviorSetpoints(new_child_index)

                elif child_type == typ.WAIT_STATE_NODE:
                    self.syncLeafWaitStateSetpoints(new_child_index)

                elif child_type == typ.WAIT_NODE:
                    self.syncLeafSetpoints(new_child_index)

                elif child_type == typ.TOLERANCE_NODE:
                    self.syncLeafTolerancepoints(new_child_index)




            #Shoud this go above the sync block?
            self.endInsertRows()

            return new_child_index


    def removeRows(self, row, count, parent_index):
        parent_node = parent_index.internalPointer()

        if not isinstance(row, int):
            MessageBox("Behavior Tree Model removeRows 'row' must be of type 'int', is of type: ", type(row))
            return False

        if not isinstance(count, int):
            MessageBox("Behavior Tree Model removeRows 'count' must be of type 'int', is of type: ", type(count))
            return False

        if   row <  0:
            MessageBox("Behavior Tree Model removeRows 'row' must be >= 0, is: ", row)
            return False

        if count <= 0:
            MessageBox("Behavior Tree Model removeRows 'count' must be > 0, is: ", count)
            return False

        if parent_node.childCount() <= row+count-1:
            MessageBox("Behavior Tree Model removeRows, row doesn't exist")
            return False

        self.beginRemoveRows(parent_index, row, row+count-1)

        for i in list(range(count)):
            parent_node.removeChild(row)

        self.endRemoveRows()
        #self.modelReset.emit()


    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None

        node = index.internalPointer()

        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            return node.data(index.column())

        elif role == QtCore.Qt.DecorationRole:
            if index.column() == 0:
                return None

    def moveRows(self, parent, source_row, count, destination_parent, destination_child):
        parent_node = parent.internalPointer()
        nodes = []

        source_first = source_row
        source_last = source_row + count -1
        self.beginMoveRows(parent, source_first, source_last, destination_parent, destination_child)

        for i in range(source_row, source_row-count, -1):
            node = parent_node.removeChild(i)
            nodes.append(node)

        for node in nodes:
            parent_node.insertChild(destination_child, node)

        self.endMoveRows()

        return True

    def itemFromIndex(self, index):
        if index.isValid():
            return index.internalPointer()
        return self._root_node

    def mimeTypes(self):
        types = QtCore.QStringList()
        types.append('application/x-pyobj')
        return types

    def mimeData(self, index):
        '''Encode serialized data from the item at the given index into a QMimeData object.'''
        data = ''
        item = self.itemFromIndex(index)

        print(item)
        for k, v in item.__dict__.items():
            try:
                pickle.dumps(v)
                print("can pickle: ", k, " - ", v)
            except:
                attribute = k
                print("can't pickle: ", attribute)



        #try:
        #    data += pickle.dumps( item )
        #except:
        #    pass
        #
        #print("mimeData")
        #print(data)

        #mimedata = QtCore.QMimeData()
        #mimedata.setData('application/x-pynode-item-instance', data )
        #print(mimedata)
        #return mimedata


    #TODO might be buggy casue not all nodes have position now
    def sortChildrenByXPos(self, index):
        node = index.internalPointer()
        if node is not None:
            moved = False
            x_positions = []

            for child in node.children():
                if hasattr(child, 'pos'):
                    x_positions.append((child.row(), child.pos[0]))

            x_sorted = sorted(x_positions, key=lambda x: x[1])

            while x_sorted != x_positions:
                i = 0
                for row, x_pos in x_sorted:
                    if row != i:
                        moved = True
                        self.moveRow(index, row, index, i)
                        break
                    i += 1

                x_positions = []
                for child in node.children():
                    if hasattr(child, 'pos'):
                        x_positions.append((child.row(), child.pos[0]))
                x_sorted = sorted(x_positions, key=lambda x: x[1])

            if moved:
                node.reset()


    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if type(value) == type(QtCore.QVariant()):
            value = value.toPyObject()

        node = index.internalPointer()
        parent = node.parent()

        if index.isValid() and role == QtCore.Qt.EditRole:
            node.setData(index.column(), value)


            if index.column() == col.VAR_NODE_NAME:
                for tool_index in self.toolModel().childrenIndexes(self.toolIndex()):
                    if tool_index.internalPointer().name == value:
                        node.setVarIndex(tool_index)

            #Some day convert the tolerance node to use the VAR_NODE_NAME style
            elif index.column() == col.COMPARE_2_NAME:
                for tool_index in self.toolModel().childrenIndexes(self.toolIndex()):
                    if tool_index.internalPointer().name == value:
                        node.setCompare2Index(tool_index)

            elif index.column() == col.TOLERANCE_SCALE_NAME:
                for tool_index in self.toolModel().childrenIndexes(self.toolIndex()):
                    if tool_index.internalPointer().name == value:
                        node.setToleranceScaleIndex(tool_index)

            elif index.column() == col.TOLERANCE_OFFSET_NAME:
                for tool_index in self.toolModel().childrenIndexes(self.toolIndex()):
                    if tool_index.internalPointer().name == value:
                        node.setToleranceOffsetIndex(tool_index)
            
            elif index.column() == col.BEHAVIOR_NAME: #Only for Tool/System RUN BEHAVIOR nodes TODO refine
                device_node = node.setIndex().internalPointer()
                for behavior in device_node.behaviors():
                    if behavior.name() == value:
                        node.setBehavior(behavior)


            self.dataChanged.emit(index, index)

            if index.column() == col.POS:
                self.sortChildrenByXPos(self.parent(index)) #has to happen after dataChanged



            return True

        return False

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole and section == 0:
            return "Type"

    def supportedDropActions(self):
        return QtCore.Qt.MoveAction

    def flags(self, index):
        node = index.internalPointer()

        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | \
               QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsDropEnabled


    def parent(self, index):
        if index.internalPointer() == self._root_node:
            return QtCore.QModelIndex()

        elif index is not None and index.isValid():
            node = index.internalPointer()
            parent_node = node.parent()
            return self.createIndex(parent_node.row(), 0, parent_node)


    def index(self, row, column, parent_index):
        if parent_index is not None and parent_index.isValid():
            parent_node = parent_index.internalPointer()
            child_item = parent_node.child(row)
            return self.createIndex(row, column, child_item)

        else:
            return self.createIndex(row, column, self._root_node)



    def indexesOfTypes(self, index_types, parent_index=None):
        indexes = []
        for index_type in index_types:
            indexes += self.indexesOfType(index_type, parent_index)

        return indexes

    def indexesOfType(self, index_type, parent_index=None):
        try:
            parent_node = parent_index.internalPointer() if parent_index.isValid() else self._root_node
        except:
            parent_index = self.index(0, 0, QtCore.QModelIndex())
            parent_node = self._root_node

        indexes = []

        for row in range(self.rowCount(parent_index)):
            index = parent_index.child(row, 0)

            if index.internalPointer().typeInfo() == index_type:
                indexes.append(index)

            indexes += self.indexesOfType(index_type, index)

        return indexes

    

    def tick(self):
        result = self._root_node.tick()
        info_text = self._root_node.infoText()
        self.toolModel().setData(self.toolIndex().siblingAtColumn(col.BEHAVIOR_INFO_TEXT), info_text)

        index_1 = self.index(0, col.BT_STATUS, self._root_index)
        self.dataChanged.emit(index_1, index_1)

        return result

    def setRunning(self):
        self._root_node.reset()
        self.toolModel().setData(self.toolIndex().siblingAtColumn(col.RUNNING_BEHAVIOR_NAME), self._root_node.name)
        self.toolModel().setData(self.toolIndex().siblingAtColumn(col.RUNNING_BEHAVIOR), self)

    def setStopped(self):
        self.toolModel().setData(self.toolIndex().siblingAtColumn(col.BEHAVIOR_INFO_TEXT), '')
        self.toolModel().setData(self.toolIndex().siblingAtColumn(col.RUNNING_BEHAVIOR_NAME), '')
        self.toolModel().setData(self.toolIndex().siblingAtColumn(col.RUNNING_BEHAVIOR), None)


    def runAbortOthers(self):
        #BTModel.behaviorRunner.runAbortSiblings(self)
        self.behaviorRunner().runAbortSiblings(self)

    def abort(self):
        #BTModel.behaviorRunner.stopBehavior(self)
        self.behaviorRunner().stopBehavior(self)








        #if result != bt.RUNNING and result != bt.FAILURE:
        #    self._root_node.reset()

    #def run(self):#, var_data=None):
        #if var_data is not None:
        #    for key, value in var_data.items():
        #        for index in indexes:
        #            node = index.internalPointer()
        #            if node.name == key:
        #                self.setData(index, value)

        #        #if key in self.indexesOfTypes([typ.BOOL_VAR_NODE, typ.FLOAT_VAR_NODE])


        #self._timer.stop()
    #def runAbortOthers(self):
    #    tool_node = self.toolIndex().internalPointer()
    #    for behavior in tool_node.behaviors():
    #        if behavior is not self:
    #            behavior.abort()

    #    self.run()




