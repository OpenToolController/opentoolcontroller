import pytest
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from opentoolcontroller.views.widgets.recipe_variable_table import RecipeVariableTable

@pytest.fixture
def app():
    """Create a Qt Application"""
    return QApplication([])

@pytest.fixture
def table(app):
    """Create a RecipeVariableTable instance"""
    return RecipeVariableTable()

def test_initial_state(table):
    """Test initial state of the table"""
    assert table.table.columnCount() == 4
    assert table.table.rowCount() == 0
    headers = [table.table.horizontalHeaderItem(i).text() for i in range(4)]
    assert headers == ["Variable Name", "Variable Type", "Min", "Max"]

def test_add_variable(table):
    """Test adding a new variable"""
    initial_rows = table.table.rowCount()
    table.addVariable()
    assert table.table.rowCount() == initial_rows + 1
    
    # Check type combo box is added and set to Boolean by default
    type_combo = table.table.cellWidget(initial_rows, 1)
    assert type_combo.currentText() == "Boolean"

def test_remove_variable(table):
    """Test removing a variable"""
    table.addVariable()
    initial_rows = table.table.rowCount()
    
    # Select the row
    table.table.selectRow(0)
    table.removeVariable()
    
    assert table.table.rowCount() == initial_rows - 1

def test_boolean_type_disables_min_max(table):
    """Test that Boolean type disables min/max fields"""
    table.addVariable()
    row = 0
    
    # Get min/max items
    min_item = table.table.item(row, 2)
    max_item = table.table.item(row, 3)
    
    # Check they're disabled for Boolean (default)
    assert not (min_item.flags() & Qt.ItemIsEnabled)
    assert not (max_item.flags() & Qt.ItemIsEnabled)
    
    # Check background color is gray
    assert min_item.background().color().name() == "#f0f0f0"
    assert max_item.background().color().name() == "#f0f0f0"

def test_numeric_type_enables_min_max(table):
    """Test that numeric types enable min/max fields"""
    table.addVariable()
    row = 0
    
    # Change to Float
    type_combo = table.table.cellWidget(row, 1)
    type_combo.setCurrentText("Float")
    
    # Get min/max items
    min_item = table.table.item(row, 2)
    max_item = table.table.item(row, 3)
    
    # Check they're enabled
    assert min_item.flags() & Qt.ItemIsEnabled
    assert max_item.flags() & Qt.ItemIsEnabled
    
    # Check background color is white
    assert min_item.background().color().name() == "#ffffff"
    assert max_item.background().color().name() == "#ffffff"

def test_type_change_preserves_min_max_values(table):
    """Test that changing between numeric types preserves values"""
    table.addVariable()
    row = 0
    
    # Set to Float first
    type_combo = table.table.cellWidget(row, 1)
    type_combo.setCurrentText("Float")
    
    # Set some values
    min_item = table.table.item(row, 2)
    max_item = table.table.item(row, 3)
    min_item.setText("1.5")
    max_item.setText("10.5")
    
    # Change to Integer
    type_combo.setCurrentText("Integer")
    
    # Values should still be there
    assert min_item.text() == "1.5"
    assert max_item.text() == "10.5"
