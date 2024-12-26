# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtGui, uic, QtWidgets
import os

from opentoolcontroller.views.widgets.tool_tree_view import ToolTreeView
from opentoolcontroller.tool_model import LeafFilterProxyModel
from opentoolcontroller.views.widgets.behavior_editor_view import BTEditorWindow, BTEditor
from opentoolcontroller.strings import col, typ, defaults
from opentoolcontroller.views.widgets.recipe_variable_table import RecipeVariableTable



recipe_editor_base, recipe_editor_form = uic.loadUiType("opentoolcontroller/views/RecipeEditor.ui")



class RecipeEditor(recipe_editor_base, recipe_editor_form):
    def __init__(self, parent=None):
        super(recipe_editor_base, self).__init__(parent)
        self.setupUi(self)

        # Setup static parameters table
        self.ui_static_parameters.setColumnCount(2)
        self.ui_static_parameters.setHorizontalHeaderLabels(["Parameter", "Value"])
        header = self.ui_static_parameters.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Interactive)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Interactive)

        # Setup dynamic parameters table
        self.ui_dynamic_parameters.setColumnCount(2)
        self.ui_dynamic_parameters.setHorizontalHeaderLabels(["Parameter", "Value"])
        header = self.ui_dynamic_parameters.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Interactive)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Interactive)

        self._settings = QtCore.QSettings('OpenToolController', 'test1')
        geometry = self._settings.value('recipe_editor_geometry', bytes('', 'utf-8'))
        state = self._settings.value('recipe_editor_state', bytes('', 'utf-8'))
        splitter_state = self._settings.value('recipe_editor_splitter_state', bytes('', 'utf-8'))
        splitter_2_state = self._settings.value('recipe_editor_splitter_2_state', bytes('', 'utf-8'))

        self.restoreGeometry(geometry)
        self.restoreState(state)
        self.ui_splitter.restoreState(splitter_state)
        self.ui_splitter_2.restoreState(splitter_2_state)
        self.enableEditRecipe(False)


    #INPUTS: QModelIndex, QModelIndex
    def setSelection(self, current, old):
        model = current.model()

        if hasattr(model, 'mapToSource'):
            current_index = model.mapToSource(current)
        else:
            current_index = current

        node = current_index.internalPointer()
        
        # Clear existing rows in both parameters tables
        self.ui_static_parameters.setRowCount(0)
        self.ui_dynamic_parameters.setRowCount(0)
        
        # Get recipe variables from node
        recipe_vars = node.data(col.RECIPE_VARIABLES)
        if recipe_vars:
            # Filter for static and dynamic variables
            static_vars = [var for var in recipe_vars if not var.get('dynamic', False)]
            dynamic_vars = [var for var in recipe_vars if var.get('dynamic', False)]
            
            # Handle static variables
            self.ui_static_parameters.setRowCount(len(static_vars))
            for row, var in enumerate(static_vars):
                # Set name in first column (read-only)
                name_item = QtWidgets.QTableWidgetItem(var.get('name', ''))
                name_item.setFlags(name_item.flags() & ~QtCore.Qt.ItemIsEditable)
                self.ui_static_parameters.setItem(row, 0, name_item)
                
                # Create appropriate editor for second column based on type
                var_type = var.get('type', '')
                
                if var_type == 'Float':
                    editor = QtWidgets.QDoubleSpinBox(self.ui_static_parameters)
                    editor.setMinimum(float(var.get('min', -999999)))
                    editor.setMaximum(float(var.get('max', 999999)))
                    editor.setValue(float(var.get('value', 0)))
                    self.ui_static_parameters.setCellWidget(row, 1, editor)
                    
                elif var_type == 'Integer':
                    editor = QtWidgets.QSpinBox(self.ui_static_parameters)
                    editor.setMinimum(int(var.get('min', -999999)))
                    editor.setMaximum(int(var.get('max', 999999)))
                    editor.setValue(int(var.get('value', 0)))
                    self.ui_static_parameters.setCellWidget(row, 1, editor)
                    
                elif var_type == 'Boolean':
                    editor = QtWidgets.QCheckBox(self.ui_static_parameters)
                    editor.setChecked(var.get('value', False))
                    self.ui_static_parameters.setCellWidget(row, 1, editor)
                    
                elif var_type == 'List':
                    editor = QtWidgets.QComboBox(self.ui_static_parameters)
                    list_values = var.get('list_values', [])
                    # Handle both string and list cases
                    if isinstance(list_values, str):
                        list_values = [x.strip() for x in list_values.split(',') if x.strip()]
                    elif isinstance(list_values, list):
                        list_values = [str(x).strip() for x in list_values if str(x).strip()]
                    editor.addItems(list_values)
                    current_value = var.get('value', '')
                    index = editor.findText(str(current_value))
                    if index >= 0:
                        editor.setCurrentIndex(index)
                    self.ui_static_parameters.setCellWidget(row, 1, editor)
            
            # After populating data, resize first column to content
            self.ui_static_parameters.resizeColumnToContents(0)

            # Handle dynamic variables
            self.ui_dynamic_parameters.setRowCount(len(dynamic_vars))
            for row, var in enumerate(dynamic_vars):
                # Set name in first column (read-only)
                name_item = QtWidgets.QTableWidgetItem(var.get('name', ''))
                name_item.setFlags(name_item.flags() & ~QtCore.Qt.ItemIsEditable)
                self.ui_dynamic_parameters.setItem(row, 0, name_item)
                
                # Create appropriate editor for second column based on type
                var_type = var.get('type', '')
                
                if var_type == 'Float':
                    editor = QtWidgets.QDoubleSpinBox(self.ui_dynamic_parameters)
                    editor.setMinimum(float(var.get('min', -999999)))
                    editor.setMaximum(float(var.get('max', 999999)))
                    editor.setValue(float(var.get('value', 0)))
                    self.ui_dynamic_parameters.setCellWidget(row, 1, editor)
                    
                elif var_type == 'Integer':
                    editor = QtWidgets.QSpinBox(self.ui_dynamic_parameters)
                    editor.setMinimum(int(var.get('min', -999999)))
                    editor.setMaximum(int(var.get('max', 999999)))
                    editor.setValue(int(var.get('value', 0)))
                    self.ui_dynamic_parameters.setCellWidget(row, 1, editor)
                    
                elif var_type == 'Boolean':
                    editor = QtWidgets.QCheckBox(self.ui_dynamic_parameters)
                    editor.setChecked(var.get('value', False))
                    self.ui_dynamic_parameters.setCellWidget(row, 1, editor)
                    
                elif var_type == 'List':
                    editor = QtWidgets.QComboBox(self.ui_dynamic_parameters)
                    list_values = var.get('list_values', [])
                    # Handle both string and list cases
                    if isinstance(list_values, str):
                        list_values = [x.strip() for x in list_values.split(',') if x.strip()]
                    elif isinstance(list_values, list):
                        list_values = [str(x).strip() for x in list_values if str(x).strip()]
                    editor.addItems(list_values)
                    current_value = var.get('value', '')
                    index = editor.findText(str(current_value))
                    if index >= 0:
                        editor.setCurrentIndex(index)
                    self.ui_dynamic_parameters.setCellWidget(row, 1, editor)
            
            # After populating data, resize first column to content
            self.ui_dynamic_parameters.resizeColumnToContents(0)


    def setModel(self, model):
        self._model = model
        # Prevent expanding/collapsing of tree items
        self.ui_tree.setExpandsOnDoubleClick(False)
        self.ui_tree.mouseReleaseEvent = lambda event: None  # Disable mouse release events
        
        self.ui_tree.setModel(self._model)
        self.ui_tree.selectionModel().currentChanged.connect(self.setSelection)
        
        # Expand the root node
        root_index = self._model.index(0, 0, None)
        self.ui_tree.expand(root_index)
        self.ui_tree.hideColumn(1)


    def closeEvent(self, event):
        geometry = self.saveGeometry()
        self._settings.setValue('recipe_editor_geometry', geometry)
        state = self.saveState()
        splitter_state = self.ui_splitter.saveState()
        splitter_2_state = self.ui_splitter_2.saveState()
        self._settings.setValue('recipe_editor_state', state)
        self._settings.setValue('recipe_editor_splitter_state', splitter_state)
        self._settings.setValue('recipe_editor_splitter_2_state', splitter_2_state)
        super().closeEvent(event)


    def enableEditRecipe(self, enable):
        pass



