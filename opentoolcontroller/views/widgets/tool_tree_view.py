#!/usr/bin/python3
# -*- coding: utf-8 -*-
from PyQt5 import QtGui, QtWidgets
from opentoolcontroller.strings import typ

class ToolTreeView(QtWidgets.QTreeView):
    def __init__(self, parent=None):
        QtWidgets.QTreeView.__init__(self, parent)

        self._enable_context_menu = True

    def setEnableContextMenu(self, enable):
        self._enable_context_menu = bool(enable)

    def contextMenuEvent(self, event):
        if not self._enable_context_menu:
            event.accept()
            return 

        if self.selectionModel().selection().indexes():
            item = self.selectedIndexes()[0]
            current_index = item.model().mapToSource(item)
            node = current_index.internalPointer()

            #Setup the menu
            menu = QtWidgets.QMenu(self)
            add_menu = menu.addMenu('Add')
            if current_index.internalPointer().typeInfo() not in [typ.TOOL_NODE, typ.DEVICE_ICON_NODE]:
                menu.addAction("Delete")
            menu.addAction("Export")


            possible_children = self.model().possibleChildren(current_index)
            for possible_child in possible_children:
                if   possible_child == typ.SYSTEM_NODE    : add_menu.addAction('System')
                elif possible_child == typ.DEVICE_NODE    : add_menu.addAction('Device')
                elif possible_child == typ.D_IN_NODE      : add_menu.addAction('Digital Input')
                elif possible_child == typ.A_IN_NODE      : add_menu.addAction('Analog Input')
                elif possible_child == typ.D_OUT_NODE     : add_menu.addAction('Digital Output')
                elif possible_child == typ.A_OUT_NODE     : add_menu.addAction('Analog Output')
                elif possible_child == typ.BOOL_VAR_NODE  : add_menu.addAction('Bool Variable')
                elif possible_child == typ.INT_VAR_NODE   : add_menu.addAction('Int Variable')
                elif possible_child == typ.FLOAT_VAR_NODE : add_menu.addAction('Float Variable')

            #Do the action from the menu
            action = menu.exec_(self.mapToGlobal(event.pos()))

            if action is not None:
                if   action.text() == "System"          : self.model().insertChild(current_index, typ.SYSTEM_NODE)
                elif action.text() == "Device"          : self.model().insertChild(current_index, typ.DEVICE_NODE)
                elif action.text() == "Digital Input"   : self.model().insertChild(current_index, typ.D_IN_NODE)
                elif action.text() == "Analog Input"    : self.model().insertChild(current_index, typ.A_IN_NODE)
                elif action.text() == "Digital Output"  : self.model().insertChild(current_index, typ.D_OUT_NODE)
                elif action.text() == "Analog Output"   : self.model().insertChild(current_index, typ.A_OUT_NODE)
                elif action.text() == "Bool Variable"   : self.model().insertChild(current_index, typ.BOOL_VAR_NODE)
                elif action.text() == "Int Variable"    : self.model().insertChild(current_index, typ.INT_VAR_NODE)
                elif action.text() == "Float Variable"  : self.model().insertChild(current_index, typ.FLOAT_VAR_NODE)


                elif action.text() == "Delete":
                    result = QtWidgets.QMessageBox.question(self,"Delete...?", "Are you sure you want to delete " + str(node.name),
                                                              QtWidgets.QMessageBox.Yes| QtWidgets.QMessageBox.No)

                    if result == QtWidgets.QMessageBox.Yes:
                        self.model().removeRows(current_index.row(), 1, current_index.parent())


                elif action.text() == "Export":
                    options = QtWidgets.QFileDialog.Options()
                    #If we use the native GTK dialgo we can't give it a proper parent since this is QT not GTK
                    options |= QtWidgets.QFileDialog.DontUseNativeDialog
                    export_dialog = QtWidgets.QFileDialog(options=options)
                    export_dialog.setFileMode(QtWidgets.QFileDialog.AnyFile)

                    export_dialog.setWindowTitle('Export Node as JSON')
                    #export_dialog.setDirectory(EXPORT_DIR)
                    export_dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
                    export_dialog.setNameFilter('JSON files (*.json)')
                    export_dialog.setDefaultSuffix('json')
                    if export_dialog.exec_() == QtWidgets.QFileDialog.Accepted:
                        file = open(export_dialog.selectedFiles()[0],'w')
                        file.write(current_index.internalPointer().asJSON())
                        file.close()
