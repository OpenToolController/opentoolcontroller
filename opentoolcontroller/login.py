# -*- coding: utf-8 -*-
"""
Login system module for OpenToolController.
Handles user authentication, session management and access control.
"""
from PyQt5 import QtWidgets, QtCore, QtGui, uic
from datetime import datetime, timedelta
from enum import IntEnum
from typing import Optional, List, Tuple, Callable, Dict
import hashlib
import re
from .config import auth_config

login_base, login_form = uic.loadUiType("opentoolcontroller/views/Login.ui")

class UserPrivilege(IntEnum):
    """Enumeration of user privilege types"""
    RUN_BEHAVIORS = 0
    EDIT_BEHAVIOR = 1
    EDIT_TOOL = 2
    CLEAR_ALERTS = 3
    EDIT_USERS = 4

class SessionManager:
    """Handles user session management including timeouts"""
    def __init__(self, timeout_minutes: int = auth_config.SESSION_TIMEOUT_MINUTES):
        self.timeout_minutes = timeout_minutes
        self.last_activity: Optional[datetime] = None
        self.active = False
    
    def start_session(self) -> None:
        """Start a new user session"""
        self.last_activity = datetime.now()
        self.active = True
    
    def end_session(self) -> None:
        """End the current session"""
        self.last_activity = None
        self.active = False
    
    def update_activity(self) -> None:
        """Update the last activity timestamp"""
        self.last_activity = datetime.now()
    
    def is_session_valid(self) -> bool:
        """Check if the current session is still valid"""
        if not self.active or not self.last_activity:
            return False
        
        time_elapsed = datetime.now() - self.last_activity
        return time_elapsed < timedelta(minutes=self.timeout_minutes)

class LoginView(login_base, login_form):
    """Main login interface view"""
    def __init__(self, login_model):
        super(login_base, self).__init__()
        self.setupUi(self)

        self._login_model = login_model
        self.ui_login_table.setModel(self._login_model)
        self.ui_current_user.setText(self._login_model.currentUser())
        
        # Setup UI connections
        self.ui_login.clicked.connect(self.login)
        self.ui_logout.clicked.connect(self.logout)
        self.ui_password.returnPressed.connect(self.login)
        self.ui_password.setMaxLength(50)
        
        # Setup session timeout timer
        self._activity_timer = QtCore.QTimer(self)
        self._activity_timer.timeout.connect(self.check_session_timeout)
        self._activity_timer.start(60000)  # Check every minute
        
        self.setPasswordEditButtons()
        
    def check_session_timeout(self):
        """Check if session has timed out and logout if needed"""
        if self._login_model.is_session_expired():
            self.logout()
            QtWidgets.QMessageBox.warning(
                self, 
                "Session Expired",
                "Your session has expired due to inactivity. Please login again."
            )

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
    """Model for handling user authentication and privileges"""
    
    # Column definitions
    USERNAME = 0
    PASSWORD = 1
    RUN_BEHAVIORS = 2
    EDIT_BEHAVIOR = 3
    EDIT_TOOL = 4
    CLEAR_ALERTS = 5
    EDIT_USERS = 6

    PRIVILEGES = [RUN_BEHAVIORS, EDIT_BEHAVIOR, EDIT_TOOL, CLEAR_ALERTS, EDIT_USERS]
    
    def __init__(self):
        super().__init__()
        self._login_changed_callbacks: List[Tuple[Callable, int]] = []
        
        # Initialize session management
        self._session = SessionManager()
        
        # Load user data from config
        self._data = self._load_user_data()
        self._horizontal_header_labels = [
            'User', 'Password', 'Run Behaviors', 'Edit Behavior',
            'Edit Tool', 'Clear Alerts', 'Edit Users'
        ]
        
        self._current_user = None
        self._current_user_privileges = None
        
    def _load_user_data(self) -> List[List]:
        """Convert config data to model format"""
        data = []
        for username, info in auth_config.DEFAULT_USERS.items():
            privileges = info['privileges']
            data.append([
                username,
                info['password_hash'],
                privileges['run_behaviors'],
                privileges['edit_behavior'],
                privileges['edit_tool'],
                privileges['clear_alerts'],
                privileges['edit_users']
            ])
        return data


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


    def validate_password(self, password: str) -> Tuple[bool, str]:
        """Validate password meets requirements
        
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        if len(password) < auth_config.MIN_PASSWORD_LENGTH:
            return False, f"Password must be at least {auth_config.MIN_PASSWORD_LENGTH} characters"
            
        if auth_config.REQUIRE_SPECIAL_CHARS and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain at least one special character"
            
        if auth_config.REQUIRE_NUMBERS and not re.search(r'\d', password):
            return False, "Password must contain at least one number"
            
        return True, ""

    def hashPassword(self, password: str) -> str:
        """Hash password using SHA-256"""
        password = str(password)
        return hashlib.sha256(bytes(password, encoding='utf8')).hexdigest()

    def login(self, user: str, password: str) -> bool:
        """Attempt to log in a user
        
        Returns:
            bool: True if login successful
        """
        hashed_password = self.hashPassword(password)

        for row in self._data:
            if row[self.USERNAME] == user and hashed_password == row[self.PASSWORD]:
                self._current_user = user
                self._current_user_privileges = row
                self._session.start_session()
                self.runLoginChangedCallbacks()
                return True

        self._current_user = None
        self._current_user_privileges = None
        self._session.end_session()
        self.runLoginChangedCallbacks()
        return False
        
    def is_session_expired(self) -> bool:
        """Check if current session has expired"""
        if self._current_user is None:
            return False
        return not self._session.is_session_valid()

    def logout(self):
        self._current_user = None
        self._current_user_privileges = None
        self.runLoginChangedCallbacks()

    
    def runLoginChangedCallbacks(self):
        for callback, privilege in self._login_changed_callbacks:
            if self._current_user_privileges:
                callback(self._current_user_privileges[privilege])
            else:
                callback(True) #TODO for testing other stuff w/out logging in
                #callback(False)


    #TODO check the method!
    def addLoginChangedCallback(self, callback, privilege):
        if privilege in self.PRIVILEGES:
            self._login_changed_callbacks.append((callback, privilege))
