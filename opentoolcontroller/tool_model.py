from PyQt5 import QtCore, QtGui

from opentoolcontroller.strings import col, typ
from opentoolcontroller.tool_data import *
from opentoolcontroller.message_box import MessageBox


#The tool model represents an entire tool in a tree structure.
class ToolModel(QtCore.QAbstractItemModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tool_node = ToolNode()
        self._tool_index = self.createIndex(0, 0, self._tool_node) #There's a empty index w/out a valid parent above this
        self._alert_callback = None


    def alertCallback(self):
        return self._alert_callback

    def setAlertCallback(self, callback):
        self._alert_callback = callback


    def setLaunchValues(self):
        indexes = self.indexesOfTypes([typ.BOOL_VAR_NODE, typ.INT_VAR_NODE, typ.FLOAT_VAR_NODE])
        for index in indexes:
            node = index.internalPointer()
            if node.useLaunchValue:
                node.setData(col.VALUE, node.launchValue)

    #needs to happen after tool is loaded so all the tool nodes have their properties
    def loadBehaviors(self):
        indexes = self.indexesOfType(typ.DEVICE_NODE)
        indexes += self.indexesOfType(typ.SYSTEM_NODE)
        indexes += [self._tool_index]

        for index in indexes:
            node = index.internalPointer()
            node.loadBehaviors()

            bt_models = node.behaviors()

            for bt_model in bt_models:
                bt_model.setToolModel(self)
                bt_model.setToolIndex(index)
                bt_model.syncToTool()



    def asJSON(self):
        return self._tool_node.asJSON()

    def loadJSON(self, json):
        try:
            if json['type_info'] == typ.TOOL_NODE:
                self._tool_node.loadAttrs(json)

                if 'children' in json:
                    for child in json['children']:
                        index = self.insertChild(self._tool_index, child['type_info'], None, True)
                        index.internalPointer().loadAttrs(child)
                        self._recurseJSON(index, child)

            return True
        except Exception as e:
            MessageBox("Failed to behavior from JSON", e)
            return False

    def _recurseJSON(self, parent_index, json):
        if 'children' in json:
            for child in json['children']:
                index = self.insertChild(parent_index, child['type_info'], None, True)
                index.internalPointer().loadAttrs(child)
                self._recurseJSON(index, child)


    def rowCount(self, parent):
        if not parent.isValid():
            return 1 #Only a single tool
        else:
            parentNode = parent.internalPointer()

        return parentNode.childCount()

    def columnCount(self, parent):
        return 2 #Number of columns the QTreeView displays

    def possibleChildren(self, index):
        node_type = index.internalPointer().typeInfo()

        if   node_type == typ.TOOL_NODE:
            return [typ.SYSTEM_NODE,
                    typ.BOOL_VAR_NODE,
                    typ.INT_VAR_NODE,
                    typ.FLOAT_VAR_NODE]

        elif node_type == typ.SYSTEM_NODE:
            return [typ.DEVICE_NODE,
                    typ.BOOL_VAR_NODE,
                    typ.INT_VAR_NODE,
                    typ.FLOAT_VAR_NODE]

        elif node_type == typ.DEVICE_NODE:
            return [typ.DEVICE_ICON_NODE,
                    typ.D_IN_NODE,
                    typ.D_OUT_NODE,
                    typ.A_IN_NODE,
                    typ.A_OUT_NODE,
                    typ.BOOL_VAR_NODE,
                    typ.INT_VAR_NODE,
                    typ.FLOAT_VAR_NODE]

        elif node_type == typ.DEVICE_ICON_NODE:
            return []

        elif node_type in [typ.D_IN_NODE, typ.D_OUT_NODE, typ.A_IN_NODE, typ.A_OUT_NODE, typ.BOOL_VAR_NODE, typ.INT_VAR_NODE, typ.FLOAT_VAR_NODE]:
            return []


    def insertChild(self, parent_index, child_type, insert_row = None, from_load = False):
        parent_node  = parent_index.internalPointer()

        if insert_row is None:
            insert_row = parent_index.internalPointer().childCount()

        if insert_row is not False:
            self.beginInsertRows(parent_index, insert_row, insert_row)

            if    child_type == typ.TOOL_NODE        : parent_node.insertChild(insert_row, ToolNode())
            elif  child_type == typ.SYSTEM_NODE      : parent_node.insertChild(insert_row, SystemNode())
            elif  child_type == typ.DEVICE_NODE      : parent_node.insertChild(insert_row, DeviceNode())
            elif  child_type == typ.DEVICE_ICON_NODE : parent_node.insertChild(insert_row, DeviceIconNode())
            elif  child_type == typ.D_IN_NODE        : parent_node.insertChild(insert_row, DigitalInputNode())
            elif  child_type == typ.D_OUT_NODE       : parent_node.insertChild(insert_row, DigitalOutputNode())
            elif  child_type == typ.A_IN_NODE        : parent_node.insertChild(insert_row, AnalogInputNode())
            elif  child_type == typ.A_OUT_NODE       : parent_node.insertChild(insert_row, AnalogOutputNode())
            elif  child_type == typ.BOOL_VAR_NODE    : parent_node.insertChild(insert_row, BoolVarNode())
            elif  child_type == typ.INT_VAR_NODE     : parent_node.insertChild(insert_row, IntVarNode())
            elif  child_type == typ.FLOAT_VAR_NODE   : parent_node.insertChild(insert_row, FloatVarNode())

            else: MessageBox('Attempting to insert unknown node of type', child_type)

            self.endInsertRows()

            new_child_index = self.index(insert_row, 0, parent_index)
            new_child_node = new_child_index.internalPointer()


            #Add the node to each behavior tree
            if parent_node.typeInfo() == typ.DEVICE_NODE and not from_load:
                for bt_model in parent_node.behaviors():
                    bt_model.syncToTool()




            return new_child_index


    def removeRows(self, row, count, parent_index):
        parent_node = parent_index.internalPointer()
        node = self.index(row, 0, parent_index).internalPointer()

        if not isinstance(row, int):
            raise TypeError("Tool Model removeRows 'row' must be of type 'int")

        if not isinstance(count, int):
            raise TypeError("Tool Model removeRows 'count' must be of type 'int'")

        if row < 0:
            raise ValueError("Tool Model removeRows 'row' must be >= 0")

        if count <= 0:
            raise ValueError("Tool Model removeRows 'count' must be > 0")


        self.beginRemoveRows(parent_index, row, row+count-1)

        for i in list(range(count)):
            parent_node.removeChild(row)

        self.endRemoveRows()


        #Remove it from the behavior tree
        if parent_node.typeInfo() == typ.DEVICE_NODE:
            for bt_model in parent_node.behaviors():
                bt_model.syncToTool()



    #Views access data through this interface, index is a QModelIndex
    #Returns a QVariant, strings are cast to QString which is a QVariant
    def data(self, index, role):
        if not index.isValid():
            return None

        node = index.internalPointer()

        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            return node.data(index.column())

        elif role == QtCore.Qt.DecorationRole:
            if index.column() == 0:
                return None


    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if type(value) == type(QtCore.QVariant()):
            value = value.toPyObject()

        #TODO this might break something
        #if index.isValid() and role == QtCore.Qt.EditRole and value is not None:
        #need to set the running behavior to None, not sure why I forced value to not be None, proabbly gonna break something 10/7/23
        if index.isValid() and role == QtCore.Qt.EditRole:
            node = index.internalPointer()
            old_value = node.data(index.column())
            node.setData(index.column(), value)
            self.dataChanged.emit(index, index)

            if index.column() == col.HAL_VALUE and node.typeInfo() in typ.HAL_NODES:
                self.dataChanged.emit(index.siblingAtColumn(col.VALUE), index.siblingAtColumn(col.VALUE))

            if index.column() == col.HAL_PIN and node.typeInfo() in typ.HAL_NODES:
                self.dataChanged.emit(index.siblingAtColumn(col.HAL_PIN_TYPE), index.siblingAtColumn(col.HAL_PIN_TYPE))


            if index.column() == col.POS and node.typeInfo() == typ.DEVICE_ICON_NODE:
                self.dataChanged.emit(index.siblingAtColumn(col.X), index.siblingAtColumn(col.X))
                self.dataChanged.emit(index.siblingAtColumn(col.Y), index.siblingAtColumn(col.Y))

            if index.column() == col.BEHAVIORS and node.typeInfo() in [typ.DEVICE_NODE, typ.SYSTEM_NODE, typ. TOOL_NODE]:
                for i, item in enumerate(value): 
                    #If a string is inserted into the behavior list we convert that into a new bt model
                    if isinstance(item, str):
                        new_bt_model = BTModel()
                        new_bt_model.setFile(item)
                        new_bt_model.setToolModel(self)
                        new_bt_model.setToolIndex(index)
                        new_bt_model.syncToTool()
                        value[i] = new_bt_model
                node.setBehaviors(value)
                self.dataChanged.emit(index, index)


            #If the system is put online the devices must not be in manual control
            if index.column() == col.SYSTEM_IS_ONLINE and node.typeInfo() == typ.SYSTEM_NODE:
                if value == True:
                    node.setData(col.DEVICE_MANUAL_CONTROL, False)
                    self.dataChanged.emit(index.siblingAtColumn(col.DEVICE_MANUAL_CONTROL), index.siblingAtColumn(col.DEVICE_MANUAL_CONTROL))

            '''Add something for single behavior running per system? '''

            return True

        return False


    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if   section == 0: return "Name"
            elif section == 1: return "Type"

    def flags(self, index):
        node = index.internalPointer()
        flag = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

        if (index.column() == 1) and node.typeInfo() == typ.DEVICE_NODE:
            return flag | QtCore.Qt.ItemIsEditable

        return flag


    def parent(self, index):
        if index.internalPointer() == self._tool_node:
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
            return self.createIndex(row, column, self._tool_node)


    def indexesOfTypes(self, index_types, parent_index=None, depth=10):
        indexes = []
        for index_type in index_types:
            indexes += self.indexesOfType(index_type, parent_index, depth)
        return indexes

    def indexesOfType(self, index_type, parent_index=None, depth=10):
        if parent_index is None:
            parent_index = self._tool_index

        elif parent_index.isValid() is not True:
            parent_index = self._tool_index


        indexes = []

        if depth>0:
            for row in range(self.rowCount(parent_index)):
                index = parent_index.child(row, 0)

                if index.internalPointer().typeInfo() == index_type:
                    indexes.append(index)

                indexes += self.indexesOfType(index_type, index, depth-1)

        return indexes

    def childrenIndexes(self, parent_index=None):
        if parent_index is None:
            return []

        if not parent_index.isValid():
            return []

        indexes = []
        for row in range(self.rowCount(parent_index)):
            indexes.append(parent_index.child(row, 0))

        return indexes






## Taken from: http://gaganpreet.in/blog/2013/07/04/qtreeview-and-custom-filter-models/
class LeafFilterProxyModel(QtCore.QSortFilterProxyModel):
    ''' Class to override the following behaviour:
            If a parent item doesn't match the filter,
            none of its children will be shown.

        This Model matches items which are descendants
        or ascendants of matching items.
    '''


    #Overriding the parent function
    def filterAcceptsRow(self, row_num, source_parent):

        # Check if the current row matches
        if self.filter_accepts_row_itself(row_num, source_parent):
            return True

        # Traverse up all the way to root and check if any of them match
        if self.filter_accepts_any_parent(source_parent):
            return True

        # Finally, check if any of the children match
        return self.has_accepted_children(row_num, source_parent)

    def filter_accepts_row_itself(self, row_num, parent):
        return super(LeafFilterProxyModel, self).filterAcceptsRow(row_num, parent)

    #Traverse to the root node and check if any of the ancestors match the filter
    def filter_accepts_any_parent(self, parent):
        while parent.isValid():
            if self.filter_accepts_row_itself(parent.row(), parent.parent()):
                return True
            parent = parent.parent()
        return False

    #Starting from the current node as root, traverse all the descendants and test if any of the children match
    def has_accepted_children(self, row_num, parent):
        model = self.sourceModel()
        source_index = model.index(row_num, 0, parent)

        children_count =  model.rowCount(source_index)
        for i in range(children_count):
            if self.filterAcceptsRow(i, source_index):
                return True

        return False

    def removeRows(self, row, count, index):
        self.sourceModel().removeRows(row, count, index)

    def insertChild(self, parent_index, node_type, preferred_row = None):
        return self.sourceModel().insertChild(parent_index, node_type, preferred_row)

    def possibleChildren(self, index):
        return self.sourceModel().possibleChildren(index)
