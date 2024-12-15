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
import os
import json

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
    def __init__(self, timeout_minutes: int = 30):
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
        self.ui_current_user.setText('none')
        self.ui_current_user.setStyleSheet("font: italic")
        
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
        success = self._login_model.login(username, password)
        if success:
            self.setCurrentUserText()
            self.setPasswordEditButtons()
        return success


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
    TIMEOUT = 7

    PRIVILEGES = [RUN_BEHAVIORS, EDIT_BEHAVIOR, EDIT_TOOL, CLEAR_ALERTS, EDIT_USERS]
    EDITABLE_COLUMNS = PRIVILEGES + [TIMEOUT]
    
    def __init__(self, config_path=None):
        super().__init__()
        self._login_changed_callbacks: List[Tuple[Callable, int]] = []
        self._config_path = config_path
        
        # Load the config from JSON
        with open(self._config_path, 'r') as f:
            self.auth_config = json.load(f)
        
        # Initialize session management with default timeout
        self._session = SessionManager(self.auth_config['password_policy']['session_timeout_minutes'])
        
        # Load user data from config
        self._data = self._load_user_data()
        self._horizontal_header_labels = [
            'User', 'Password', 'Run Behaviors', 'Edit Behavior',
            'Edit Tool', 'Clear Alerts', 'Edit Users', 'Timeout (min)'
        ]
        
        self._current_user = None
        self._current_user_privileges = None

        # Install event filter to track user activity if QApplication exists
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
        
    def _load_user_data(self) -> List[List]:
        """Convert config data to model format"""
        data = []
        for username, info in self.auth_config['users'].items():
            data.append([
                username,
                info['password_hash'],
                info['run_behaviors'],
                info['edit_behavior'], 
                info['edit_tool'],
                info['clear_alerts'],
                info['edit_users'],
                info.get('timeout_minutes', self.auth_config['password_policy']['session_timeout_minutes'])
            ])
        return data


    def data(self, index, role):
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            if index.column() != self.PASSWORD:
                return self._data[index.row()][index.column()]
        return None


    def _update_config_privileges(self, username: str, privileges: dict, timeout: int) -> None:
        """Update user privileges in auth_config.json"""
        config_path = os.path.join(os.path.dirname(__file__), self._config_path)
        
        # Read current config
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Update the user data
        config['users'][username].update({
            "password_hash": next((row[self.PASSWORD] for row in self._data if row[self.USERNAME] == username), ""),
            "run_behaviors": privileges["run_behaviors"],
            "edit_behavior": privileges["edit_behavior"],
            "edit_tool": privileges["edit_tool"],
            "clear_alerts": privileges["clear_alerts"],
            "edit_users": privileges["edit_users"],
            "timeout_minutes": timeout
        })
        
        # Write the updated config back to file
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
            
        # Update our in-memory config to match
        self.auth_config = config

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if type(value) == type(QtCore.QVariant()):
            value = value.toPyObject()

        if self.canEditUsers():
            row = index.row()
            username = self._data[row][self.USERNAME]
            
            if index.column() in self.PRIVILEGES:
                self._data[row][index.column()] = bool(value)
                
                # Update config file with new privileges
                privileges = {
                    "run_behaviors": self._data[row][self.RUN_BEHAVIORS],
                    "edit_behavior": self._data[row][self.EDIT_BEHAVIOR],
                    "edit_tool": self._data[row][self.EDIT_TOOL],
                    "clear_alerts": self._data[row][self.CLEAR_ALERTS],
                    "edit_users": self._data[row][self.EDIT_USERS]
                }
                self._update_config_privileges(username, privileges, self._data[row][self.TIMEOUT])
                return True
                
            elif index.column() == self.TIMEOUT:
                try:
                    timeout = int(value)
                    if timeout > 0:
                        self._data[row][index.column()] = timeout
                        if self._current_user == username:
                            self._session.timeout_minutes = timeout
                            
                        # Update config file with new timeout
                        privileges = {
                            "run_behaviors": self._data[row][self.RUN_BEHAVIORS],
                            "edit_behavior": self._data[row][self.EDIT_BEHAVIOR],
                            "edit_tool": self._data[row][self.EDIT_TOOL],
                            "clear_alerts": self._data[row][self.CLEAR_ALERTS],
                            "edit_users": self._data[row][self.EDIT_USERS]
                        }
                        self._update_config_privileges(username, privileges, timeout)
                        return True
                except (ValueError, TypeError):
                    pass


        return False






    def flags(self, index):
        if self.canEditUsers():
            if index.column() in self.EDITABLE_COLUMNS:
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
        """Update password hash in both model and config file"""
        password_hash = self.hashPassword(new_password)
        username = self._data[row][self.USERNAME]
        
        # Update model
        self._data[row][self.PASSWORD] = password_hash
        
        # Update config file
        config_path = os.path.join(os.path.dirname(__file__), self._config_path)
        
        # Update the password hash in our loaded config
        self.auth_config['users'][username]['password_hash'] = password_hash
        
        # Write the updated config back to file
        with open(config_path, 'w') as f:
            json.dump(self.auth_config, f, indent=4)


    def validate_password(self, password: str) -> Tuple[bool, str]:
        """Validate password meets requirements
        
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        if len(password) < self.auth_config['password_policy']['min_length']:
            return False, f"Password length must be at least {self.auth_config['password_policy']['min_length']} characters"
            
        if self.auth_config['password_policy']['require_special_chars'] and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain at least one special character"
            
        if self.auth_config['password_policy']['require_numbers'] and not re.search(r'\d', password):
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
        # Always logout current user first
        self.logout()
            
        hashed_password = self.hashPassword(password)

        for row in self._data:
            if row[self.USERNAME] == user and hashed_password == row[self.PASSWORD]:
                self._current_user = user
                self._current_user_privileges = row
                self._session.timeout_minutes = row[self.TIMEOUT]  # Set timeout from user data
                self._session.start_session()
                self.runLoginChangedCallbacks()
                return True

        self._current_user = None
        self._current_user_privileges = None
        self._session.end_session()
        self.runLoginChangedCallbacks()
        return False
        
    def eventFilter(self, obj, event) -> bool:
        """Filter application events to track user activity"""
        if self._current_user is not None:
            # Update activity on mouse or keyboard events
            if event.type() in (QtCore.QEvent.MouseButtonPress, 
                              QtCore.QEvent.KeyPress):
                self._session.update_activity()
        return False

    def is_session_expired(self) -> bool:
        """Check if current session has expired"""
        if self._current_user is None:
            return False
        return not self._session.is_session_valid()

    def logout(self):
        self._current_user = None
        self._current_user_privileges = None
        self._session.end_session()
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
