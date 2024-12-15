import pytest
from PyQt5 import QtCore, QtWidgets
from opentoolcontroller.login import LoginModel, LoginView, SessionManager
import hashlib
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import os

@pytest.fixture
def app(qtbot):
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

@pytest.fixture
def login_model(qtbot, mock_config_file):
    return LoginModel(config_path=str(mock_config_file))

@pytest.fixture
def login_view(qtbot, login_model):
    view = LoginView(login_model)
    qtbot.addWidget(view)
    return view

@pytest.fixture
def mock_config_file(tmp_path):
    config_content = """
from typing import Dict, List

DEFAULT_USERS: Dict[str, List] = {
    "admin": {
        "password_hash": "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918",
        "run_behaviors": True,
        "edit_behavior": True,
        "edit_tool": True,
        "clear_alerts": True,
        "edit_users": True,
        "timeout_minutes": 10},
    "user": {
        "password_hash": "04f8996da763b7a969b1028ee3007569eaf3a635486ddab211d512c85b9df8fb",
        "run_behaviors": True,
        "edit_behavior": False,
        "edit_tool": False,
        "clear_alerts": True,
        "edit_users": False,
        "timeout_minutes": 111}
}

MIN_PASSWORD_LENGTH = 8
REQUIRE_SPECIAL_CHARS = True
REQUIRE_NUMBERS = True
SESSION_TIMEOUT_MINUTES = 30
"""
    config_file = tmp_path / "auth_config.py"
    config_file.write_text(config_content)
    return config_file

class TestSessionManager:
    def test_init_default_timeout(self):
        session = SessionManager()
        assert session.timeout_minutes == 30
        assert session.last_activity is None
        assert not session.active

    def test_custom_timeout(self):
        session = SessionManager(timeout_minutes=45)
        assert session.timeout_minutes == 45

    def test_session_start_end(self):
        session = SessionManager()
        session.start_session()
        assert session.active
        assert session.last_activity is not None
        
        session.end_session()
        assert not session.active
        assert session.last_activity is None

    def test_session_validity(self):
        session = SessionManager(timeout_minutes=1)
        assert not session.is_session_valid()
        
        session.start_session()
        assert session.is_session_valid()
        
        # Test timeout
        with patch('opentoolcontroller.login.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime.now() + timedelta(minutes=2)
            assert not session.is_session_valid()

class TestLoginModel:
    def test_init(self, mock_config_file):
        model = LoginModel(config_path=str(mock_config_file))
        assert model.rowCount() > 0
        assert model.columnCount() == 8  # All columns present
        assert model._current_user is None
        assert model._current_user_privileges is None

    def test_login_success(self, mock_config_file):
        model = LoginModel(config_path=str(mock_config_file))
        assert model.login("admin", "admin")
        assert model.currentUser() == "admin"
        assert model._session.active

    def test_login_failure(self, mock_config_file):
        model = LoginModel(config_path=str(mock_config_file))
        assert not model.login("admin", "wrong_password")
        assert model.currentUser() is None
        assert not model._session.active

    def test_login_nonexistent_user(self, mock_config_file):
        model = LoginModel(config_path=str(mock_config_file))
        assert not model.login("nonexistent", "password")
        assert model.currentUser() is None

    def test_logout(self, mock_config_file):
        model = LoginModel(config_path=str(mock_config_file))
        model.login("admin", "admin")
        model.logout()
        assert model.currentUser() is None
        assert not model._session.active

    def test_password_validation(self, mock_config_file):
        model = LoginModel(config_path=str(mock_config_file))
        # Test minimum length
        valid, msg = model.validate_password("short")
        assert not valid
        assert "length" in msg.lower()

        # Test special characters
        valid, msg = model.validate_password("password123")
        assert not valid
        assert "special character" in msg.lower()

        # Test numbers requirement
        valid, msg = model.validate_password("password@#$")
        assert not valid
        assert "number" in msg.lower()

        # Test valid password
        valid, msg = model.validate_password("Password123!")
        assert valid
        assert msg == ""

    def test_password_hash(self, mock_config_file):
        model = LoginModel(config_path=str(mock_config_file))
        password = "testpass123!"
        expected_hash = hashlib.sha256(bytes(password, encoding='utf8')).hexdigest()
        assert model.hashPassword(password) == expected_hash

    def test_privilege_checks(self, mock_config_file):
        model = LoginModel(config_path=str(mock_config_file))
        # Test before login
        assert not model.canEditUsers()
        assert not model.canClearAlerts()

        # Test after admin login
        model.login("admin", "admin")
        assert model.canEditUsers()
        assert model.canClearAlerts()

        # Test after regular user login
        model.login("user", "user")
        assert not model.canEditUsers()
        assert model.canClearAlerts()

    def test_session_timeout(self, mock_config_file):
        model = LoginModel(config_path=str(mock_config_file))
        model.login("admin", "admin")
        assert not model.is_session_expired()
        
        # Force session timeout
        model._session.timeout_minutes = 0
        assert model.is_session_expired()

    def test_callback_registration(self, mock_config_file):
        model = LoginModel(config_path=str(mock_config_file))
        callback_called = False
        callback_value = None
        
        def test_callback(value):
            nonlocal callback_called, callback_value
            callback_called = True
            callback_value = value
        
        model.addLoginChangedCallback(test_callback, model.RUN_BEHAVIORS)
        model.login("admin", "admin")
        assert callback_called
        assert callback_value is True

    def test_event_filter(self, mock_config_file):
        model = LoginModel(config_path=str(mock_config_file))
        model.login("admin", "admin")
        
        # Create mock event
        mock_event = MagicMock()
        mock_event.type.return_value = QtCore.QEvent.MouseButtonPress
        
        # Test event filtering
        model.eventFilter(None, mock_event)
        assert model._session.last_activity is not None

    def test_concurrent_access(self, mock_config_file):
        model = LoginModel(config_path=str(mock_config_file))
        
        # Simulate concurrent login attempts
        assert model.login("admin", "admin")
        assert not model.login("user", "user")  # Should fail while admin is logged in
        
        model.logout()
        assert model.login("user", "user")  # Should succeed after logout

class TestLoginView:
    def test_init(self, login_view):
        assert login_view.ui_username is not None
        assert login_view.ui_password is not None
        assert login_view.ui_login is not None
        assert login_view.ui_logout is not None

    def test_login_logout_buttons(self, qtbot, login_view):
        # Test login with correct credentials
        login_view.ui_username.setText("admin")
        login_view.ui_password.setText("admin")
        qtbot.mouseClick(login_view.ui_login, QtCore.Qt.LeftButton)
        assert login_view._login_model.currentUser() == "admin"

        # Test logout
        qtbot.mouseClick(login_view.ui_logout, QtCore.Qt.LeftButton)
        assert login_view._login_model.currentUser() is None

    def test_password_field_clear(self, qtbot, login_view):
        login_view.ui_password.setText("testpass")
        login_view.ui_username.setText("admin")
        qtbot.mouseClick(login_view.ui_login, QtCore.Qt.LeftButton)
        assert login_view.ui_password.text() == ""

    def test_current_user_display(self, qtbot, login_view):
        # Test display before login
        assert login_view.ui_current_user.text().lower() == "none"
        assert "italic" in login_view.ui_current_user.styleSheet().lower()

        # Test display after login
        login_view.ui_username.setText("admin")
        login_view.ui_password.setText("admin")
        qtbot.mouseClick(login_view.ui_login, QtCore.Qt.LeftButton)
        assert login_view.ui_current_user.text() == "admin"
        assert "bold" in login_view.ui_current_user.styleSheet().lower()

    def test_password_edit_buttons(self, qtbot, login_view):
        # Test as non-admin
        assert isinstance(
            login_view.ui_login_table.indexWidget(
                login_view._login_model.index(0, 1)
            ),
            QtWidgets.QLabel
        )
        
        # Login as admin
        login_view.ui_username.setText("admin")
        login_view.ui_password.setText("admin")
        qtbot.mouseClick(login_view.ui_login, QtCore.Qt.LeftButton)
        
        # Verify password edit buttons are present for admin
        assert isinstance(
            login_view.ui_login_table.indexWidget(
                login_view._login_model.index(0, 1)
            ),
            QtWidgets.QPushButton
        )

    def test_session_timeout_check(self, qtbot, login_view):
        # Login
        login_view.ui_username.setText("admin")
        login_view.ui_password.setText("admin")
        qtbot.mouseClick(login_view.ui_login, QtCore.Qt.LeftButton)
        
        # Force session timeout
        login_view._login_model._session.timeout_minutes = 0
        
        # Trigger timeout check
        login_view.check_session_timeout()
        
        # Verify user was logged out
        assert login_view._login_model.currentUser() is None
        assert login_view.ui_current_user.text().lower() == "none"

    def test_set_password_dialog(self, qtbot, login_view):
        # Login as admin
        login_view.ui_username.setText("admin")
        login_view.ui_password.setText("admin")
        qtbot.mouseClick(login_view.ui_login, QtCore.Qt.LeftButton)
        
        # Get password button for first user
        pw_button = login_view.ui_login_table.indexWidget(
            login_view._login_model.index(0, 1)
        )
        
        # Click password button (this will open dialog)
        with patch('PyQt5.QtWidgets.QDialog.exec_', return_value=QtWidgets.QDialog.Accepted):
            qtbot.mouseClick(pw_button, QtCore.Qt.LeftButton)
