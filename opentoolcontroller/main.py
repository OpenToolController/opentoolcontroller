#!/usr/bin/env python3
# -.- coding: utf-8 -.-
import sys, json
from PyQt5 import QtCore, QtGui, QtWidgets

import xml.etree.ElementTree as ET
from opentoolcontroller.tool_model import ToolModel
from opentoolcontroller.tool_editor import ToolEditor
from opentoolcontroller.tool_manual_view import ToolManualView
from opentoolcontroller.alert_view import AlertView, AlertTableModel

from opentoolcontroller.bt_model import BTModel

from opentoolcontroller.hardware import HalReader

import gc, pprint

# sudo halcompile --install opentoolcontroller/HAL/hardware_sim.comp
# clear; pytest 'tests/test_device_manual_view.py' -k 'test_two' -s

class Window(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__()
        file = 'tests/tools/basic_tool_1.json'
        with open(file) as f:
            json_data = json.load(f)

        self._alert_model =  AlertTableModel()
        self._alert_view = AlertView(self._alert_model)
        self._alert_view.setWindowTitle('Alerts')



        #self.reader = HalReader()
        self.tool_model = ToolModel()
        self.tool_model.loadJSON(json_data)
        self.tool_model.setAlertCallback(self._alert_model.addAlert)
        self.tool_model.loadBehaviors()

        self.setWindowTitle('Open Tool Controller')
        self.resize(800,600)


        self._manual_view = ToolManualView(self.tool_model)
        self._manual_view.setWindowTitle('Manual')

        self._tool_editor = ToolEditor()
        self._tool_editor.setModel(self.tool_model)
        self._tool_editor.setWindowTitle('Tool Editor')

        dock1 = QtWidgets.QDockWidget('Manual', self, objectName='manual')
        dock1.setWidget(self._manual_view)

        dock2 = QtWidgets.QDockWidget('Tool Editor', self, objectName='editor')
        dock2.setWidget(self._tool_editor)

        dock3 = QtWidgets.QDockWidget('Alerts', self, objectName='alerts')
        dock3.setWidget(self._alert_view)

        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock1)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock2)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock3)
        self.tabifyDockWidget(dock1, dock2)
        self.tabifyDockWidget(dock2, dock3)


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
        self.file_menu.addAction(self.toggleHalAction)
        self.file_menu.addAction(self.saveToolAction)

        #Add enable direct io control to the menu?
        #tool variable that when yes you get direct control of the hal nodes

        self._settings = QtCore.QSettings('Open Tool Controller', 'test1')
        geometry = self._settings.value('main_window_geometry', bytes('', 'utf-8'))
        state = self._settings.value('main_window_state', bytes('', 'utf-8'))
        self.restoreGeometry(geometry)
        self.restoreState(state)


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
        self._manual_view.close()
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
            self._manual_view.close()
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
