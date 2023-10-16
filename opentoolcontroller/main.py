#!/usr/bin/env python3
# -.- coding: utf-8 -.-
import sys, json
from PyQt5 import QtCore, QtGui, QtWidgets

import xml.etree.ElementTree as ET
from opentoolcontroller.tool_model import ToolModel
from opentoolcontroller.tool_editor import ToolEditor
from opentoolcontroller.tool_control_view import ToolControlView
from opentoolcontroller.alert_view import AlertView, AlertTableModel, ActionLogView, ActionLogTableModel
from opentoolcontroller.login import LoginView, LoginModel

from opentoolcontroller.bt_model import BTModel

from opentoolcontroller.hardware import HalReader

import gc, pprint

# sudo halcompile --install opentoolcontroller/HAL/hardware_sim.comp
# clear; pytest 'tests/test_device_control_view.py' -k 'test_two' -s

class Window(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__()
        file = 'tests/tools/basic_tool_1.json'
        with open(file) as f:
            json_data = json.load(f)

        self._login_model = LoginModel()
        self._login_view = LoginView(self._login_model)
        self._login_view.setWindowTitle('Login')

        self._alert_model =  AlertTableModel()
        self._alert_view = AlertView(self._alert_model)
        self._alert_view.setWindowTitle('Alerts')
        self._login_model.addLoginChangedCallback(self._alert_view.enableClearAlerts, self._login_model.CLEAR_ALERTS)

        self._action_log_model =  ActionLogTableModel()
        self._action_log_model.setCurrentUser(self._login_model.currentUser)
        self._action_log_view = ActionLogView(self._action_log_model)
        self._action_log_view.setWindowTitle('Action Log')


        self.reader = HalReader()
        self.tool_model = ToolModel()
        self.tool_model.loadJSON(json_data)
        self.tool_model.setAlertCallback(self._alert_model.addAlert)
        self.tool_model.setActionLogCallback(self._action_log_model.addAction)
        self.tool_model.setLaunchValues()
        self.tool_model.loadBehaviors()

        self.setWindowTitle('Open Tool Controller')
        self.resize(800,600)


        self._control_view = ToolControlView(self.tool_model)
        self._control_view.setWindowTitle('Control')
        self._login_model.addLoginChangedCallback(self._control_view.enableRunDeviceBehaviors, self._login_model.RUN_BEHAVIORS)
        self._login_model.addLoginChangedCallback(self._control_view.enableEditBehaviors, self._login_model.EDIT_BEHAVIOR)

        self._tool_editor = ToolEditor()
        self._tool_editor.setModel(self.tool_model)
        self._tool_editor.setWindowTitle('Tool Editor')
        self._login_model.addLoginChangedCallback(self._tool_editor.enableEditTool, self._login_model.EDIT_TOOL)
        self._login_model.addLoginChangedCallback(self._tool_editor.enableEditBehaviors, self._login_model.EDIT_BEHAVIOR)

        dock1 = QtWidgets.QDockWidget('Control', self, objectName='control')
        dock1.setWidget(self._control_view)
        dock1.setContextMenuPolicy(QtCore.Qt.PreventContextMenu)


        dock2 = QtWidgets.QDockWidget('Tool Editor', self, objectName='editor')
        dock2.setWidget(self._tool_editor)
        dock2.setContextMenuPolicy(QtCore.Qt.PreventContextMenu)

        dock3 = QtWidgets.QDockWidget('Alerts', self, objectName='alerts')
        dock3.setWidget(self._alert_view)
        dock3.setContextMenuPolicy(QtCore.Qt.PreventContextMenu)

        dock4 = QtWidgets.QDockWidget('Login', self, objectName='login')
        dock4.setWidget(self._login_view)
        dock4.setContextMenuPolicy(QtCore.Qt.PreventContextMenu)
        
        dock5 = QtWidgets.QDockWidget('Action Log', self, objectName='action_log')
        dock5.setWidget(self._action_log_view)
        dock5.setContextMenuPolicy(QtCore.Qt.PreventContextMenu)


        dock1.setFeatures(QtWidgets.QDockWidget.DockWidgetFloatable | QtWidgets.QDockWidget.DockWidgetMovable)
        dock2.setFeatures(QtWidgets.QDockWidget.DockWidgetFloatable | QtWidgets.QDockWidget.DockWidgetMovable)
        dock3.setFeatures(QtWidgets.QDockWidget.DockWidgetFloatable | QtWidgets.QDockWidget.DockWidgetMovable)
        dock4.setFeatures(QtWidgets.QDockWidget.DockWidgetFloatable | QtWidgets.QDockWidget.DockWidgetMovable)
        dock5.setFeatures(QtWidgets.QDockWidget.DockWidgetFloatable | QtWidgets.QDockWidget.DockWidgetMovable)

        self.addDockWidget(QtCore.Qt.TopDockWidgetArea, dock1)
        self.addDockWidget(QtCore.Qt.TopDockWidgetArea, dock2)
        self.addDockWidget(QtCore.Qt.TopDockWidgetArea, dock3)
        self.addDockWidget(QtCore.Qt.TopDockWidgetArea, dock4)
        self.addDockWidget(QtCore.Qt.TopDockWidgetArea, dock5)
        self.tabifyDockWidget(dock1, dock2)
        self.tabifyDockWidget(dock2, dock3)
        self.tabifyDockWidget(dock3, dock4)
        self.tabifyDockWidget(dock4, dock5)
        self.setDockNestingEnabled(True) #needed for left/right arranging


        #self.reader.setModel(self.tool_model)
        #self.reader.start()

        #Start the behavior tree
        #self.tool_model.runBehaviorTrees()


        extractAction = QtWidgets.QAction("collect garbage", self)
        extractAction.triggered.connect(self.collectGarbage)

        self.toggleHalAction = QtWidgets.QAction("Start Hal Reader", self)
        self.toggleHalAction.triggered.connect(self.toggleHalReader)

        self.saveToolAction = QtWidgets.QAction("Save", self)
        self.saveToolAction.triggered.connect(self.saveTool)
        self.saveToolAction.setShortcut('ctrl+s')

        self.file_menu = self.menuBar().addMenu('&File')
        self.file_menu.addAction(extractAction)
        self.file_menu.addAction(self.saveToolAction)
        self.file_menu.addAction(self.toggleHalAction)


        if not self.reader.halExists():
            self.toggleHalAction.setDisabled(True)


        #Add enable direct io control to the menu?
        #tool variable that when yes you get direct control of the hal nodes

        self._settings = QtCore.QSettings('Open Tool Controller', 'test1')
        geometry = self._settings.value('main_window_geometry', bytes('', 'utf-8'))
        state = self._settings.value('main_window_state', bytes('', 'utf-8'))
        self.restoreGeometry(geometry)
        self.restoreState(state)

        self._login_model.runLoginChangedCallbacks()

    def saveTool(self):
        data = self.tool_model.asJSON()
        #filename = self._bt_editor.model().file()
        filename = 'tests/tools/basic_tool_1.json'
        with open(filename, 'w') as f:
            f.write(data)

        #self.setTitle(file_changed=False)


    def collectGarbage(self):
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(gc.get_stats())
        gc.collect()
        pp.pprint(gc.get_stats())


    #fast close for testing
    def closeEvent(self, event):
        self._tool_editor.close()
        self._control_view.close()
        self._alert_view.close()
        geometry = self.saveGeometry()
        self._settings.setValue('main_window_geometry', geometry)
        state = self.saveState()
        self._settings.setValue('main_window_state', state)
        super().closeEvent(event)

    #normal close
    def _tmp_closeEvent(self, event):
        quit_msg = "Are you sure you want to exit the program?"
        reply = QtWidgets.QMessageBox.question(self, 'Message', quit_msg, QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)

        if reply == QtWidgets.QMessageBox.Yes:
            #self.reader.stop()

            self._tool_editor.close()
            self._control_view.close()
            self._alert_view.close()

            geometry = self.saveGeometry()
            self._settings.setValue('main_window_geometry', geometry)
            state = self.saveState()
            self._settings.setValue('main_window_state', state)
            super().closeEvent(event)

        else:
            event.ignore()

    def toggleHalReader(self):
        if self.reader.running():
            self.toggleHalAction.setText('Start Hal Reader')
            self.reader.stop()
        else:
            self.toggleHalAction.setText('Stop Hal Reader')
            self.reader.start()








if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    #app.setStyle("fusion") #Changing the style
    w = Window()
    w.show()
    sys.exit(app.exec_())
