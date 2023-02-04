#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from PyQt5 import QtGui, QtCore, QtWidgets
from opentoolcontroller.calibration_table_model import CalibrationTableModel
from opentoolcontroller.views.widgets.scientific_spin import ScientificDoubleSpinBox


class CalibrationTableView(QtWidgets.QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.menu_add_row_before = "Add Row Before"
        self.menu_add_row_after  = "Add Row After"
        self.menu_remove_row     = "Remove Row"

        item_delegate = ValidatedDelegate()
        self.setItemDelegate(item_delegate)

        self.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)

    def setModel(self, value):
        super(CalibrationTableView, self).setModel(value)
        self.__setupGUI()

    def getModel(self):
        return self.model()

    def addRowBeforeSelected(self):
        if len(self.selectedIndexes()) == 1:
            item = self.selectedIndexes()[0]
            self.model().insertRows(item.row(), 1)

    def addRowAfterSelected(self):
        if len(self.selectedIndexes()) == 1:
            item = self.selectedIndexes()[0]
            self.model().insertRows(item.row()+1, 1)

    def removeSelectedRow(self):
        if len(self.selectedIndexes()) == 1:
            item = self.selectedIndexes()[0]
            self.model().removeRows(item.row(),1)

    def contextMenuEvent(self, event):
        if self.selectionModel().selection().indexes():

            #Setup the menu
            menu     = QtWidgets.QMenu(self)
            menu.addAction(self.menu_add_row_before)
            menu.addAction(self.menu_add_row_after)

            if self.model().rowCount() > 2:
                menu.addAction(self.menu_remove_row)

            action = menu.exec_(self.mapToGlobal(event.pos()))

            if action is not None:
                if   action.text() == self.menu_add_row_before: self.addRowBeforeSelected()
                elif action.text() == self.menu_add_row_after : self.addRowAfterSelected()
                elif action.text() == self.menu_remove_row    : self.removeSelectedRow()


    def __setupGUI(self):
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)

        font = QtGui.QFont("Helvetica", 14)
        self.setFont(font)

    #def reset(self):
    #    super(CalibrationTableView, self).reset()
    #    self.__setupGUI()

    calibrationTableView = QtCore.pyqtProperty(type(CalibrationTableModel()), getModel, setModel)



class ValidatedDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        if not index.isValid():
            return 0

        if index.column() == 0 or index.column() == 1:
            scienceSpinBox = ScientificDoubleSpinBox(parent)
            return scienceSpinBox

        return super().createEditor(parent, option, index)
