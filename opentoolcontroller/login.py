# -*- coding: utf-8 -*-
from PyQt5 import QtWidgets, QtCore, QtGui, uic
from datetime import datetime

import hashlib
login_base, login_form = uic.loadUiType("opentoolcontroller/views/Login.ui")

class LoginView(login_base, login_form):
    def __init__(self, login_model):
        super(login_base, self).__init__()

        self.setupUi(self)

        self._login_model = login_model
        #self._login_model = LoginModel()
        #self.ui_login_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.ui_login_table.setModel(self._login_model)
        self.ui_current_user.setText(self._login_model.currentUser())
        self.ui_login.clicked.connect(self.login)
        self.ui_logout.clicked.connect(self.logout)
        self.ui_password.returnPressed.connect(self.login)

        self.setPasswordEditButtons()

    def setPasswordClicked(self, row):
        username = self._login_model.usernameByRow(row)
        dlg = SetPasswordDialog(self)
        dlg.setWindowTitle("Set password for " + str(username))

        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            new_password = dlg.getValue()
            self._login_model.setPasswordByRow(row, new_password)


    def login(self):
        username = self.ui_username.text()
        password = self.ui_password.text()
        self.ui_password.setText('')
        self._login_model.login(username, password)
        self.setCurrentUserText()
        self.setPasswordEditButtons()


    def logout(self):
        self._login_model.logout()
        self.setCurrentUserText()
        self.setPasswordEditButtons()


    def setCurrentUserText(self):
        current_user = self._login_model.currentUser()
        if current_user is not None:
            self.ui_current_user.setText(current_user)
            self.ui_current_user.setStyleSheet("font: bold")
        else:
            self.ui_current_user.setText('none')
            self.ui_current_user.setStyleSheet("font: italic")


    def setPasswordEditButtons(self):
        if self._login_model.canEditUsers():
            for row in range(self._login_model.rowCount()):
                self.btn_sell = QtWidgets.QPushButton('Set PW')
                self.btn_sell.clicked.connect(lambda a, b=row: self.setPasswordClicked(b))
                self.ui_login_table.setIndexWidget(self._login_model.index(row, 1),  self.btn_sell)
            
                #self.ui_login_table.openPersistentEditor(self._login_model.index(row, 2))
        else:
            for row in range(self._login_model.rowCount()):
                self.ui_login_table.setIndexWidget(self._login_model.index(row, 1),  QtWidgets.QLabel("****"))

                #self.ui_login_table.closePersistentEditor(self._login_model.index(row, 2))



class SetPasswordDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        QBtn = QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        self.buttonBox = QtWidgets.QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

        self.layout = QtWidgets.QFormLayout()

        self.password_box_1 = QtWidgets.QLineEdit()
        self.password_box_2 = QtWidgets.QLineEdit()
        self.password_box_1.textChanged.connect(self.comparePasswords)
        self.password_box_2.textChanged.connect(self.comparePasswords)

        self.password_box_1.setEchoMode(QtWidgets.QLineEdit.Password)
        self.password_box_2.setEchoMode(QtWidgets.QLineEdit.Password)

        self.layout.addRow(QtWidgets.QLabel("New Password"), self.password_box_1) 
        self.layout.addRow(QtWidgets.QLabel("Confirm New Password"), self.password_box_2) 

        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

        self.show()

    def comparePasswords(self):
        if self.password_box_1.text() == self.password_box_2.text() and len(self.password_box_1.text())>0:
            self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)


    def getValue(self):
        password = self.password_box_1.text()
        password_verify = self.password_box_2.text()

        if password == password_verify:
            if len(password) > 0:
                return password
        return None



class LoginModel(QtCore.QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self._login_changed_callbacks = [] #list of callbacks to update stuff when login/out

        pw_admin = "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918"
        pw_user = "04f8996da763b7a969b1028ee3007569eaf3a635486ddab211d512c85b9df8fb"

        self._data = [['admin', pw_admin, True, True, True, True, True], ['user', pw_user, True, False, False, True, False]]
        self._horizontal_header_labels = ['User','pw','Run Behaviors', 'Edit Behavior', 'Edit Tool', 'Clear Alerts','Edit Users']

        self._current_user = None
        self._current_user_privileges = None

        #column names
        self.USERNAME       = 0
        self.PASSWORD       = 1
        self.RUN_BEHAVIORS  = 2 
        self.EDIT_BEHAVIOR  = 3 
        self.EDIT_TOOL      = 4 
        self.CLEAR_ALERTS   = 5 
        self.EDIT_USERS     = 6 

        self.PRIVILEGES = [self.RUN_BEHAVIORS, self.EDIT_BEHAVIOR, self.EDIT_TOOL, self.CLEAR_ALERTS, self.EDIT_USERS]


    def data(self, index, role):
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            if index.column() != self.PASSWORD:
                return self._data[index.row()][index.column()]
        return None


    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if type(value) == type(QtCore.QVariant()):
            value = value.toPyObject()
        

        if self.canEditUsers():
            if index.column() in self.PRIVILEGES:
                self._data[index.row()][index.column()] = bool(value)
                print(self._data[index.row()][index.column()])
                return True


        return False






    def flags(self, index):
        if self.canEditUsers():
            if index.column() in self.PRIVILEGES: 
                return QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled

        return QtCore.Qt.ItemIsEnabled

    def rowCount(self, index=QtCore.QModelIndex()):
        return  0 if index.isValid() else len(self._data)

    def columnCount(self, index=QtCore.QModelIndex()):
        return len(self._data[0])
 
    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            if 0 <= section < self.columnCount():
                return self._horizontal_header_labels[section]



    def users(self):
        return [row[self.USERNAME] for row in self._data]

    def usernameByRow(self, row):
        return self._data[row][self.USERNAME]

    def currentUser(self):
        return self._current_user

    def canEditUsers(self):
        if self._current_user_privileges is not None:
            return self._current_user_privileges[self.EDIT_USERS]
        return False

    def canClearAlerts(self):
        if self._current_user_privileges is not None:
            return self._current_user_privileges[self.CLEAR_ALERTS]
        return False

    def setPasswordByRow(self, row, new_password):
        self._data[row][self.PASSWORD] = self.hashPassword(new_password)


    def hashPassword(self, password):
        password = str(password)
        return hashlib.sha256(bytes(password, encoding='utf8')).hexdigest()

    def login(self, user, password):
        hashed_password = self.hashPassword(password)

        for row in self._data:
            if row[self.USERNAME] == user:
                if hashed_password == row[self.PASSWORD]:
                    self._current_user = user
                    self._current_user_privileges = row
                    self.runLoginChangedCallbacks()
                    return True


        self._current_user = None
        self._current_user_privileges = None
        self.runLoginChangedCallbacks()
        return False

    def logout(self):
        self._current_user = None
        self._current_user_privileges = None
        self.runLoginChangedCallbacks()

    
    def runLoginChangedCallbacks(self):
        for callback, privilege in self._login_changed_callbacks:
            if self._current_user_privileges:
                callback(self._current_user_privileges[privilege])
            else:
                callback(False)


    #TODO check the method!
    def addLoginChangedCallback(self, callback, privilege):
        if privilege in self.PRIVILEGES:
            self._login_changed_callbacks.append((callback, privilege))
