# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtGui, uic, QtWidgets
import os

from opentoolcontroller.views.widgets.tool_tree_view import ToolTreeView
from opentoolcontroller.tool_model import LeafFilterProxyModel
from opentoolcontroller.views.widgets.behavior_editor_view import BTEditorWindow, BTEditor
from opentoolcontroller.strings import col, typ, defaults
from PyQt5.QtCore import Qt


d_in_base,  d_in_form  = uic.loadUiType("opentoolcontroller/views/DigitalInputEditor.ui")
d_out_base, d_out_form = uic.loadUiType("opentoolcontroller/views/DigitalOutputEditor.ui")
a_in_base,  a_in_form  = uic.loadUiType("opentoolcontroller/views/AnalogInputEditor.ui")
a_out_base, a_out_form = uic.loadUiType("opentoolcontroller/views/AnalogOutputEditor.ui")

recipe_var_base, recipe_var_form = uic.loadUiType("opentoolcontroller/views/RecipeVariableEditor.ui")
bool_var_base,  bool_var_form  = uic.loadUiType("opentoolcontroller/views/BoolVarEditor.ui")
int_var_base, int_var_form = uic.loadUiType("opentoolcontroller/views/IntVarEditor.ui")
float_var_base, float_var_form = uic.loadUiType("opentoolcontroller/views/FloatVarEditor.ui")

device_icon_base, device_icon_form  = uic.loadUiType("opentoolcontroller/views/DeviceIconEditor.ui")
device_base, device_form  = uic.loadUiType("opentoolcontroller/views/DeviceEditor.ui")
tool_base, tool_form  = uic.loadUiType("opentoolcontroller/views/ToolEditor.ui")
system_base, system_form  = uic.loadUiType("opentoolcontroller/views/SystemEditor.ui")
node_base, node_form  = uic.loadUiType("opentoolcontroller/views/NodeEditor.ui")

common_editor_base, common_editor_form  = uic.loadUiType("opentoolcontroller/views/CommonEditor.ui")


class CommonEditor(common_editor_base, common_editor_form):
    def __init__(self, parent=None):
        super(common_editor_base, self).__init__(parent)
        self.setupUi(self)

        #The node editor is common for every node in a tool
        self._node_editor = NodeEditor(self)
        self._behavior_state_editor = BehaviorStateEditor(self)
        self._recipe_variable_editor = RecipeVariableEditor(self)
        self.ui_common_box.addWidget(self._node_editor)

        #Only one of these is shown at a time
        self._specific_editors = { typ.TOOL_NODE        : ToolEditor(self),
                                   typ.SYSTEM_NODE      : SystemEditor(self),
                                   typ.DEVICE_NODE      : DeviceEditor(self),
                                   typ.DEVICE_ICON_NODE : DeviceIconEditor(self),
                                   typ.D_IN_NODE        : DigitalInputEditor(self),
                                   typ.D_OUT_NODE       : DigitalOutputEditor(self),
                                   typ.A_IN_NODE        : AnalogInputEditor(self),
                                   typ.A_OUT_NODE       : AnalogOutputEditor(self),
                                   typ.BOOL_VAR_NODE    : BoolVarEditor(self),
                                   typ.INT_VAR_NODE     : IntVarEditor(self),
                                   typ.FLOAT_VAR_NODE   : FloatVarEditor(self) }

        for editor in self._specific_editors.values():
            self.ui_specific_box.addWidget(editor)

        self.ui_specific_box.addWidget(self._behavior_state_editor)
        self.ui_specific_box.addWidget(self._recipe_variable_editor)
        self.hideEditors()


        self._settings = QtCore.QSettings('OpenToolController', 'test1')
        geometry = self._settings.value('tool_editor_geometry', bytes('', 'utf-8'))
        state = self._settings.value('tool_editor_state', bytes('', 'utf-8'))
        splitter_state = self._settings.value('tool_editor_splitter_state', bytes('', 'utf-8'))

        self.restoreGeometry(geometry)
        self.restoreState(state)
        self.ui_splitter.restoreState(splitter_state)
        self.enableEditTool(False)


    def hideEditors(self):
        self._behavior_state_editor.setVisible(False)
        for editor in self._specific_editors.values():
            editor.setVisible(False)


    #INPUTS: QModelIndex, QModelIndex
    def setSelection(self, current, old):
        model = current.model()

        if hasattr(model, 'mapToSource') : current_index = model.mapToSource(current)
        else                             : current_index = current

        node = current_index.internalPointer()
        self.hideEditors()

        # Always set it for the common parts to the node
        if node is not None:
            self._node_editor.setSelection(current_index)
            typeInfo = node.typeInfo()

            if typeInfo in self._specific_editors:
                self._specific_editors[typeInfo].setSelection(current_index)
                self._specific_editors[typeInfo].setVisible(True)

            if typeInfo in [typ.TOOL_NODE, typ.SYSTEM_NODE, typ.DEVICE_NODE]:
                self._behavior_state_editor.setSelection(current_index)
                self._behavior_state_editor.setVisible(True)
                
            if typeInfo in [typ.TOOL_NODE, typ.SYSTEM_NODE]:
                self._recipe_variable_editor.setSelection(current_index)
                self._recipe_variable_editor.setVisible(True)
            else:
                self._recipe_variable_editor.setVisible(False)


    def setModel(self, model):
        self._model = model
        self._proxy_model =  LeafFilterProxyModel(self) #maybe not self?

        #VIEW <------> PROXY MODEL <------> DATA MODEL
        self._proxy_model.setSourceModel(self._model)
        self._proxy_model.setDynamicSortFilter(True)
        self._proxy_model.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

        self.ui_tree.setModel(self._proxy_model) #maybe not self?)
        self.ui_filter.textChanged.connect(self._proxy_model.setFilterRegExp)
        self.ui_tree.selectionModel().currentChanged.connect(self.setSelection)#self._property_editor.setSelection)
        self.ui_tree.expandAll()
        self.ui_tree.setColumnWidth(0,200)

        self._node_editor.setModel(self._proxy_model)
        self._behavior_state_editor.setModel(self._proxy_model) #TODO do we need to check for type?

        for editor in self._specific_editors.values():
            editor.setModel(self._proxy_model)

    def closeEvent(self, event):
        geometry = self.saveGeometry()
        self._settings.setValue('tool_editor_geometry', geometry)
        state = self.saveState()
        splitter_state = self.ui_splitter.saveState()
        self._settings.setValue('tool_editor_state', state)
        self._settings.setValue('tool_editor_splitter_state', splitter_state)
        super().closeEvent(event)


    def enableEditTool(self, enable):
        self._node_editor.setEnabled(enable)
        #self._behavior_state_editor.setEnabled(enable)
        self.ui_tree.setEnableContextMenu(enable)

        for editor in self._specific_editors.values():
            editor.setEnabled(enable)

    def enableEditBehaviors(self, enable):
        self._behavior_state_editor.enableEditBehaviors(enable)


class NodeEditor(node_base, node_form):
    def __init__(self, parent=None):
        super(node_base, self).__init__(parent)
        self.setupUi(self)
        self.mapper = QtWidgets.QDataWidgetMapper()

    def setModel(self, model):
        if hasattr(model, 'sourceModel'):
            model = model.sourceModel()

        self.mapper.setModel(model)
        self.mapper.addMapping(self.ui_name       , col.NAME)
        self.mapper.addMapping(self.ui_type       , col.TYPE_INFO)
        self.mapper.addMapping(self.ui_description, col.DESCRIPTION)


    def setSelection(self, current):
        parent = current.parent()
        self.mapper.setRootIndex(parent)
        self.mapper.setCurrentModelIndex(current)


class ToolEditor(tool_base, tool_form):
    def __init__(self, parent=None):
        super(tool_base, self).__init__(parent)
        self.setupUi(self)
        self.mapper = QtWidgets.QDataWidgetMapper()

        self.ui_number_of_hal_readers.valueChanged.connect(self.updatePeriodBoxDisplay)
        self._period_boxes = []
        self._period_labels = []

        spin_box = QtWidgets.QSpinBox()
        spin_box.setRange(1, 200)
        spin_box.setSingleStep(1)
        spin_box.valueChanged.connect(self.updatePeriodBoxRange)

        label = QtWidgets.QLabel("Realtime Period (ms)")
        self.ui_form_layout.addRow(label, spin_box)
        self._period_labels.append(label)
        self._period_boxes.append(spin_box)

        for i in range(defaults.MAX_HAL_READERS):
            spin_box = QtWidgets.QSpinBox()
            spin_box.setRange(50, 2000)
            spin_box.setSingleStep(50)
            spin_box.valueChanged.connect(self.updatePeriodBoxRange)

            n = i + 1
            label = QtWidgets.QLabel("GUI Period %i (ms)" % n)

            self.ui_form_layout.addRow(label, spin_box)
            self._period_labels.append(label)
            self._period_boxes.append(spin_box)


    def updatePeriodBoxDisplay(self):
        number_of_readers = self.ui_number_of_hal_readers.value()

        for i, box in enumerate(self._period_boxes):
            if i < number_of_readers+1:
                self._period_boxes[i].show()
                self._period_labels[i].show()
            else:
                self._period_boxes[i].hide()
                self._period_labels[i].hide()

    
    def updatePeriodBoxRange(self):
        current_min = 1 

        for i, box in enumerate(self._period_boxes):
            if box.value() >= current_min:
                current_min = box.value()
            else:
                box.setValue(current_min)


    def setModel(self, model):
        if hasattr(model, 'sourceModel'):
            model = model.sourceModel()

        self.mapper.setModel(model)
        self.mapper.addMapping(self.ui_number_of_hal_readers, col.NUMBER_OF_HAL_READERS)
        self.mapper.addMapping(self._period_boxes[0], col.REALTIME_PERIOD_MS)
        
        for i, current_col in enumerate(col.GUI_PERIOD_MS_GROUP):
            self.mapper.addMapping(self._period_boxes[i+1], current_col)


    def setSelection(self, current):
        parent = current.parent()
        self.mapper.setRootIndex(parent)
        self.mapper.setCurrentModelIndex(current)


class SystemEditor(system_base, system_form):
    file_signal = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(system_base, self).__init__(parent)
        self.setupUi(self)
        self.mapper = QtWidgets.QDataWidgetMapper()

        #Background SVG file selection
        self.file_signal.connect(self.mapper.submit)
        self.ui_select_image.clicked.connect(self.selectSVG)
        self.ui_background_svg.textChanged.connect(lambda update_system_svg: self.ui_svg_widget.load(self.fullPath(self.ui_background_svg.text())))
    

    def fullPath(self, relative_path):
        return defaults.TOOL_DIR +'/'+ relative_path

    def setModel(self, model):
        if hasattr(model, 'sourceModel'):
            model = model.sourceModel()

        self.mapper.setModel(model)
        self.mapper.addMapping(self.ui_background_svg, col.BACKGROUND_SVG)


    def setSelection(self, current):
        parent = current.parent()
        self.mapper.setRootIndex(parent)
        self.mapper.setCurrentModelIndex(current)


    def selectSVG(self,sender):
        starting_dir = defaults.TOOL_DIR + '/graphics/system_backgrounds'
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog

        file = QtWidgets.QFileDialog.getOpenFileName(self,"QFileDialog.getOpenFileName()", starting_dir, 
                                                            "SVG (*.svg);;All Files (*)", options=options)
        file = file[0]
        if file and os.path.isfile(file):
            relative_path = os.path.relpath(file, defaults.TOOL_DIR)
            self.ui_background_svg.setText(relative_path)
            self.file_signal.emit()


class BehaviorStateEditor(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._mapper1 = QtWidgets.QDataWidgetMapper()
        self._mapper2 = QtWidgets.QDataWidgetMapper()
        self._behaviors = None #list of behavior models

        self._edit_btns = [] #just used to enable/disable these easier
        self._enable_edit_behaviors = False

        #behaviors
        self._grid = QtWidgets.QGridLayout()
        self._grid.setVerticalSpacing(5)
        self.setLayout(self._grid)

        ui_row = 0
        self._grid.addWidget(QtWidgets.QLabel('Behavior Trees'), ui_row, 0)

        ui_row += 1
        #set selection will add the stuff into the list_grid
        wid = QtWidgets.QWidget(self)
        self._list_grid = QtWidgets.QGridLayout()
        self._list_grid.setVerticalSpacing(5)
        self._list_grid.setColumnStretch(1,1)
        wid.setLayout(self._list_grid)
        self._grid.addWidget(wid, ui_row, 0, 1, 2)

        
        #Hal Reader Number
        ui_row += 1
        self.ui_hal_reader_number = QtWidgets.QComboBox()
        #self.ui_hal_reader_number.currentIndexChanged.connect(self._mapper2.submit)
        self._grid.addWidget(QtWidgets.QLabel('Hal Reader Number'), ui_row, 0)
        self._grid.addWidget(self.ui_hal_reader_number, ui_row, 1, 1, -1)

        #state
        self.ui_state = QtWidgets.QLineEdit('')
        self.ui_state.setEnabled(False)

        ui_row += 1
        self._grid.addWidget(QtWidgets.QLabel('State'), ui_row, 0)
        self._grid.addWidget(self.ui_state, ui_row, 1, 1, -1)
        
        ui_row += 1
        self._grid.addWidget(QtWidgets.QLabel('States'), ui_row, 0)
        self._ui_states = QtWidgets.QListView()
        self._states_model = QtCore.QStringListModel()
        self._states_model.dataChanged.connect(self._mapper2.submit)
        self._ui_states.setModel(self._states_model)
        self._ui_states.setSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Minimum)
        
        ui_row += 1
        self._grid.addWidget(self._ui_states, ui_row, 0,1,-1)

        insert_state_action = QtWidgets.QAction("Insert", self)
        insert_state_action.triggered.connect(self.insertState)

        remove_state_action = QtWidgets.QAction("Delete", self)
        remove_state_action.triggered.connect(self.removeState)

        self._ui_states.addActions([insert_state_action, remove_state_action])
        self._ui_states.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)


    def setModel(self, model):
        if hasattr(model, 'sourceModel'):
            model = model.sourceModel()

        self._mapper1.setModel(model)
        self._mapper2.setModel(model)
        self._mapper1.addMapping(self.ui_state, col.STATE)
        self._mapper2.addMapping(self.ui_hal_reader_number, col.HAL_READER_NUMBER,  b"currentIndex") #index of the dropdown item
        self._mapper1.addMapping(self, col.BEHAVIORS, bytes('behaviors','ascii'))
        self._mapper2.addMapping(self, col.STATES, bytes('states','ascii'))

    def setSelection(self, current):
        parent = current.parent()
        self._mapper1.setRootIndex(parent)
        self._mapper1.setCurrentModelIndex(current)

        self._mapper2.setRootIndex(parent)
        self._mapper2.setCurrentModelIndex(current)


        #HAL Reader number is same as Behavior Runner Number
        self.ui_hal_reader_number.clear()
        self.ui_hal_reader_number.addItem("") #Empty for none
        
        #runners = current.internalPointer().model().behaviorRunners()
        runners = self._mapper1.model().behaviorRunners()
        for runner in runners:
            name = "%i - %i ms" % (runner.behaviorRunnerNumber(), runner.tickRateMS())
            self.ui_hal_reader_number.addItem(name)

        index = current.internalPointer().halReaderNumber
        if index is not None:
            self.ui_hal_reader_number.setCurrentIndex(index)



        

    def insertBehavior(self, row):
        starting_dir = defaults.TOOL_DIR + '/behaviors'

        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        file_name = QtWidgets.QFileDialog.getOpenFileName(self,"QFileDialog.getOpenFileName()", starting_dir, 
                                                           "JSON (*.json);;All Files (*)", options=options)
        if file_name[0]:
            relative_path = os.path.relpath(file_name[0], defaults.TOOL_DIR)
            self.behaviors.insert(row, relative_path)
            self._mapper1.submit()

    def editBehavior(self, row):
        behavior = self.behaviors[row]
        name = behavior.name()

        if behavior:
            editor = BTEditorWindow(self)
            editor.setModel(behavior)
            editor.setEditable(True)
            editor.show()

    def viewBehavior(self, row):
        behavior = self.behaviors[row]
        name = behavior.name()

        if behavior:
            editor = BTEditorWindow(self)
            editor.setModel(behavior)
            editor.setEditable(False)
            editor.show()

    def removeBehavior(self, row):
        self.behaviors.pop(row)
        self._mapper1.submit()

    def updateText(self):
        try:
            for i, row in enumerate(self._behavior_editors):
                ui_name = row[0]
                ui_file_name = row[1]

                behavior = self._behaviors[i]
                ui_name.setText(behavior.name())
                ui_file_name.setText(behavior.file())
        except:
            pass


    def getStates(self):
        return self._states_model.stringList()

    def setStates(self, value):
        self._states_model.setStringList(value)

    def removeState(self, index):
        try:
            row = self._ui_states.selectedIndexes()[0].row()
            count = len(self._ui_states.selectedIndexes())
            self._states_model.removeRows(row, count)
        except:
            pass

    def insertState(self, index):
        try:
            if len(self._ui_states.selectedIndexes()) > 0:
                row = self._ui_states.selectedIndexes()[0].row()
            else:
                row = self._states_model.rowCount()

            self._states_model.insertRows(row,1)
            index = self._states_model.index(row,0)
            self._states_model.setData(index, "new state")

        except:
            pass


    def enableEditBehaviors(self, enable=None):
        if enable:
            self._enable_edit_behaviors = bool(enable)

        for edit_btn in self._edit_btns:
            edit_btn.setEnabled(self._enable_edit_behaviors)


    @QtCore.pyqtProperty(list)
    def behaviors(self):
        return self._behaviors

    @behaviors.setter
    def behaviors(self, behaviors=None):
        if behaviors is not None:
            self._behaviors = behaviors

        self._behavior_editors = []
        self._edit_btns = []

        #clear the grid
        for i in reversed(range(self._list_grid.count())):
            wid = self._list_grid.itemAt(i).widget()
            self._list_grid.removeWidget(wid)
            wid.hide()
            wid.setParent(None)
            wid.deleteLater()

        #top labels
        self._list_grid.addWidget(QtWidgets.QLabel('name'), 0, 0)
        self._list_grid.addWidget(QtWidgets.QLabel('file'), 0, 1)

        #insert each behavior
        i = 1
        for behavior in self._behaviors:
            ui_name = QtWidgets.QLineEdit(behavior.name())
            ui_name.setEnabled(False)
            ui_file_name = QtWidgets.QLineEdit(behavior.file())
            ui_file_name.setEnabled(False)
            view_btn = QtWidgets.QPushButton('View')
            edit_btn = QtWidgets.QPushButton('Edit')
            rm_btn = QtWidgets.QPushButton('-') #Todo change to icons
            add_btn = QtWidgets.QPushButton('+')

            
            self._edit_btns.append(edit_btn)
            self._edit_btns.append(rm_btn)
            self._edit_btns.append(add_btn)

            self._behavior_editors.append([ui_name, ui_file_name])
            self._list_grid.addWidget(ui_name     , i, 0)
            self._list_grid.addWidget(ui_file_name, i, 1)
            self._list_grid.addWidget(view_btn    , i, 2)
            self._list_grid.addWidget(edit_btn    , i, 3)
            self._list_grid.addWidget(rm_btn      , i, 4)
            self._list_grid.addWidget(add_btn     , i, 5)

            view_btn.clicked.connect(lambda a, b=i-1: self.viewBehavior(b)) #first parameter passed is False  from the btn
            edit_btn.clicked.connect(lambda a, b=i-1: self.editBehavior(b)) #first parameter passed is False  from the btn
            rm_btn.clicked.connect(lambda a, b=i-1: self.removeBehavior(b))
            add_btn.clicked.connect(lambda a, b=i-1: self.insertBehavior(b))


            i += 1
        add_btn = QtWidgets.QPushButton('+')
        self._edit_btns.append(add_btn)
        self._list_grid.addWidget(add_btn     , i, 4)
        add_btn.clicked.connect(lambda a, b=i-1: self.insertBehavior(b))
        self.enableEditBehaviors()

    states = QtCore.pyqtProperty(QtCore.QVariant, getStates, setStates)


class DeviceEditor(device_base, device_form):
    def __init__(self, parent=None):
        super(device_base, self).__init__(parent)
        self.setupUi(self)
        self.mapper = QtWidgets.QDataWidgetMapper()

    def setModel(self, model):
        if hasattr(model, 'sourceModel'):
            model = model.sourceModel()

        self.mapper.setModel(model)

    def setSelection(self, current):
        parent = current.parent()
        self.mapper.setRootIndex(parent)
        self.mapper.setCurrentModelIndex(current)


class DeviceIconEditor(device_icon_base, device_icon_form):
    file_signal = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(device_icon_base, self).__init__(parent)
        self.setupUi(self)
        self.mapper = QtWidgets.QDataWidgetMapper()
        self.mapper2 = QtWidgets.QDataWidgetMapper()
        self._node = None

        self.file_signal.connect(self.mapper.submit)
        self.ui_select_image.clicked.connect(self.selectSVG)
        self.ui_svg.textChanged.connect(lambda update_system_svg: self.ui_svg_widget.load(self.fullPath(self.ui_svg.text())))

        self.ui_default_layer.currentIndexChanged.connect(self.defaultLayerChanged)

        self.ui_color_button.clicked.connect(self.colorDialog)
        self._font_color = QtGui.QColor(0xFFFFFF) 

    def fullPath(self, relative_path):
        return defaults.TOOL_DIR +'/'+ relative_path

    def updateColorBox(self):
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Window, self._font_color)
        self.ui_color_box.setAutoFillBackground(True)
        self.ui_color_box.setPalette(pal)

    def colorDialog(self):
        color = QtWidgets.QColorDialog.getColor()
        if color.isValid():
            self._font_color = color
            self.updateColorBox()
            self.mapper.submit()

    def getFontColor(self):
        return self._font_color

    def setFontColor(self, color):
        self._font_color = color
        self.updateColorBox()

    def setModel(self, model):
        if hasattr(model, 'sourceModel'):
            model = model.sourceModel()
        self.mapper.setModel(model)
        self.mapper2.setModel(model)

        self.mapper.addMapping(self.ui_svg      , col.SVG)
        self.mapper.addMapping(self.ui_x        , col.X)
        self.mapper.addMapping(self.ui_y        , col.Y)
        self.mapper.addMapping(self.ui_scale    , col.SCALE)
        self.mapper.addMapping(self.ui_rotation , col.ROTATION)

        #probably causing a loop due to the submit on state change w/ the others
        self.mapper2.addMapping(self.ui_default_layer , col.DEFAULT_LAYER, b'currentText') #this goes crazy on a shared mapper

        self.mapper.addMapping(self.ui_has_text    , col.HAS_TEXT)
        self.mapper.addMapping(self.ui_text        , col.TEXT)
        self.mapper.addMapping(self.ui_default_text, col.DEFAULT_TEXT)
        self.mapper.addMapping(self.ui_text_x      , col.TEXT_X)
        self.mapper.addMapping(self.ui_text_y      , col.TEXT_Y)
        self.mapper.addMapping(self.ui_font_size   , col.FONT_SIZE)
        self.mapper.addMapping(self, col.FONT_COLOR, bytes('fontColorZ', 'ascii'))

        
        #self.mapper.setSubmitPolicy(QtWidgets.QDataWidgetMapper.ManualSubmit)
        #self.ui_x.valueChanged.connect(self.mapper.submit) #These mess up the movable icon
        #self.ui_y.valueChanged.connect(self.mapper.submit)
        self.ui_scale.valueChanged.connect(self.mapper.submit)
        self.ui_rotation.valueChanged.connect(self.mapper.submit)
        self.ui_has_text.stateChanged.connect(self.mapper.submit)
        self.ui_text_x.valueChanged.connect(self.mapper.submit)
        self.ui_text_y.valueChanged.connect(self.mapper.submit)
        self.ui_font_size.valueChanged.connect(self.mapper.submit)


    def setSelection(self, current):
        parent = current.parent()
        self._node = current.internalPointer()
        self.mapper.setRootIndex(parent)
        self.mapper.setCurrentModelIndex(current)


        self.ui_default_layer.blockSignals(True)
        self.loadDefaultLayerBox()
        self.mapper2.setRootIndex(parent)
        self.mapper2.setCurrentModelIndex(current)
        self.ui_default_layer.blockSignals(False)
        self.ui_svg_widget.setElementId(self.ui_default_layer.currentText())


    def loadDefaultLayerBox(self):
        if self._node is not None:
            layers = self._node.layers()
            self.ui_default_layer.clear()
            self.ui_default_layer.addItems(layers)


    def defaultLayerChanged(self):
        self.ui_svg_widget.setElementId(self.ui_default_layer.currentText())
        self.mapper2.submit()


    def selectSVG(self,sender):
        starting_dir = defaults.TOOL_DIR + '/graphics/device_icons'
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog

        file = QtWidgets.QFileDialog.getOpenFileName(self,"QFileDialog.getOpenFileName()", starting_dir, 
                                                          "SVG (*.svg);;All Files (*)", options=options)

        file = file[0]
        if file and os.path.isfile(file):
            relative_path = os.path.relpath(file, defaults.TOOL_DIR)
            print("Path: ", relative_path)
            self.ui_svg.setText(relative_path)
            self.file_signal.emit()
            self.loadDefaultLayerBox()

    
    fontColorZ = QtCore.pyqtProperty(QtCore.QVariant, getFontColor, setFontColor)


class DigitalInputEditor(d_in_base, d_in_form):
    def __init__(self, parent=None):
        super(d_in_base, self).__init__(parent)
        self.setupUi(self)
        self.mapper = QtWidgets.QDataWidgetMapper()

    def setModel(self, model):
        if hasattr(model, 'sourceModel'):
            model = model.sourceModel()

        self.mapper.setModel(model)
        self.mapper.addMapping(self.ui_hal_pin      , col.HAL_PIN,  b"currentIndex") #index of the dropdown item
        self.mapper.addMapping(self.ui_hal_pin_type , col.HAL_PIN_TYPE)
        self.mapper.addMapping(self.ui_value        , col.VALUE)
        self.mapper.addMapping(self.ui_off_name     , col.OFF_NAME)
        self.mapper.addMapping(self.ui_on_name      , col.ON_NAME)

    def setSelection(self, current):
        parent = current.parent()
        self.mapper.setRootIndex(parent)
        self.mapper.setCurrentModelIndex(current)

        self.ui_hal_pin.clear()
        pins = current.internalPointer().halPins()
        for name in pins.names:
            self.ui_hal_pin.addItem(name)

        index = self.ui_hal_pin.findText(current.internalPointer().halPin, QtCore.Qt.MatchFixedString)
        if index >= 0:
            self.ui_hal_pin.setCurrentIndex(index)


class DigitalOutputEditor(d_out_base, d_out_form):
    def __init__(self, parent=None):
        super(d_out_base, self).__init__(parent)
        self.setupUi(self)
        self.mapper = QtWidgets.QDataWidgetMapper()

    def setModel(self, model):
        if hasattr(model, 'sourceModel'):
            model = model.sourceModel()

        self.mapper.setModel(model)
        self.mapper.addMapping(self.ui_hal_pin      , col.HAL_PIN,  b"currentIndex") #index of the dropdown item
        self.mapper.addMapping(self.ui_hal_pin_type , col.HAL_PIN_TYPE)
        self.mapper.addMapping(self.ui_value        , col.VALUE)
        self.mapper.addMapping(self.ui_off_name     , col.OFF_NAME)
        self.mapper.addMapping(self.ui_on_name      , col.ON_NAME)

    def setSelection(self, current):
        parent = current.parent()
        self.mapper.setRootIndex(parent)
        self.mapper.setCurrentModelIndex(current)

        self.ui_hal_pin.clear()
        pins = current.internalPointer().halPins()
        for name in pins.names:
            self.ui_hal_pin.addItem(name)

        index = self.ui_hal_pin.findText(current.internalPointer().halPin, QtCore.Qt.MatchFixedString)
        if index >= 0:
            self.ui_hal_pin.setCurrentIndex(index)


class AnalogInputEditor(a_in_base, a_in_form):
    def __init__(self, parent=None):
        super(a_in_base, self).__init__(parent)
        self.setupUi(self)
        self.mapper = QtWidgets.QDataWidgetMapper()

    def setModel(self, model):
        if hasattr(model, 'sourceModel'):
            model = model.sourceModel()
        self.mapper.setModel(model)

        self.mapper.addMapping(self.ui_hal_pin           , col.HAL_PIN,  b"currentIndex") #index of the dropdown item
        self.mapper.addMapping(self.ui_hal_pin_type      , col.HAL_PIN_TYPE)
        self.mapper.addMapping(self.ui_hal_value         , col.HAL_VALUE)
        self.mapper.addMapping(self.ui_value             , col.VALUE)
        self.mapper.addMapping(self.ui_units             , col.UNITS)
        self.mapper.addMapping(self.ui_display_digits    , col.DISPLAY_DIGITS)
        self.mapper.addMapping(self.ui_display_scientific, col.DISPLAY_SCIENTIFIC)
        self.mapper.addMapping(self.ui_calibration_table , col.CALIBRATION_TABLE_MODEL,  b"calibrationTableView")

        self.ui_display_scientific.stateChanged.connect(self.mapper.submit)

    def setSelection(self, current):
        parent = current.parent()
        self.mapper.setRootIndex(parent)
        self.mapper.setCurrentModelIndex(current)

        self.ui_hal_pin.clear()
        pins = current.internalPointer().halPins()
        for name in pins.names:
            self.ui_hal_pin.addItem(name)

        index = self.ui_hal_pin.findText(current.internalPointer().halPin, QtCore.Qt.MatchFixedString)
        if index >= 0:
            self.ui_hal_pin.setCurrentIndex(index)


class AnalogOutputEditor(a_out_base, a_out_form):
    def __init__(self, parent=None):
        super(a_out_base, self).__init__(parent)
        self.setupUi(self)
        self.mapper = QtWidgets.QDataWidgetMapper()

    def setModel(self, model):
        if hasattr(model, 'sourceModel'):
            model = model.sourceModel()
        self.mapper.setModel(model)

        self.mapper.addMapping(self.ui_hal_pin           , col.HAL_PIN,  b"currentIndex") #index of the dropdown item
        self.mapper.addMapping(self.ui_hal_pin_type      , col.HAL_PIN_TYPE)
        self.mapper.addMapping(self.ui_hal_value         , col.HAL_VALUE)
        self.mapper.addMapping(self.ui_value             , col.VALUE)
        self.mapper.addMapping(self.ui_min               , col.MIN)
        self.mapper.addMapping(self.ui_max               , col.MAX)
        self.mapper.addMapping(self.ui_units             , col.UNITS)
        self.mapper.addMapping(self.ui_display_digits    , col.DISPLAY_DIGITS)
        self.mapper.addMapping(self.ui_display_scientific, col.DISPLAY_SCIENTIFIC)
        self.mapper.addMapping(self.ui_calibration_table , col.CALIBRATION_TABLE_MODEL,  b"calibrationTableView")

        self.ui_display_scientific.stateChanged.connect(self.mapper.submit)

    def setSelection(self, current):
        parent = current.parent()
        self.mapper.setRootIndex(parent)
        self.mapper.setCurrentModelIndex(current)

        self.ui_hal_pin.clear()
        pins = current.internalPointer().halPins()
        for name in pins.names:
            self.ui_hal_pin.addItem(name)

        index = self.ui_hal_pin.findText(current.internalPointer().halPin, QtCore.Qt.MatchFixedString)
        if index >= 0:
            self.ui_hal_pin.setCurrentIndex(index)


class RecipeVariableEditor(recipe_var_base, recipe_var_form):
    def __init__(self, parent=None):
        super(recipe_var_base, self).__init__(parent)
        self.setupUi(self)
        self.mapper = QtWidgets.QDataWidgetMapper()
        
        self.ui_edit_variables.clicked.connect(self.openVariableTable)
        self._variable_table = None

    def setModel(self, model):
        if hasattr(model, 'sourceModel'):
            model = model.sourceModel()
        self.mapper.setModel(model)

    def setSelection(self, current):
        parent = current.parent()
        self.mapper.setRootIndex(parent)
        self.mapper.setCurrentModelIndex(current)
        self._current_node = current.internalPointer()

    def openVariableTable(self):
        if not self._variable_table:
            self._variable_table = RecipeVariableTable(self)
        self._variable_table.show()


class RecipeVariableTable(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Recipe Variables")
        self.resize(600, 400)  # Set a reasonable default size
        
        # Create central widget and layout
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)
        
        # Create validator for integer fields
        self.int_validator = QtGui.QIntValidator()
        
        # Create table
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Variable Name", "Variable Type", "Min", "Max"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        layout.addWidget(self.table)
        
        # Create button widget and layout
        button_widget = QtWidgets.QWidget()
        button_layout = QtWidgets.QHBoxLayout(button_widget)
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add buttons
        add_btn = QtWidgets.QPushButton("Add Variable")
        remove_btn = QtWidgets.QPushButton("Remove Variable")
        add_btn.clicked.connect(self.addVariable)
        remove_btn.clicked.connect(self.removeVariable)
        button_layout.addWidget(add_btn)
        button_layout.addWidget(remove_btn)
        button_layout.addStretch()  # Push buttons to the left
        
        layout.addWidget(button_widget)
        
        # Set up type combo delegate for Variable Type column
        type_delegate = TypeComboDelegate(self.table)
        self.table.setItemDelegateForColumn(1, type_delegate)
        
    def handleTypeChange(self, var_type, row):
        """Handle changes to variable type by updating min/max fields"""
        min_item = self.table.item(row, 2)
        max_item = self.table.item(row, 3)
        
        if not min_item or not max_item:
            return
            
        if var_type == "Boolean":
            # Disable and clear min/max for boolean
            min_item.setFlags(min_item.flags() & ~Qt.ItemIsEnabled)
            max_item.setFlags(max_item.flags() & ~Qt.ItemIsEnabled)
            min_item.setText("")
            max_item.setText("")
            # Set light gray background for disabled cells
            min_item.setBackground(QtGui.QColor(240, 240, 240))
            max_item.setBackground(QtGui.QColor(240, 240, 240))
        else:
            # Enable min/max for numeric types
            min_item.setFlags(min_item.flags() | Qt.ItemIsEnabled | Qt.ItemIsEditable)
            max_item.setFlags(max_item.flags() | Qt.ItemIsEnabled | Qt.ItemIsEditable)
            # Set white background for enabled cells
            min_item.setBackground(QtGui.QColor(255, 255, 255))
            max_item.setBackground(QtGui.QColor(255, 255, 255))
            
            # Set validators based on type
            if var_type == "Integer":
                validator = QtGui.QIntValidator()
            else:  # Float
                validator = QtGui.QDoubleValidator()
            
            # Create new delegates with appropriate validators
            delegate = QtWidgets.QStyledItemDelegate()
            delegate.createEditor = lambda parent, option, index: QtWidgets.QSpinBox(parent) if isinstance(validator, QtGui.QIntValidator) else QtWidgets.QDoubleSpinBox(parent)
            delegate.setEditorData = lambda editor, index: editor.setValue(float(index.data()) if index.data() and index.data().strip() else 0)
            delegate.setModelData = lambda editor, model, index: model.setData(index, str(editor.value()), Qt.EditRole)
            
            self.table.setItemDelegateForColumn(2, delegate)
            self.table.setItemDelegateForColumn(3, delegate)
    
    def validateAndSetData(self, editor, model, index, validator):
        """Validate and set data for min/max fields"""
        value = editor.text()
        pos = 0
        
        # For integer fields, try to convert float input to int
        if isinstance(validator, QtGui.QIntValidator):
            try:                                                                                                                                                                           
                float_val = float(value)                                                                                                                                                   
                value = str(round(float_val))  # Round to nearest integer                                                                                                                  
            except ValueError:                                                                                                                                                             
                pass       
        
        if validator.validate(value, pos)[0] == QtGui.QValidator.Acceptable:
            model.setData(index, value, Qt.EditRole)
        else:
            # Reset to previous value on invalid input
            editor.setText(index.data())

    def addVariable(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Add type combo box
        type_combo = QtWidgets.QComboBox()
        type_combo.addItems(["Float", "Integer", "Boolean"])
        type_combo.currentTextChanged.connect(lambda text, r=row: self.handleTypeChange(text, r))
        self.table.setCellWidget(row, 1, type_combo)
        
        # Add min/max cells
        min_item = QtWidgets.QTableWidgetItem()
        max_item = QtWidgets.QTableWidgetItem()
        self.table.setItem(row, 2, min_item)
        self.table.setItem(row, 3, max_item)
        
        # Initialize as Boolean (disabled min/max)
        type_combo.setCurrentText("Boolean")

    def removeVariable(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.table.removeRow(current_row)


class TypeComboDelegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QtWidgets.QComboBox(parent)
        editor.addItems(["Float", "Integer", "Boolean"])
        # Connect to parent table's handler
        editor.currentTextChanged.connect(
            lambda text: self.parent().handleTypeChange(text, index.row())
        )
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.EditRole)
        editor.setCurrentText(value)

    def setModelData(self, editor, model, index):
        value = editor.currentText()
        model.setData(index, value, Qt.EditRole)
        # Ensure min/max fields are updated when type changes via delegate
        self.parent().handleTypeChange(value, index.row())

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


class BoolVarEditor(bool_var_base, bool_var_form):
    def __init__(self, parent=None):
        super(bool_var_base, self).__init__(parent)
        self.setupUi(self)
        self.mapper = QtWidgets.QDataWidgetMapper()

    def setModel(self, model):
        if hasattr(model, 'sourceModel'):
            model = model.sourceModel()
        self.mapper.setModel(model)

        self.mapper.addMapping(self.ui_value           , col.VALUE)
        self.mapper.addMapping(self.ui_off_name        , col.OFF_NAME)
        self.mapper.addMapping(self.ui_on_name         , col.ON_NAME)
        self.mapper.addMapping(self.ui_user_manual_set , col.USER_MANUAL_SET)
        self.mapper.addMapping(self.ui_launch_value    , col.LAUNCH_VALUE)
        self.mapper.addMapping(self.ui_use_launch_value, col.USE_LAUNCH_VALUE)

        self.ui_user_manual_set.stateChanged.connect(self.mapper.submit)
        self.ui_launch_value.stateChanged.connect(self.mapper.submit)
        self.ui_use_launch_value.stateChanged.connect(self.mapper.submit)

    def setSelection(self, current):
        parent = current.parent()
        self.mapper.setRootIndex(parent)
        self.mapper.setCurrentModelIndex(current)


class IntVarEditor(int_var_base, int_var_form):
    def __init__(self, parent=None):
        super(int_var_base, self).__init__(parent)
        self.setupUi(self)
        self.mapper = QtWidgets.QDataWidgetMapper()

    def setModel(self, model):
        if hasattr(model, 'sourceModel'):
            model = model.sourceModel()
        self.mapper.setModel(model)

        self.mapper.addMapping(self.ui_value           , col.VALUE)
        self.mapper.addMapping(self.ui_min             , col.MIN)
        self.mapper.addMapping(self.ui_max             , col.MAX)
        self.mapper.addMapping(self.ui_units           , col.UNITS)
        self.mapper.addMapping(self.ui_user_manual_set , col.USER_MANUAL_SET)
        self.mapper.addMapping(self.ui_launch_value    , col.LAUNCH_VALUE)
        self.mapper.addMapping(self.ui_use_launch_value, col.USE_LAUNCH_VALUE)

        self.ui_user_manual_set.stateChanged.connect(self.mapper.submit)
        self.ui_use_launch_value.stateChanged.connect(self.mapper.submit)

    def setSelection(self, current):
        parent = current.parent()
        self.mapper.setRootIndex(parent)
        self.mapper.setCurrentModelIndex(current)

        node = current.internalPointer()
        self.ui_launch_value.setMinimum(node.min)
        self.ui_launch_value.setMaximum(node.max)


class FloatVarEditor(float_var_base, float_var_form):
    def __init__(self, parent=None):
        super(float_var_base, self).__init__(parent)
        self.setupUi(self)
        self.mapper = QtWidgets.QDataWidgetMapper()

    def setModel(self, model):
        if hasattr(model, 'sourceModel'):
            model = model.sourceModel()
        self.mapper.setModel(model)

        self.mapper.addMapping(self.ui_value             , col.VALUE)
        self.mapper.addMapping(self.ui_min               , col.MIN)
        self.mapper.addMapping(self.ui_max               , col.MAX)
        self.mapper.addMapping(self.ui_units             , col.UNITS)
        self.mapper.addMapping(self.ui_display_digits    , col.DISPLAY_DIGITS)
        self.mapper.addMapping(self.ui_display_scientific, col.DISPLAY_SCIENTIFIC)
        self.mapper.addMapping(self.ui_user_manual_set   , col.USER_MANUAL_SET)
        self.mapper.addMapping(self.ui_launch_value      , col.LAUNCH_VALUE)
        self.mapper.addMapping(self.ui_use_launch_value  , col.USE_LAUNCH_VALUE)
        
        self.ui_display_scientific.stateChanged.connect(self.mapper.submit)
        self.ui_user_manual_set.stateChanged.connect(self.mapper.submit)
        self.ui_use_launch_value.stateChanged.connect(self.mapper.submit)


    def setSelection(self, current):
        parent = current.parent()
        self.mapper.setRootIndex(parent)
        self.mapper.setCurrentModelIndex(current)

        node = current.internalPointer()
        self.ui_launch_value.setMinimum(node.min)
        self.ui_launch_value.setMaximum(node.max)
