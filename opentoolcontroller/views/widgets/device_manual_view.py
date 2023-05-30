#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt5 import QtCore, QtGui, QtWidgets, uic
from opentoolcontroller.strings import col, typ, bt
from opentoolcontroller.views.widgets.scientific_spin import ScientificDoubleSpinBox
from opentoolcontroller.views.widgets.behavior_editor_view import BTEditorWindow

manual_device_view_base, manual_device_view_form = uic.loadUiType("opentoolcontroller/views/DeviceManualView.ui")


class BehaviorButton(QtWidgets.QPushButton):
    def __init__(self, parent=None):
        super(BehaviorButton, self).__init__(parent)
        self._behavior = None
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.buttonMenu)

    def buttonMenu(self, pos):
        menu = QtWidgets.QMenu()
        menu.addAction('View Behavior', self.viewBehavior)
        menu.exec_(QtGui.QCursor.pos())

    def viewBehavior(self):
        if self._behavior:
            name = self._behavior.name()
            editor = BTEditorWindow(self)
            editor.setModel(self._behavior)
            editor.setEditable(False)
            editor.show()

    def behavior(self):
        return self._behavior

    def setBehavior(self, behavior):
        self._behavior = behavior


class DeviceManualView(manual_device_view_base, manual_device_view_form):
    def __init__(self, parent=None):
        super(manual_device_view_base, self).__init__()
        self.setupUi(self)

        self._model = None
        self._mapper = QtWidgets.QDataWidgetMapper()
        self._current_index = None
        self._enable_device_behaviors = False

    def viewBehavior(self):
        print("view that behavior")

    def onContextMenu(self, point):
        # show right click menu
        self._behavior_menu.exec_()#self.button.mapToGlobal(point))

    def setSelection(self, index):
        self._current_index = index
        self._sub_mappers = []

        #Clear out the layout with the Hal Nodes
        for i in reversed(range(self.ui_wids.count())):
            wid = self.ui_wids.takeAt(i).widget()
            if wid is not None:
                wid.deleteLater()

        if hasattr(index.model(), 'mapToSource'):
            index = index.model().mapToSource(index)

        device_node = index.internalPointer()
        if device_node is not None:
            typeInfo = device_node.typeInfo()

        parent_index = index.parent()
        self._mapper.setRootIndex(parent_index)
        self._mapper.setCurrentModelIndex(index)

        ui_row, ui_col = 0,0 #grid layout positions


        #First add any BOOL/INT/FLOAT_VAR_NODES
        for row in range(self._model.rowCount(index)):
            child_index = index.child(row,0)
            node =  child_index.internalPointer()

            wid = None

            if node.typeInfo() in [typ.BOOL_VAR_NODE, typ.INT_VAR_NODE, typ.FLOAT_VAR_NODE]:
                if node.userManualSet:
                    if   node.typeInfo() == typ.BOOL_VAR_NODE  : wid = ManualBoolSet()
                    elif node.typeInfo() == typ.INT_VAR_NODE   : wid = ManualIntSet()
                    elif node.typeInfo() == typ.FLOAT_VAR_NODE : wid = ManualFloatSet()

            if wid is not None:
                wid.setModel(child_index.model())
                wid.setRootIndex(index)
                wid.setCurrentModelIndex(child_index)
                wid.setEnabled(self._enable_device_behaviors)
                self.ui_wids.addWidget(wid, ui_row, ui_col, 1, -1) #1 row, full width
                ui_row += 1
       


        first_behavior = True
        #Then add in a button for each behavior
        for behavior in device_node.behaviors():
            if first_behavior:
                ui_col = 0

            else:
                if behavior.rootIndex().internalPointer().manualButtonNewLine:
                    ui_row += 1
                    ui_col = 0
                else:
                    ui_col += 1
            
            ui_col_span = 1
            if behavior.rootIndex().internalPointer().manualButtonSpanColEnd:
                ui_col_span = -1


            #btn = QtWidgets.QPushButton(behavior.name())
            btn = BehaviorButton(behavior.name())
            btn.clicked.connect(behavior.run)
            btn.setBehavior(behavior)
            btn.setEnabled(self._enable_device_behaviors)
            
            #Right click button to view behavior
            #btn.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            #btn.customContextMenuRequested.connect(self.onContextMenu)
            #self._behavior_menu = QtWidgets.QMenu(self)

            #view_behavior_action = QtWidgets.QAction('View Behavior', self)
            #view_behavior_action.triggered.connect(self.viewBehavior)
            #self._behavior_menu.addAction(view_behavior_action)


            #btn.clicked.connect(lambda a, b=behavior.run, c=run_data: self.runBehavior(b, c))
            self.ui_wids.addWidget(btn, ui_row, ui_col, 1, ui_col_span)
            first_behavior = False


        #Finally the viewers for the IO
        ui_row += 1
        ui_col = 0
        for row in range(self._model.rowCount(index)):
            child_index = index.child(row,0)
            node =  child_index.internalPointer()

            wid = None

            if   node.typeInfo() == typ.D_IN_NODE  : wid = ManualBoolView()
            elif node.typeInfo() == typ.D_OUT_NODE : wid = ManualBoolView()
            elif node.typeInfo() == typ.A_IN_NODE  : wid = ManualFloatView()
            elif node.typeInfo() == typ.A_OUT_NODE : wid = ManualFloatView()


            if node.typeInfo() in [typ.BOOL_VAR_NODE, typ.INT_VAR_NODE, typ.FLOAT_VAR_NODE]:
                if not node.userManualSet:
                    if   node.typeInfo() == typ.BOOL_VAR_NODE  : wid = ManualBoolView()
                    elif node.typeInfo() == typ.INT_VAR_NODE   : wid = ManualIntView()
                    elif node.typeInfo() == typ.FLOAT_VAR_NODE : wid = ManualFloatView()



            if wid is not None:
                wid.setModel(child_index.model())
                wid.setRootIndex(index)
                wid.setCurrentModelIndex(child_index)
                self.ui_wids.addWidget(wid, ui_row, ui_col, 1, -1) #1 row, full width
                ui_row += 1
       





    def setModel(self, model):
        if hasattr(model, 'mapToSource'):
            model = model.sourceModel()
        self._model = model

        self._mapper.setModel(model)
        self._mapper.addMapping(self.ui_name, col.NAME, bytes("text",'ascii'))
        self._mapper.addMapping(self.ui_description, col.DESCRIPTION, bytes("text",'ascii'))
        self._mapper.addMapping(self.ui_state, col.STATE, bytes("text",'ascii'))

    def model(self):
        return self._model
    
    def enableRunDeviceBehaviors(self, enable):
        self._enable_device_behaviors = bool(enable)
        if self._current_index:
            self.setSelection(self._current_index)


''' holding pen for behaviro code that references like a file?'''
    #   n = QtWidgets.QPushButton(behavior.name())
    #btn.clicked.connect(lambda a, b=behavior.run, c=run_data: self.runBehavior(b, c))
    #self.ui_wids.addWidget(btn, ui_row, ui_col, 1, ui_col_stretch)

    #def runBehavior(self, run_function, run_wids):
    #   run_data = {}

    #    for key in run_wids:
    #        wid = run_wids[key]

    #        if hasattr(wid, 'isChecked'):
    #            run_data[key] = wid.isChecked()
    #        elif hasattr(wid, 'value'):
    #            run_data[key] = wid.value()

    #    run_function(run_data)




class ManualBoolView(QtWidgets.QWidget):
    #Format: "Name : value"
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.mapper = QtWidgets.QDataWidgetMapper()
        hbox = QtWidgets.QHBoxLayout()
        self.setLayout(hbox)

        self._val = False
        self.ui_name = QtWidgets.QLabel('unknown')
        self.ui_val = QtWidgets.QLabel('?')
        self._off_name = ""
        self._on_name = ""

        hbox.addWidget(self.ui_name)
        hbox.addWidget(QtWidgets.QLabel(': '))
        hbox.addWidget(self.ui_val)
        hbox.addStretch(1)
        hbox.setContentsMargins(0,0,0,0)

    def setRootIndex(self, index):
        self.mapper.setRootIndex(index)

    def setCurrentModelIndex(self, index):
        self.mapper.setCurrentModelIndex(index)
        node = index.internalPointer()

        #These aren't changing often so they can just be set
        self.ui_name.setText(str(node.name))
        self._off_name = node.offName
        self._on_name = node.onName

        txt = self._on_name if node.value() else self._off_name
        self.ui_val.setText(txt)


    @QtCore.pyqtProperty(int)
    def value(self):
        return self._val

    @value.setter
    def value(self, value):
        self._val = value
        txt = self._on_name if value else self._off_name
        self.ui_val.setText(txt)

    def setModel(self, model):
        if hasattr(model, 'sourceModel'):model = model.sourceModel()
        self.mapper.setModel(model)
        self.mapper.addMapping(self, col.VALUE, bytes('value','ascii'))


class ManualBoolSet(QtWidgets.QWidget):
    #Format "Name : bnt_off btn_on"
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.mapper_1 = QtWidgets.QDataWidgetMapper()

        hbox = QtWidgets.QHBoxLayout(self)
        self.setLayout(hbox)

        self.ui_name = QtWidgets.QLabel('unknown')

        self.btn_group = QtWidgets.QButtonGroup()
        self.btn_group.setExclusive(True)
        self.btn_group.buttonClicked.connect(self.onClicked)

        self.ui_btn1 = QtWidgets.QPushButton('?', self)
        self.ui_btn2 = QtWidgets.QPushButton('?', self)
        self.ui_btn1.setCheckable(True)
        self.ui_btn2.setCheckable(True)

        self.btn_group.addButton(self.ui_btn1, 0)
        self.btn_group.addButton(self.ui_btn2, 1)

        hbox.addWidget(self.ui_name)
        hbox.addWidget(QtWidgets.QLabel(': '))
        hbox.addWidget(self.ui_btn1)
        hbox.addWidget(self.ui_btn2)
        hbox.addStretch(1)
        hbox.setContentsMargins(0,0,0,0)

        self.via_this_button = False
        self.btn_group.buttonClicked.connect(self.mapper_1.submit)


    def setRootIndex(self, index):
        self.mapper_1.setRootIndex(index)

    def setCurrentModelIndex(self, index):
        self.mapper_1.setCurrentModelIndex(index)

        node = index.internalPointer()

        #These aren't changing often so they can just be set
        self.ui_name.setText(str(node.name))
        self.ui_btn1.setText(str(node.offName))
        self.ui_btn2.setText(str(node.onName))

    def onClicked(self, btn):
        self.via_this_button = True
        self.value = self.btn_group.checkedId()

    @QtCore.pyqtProperty(int)
    def value(self):
        return self.btn_group.checkedId()

    @value.setter
    def value(self, value):
        if not self.via_this_button:
            if value:
                self.ui_btn2.setChecked(True)
            else:
                self.ui_btn1.setChecked(True)

        self.via_this_button = False


    def setModel(self, model):
        if hasattr(model, 'sourceModel'):model = model.sourceModel()
        self.mapper_1.setModel(model)
        self.mapper_1.addMapping(self, col.VALUE, bytes('value','ascii'))


class ManualIntView(QtWidgets.QWidget):
    #Format: "Name : value units"
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.mapper = QtWidgets.QDataWidgetMapper()

        hbox = QtWidgets.QHBoxLayout()
        self.setLayout(hbox)

        self._val = 0
        self.ui_name = QtWidgets.QLabel('unknown')
        self.ui_val = QtWidgets.QLabel('?')
        self.ui_units = QtWidgets.QLabel('')

        hbox.addWidget(self.ui_name)
        hbox.addWidget(QtWidgets.QLabel(': '))
        hbox.addWidget(self.ui_val)
        hbox.addWidget(self.ui_units)
        hbox.addStretch(1)
        hbox.setContentsMargins(0,0,0,0)

    def setRootIndex(self, index):
        self.mapper.setRootIndex(index)

    def setCurrentModelIndex(self, index):
        node = index.internalPointer()
        self.ui_name.setText(str(node.name))
        self.ui_units.setText(str(node.units))

        self.mapper.setCurrentModelIndex(index)


    @QtCore.pyqtProperty(float)
    def val(self):
        return self._val

    @val.setter
    def val(self, value):
        try:
            self._val = value
            txt = "{0:d}".format(int(self._val))
            self.ui_val.setText(txt)

        except:
            self.ui_val.setText('')

    def setModel(self, model):
        if hasattr(model, 'sourceModel'):model = model.sourceModel()
        self.mapper.setModel(model)
        self.mapper.addMapping(self, col.VALUE, bytes('val','ascii')) #Only one mapping of 'self' allowed per mapper




class ManualFloatView(QtWidgets.QWidget):
    #Format: "Name : value units"
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.mapper = QtWidgets.QDataWidgetMapper()

        hbox = QtWidgets.QHBoxLayout()
        self.setLayout(hbox)

        self._val = 0
        self._display_digits = 3
        self._display_scientific = False

        self.ui_name = QtWidgets.QLabel('unknown')
        self.ui_val = QtWidgets.QLabel('?')
        self.ui_units = QtWidgets.QLabel('')

        hbox.addWidget(self.ui_name)
        hbox.addWidget(QtWidgets.QLabel(': '))
        hbox.addWidget(self.ui_val)
        hbox.addWidget(self.ui_units)
        hbox.addStretch(1)
        hbox.setContentsMargins(0,0,0,0)

    def setRootIndex(self, index):
        self.mapper.setRootIndex(index)

    def setCurrentModelIndex(self, index):
        node = index.internalPointer()
        #These aren't changing often so they can just be set
        self.ui_name.setText(str(node.name))
        self.ui_units.setText(str(node.units))
        self._display_digits = node.displayDigits
        self._display_scientific = node.displayScientific

        self.mapper.setCurrentModelIndex(index)


    @QtCore.pyqtProperty(float)
    def val(self):
        return self._val

    @val.setter
    def val(self, value):
        try:
            self._val = value

            if self._display_scientific:
                txt = "{0:0.{prec}e}".format(self._val, prec=self._display_digits)
            else:
                txt = "{0:0.{prec}f}".format(self._val, prec=self._display_digits)

            self.ui_val.setText(txt)

        except:
            self.ui_val.setText('')

    def setModel(self, model):
        if hasattr(model, 'sourceModel'):model = model.sourceModel()
        self.mapper.setModel(model)
        self.mapper.addMapping(self, col.VALUE, bytes('val','ascii')) #Only one mapping of 'self' allowed per mapper




class ManualIntSet(QtWidgets.QWidget):
    #Format: "Name : value units"
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.mapper = QtWidgets.QDataWidgetMapper()
        self.mapper = QtWidgets.QDataWidgetMapper()

        hbox = QtWidgets.QHBoxLayout()
        self.setLayout(hbox)

        self.ui_name = QtWidgets.QLabel('unknown')
        self.ui_value = QtWidgets.QSpinBox()
        self.ui_units = QtWidgets.QLabel('units')
        hbox.addWidget(self.ui_name)
        hbox.addWidget(QtWidgets.QLabel(': '))
        hbox.addWidget(self.ui_value)
        hbox.addWidget(self.ui_units)
        hbox.addStretch(1)
        hbox.setContentsMargins(0,0,0,0)

    def setRootIndex(self, index):
        self.mapper.setRootIndex(index)

    def setCurrentModelIndex(self, index):
        self.mapper.setCurrentModelIndex(index)

        #These aren't changing often so they can just be set
        node = index.internalPointer()
        self.ui_name.setText(str(node.name))
        self.ui_units.setText(str(node.units))


    def setModel(self, model):
        if hasattr(model, 'sourceModel'):model = model.sourceModel()
        self.mapper.setModel(model)
        self.mapper.addMapping(self.ui_value, col.VALUE)# bytes("text",'ascii'))


class ManualFloatSet(QtWidgets.QWidget):
    #Format: "Name : value units"
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.mapper = QtWidgets.QDataWidgetMapper()
        self.mapper = QtWidgets.QDataWidgetMapper()

        hbox = QtWidgets.QHBoxLayout()
        self.setLayout(hbox)

        self.ui_name = QtWidgets.QLabel('unknown')
        self.ui_value = ScientificDoubleSpinBox()
        self.ui_units = QtWidgets.QLabel('units')
        hbox.addWidget(self.ui_name)
        hbox.addWidget(QtWidgets.QLabel(': '))
        hbox.addWidget(self.ui_value)
        hbox.addWidget(self.ui_units)
        hbox.addStretch(1)
        hbox.setContentsMargins(0,0,0,0)

    def setRootIndex(self, index):
        self.mapper.setRootIndex(index)

    def setCurrentModelIndex(self, index):
        self.mapper.setCurrentModelIndex(index)

        #These aren't changing often so they can just be set
        node = index.internalPointer()
        self.ui_name.setText(str(node.name))
        self.ui_units.setText(str(node.units))
        self.ui_value.setDisplayScientific(node.displayScientific)
        self.ui_value.setDisplayDigits(node.displayDigits)


    def setModel(self, model):
        if hasattr(model, 'sourceModel'):model = model.sourceModel()
        self.mapper.setModel(model)
        self.mapper.addMapping(self.ui_value, col.VALUE)# bytes("text",'ascii'))
