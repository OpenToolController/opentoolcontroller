from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt

class RecipeVariableTable(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Recipe Variables")
        self.resize(600, 400)  # Set a reasonable default size
        
        # Add model reference
        self._model = None
        self._current_node = None
        
        # Create central widget and layout
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)
        
        # Create table
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Variable Name", "Variable Type", "Min", "Max", "Basic"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        layout.addWidget(self.table)
        
        # Create button widget and layout
        button_widget = QtWidgets.QWidget()
        button_layout = QtWidgets.QHBoxLayout(button_widget)
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add buttons
        add_btn = QtWidgets.QPushButton("Add Variable")
        remove_btn = QtWidgets.QPushButton("Remove Variable")
        add_btn.clicked.connect(self.addVariable)
        remove_btn.clicked.connect(self.removeVariable)
        button_layout.addWidget(add_btn)
        button_layout.addWidget(remove_btn)
        button_layout.addStretch()  # Push buttons to the left
        
        layout.addWidget(button_widget)
        
        # Set up type combo delegate for Variable Type column
        type_delegate = TypeComboDelegate(self.table)
        self.table.setItemDelegateForColumn(1, type_delegate)

        # Set up a delegate with specific numeric editors
        numeric_delegate = QtWidgets.QStyledItemDelegate()

        def create_editor(parent, option, index):
            """Create the appropriate numeric editor."""
            editor = QtWidgets.QDoubleSpinBox(parent)
            editor.setDecimals(2)  # Optional: Adjust decimals for float
            editor.setRange(-1e9, 1e9)  # Optional: Adjust range
            return editor

        numeric_delegate.createEditor = lambda parent, option, index: create_editor(parent, option, index)

        # Correctly set and retrieve data for the editor
        def set_editor_data(editor, index):
            value = index.data(Qt.EditRole)
            if value:
                try:
                    editor.setValue(float(value)) 
                except ValueError:
                    editor.setValue(0)

        def set_model_data(editor, model, index):
            model.setData(index, float(editor.value()), Qt.EditRole)

        numeric_delegate.setEditorData = set_editor_data
        numeric_delegate.setModelData = set_model_data

        # Assign the delegate to columns 2 and 3
        self.table.setItemDelegateForColumn(2, numeric_delegate)
        self.table.setItemDelegateForColumn(3, numeric_delegate)

    def handleTypeChange(self, var_type, row):
        """Handle changes to variable type by updating min/max fields"""
        min_item = self.table.item(row, 2)
        max_item = self.table.item(row, 3)
        
        if not min_item or not max_item:
            return
            
        if var_type == "Boolean":
            # Disable and clear min/max for boolean
            min_item.setFlags(min_item.flags() & ~Qt.ItemIsEnabled)
            max_item.setFlags(max_item.flags() & ~Qt.ItemIsEnabled)
            min_item.setText("")
            max_item.setText("")
            # Set light gray background for disabled cells
            min_item.setBackground(QtGui.QColor(240, 240, 240))
            max_item.setBackground(QtGui.QColor(240, 240, 240))
        else:
            # Enable min/max for numeric types
            min_item.setFlags(min_item.flags() | Qt.ItemIsEnabled | Qt.ItemIsEditable)
            max_item.setFlags(max_item.flags() | Qt.ItemIsEnabled | Qt.ItemIsEditable)
            # Set white background for enabled cells
            min_item.setBackground(QtGui.QColor(255, 255, 255))
            max_item.setBackground(QtGui.QColor(255, 255, 255))

    def addVariable(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Add type combo box
        type_combo = QtWidgets.QComboBox()
        type_combo.addItems(["Float", "Integer", "Boolean"])
        type_combo.currentTextChanged.connect(lambda text, r=row: self.handleTypeChange(text, r))
        self.table.setCellWidget(row, 1, type_combo)
        
        # Add min/max cells
        min_item = QtWidgets.QTableWidgetItem()
        max_item = QtWidgets.QTableWidgetItem()
        self.table.setItem(row, 2, min_item)
        self.table.setItem(row, 3, max_item)
        
        # Add Basic checkbox
        basic_item = QtWidgets.QTableWidgetItem()
        basic_item.setFlags(basic_item.flags() | Qt.ItemIsUserCheckable)
        basic_item.setCheckState(Qt.Unchecked)
        self.table.setItem(row, 4, basic_item)
        
        # Initialize as Boolean (disabled min/max)
        type_combo.setCurrentText("Boolean")

    def removeVariable(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.table.removeRow(current_row)
            self.saveVariables()

    def setModel(self, model, node):
        """Set the model and current node for the table"""
        self._model = model
        self._current_node = node
        # Load existing variables if any
        self.loadVariables()
        
    def loadVariables(self):
        """Load variables from the model"""
        if self._model and self._current_node:
            index = self._model.createIndex(self._current_node.row(), col.RECIPE_VARIABLES, self._current_node)
            variables = self._model.data(index)
            if variables:
                # Clear existing rows
                self.table.setRowCount(0)
                # Add each variable
                for var in variables:
                    row = self.table.rowCount()
                    self.table.insertRow(row)
                    self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(var['name']))
                    type_combo = QtWidgets.QComboBox()
                    type_combo.addItems(["Float", "Integer", "Boolean"])
                    type_combo.setCurrentText(var['type'])
                    type_combo.currentTextChanged.connect(lambda text, r=row: self.handleTypeChange(text, r))
                    self.table.setCellWidget(row, 1, type_combo)
                    self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(str(var.get('min', ''))))
                    self.table.setItem(row, 3, QtWidgets.QTableWidgetItem(str(var.get('max', ''))))
                    basic_item = QtWidgets.QTableWidgetItem()
                    basic_item.setFlags(basic_item.flags() | Qt.ItemIsUserCheckable)
                    basic_item.setCheckState(Qt.Checked if var.get('basic', False) else Qt.Unchecked)
                    self.table.setItem(row, 4, basic_item)

    def saveVariables(self):
        """Save variables back to the model"""
        if self._model and self._current_node:
            variables = []
            for row in range(self.table.rowCount()):
                var = {
                    'name': self.table.item(row, 0).text(),
                    'type': self.table.cellWidget(row, 1).currentText(),
                    'min': self.table.item(row, 2).text() if self.table.item(row, 2).text() else None,
                    'max': self.table.item(row, 3).text() if self.table.item(row, 3).text() else None,
                    'basic': self.table.item(row, 4).checkState() == Qt.Checked
                }
                variables.append(var)
            
            # Update the model with new variables
            index = self._model.createIndex(self._current_node.row(), col.RECIPE_VARIABLES, self._current_node)
            self._model.setData(index, variables)


class TypeComboDelegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QtWidgets.QComboBox(parent)
        editor.addItems(["Float", "Integer", "Boolean"])
        # Connect to parent table's handler
        editor.currentTextChanged.connect(
            lambda text: self.parent().handleTypeChange(text, index.row())
        )
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.EditRole)
        if value:
            editor.setCurrentText(value)

    def setModelData(self, editor, model, index):
        value = editor.currentText()
        model.setData(index, value, Qt.EditRole)
        # Ensure min/max fields are updated when type changes via delegate
        self.parent().handleTypeChange(value, index.row())

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)
