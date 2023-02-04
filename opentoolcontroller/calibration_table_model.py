#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from PyQt5 import QtCore

import copy
import numpy as np
from scipy.interpolate import interp1d

class CalibrationTableModel(QtCore.QAbstractTableModel):
    '''Stores analog value calibration, i.e. HAL units to software units
        - HAL: An analog value from HAL
        - GUI: A scaled value from the gui

        HAL Value  GUI Value
           0.0         0
           1.0        50
           2.0        250
           3.0        350
           4.0        450
           5.0        750
    '''

    def __init__(self, parent = None):
        super().__init__(parent)
        self._headers = ['HAL Value', 'GUI Value']
        self._data  = [[0.0, 0.0],
                       [1.0, 0.0]]

    def halValueColumn (self): return 0
    def guiValueColumn (self): return 1

    def halValues(self):
        return [row[self.halValueColumn()] for row in self._data]

    def guiValues(self):
        return [row[self.guiValueColumn()] for row in self._data]

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._data[0])

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return self._headers[section]
            else:
                return str(section).format("%1")


    def dataArray(self):
        data = []
        data.append(['hal_value', 'gui_value'])

        data_main = copy.deepcopy(self._data)
        data += data_main

        return data


    def setDataArray(self, data):
        '''
            in format [ ['hal_value', 'gui_value' ],
                        [        0.0,        0.01 ],
                        [        2.0,       11.57 ],
                        [        5.0,       46.00 ],
                        [        9.0,        9183 ] ]
        '''

        if data[0] != ['hal_value', 'gui_value']:
            raise ValueError("First row must be ['hal_value', 'gui_value']")

        data_main = []
        data_main = data[1:]


        #min 2 points to draw a line
        if len(data_main) < 2:
            raise ValueError("Must have 2 or more rows in calibration table")


        #Check that these are all floats
        for row in data_main:
            if not all(isinstance(i, (int, float)) for i in row):
                raise ValueError('Calibration table data must be of type int or float')


        #Check that these are all increasing values
        hal_values = [row[0] for row in data_main]
        gui_values = [row[1] for row in data_main]

        hal_is_increasing = all(i < j for i, j in zip(hal_values, hal_values[1:]))
        gui_is_increasing = all(i < j for i, j in zip(gui_values, gui_values[1:]))
        gui_is_decreasing = all(i > j for i, j in zip(gui_values, gui_values[1:]))

        if not (hal_is_increasing):
            raise ValueError('Calibration table hal values must increasing in order')

        if not (gui_is_increasing ^ gui_is_decreasing):
            raise ValueError('Calibration table gui values must ordered either increasing or decreasing')


        #Set the data now
        self.beginResetModel()
        for i, row in enumerate(data_main):
            data_main[i][0] = float(row[0])
            data_main[i][1] = float(row[1])

        self._data = copy.deepcopy(data_main)
        self.endResetModel()


    def data(self, index, role):
        row = index.row()
        col = index.column()

        if role == QtCore.Qt.EditRole or role == QtCore.Qt.DisplayRole:
            return self._data[row][col]

        if role == QtCore.Qt.ToolTipRole:
            return "These values are used to scale the numbers in HAL to the units in OpenToolController"

        if role == QtCore.Qt.TextAlignmentRole:
            if col == 0:
                return QtCore.Qt.AlignCenter
            else:
                return QtCore.Qt.AlignRight


    def setData(self, index, value, role = QtCore.Qt.EditRole):
        if role == QtCore.Qt.EditRole:
            if not isinstance(value, (int, float)):
                raise ValueError("Must be of type integer or float")

            row = index.row()
            col = index.column()
            num_rows = len(self._data)


            if col == self.halValueColumn():
                if row < num_rows-1:
                    if value >= self._data[row+1][col]:
                        raise ValueError('Hal Value must be less than next index')
                if row > 0:
                    if value <= self._data[row-1][col]:
                        raise ValueError('Hal Value must be more than previous index')

            elif col == self.guiValueColumn():


                #Check if the gui values are increasing or decreasing if we have more then 2
                if self.rowCount() > 2:
                    gui_values = [row[self.guiValueColumn()] for row in self._data]
                    gui_is_increasing = all(i < j for i, j in zip(gui_values, gui_values[1:]))

                    if gui_is_increasing:
                        if row < num_rows-1:
                            if value >= self._data[row+1][col]:
                                raise ValueError('GUI value must be less than next index')
                        if row > 0:
                            if value <= self._data[row-1][col]:
                                raise ValueError('GUI value must be more than previous index')
                    else:
                        if row < num_rows-1:
                            if value <= self._data[row+1][col]:
                                raise ValueError('GUI value must be more than next index')
                        if row > 0:
                            if value >= self._data[row-1][col]:
                                raise ValueError('GUI value must be less than previous index')



            self._data[row][col] = float(value)
            self.dataChanged.emit(index, index)

            return True
        return False




    def flags(self, index):
        if index.row() >= 0 and index.row() < len(self._data):
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable

        else:
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable


    def removeRows(self, position, rows=1, index=QtCore.QModelIndex()):
        if self.rowCount() > 2:
            self.beginRemoveRows(QtCore.QModelIndex(), position, position + rows - 1)
            self._data = self._data[:position] + self._data[position + rows:]
            self.endRemoveRows()
            return True

    def insertRows(self, position, rows=1, index=QtCore.QModelIndex()):
        #min two rows in this dataset
        #numpy.linspace(start, stop, num=50, endpoint=True, retstep=False, dtype=None, axis=0)
        if position == 0:

            hal_inc      = self._data[position][0] - self._data[position+1][0]
            new_hal_vals = [self._data[position][0] + hal_inc*i for i in range(1,rows+1)]
            new_hal_vals.reverse()

            gui_inc      = self._data[position][1] - self._data[position+1][1]
            new_gui_vals = [self._data[position][1] + gui_inc*i for i in range(1,rows+1)]
            new_gui_vals.reverse()


        elif position == len(self._data):

            hal_inc      = self._data[position-1][0] - self._data[position-2][0]
            new_hal_vals = [self._data[position-1][0] + hal_inc*i for i in range(1,rows+1)]

            gui_inc      = self._data[position-1][1] - self._data[position-2][1]
            new_gui_vals = [self._data[position-1][1] + gui_inc*i for i in range(1,rows+1)]


        else:
            new_hal_vals = np.linspace(self._data[position-1][0], self._data[position][0], rows+1, endpoint=False)
            new_hal_vals = new_hal_vals.tolist()
            new_hal_vals.pop(0)

            new_gui_vals = np.linspace(self._data[position-1][1], self._data[position][1], rows+1, endpoint=False)
            new_gui_vals = new_gui_vals.tolist()
            new_gui_vals.pop(0)


        self.beginInsertRows(QtCore.QModelIndex(), position, position + rows - 1)

        for row in range(rows):
            self._data.insert(position + row,  [new_hal_vals[row], new_gui_vals[row]])#"%s_%s"% (itemSelected, self.added))

        self.endInsertRows()

        return True
