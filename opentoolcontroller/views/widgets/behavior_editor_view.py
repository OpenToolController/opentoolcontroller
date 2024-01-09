#!/usr/bin/python3
# -*- coding: utf-8 -*-
from PyQt5 import QtGui, QtCore, QtWidgets
from opentoolcontroller.strings import bt, col, typ
import math
from opentoolcontroller.message_box import MessageBox
#from opentoolcontroller.views.widgets.svg_widget import SVGWidget
from opentoolcontroller.views.widgets.behavior_editor_nodes import *

import pprint
pp = pprint.PrettyPrinter(width=82, compact=True)


class BTEditorWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._bt_editor = BTEditor(self)
        self.setCentralWidget(self._bt_editor)
        self.initMenu()

        self._settings = QtCore.QSettings('OpenToolController', 'test1')
        self._filename = None
        geometry = self._settings.value('bt_editor_geometry', bytes('', 'utf-8'))
        self.restoreGeometry(geometry)



    def setTitle(self, file_changed = False):
        try:
            name = self._bt_editor.model().name()

            if file_changed == False:
                self.setWindowTitle(str("Behavior: " + name))
            else:
                self.setWindowTitle(str("Behavior: " + name + "*"))
        except:
            self.setWindowTitle("unknown")


    def setFileName(self, value):
        self._filename = value

    def initMenu(self):

        self.save_action = QtWidgets.QAction("&Save", self)
        self.save_action.setShortcut('ctrl+s')
        self.save_action.triggered.connect(self.saveBehavior)

        self.save_as_action = QtWidgets.QAction("&Save A Copy", self)
        self.save_as_action.triggered.connect(self.saveBehaviorCopy)

        self.exit_action = QtWidgets.QAction("&Exit", self)
        self.exit_action.triggered.connect(self.close)

        menu_bar = self.menuBar()
        file_menu = QtWidgets.QMenu("&File", self)
        menu_bar.addMenu(file_menu)
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_as_action)
        file_menu.addAction(self.exit_action)


    def initToolbar(self, node_typeInfo):
        toolbar = QtWidgets.QToolBar(self)
        self.addToolBar(toolbar)
        self.setStatusBar(QtWidgets.QStatusBar(self))

        self._button_group = QtWidgets.QActionGroup(toolbar)
        self._button_group.setExclusive(True)

        menu_data = []

        if node_typeInfo == typ.TOOL_NODE:
            menu_data = [('opentoolcontroller/resources/icons/menu/behavior_tree/sequencer.png',"Sequencer", typ.SEQUENCE_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/repeat.png',"Repeat", typ.REPEAT_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/selector.png',"Selector", typ.SELECTOR_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/wait_time.png',"Wait Time", typ.WAIT_TIME_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/alert.png',"Alert", typ.ALERT_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/alert_sequence.png',"Alert Sequence", typ.ALERT_SEQUENCE_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/message.png',"Message", typ.MESSAGE_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/dialog.png',"Dialog", typ.DIALOG_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/set.png',"Run Behavior", typ.RUN_BEHAVIOR_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/wait.png',"Wait for State", typ.WAIT_STATE_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/success.png',"Success", typ.SUCCESS_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/failure.png',"Failure", typ.FAILURE_NODE)]


        elif node_typeInfo == typ.SYSTEM_NODE:
            menu_data = [('opentoolcontroller/resources/icons/menu/behavior_tree/sequencer.png',"Sequencer", typ.SEQUENCE_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/repeat.png',"Repeat", typ.REPEAT_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/selector.png',"Selector", typ.SELECTOR_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/wait_time.png',"Wait Time", typ.WAIT_TIME_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/alert.png',"Alert", typ.ALERT_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/alert_sequence.png',"Alert Sequence", typ.ALERT_SEQUENCE_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/message.png',"Message", typ.MESSAGE_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/dialog.png',"Dialog", typ.DIALOG_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/set.png',"Run Behavior", typ.RUN_BEHAVIOR_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/wait.png',"Wait for State", typ.WAIT_STATE_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/success.png',"Success", typ.SUCCESS_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/failure.png',"Failure", typ.FAILURE_NODE)]

        elif node_typeInfo == typ.DEVICE_NODE:
            menu_data = [('opentoolcontroller/resources/icons/menu/behavior_tree/sequencer.png',"Sequencer", typ.SEQUENCE_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/repeat.png',"Repeat", typ.REPEAT_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/selector.png',"Selector", typ.SELECTOR_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/wait_time.png',"Wait Time", typ.WAIT_TIME_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/set.png',"Set", typ.SET_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/wait.png',"Wait", typ.WAIT_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/tolerance.png',"Wait", typ.TOLERANCE_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/alert.png',"Alert", typ.ALERT_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/alert_sequence.png',"Alert Sequence", typ.ALERT_SEQUENCE_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/message.png',"Message", typ.MESSAGE_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/dialog.png',"Dialog", typ.DIALOG_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/set_icon_layer.png',"Set Icon", typ.SET_ICON_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/set_device_state.png',"Set Device State", typ.SET_DEVICE_STATE_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/success.png',"Success", typ.SUCCESS_NODE),
                 ('opentoolcontroller/resources/icons/menu/behavior_tree/failure.png',"Failure", typ.FAILURE_NODE)]




        for file, name, btn_typ in menu_data:
            button_action = QtWidgets.QAction(QtGui.QIcon(file), "Insert a " + str(name) + " node", self)
            button_action.triggered.connect(lambda name, item=btn_typ: self._bt_editor.setNewItemType(item))

            button_action.setCheckable(True)
            self._button_group.addAction(button_action)
            toolbar.addAction(button_action)

    def setModel(self, model):
        self._bt_editor.setModel(model)
        self.setTitle(file_changed=False)
        self.initToolbar(model.toolIndex().internalPointer().typeInfo())

    def model(self):
        return self._bt_editor.model()

    def setEditable(self, value):
        value = bool(value)

        self._bt_editor.setEditable(value)
        for btn in self._button_group.actions():
            btn.setEnabled(value)

    def closeEvent(self, event):
        geometry = self.saveGeometry()
        self._settings.setValue('bt_editor_geometry', geometry)
        super().closeEvent(event)

    def saveBehavior(self):
        data = self._bt_editor.model().asJSON()
        filename = self._bt_editor.model().fileFullPath()
        with open(filename, 'w') as f:
            f.write(data)

        self.setTitle(file_changed=False)

    def saveBehaviorCopy(self):
        data = self._bt_editor.model().asJSON()

        #FIXME: this doesn't let me save a new file for some reason
        #options = QtWidgets.QFileDialog.Options()
        #options |= QtWidgets.QFileDialog.DontUseNativeDialog
        dialog = QtWidgets.QFileDialog(self)
        dialog.setWindowTitle('save a copy')
        dialog.setNameFilter('(*.json)')
        dialog.setFileMode(QtWidgets.QFileDialog.AnyFile)
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)

        filename = None
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            filename = dialog.selectedFiles()

        if filename:
            filename = str(filename[0])
            with open(filename, 'w') as f:
                f.write(data)



class BTGraphicsView(QtWidgets.QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.zoom = 1
        self.zoom_rate = 1.05
        self.zoom_max = 5
        self.zoom_min = 0.2

        self.setup()


    def setup(self):
        self.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.HighQualityAntialiasing | QtGui.QPainter.TextAntialiasing | QtGui.QPainter.SmoothPixmapTransform)
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.FullViewportUpdate)

        self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor( QtWidgets.QGraphicsView.AnchorUnderMouse)

    def wheelEvent(self, event):
        old_pos = self.mapToScene(event.pos())
        scroll_amount = event.angleDelta().y()

        if   scroll_amount == 0: return
        elif scroll_amount >  1: zoom_amount = self.zoom_rate
        elif scroll_amount < -1: zoom_amount = 1.0 / self.zoom_rate

        if not self.zoom_min < (self.zoom * zoom_amount) < self.zoom_max:
            zoom_amount = 1

        self.scale(zoom_amount, zoom_amount)

        #translate so we zoom where the mouse is
        new_pos = self.mapToScene(event.pos())
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())


class BTGraphicsScene(QtWidgets.QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)

        # settings
        self.scene_width, self.scene_height = 64000, 64000
        self.setSceneRect(-self.scene_width//2, -self.scene_height//2, self.scene_width, self.scene_height)

        self.gridSize = 20
        self.gridSquares = 5

        self._color_background = QtGui.QColor("#393939")
        self._color_light = QtGui.QColor("#2f2f2f")
        self._color_dark = QtGui.QColor("#292929")

        self._pen_light = QtGui.QPen(self._color_light)
        self._pen_light.setWidth(1)
        self._pen_dark = QtGui.QPen(self._color_dark)
        self._pen_dark.setWidth(2)
        self.setBackgroundBrush(self._color_background)


    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)

        # here we create our grid
        left = int(math.floor(rect.left()))
        right = int(math.ceil(rect.right()))
        top = int(math.floor(rect.top()))
        bottom = int(math.ceil(rect.bottom()))

        first_left = left - (left % self.gridSize)
        first_top = top - (top % self.gridSize)

        # compute all lines to be drawn
        lines_light, lines_dark = [], []
        for x in range(first_left, right, self.gridSize):
            if (x % (self.gridSize*self.gridSquares) != 0): lines_light.append(QtCore.QLine(x, top, x, bottom))
            else: lines_dark.append(QtCore.QLine(x, top, x, bottom))

        for y in range(first_top, bottom, self.gridSize):
            if (y % (self.gridSize*self.gridSquares) != 0): lines_light.append(QtCore.QLine(left, y, right, y))
            else: lines_dark.append(QtCore.QLine(left, y, right, y))

        # draw the lines
        painter.setPen(self._pen_light)
        painter.drawLines(*lines_light)

        painter.setPen(self._pen_dark)
        painter.drawLines(*lines_dark)



class BTEditor(QtWidgets.QAbstractItemView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = BTGraphicsScene(self)
        self._scene_items = []  #[(p_index, item),(p_index2, item2)]
        self._paths = [] #[(p_index, path),...]
        #self._from_callback = False
        self._new_item_type = typ.WAIT_TIME_NODE
        self._mappers = []

        self._editable = True

        #UI Stuff
        self._view = BTGraphicsView(self)
        self._view.setScene(self._scene)

        #Layout
        self.h_layout = QtWidgets.QHBoxLayout()
        self.h_layout.addWidget(self._view)
        self.h_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.h_layout)

    def setEditable(self, value):
        value = bool(value)

        self._editable = value
        for p_index, g_item in self._scene_items:
            g_item.setEditable(value)

    def setNewItemType(self, new_type):
        self._new_item_type = new_type

    #Dont use setSelection or setModel with this view
    def reset(self):
        self._scene.clear()
        self._view.viewport().update()
        self._scene_items = []  #[(p_index, item),(p_index2, item2)]
        self._paths = [] #[(p_index, path),...]

        root_index =  self.model().index(0, 0, QtCore.QModelIndex())
        self.addNodeItem(root_index)

        for row in range(self.model().rowCount(root_index)):
            index = root_index.child(row, 0)
            self.addNodeItem(index)
            self._recurseAdd(index)


    def _recurseAdd(self, parent_index):
        for row in range(self.model().rowCount(parent_index)):
            index = parent_index.child(row, 0)
            self.addNodeItem(index)
            self._recurseAdd(index)

    def _recurseRemove(self, parent_index):
        for row in range(self.model().rowCount(parent_index)):
            index = parent_index.child(row, 0)
            self._recurseRemove(index) #have to recurse before remove
            self.removeNodeItem(index)

    def setData(self, p_index, value):
        #self._from_callback = True
        index = self.model().index(p_index.row(), p_index.column(), p_index.parent())
        self.model().setData(index, value)

    def graphicItemFromIndex(self, index):
        index = index.siblingAtColumn(0)
        items = [item for item in self._scene_items if QtCore.QModelIndex(item[0]) == index] # Returns list of all tuples that match
        graphic_item = items[0][1] #[ (p_index, item), (p_index2, item2) ]
        return graphic_item

    def indexFromGraphicItem(self, g_item):
        try:
            items = [item for item in self._scene_items if item[1] == g_item] # Returns list of all tuples that match
            index = items[0][0] #[ (index, item), (index2, item2) ]
            return index
        except:
            return None

    #Called by methods that interface the bt_model
    def addNodeItem(self, index):
        node = index.internalPointer()
        type = node.typeInfo()


        if type in [typ.SETPOINT,
                    typ.TOLERANCEPOINT,
                    typ.WAIT_STATE_SETPOINT,
                    typ.RUN_BEHAVIOR_SETPOINT, 
                    typ.PROPERTY_SETPOINT,
                    typ.BEHAVIOR_INPUT]:
            return

        elif type == typ.ROOT_SEQUENCE_NODE:
            '''next have this pull from the model! '''
            item = RootSequenceNodeGraphicsItem(type, self.model().indexesOfType(typ.BEHAVIOR_INPUT, index))
            #item = RootSequenceNodeGraphicsItem(type, node.childrenByTreeType(bt.PROPERTY))
            item.setModelAndIndex(self.model(), index)

        elif type == typ.SEQUENCE_NODE:
            item = SequenceNodeGraphicsItem(type) 

        elif type == typ.SELECTOR_NODE:
            item = SelectorNodeGraphicsItem(type) 

        elif type == typ.SUCCESS_NODE:
            item = SuccessNodeGraphicsItem(type) 

        elif type == typ.FAILURE_NODE:
            item = FailureNodeGraphicsItem(type) 

        elif type == typ.REPEAT_NODE:
            item = RepeatNodeGraphicsItem(type, node.children())
            item.setModelAndIndex(self.model(), index)
        
        elif type == typ.SET_NODE:
            item = SetNodeGraphicsItem(type, node.children())
            item.setModelAndIndex(self.model(), index)

        elif type == typ.RUN_BEHAVIOR_NODE:
            item = RunBehaviorNodeGraphicsItem(type, node.children())
            item.setModelAndIndex(self.model(), index)

        elif type == typ.WAIT_STATE_NODE:
            item = WaitStateNodeGraphicsItem(type, node.children())
            item.setModelAndIndex(self.model(), index)

        elif type == typ.WAIT_NODE:
            item = WaitNodeGraphicsItem(type, node.children())
            item.setModelAndIndex(self.model(), index)

        elif type == typ.TOLERANCE_NODE:
            item = ToleranceNodeGraphicsItem(type, node.children())
            item.setModelAndIndex(self.model(), index)

        elif type == typ.SET_ICON_NODE:
            item = SetIconNodeGraphicsItem(type)
            item.setModelAndIndex(self.model(), index)

        elif type in [typ.ALERT_NODE, typ.ALERT_SEQUENCE_NODE]:
            item = AlertNodeGraphicsItem(type)
            item.setModelAndIndex(self.model(), index)
        
        elif type == typ.MESSAGE_NODE:
            item = MessageNodeGraphicsItem(type)
            item.setModelAndIndex(self.model(), index)

        elif type == typ.DIALOG_NODE:
            item = DialogNodeGraphicsItem(type)
            item.setModelAndIndex(self.model(), index)

        elif type == typ.WAIT_TIME_NODE:
            item = WaitTimeNodeGraphicsItem(type)
            item.setModelAndIndex(self.model(), index)

        elif type == typ.SET_DEVICE_STATE_NODE:
            item = SetDeviceStateGraphicsItem(type)
            item.setModelAndIndex(self.model(), index)

        else:
            MessageBox("Node not defined in behavior view", str(type))
            return


        #Sets if theres the box on the bottom to drag a new node
        if node.treeType() == bt.BRANCH:
            item.setIsBranch()

        #Dont allow the root one to be deleted
        if node.parent() is None:
            item.setAllowDelete(False)

        item.setIndexPos(QtCore.QPersistentModelIndex(index.siblingAtColumn(col.POS)))
        item.setCallback(self.setData)
        item.setDeleteCallback(self.removeGraphicItem)
        item.setCutCallback(self.cutGraphicItem)
        item.setAddCallback(self.addGraphicItem)


        self._scene.addItem(item)
        p_index = QtCore.QPersistentModelIndex(index)
        self._scene_items.append((p_index, item))

        self.updateNodeItem(index)


        #Add lines between nodes
        if index.parent().internalPointer():
            parent_item = self.graphicItemFromIndex(index.parent())

            new_path = Path(parent_item.centerBottomPos(), item.centerTopPos())
            self._scene.addItem(new_path)
            self._paths.append((QtCore.QPersistentModelIndex(index), new_path))

            item.addLine(new_path, 1)
            parent_item.addLine(new_path, 0)


    def removeNodeItem(self, index):
        #Remove all the graphic items for that index
        for p_index, g_item in self._scene_items:
            if QtCore.QModelIndex(p_index) == index:
                self._scene.removeItem(g_item)
                #Remove the (index, graphic_item) reference
                self._scene_items = [val for val in self._scene_items if val != (p_index, g_item)]


        #Remove its lines
        for path_index, path in self._paths:
            if path_index == index:
                self._scene.removeItem(path)

        #Remove the (index, path) reference
        self._paths = [val for val in self._paths if val[0] != index]


    def updateStatuses(self):
        for g_index, g_item in self._scene_items:
            try:
                index = QtCore.QModelIndex(g_index)
                node = index.internalPointer()
                g_item.setStatus(node.status())
                g_item.update()
            except:
                pass

    def updateStatus(self, index):
        g_item = self.gItemFromIndex(index)
        node = index.internalPointer()
        g_item.setStatus(node.status())

    def updateNodeItem(self, index):
        g_item = self.graphicItemFromIndex(index)
        node = index.internalPointer()

        #Update the gs item
        x, y = node.pos
        g_item.setPos(x, y)
        g_item.setStatus(node.status())
        g_item.updateLines()





    def closeEvent(self, event):
        self._scene.clear() # Clear QGraphicsPixmapItem
        event.accept() # Accept to close program

    def dataChanged(self, index_top_left, index_bottom_right, roles):
        #QAbstractItemModel calls this
        try:
            for i in range(index_top_left.row(), index_bottom_right.row()+1):
                index = index_top_left.siblingAtRow(i)

                if index.column() == col.BT_STATUS:
                    self.updateStatuses()
                else:
                    self.updateNodeItem(index)
                    self.parent().setTitle(file_changed=True)
        except:
            pass


    #QAbstractItemModel calls this
    def rowsInserted(self, parent_index, start, end):
        for row in range(start, end+1):
            index = parent_index.child(row, 0)
            self.addNodeItem(index)


    #QAbstractItemModel calls this
    def rowsAboutToBeRemoved(self, parent_index, start, end):
        for row in range(start, end+1):
            index = parent_index.child(row, 0)
            self._recurseRemove(index) #have to recurse before remove
            self.removeNodeItem(index)



    #Called from the scene to remove a node from the model
    def removeGraphicItem(self, g_item):
        p_index = self.indexFromGraphicItem(g_item)
        if p_index is not None:
            self.model().removeRows(p_index.row(), 1, p_index.parent())
    
    def cutGraphicItem(self, g_item):
        p_index = self.indexFromGraphicItem(g_item)
        if p_index is not None:
            index = QtCore.QModelIndex(p_index)
            self.model().mimeData(index)




    #Called from the scene to insert a node into the model
    def addGraphicItem(self, g_item, pos):
        x, y = pos.x(), pos.y()

        p_index = self.indexFromGraphicItem(g_item)
        index = QtCore.QModelIndex(p_index)

        new_index = self.model().insertChildAtPos(index, self._new_item_type, (x,y))


    # TODO : We have to have these methods but aren't currently doing anything with them
    def visualRegionForSelection(self, selection):
        return QtGui.QRegion()

    def scrollTo(self, index, hint):
        return

    def visualRect(self, index):
        return QtCore.QRect()

    def verticalOffset(self):
        return 0

    def horizontalOffset(self):
        return 0

    def moveCursor(self, action, modifier):
        return QtCore.QModelIndex()
