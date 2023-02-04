# -*- coding: utf-8 -*-
from PyQt5 import QtWidgets, QtCore, QtGui
from datetime import datetime

class AlertView(QtWidgets.QMainWindow):
    def __init__(self, alert_model):
        super().__init__()

        self._alert_model = alert_model

        #For the filter
        self._proxy_model = QtCore.QSortFilterProxyModel()
        self._proxy_model.setFilterKeyColumn(-1)
        self._proxy_model.setSourceModel(self._alert_model)
        self._proxy_model.sort(1, QtCore.Qt.DescendingOrder)


        self._alert_search_bar = QtWidgets.QLineEdit()
        self._alert_search_bar.textChanged.connect(self._proxy_model.setFilterFixedString)

        self._table = QtWidgets.QTableView()
        self._table.setModel(self._proxy_model)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setColumnWidth(0, 70)
        self._table.setColumnWidth(1, 170)
        self._table.setColumnWidth(2, 100)
        self._table.setColumnWidth(3, 100)

        grid = QtWidgets.QGridLayout()
        wid = QtWidgets.QWidget(self)
        wid.setLayout(grid)
        self.setCentralWidget(wid)

        grid.addWidget(self._alert_search_bar, 0, 0, 1, 5)
        grid.addWidget(self._table, 1, 0, 1, 5)

        clear_btn = QtWidgets.QPushButton('Clear All')
        clear_btn.clicked.connect(self.clearAlerts)
        grid.addWidget(clear_btn, 2, 4)


    def clearAlerts(self):
        self._alert_model.clearAlerts()

        


#TODO change out some of the constanst for string named

class AlertTableModel(QtCore.QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self._data = []
        self._horizontal_header_labels = ['Type','Time', 'System', 'Device', 'Alert']

    def data(self, index, role):
        if role == QtCore.Qt.DisplayRole:
            return self._data[index.row()][index.column()]

        elif role == QtCore.Qt.FontRole:
            font = QtGui.QFont()
            if self._data[index.row()][6] == True:
                font.setWeight(QtGui.QFont.Light)
            else:
                font.setWeight(QtGui.QFont.ExtraBold)
            return font

    def rowCount(self, index=QtCore.QModelIndex()):
        return  0 if index.isValid() else len(self._data)

    def columnCount(self, index=QtCore.QModelIndex()):
        return 5
 
    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            if 0 <= section <= 4:
                return self._horizontal_header_labels[section]




    def addAlert(self, alert_type=None, system=None, device=None, alert=None, user_clear=True):
        current_time = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")

        alert_text = ''
        if alert_type == 0:
            alert_text = 'Message'
        elif alert_type == 1:
            alert_text = 'Warning'
        elif alert_type == 2:
            alert_text = 'Alarm'

        is_cleared = False

        new_row = [alert_text, current_time, str(system), str(device), str(alert), bool(user_clear), bool(is_cleared)]

        #insert at end, soring done by proxy view
        row_count = self.rowCount(QtCore.QModelIndex())
        self.beginInsertRows(QtCore.QModelIndex(), row_count, row_count)
        self._data.append(new_row)
        self.endInsertRows()


        clear_alarm_callback = lambda y=row_count: self.clearAlertByRow(y)
        set_user_clearable = lambda y=row_count: self.setUserClearByRow(y)

        return clear_alarm_callback, set_user_clearable
    
    def clearAlertByRow(self, row):
        self._data[row][6] = True
        index_1 = self.index(row, 0)
        index_2 = self.index(row, self.columnCount()-1)
        self.dataChanged.emit(index_1, index_2, [QtCore.Qt.FontRole])

    def setUserClearByRow(self, row):
        self._data[row][5] = True

    def clearAlerts(self):
        for i, row in enumerate(self._data):
            if row[5]:
                self._data[i][6] = True

        index_1 = self.index(0, 0)
        index_2 = self.index(self.rowCount()-1, self.columnCount()-1)
        self.dataChanged.emit(index_1, index_2, [QtCore.Qt.FontRole])

        
