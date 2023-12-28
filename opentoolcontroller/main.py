#!/usr/bin/env python3
# -.- coding: utf-8 -.-
import sys, json, os
import argparse

from PyQt5 import QtCore, QtGui, QtWidgets

import xml.etree.ElementTree as ET
from opentoolcontroller.tool_model import ToolModel
from opentoolcontroller.tool_editor import CommonEditor
from opentoolcontroller.tool_control_view import ToolControlView
from opentoolcontroller.alert_view import AlertView, AlertTableModel, ActionLogView, ActionLogTableModel
from opentoolcontroller.login import LoginView, LoginModel

from opentoolcontroller.bt_model import BTModel, BehaviorRunner

from opentoolcontroller.hardware import HalReader
from opentoolcontroller.strings import defaults, col

import gc, pprint

# sudo halcompile --install opentoolcontroller/HAL/hardware_sim.comp
# clear; pytest 'tests/test_device_control_view.py' -k 'test_two' -s

class Window(QtWidgets.QMainWindow):
    def __init__(self, tool_dir, parent=None):
        super().__init__()

        json_data = None
        self._allow_save = False

        if tool_dir:
            defaults.TOOL_DIR = tool_dir
            self._allow_save = True

            try:
                tool_config_file = tool_dir + '/tool_config.json'
                with open(tool_config_file) as f:
                    json_data = json.load(f)
            except:
                pass

        '''Add something to select where to save if we start a new one '''

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



        '''Work on enforcing this next! '''
        if json_data is not None:
            self.tool_model.loadJSON(json_data)
        self.tool_model.setAlertCallback(self._alert_model.addAlert)
        self.tool_model.setActionLogCallback(self._action_log_model.addAction)
        self.tool_model.setLaunchValues()
        self.tool_model.loadBehaviors()




        tool_index = self.tool_model.index(0, 0, QtCore.QModelIndex())
        tick_rate_ms = self.tool_model.data(tool_index.siblingAtColumn(col.TICK_RATE_MS), QtCore.Qt.DisplayRole)
        self.behavior_runner = BehaviorRunner()
        BTModel.behaviorRunner = self.behavior_runner
        print("Tick Rate: ", tick_rate_ms)



        self.setWindowTitle('Open Tool Controller')
        self.resize(800,600)


        self._control_view = ToolControlView(self.tool_model)
        self._control_view.setWindowTitle('Control')
        self._login_model.addLoginChangedCallback(self._control_view.enableRunDeviceBehaviors, self._login_model.RUN_BEHAVIORS)
        self._login_model.addLoginChangedCallback(self._control_view.enableEditBehaviors, self._login_model.EDIT_BEHAVIOR)

        self._tool_editor = CommonEditor()
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


        self.reader.setModel(self.tool_model)
        #Start the behavior tree
        #self.tool_model.runBehaviorTrees()


        extractAction = QtWidgets.QAction("collect garbage", self)
        extractAction.triggered.connect(self.collectGarbage)

        self.toggleHalAction = QtWidgets.QAction("Start Hal Reader", self)
        self.toggleHalAction.triggered.connect(self.toggleHalReader)

        self.saveToolAction = QtWidgets.QAction("Save", self)
        self.saveToolAction.triggered.connect(self.saveTool)
        self.saveToolAction.setShortcut('ctrl+s')

        self.saveToolAsAction = QtWidgets.QAction("Save As", self)
        self.saveToolAsAction.triggered.connect(self.saveToolAs)

        self.halMeterAction = QtWidgets.QAction("HAL Meter", self)
        self.halMeterAction.triggered.connect(self.reader.loadHalMeter)

        self.halScopeAction = QtWidgets.QAction("HAL Scope", self)
        self.halScopeAction.triggered.connect(self.reader.loadHalScope)

        self.file_menu = self.menuBar().addMenu('&File')
        self.hal_menu = self.menuBar().addMenu('&HAL')
        self.file_menu.addAction(extractAction)
        if self._allow_save:
            self.file_menu.addAction(self.saveToolAction)
        self.file_menu.addAction(self.saveToolAsAction)

        self.hal_menu.addAction(self.toggleHalAction)
        self.hal_menu.addAction(self.halMeterAction)
        self.hal_menu.addAction(self.halScopeAction)


        if not self.reader.halExists():
            self.toggleHalAction.setDisabled(True)
            self.halMeterAction.setDisabled(True)
            self.halScopeAction.setDisabled(True)


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
        filename = defaults.TOOL_DIR + '/tool_config.json'
        with open(filename, 'w') as f:
            f.write(data)

    def saveToolAs(self):
        data = self.tool_model.asJSON()

        options = QtWidgets.QFileDialog.Options()
        save_as_dialog = QtWidgets.QFileDialog(options=options)
        save_as_dialog.setFileMode(QtWidgets.QFileDialog.AnyFile)
        save_as_dialog.setWindowTitle('Save Tool Config As')
        save_as_dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        save_as_dialog.setNameFilter('JSON files (*.json)')
        save_as_dialog.setDefaultSuffix('json')

        if save_as_dialog.exec_() == QtWidgets.QFileDialog.Accepted:
            f = open(save_as_dialog.selectedFiles()[0],'w')
            f.write(data)
            f.close()

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
        self.reader.stop()
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

    def startHalReader(self):
        self.toggleHalAction.setText('Stop Hal Reader')
        self.reader.start()

    def setMovableIcons(self):
        self._control_view.setMovableIcons(True)




if __name__ == '__main__':
    tool_dir = None

    parser = argparse.ArgumentParser(
                    prog='Open Tool Controller',
                    description='TODO',
                    epilog='TODO')

    parser.add_argument('tool_dir', help='The directory containing the tool definition.')
    parser.add_argument('-S', '--Start', action='store_true', help='Starts HAL reader on launch')
    parser.add_argument('-m', '--movable_icons', action='store_true', help='Allows device icons to be moved by the mouse')
    #TODO add option to start a tool behavior?
    #parser.add_argument('-v', '--verbose')

    args = parser.parse_args()
    tool_dir = args.tool_dir
    tool_dir = tool_dir.rstrip("/")


    app = QtWidgets.QApplication(sys.argv)
    #app.setStyle("fusion") #Changing the style
    w = Window(tool_dir)
    if args.Start:
        w.startHalReader()
    if args.movable_icons:
        w.setMovableIcons()
    w.show()
    sys.exit(app.exec_())


