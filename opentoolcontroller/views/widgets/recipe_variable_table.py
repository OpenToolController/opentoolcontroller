from PyQt5 import QtCore, QtGui, QtWidgets
from opentoolcontroller.strings import col
from PyQt5.QtCore import Qt

class RecipeVariableTable(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Recipe Variables")
        self.resize(1000, 400)  # Further increased width to show all columns including List Values
        
        # Add model reference
        self._model = None
        self._current_node = None
        
        # Create central widget and layout
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)
        
        # Create table
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["Variable Name", "Variable Type", "Min", "Max", "List Values", "Basic", "Time Varying"])
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
        apply_btn = QtWidgets.QPushButton("Apply")
        add_btn.clicked.connect(self.addVariable)
        remove_btn.clicked.connect(self.removeVariable)
        apply_btn.clicked.connect(self.saveVariables)
        button_layout.addWidget(add_btn)
        button_layout.addWidget(remove_btn)
        button_layout.addWidget(apply_btn)
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
        list_item = self.table.item(row, 4)
        
        if not min_item or not max_item:
            return
            
        if var_type in ["Boolean", "List"]:
            # Disable and clear min/max for boolean and list types
            min_item.setFlags(min_item.flags() & ~Qt.ItemIsEnabled)
            max_item.setFlags(max_item.flags() & ~Qt.ItemIsEnabled)
            min_item.setText("")
            max_item.setText("")
            # Set light gray background for disabled cells
            min_item.setBackground(QtGui.QColor(240, 240, 240))
            max_item.setBackground(QtGui.QColor(240, 240, 240))
            
            # Enable/disable list values field
            if var_type == "List":
                if not list_item:
                    list_item = QtWidgets.QTableWidgetItem("")
                    self.table.setItem(row, 4, list_item)
                list_item.setFlags(list_item.flags() | Qt.ItemIsEnabled | Qt.ItemIsEditable)
                list_item.setBackground(QtGui.QColor(255, 255, 255))
            else:
                if list_item:
                    list_item.setFlags(list_item.flags() & ~Qt.ItemIsEnabled)
                    list_item.setText("")
                    list_item.setBackground(QtGui.QColor(240, 240, 240))
        else:
            # Enable min/max for numeric types
            min_item.setFlags(min_item.flags() | Qt.ItemIsEnabled | Qt.ItemIsEditable)
            max_item.setFlags(max_item.flags() | Qt.ItemIsEnabled | Qt.ItemIsEditable)
            # Set white background for enabled cells
            min_item.setBackground(QtGui.QColor(255, 255, 255))
            max_item.setBackground(QtGui.QColor(255, 255, 255))
            
            # Disable list values field
            if list_item:
                list_item.setFlags(list_item.flags() & ~Qt.ItemIsEnabled)
                list_item.setText("")
                list_item.setBackground(QtGui.QColor(240, 240, 240))

    def addVariable(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Add type combo box
        type_combo = QtWidgets.QComboBox()
        type_combo.addItems(["Float", "Integer", "Boolean", "List"])
        type_combo.currentTextChanged.connect(lambda text, r=row: self.handleTypeChange(text, r))
        self.table.setCellWidget(row, 1, type_combo)
        
        # Add min/max cells
        min_item = QtWidgets.QTableWidgetItem()
        max_item = QtWidgets.QTableWidgetItem()
        self.table.setItem(row, 2, min_item)
        self.table.setItem(row, 3, max_item)
        
        # Add List Values cell
        list_values_item = QtWidgets.QTableWidgetItem()
        self.table.setItem(row, 4, list_values_item)
        
        # Add Basic checkbox
        basic_item = QtWidgets.QTableWidgetItem()
        basic_item.setFlags(basic_item.flags() | Qt.ItemIsUserCheckable)
        basic_item.setCheckState(Qt.Unchecked)
        self.table.setItem(row, 5, basic_item)
        
        # Add Time Varying checkbox
        time_varying_item = QtWidgets.QTableWidgetItem()
        time_varying_item.setFlags(time_varying_item.flags() | Qt.ItemIsUserCheckable)
        time_varying_item.setCheckState(Qt.Unchecked)
        self.table.setItem(row, 6, time_varying_item)
        
        # Initialize as Boolean (disabled min/max)
        type_combo.setCurrentText("Boolean")

    def removeVariable(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.table.removeRow(current_row)

    def setModel(self, model, node):
        """Set the model and current index for the table"""
        self._model = model
        self._current_node = node
        self.loadVariables()
        
    def loadVariables(self):
        """Load variables from the model"""
        if self._model and self._current_node:
            index = self._model.createIndex(self._current_node.row(), col.RECIPE_VARIABLES, self._current_node)
            variables = self._model.data(index, QtCore.Qt.EditRole)
        
            self.setWindowTitle(self._current_node.name + " Recipe Variables")
            if variables:
                # Clear existing rows
                self.table.setRowCount(0)
                # Add each variable
                for var in variables:
                    row = self.table.rowCount()
                    self.table.insertRow(row)
                    self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(var['name']))
                    type_combo = QtWidgets.QComboBox()
                    type_combo.addItems(["Float", "Integer", "Boolean", "List"])
                    type_combo.setCurrentText(var['type'])
                    type_combo.currentTextChanged.connect(lambda text, r=row: self.handleTypeChange(text, r))
                    self.table.setCellWidget(row, 1, type_combo)
                    self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(str(var.get('min', ''))))
                    self.table.setItem(row, 3, QtWidgets.QTableWidgetItem(str(var.get('max', ''))))

                    # Add list values
                    list_values = var.get('list_values', '')
                    if isinstance(list_values, list):
                        list_values = ','.join(list_values)
                    self.table.setItem(row, 4, QtWidgets.QTableWidgetItem(str(list_values)))
                    

                    basic_item = QtWidgets.QTableWidgetItem()
                    basic_item.setFlags(basic_item.flags() | Qt.ItemIsUserCheckable)
                    basic_item.setCheckState(Qt.Checked if var.get('basic', False) else Qt.Unchecked)
                    self.table.setItem(row, 5, basic_item)
                    
                    time_varying_item = QtWidgets.QTableWidgetItem()
                    time_varying_item.setFlags(time_varying_item.flags() | Qt.ItemIsUserCheckable)
                    time_varying_item.setCheckState(Qt.Checked if var.get('time_varying', False) else Qt.Unchecked)
                    self.table.setItem(row, 6, time_varying_item)
                    
                # After loading all variables, resize the name column
                self.table.resizeColumnToContents(0)  # Column 0 is Variable Name

    def saveVariables(self):
        """Save variables back to the model"""
        if self._model and self._current_node:
            variables = []
            for row in range(self.table.rowCount()):
                try:
                    # Get name (default to empty string if cell is None)
                    name_item = self.table.item(row, 0)
                    name = name_item.text() if name_item else ""
                    
                    # Get type from combo box
                    type_widget = self.table.cellWidget(row, 1)
                    var_type = type_widget.currentText() if type_widget else "Float"
                    
                    # Get min/max values (handle empty or invalid cells)
                    min_item = self.table.item(row, 2)
                    max_item = self.table.item(row, 3)
                    
                    try:
                        min_val = float(min_item.text()) if min_item and min_item.text() else None
                    except ValueError:
                        min_val = None
                        
                    try:
                        max_val = float(max_item.text()) if max_item and max_item.text() else None
                    except ValueError:
                        max_val = None
                    
                    # Get list values
                    list_item = self.table.item(row, 4)
                    list_values = []
                    if list_item and list_item.text():
                        list_values = [x.strip() for x in list_item.text().split(',')]

                    # Get basic checkbox state (default to unchecked if cell is None)
                    basic_item = self.table.item(row, 5)
                    basic = basic_item.checkState() == Qt.Checked if basic_item else False
                    
                    # Get time varying checkbox state
                    time_varying_item = self.table.item(row, 6)
                    time_varying = time_varying_item.checkState() == Qt.Checked if time_varying_item else False
                    list_values = []
                    if list_item and list_item.text():
                        list_values = [x.strip() for x in list_item.text().split(',')]
                    
                    var = {
                        'name': name,
                        'type': var_type,
                        'min': min_val,
                        'max': max_val,
                        'list_values': list_values if var_type == "List" else [],
                        'basic': basic,
                        'time_varying': time_varying
                    }
                    variables.append(var)
                    
                except Exception as e:
                    print(f"Error saving row {row}: {str(e)}")
                    continue
            
            # Update the model with new variables
            index = self._model.createIndex(self._current_node.row(), col.RECIPE_VARIABLES, self._current_node)
            self._model.setData(index, variables)


class TypeComboDelegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QtWidgets.QComboBox(parent)
        editor.addItems(["Float", "Integer", "Boolean", "List"])
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
