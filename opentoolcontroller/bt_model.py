from PyQt5 import QtCore, QtGui

from opentoolcontroller.strings import bt, col, typ
from opentoolcontroller.bt_data import *
from opentoolcontroller.message_box import MessageBox

import json
import os.path
import pprint
pp = pprint.PrettyPrinter(width=82, compact=True)

class BTModel(QtCore.QAbstractItemModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._root_node = RootSequenceNode()
        self._root_index = self.createIndex(0, 0, self._root_node) #There's a empty index w/out a valid parent above this
        self._timer = QtCore.QTimer()
        self._timer.timeout.connect(self.tick)

        self._tool_callback = None
        self._index_icon = None

        self._tool_model = None
        self._tool_index = None

        self._node_types = {}



    def setToolModel(self, tool_model):
        self._tool_model = tool_model

    def toolModel(self):
        return self._tool_model

    def setToolIndex(self, tool_index):
        self._tool_index = tool_index

    def toolIndex(self):
        return self._tool_index

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


        #After all the sets are usable then we need to sync the compare2Index and tolernaceIndex
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


    def file(self):
        return str(self._root_node.file())

    def setFile(self, file_name):
        self._root_node.setFile(file_name)

        if isinstance(file_name, str) and os.path.isfile(file_name):
            with open(file_name) as f:
                json_data = json.load(f)
                self.loadJSON(json_data)








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
        #result = self._root_node.child(0).tick()
        result = self._root_node.tick()
        info_text = self._root_node.infoText()
        self.toolModel().setData(self.toolIndex().siblingAtColumn(col.BEHAVIOR_INFO_TEXT), info_text)

        #TODO For the BT_STATUS column it will just update the status from all of them
        #Might want to change that to update all of them that are in view at some point
        index_1 = self.index(0, col.BT_STATUS, self._root_index)
        self.dataChanged.emit(index_1, index_1)

        if result == bt.SUCCESS or result == bt.FAILURE:
            self._timer.stop()
            self.toolModel().setData(self.toolIndex().siblingAtColumn(col.BEHAVIOR_INFO_TEXT), "")
            self.toolModel().setData(self.toolIndex().siblingAtColumn(col.RUNNING_BEHAVIOR_NAME), '')
            self.toolModel().setData(self.toolIndex().siblingAtColumn(col.RUNNING_BEHAVIOR), None)

        #if result != bt.RUNNING and result != bt.FAILURE:
        #    self._root_node.reset()

    def run(self):#, var_data=None):
        #if var_data is not None:
        #    for key, value in var_data.items():
        #        for index in indexes:
        #            node = index.internalPointer()
        #            if node.name == key:
        #                self.setData(index, value)

        #        #if key in self.indexesOfTypes([typ.BOOL_VAR_NODE, typ.FLOAT_VAR_NODE])


        self._timer.stop()
        self._root_node.reset()
        self._timer.start(self._root_node.tick_rate_ms)
        self.toolModel().setData(self.toolIndex().siblingAtColumn(col.RUNNING_BEHAVIOR_NAME), self._root_node.name)
        self.toolModel().setData(self.toolIndex().siblingAtColumn(col.RUNNING_BEHAVIOR), self)
        #print(self.toolIndex().internalPointer().name)
        #TODO this timer might not be the most consistent
        self.tick()


    def runAbortOthers(self):
        tool_node = self.toolIndex().internalPointer()
        for behavior in tool_node.behaviors():
            if behavior is not self:
                behavior.abort()

        self.run()

    def abort(self):
        self._timer.stop()
        self.toolModel().setData(self.toolIndex().siblingAtColumn(col.BEHAVIOR_INFO_TEXT), '')
        self.toolModel().setData(self.toolIndex().siblingAtColumn(col.RUNNING_BEHAVIOR_NAME), '')
        self.toolModel().setData(self.toolIndex().siblingAtColumn(col.RUNNING_BEHAVIOR), None)

