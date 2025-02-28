# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtGui, uic, QtWidgets
import os
import json
from pathlib import Path

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
        self._allow_parameter_changed = True
        
        # Dictionary to store open recipes for each node
        self._node_recipes = {}  # {node_id: [(recipe_name, recipe_data, file_path, modified), ...]}
        self._current_node = None
        
        # Setup recipe list
        self.ui_recipes.itemSelectionChanged.connect(self.recipeSelectionChanged)
        
        # Connect open button
        self.ui_open.clicked.connect(self.openRecipe)

        # Setup static parameters table
        self.ui_static_parameters.setColumnCount(2)
        self.ui_static_parameters.setHorizontalHeaderLabels(["Parameter", "Value"])
        header = self.ui_static_parameters.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Interactive)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Interactive)
        self.ui_static_parameters.itemChanged.connect(self.recipeModified)

        # Setup dynamic parameters table
        self.ui_dynamic_parameters.setColumnCount(2)
        self.ui_dynamic_parameters.setHorizontalHeaderLabels(["Parameter", "Step 1"])
        header = self.ui_dynamic_parameters.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Interactive)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Interactive)
        self.ui_dynamic_parameters.itemChanged.connect(self.recipeModified)
        
        # Enable context menu for header
        self.ui_dynamic_parameters.horizontalHeader().setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.ui_dynamic_parameters.horizontalHeader().customContextMenuRequested.connect(self.showHeaderContextMenu)
        
        # Store clipboard data
        self._step_clipboard = None

        # Setup step spinbox
        self.ui_step.setMinimum(1)
        self.ui_step.setMaximum(2)  # Initial max is current columns + 1
        
        # Connect step manipulation buttons
        self.ui_insert_step.clicked.connect(lambda: self.insertStep(None))
        self.ui_copy_step.clicked.connect(lambda: self.copyStep(None))
        self.ui_paste_step.clicked.connect(lambda: self.pasteStep(None))
        self.ui_delete_step.clicked.connect(lambda: self.deleteStep(None))
        self.ui_save_as.clicked.connect(self.saveRecipeAs)
        self.ui_save.clicked.connect(self.saveRecipe)
        self.ui_close.clicked.connect(self.closeRecipe)

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
        self._allow_parameter_changed = False
        model = current.model()

        if hasattr(model, 'mapToSource'):
            current_index = model.mapToSource(current)
        else:
            current_index = current

        node = current_index.internalPointer()
        self._current_node = node
        
        # Update recipe list for the new node
        self.updateRecipeList()
        
        # Clear existing rows in both parameters tables
        self.ui_static_parameters.setRowCount(0)
        self.ui_static_parameters.setColumnCount(2)
        self.ui_dynamic_parameters.setRowCount(0)
        self.ui_dynamic_parameters.setColumnCount(2)
        
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
                #TODO Keep?
                var_type = var.get('type', '')
                
                editor = self.createEditorForVariable(var, self.ui_static_parameters)
                if editor:
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
                #TODO Keep?
                var_type = var.get('type', '')
                
                editor = self.createEditorForVariable(var, self.ui_dynamic_parameters)
                if editor:
                    self.ui_dynamic_parameters.setCellWidget(row, 1, editor)
            
            # After populating data, resize first column to content
            self.ui_dynamic_parameters.resizeColumnToContents(0)
        self._allow_parameter_changed = True
        self.ui_recipes.setCurrentRow(0)


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


    def getCurrentRecipeData(self):
        """Get current recipe data from both parameter tables"""
        recipe_data = {
            'static_parameters': {},
            'dynamic_parameters': {}
        }
        
        # Collect static parameters
        for row in range(self.ui_static_parameters.rowCount()):
            param_name = self.ui_static_parameters.item(row, 0).text()
            widget = self.ui_static_parameters.cellWidget(row, 1)
            value = self._getWidgetValue(widget)
            recipe_data['static_parameters'][param_name] = value
        
        # Collect dynamic parameters
        for row in range(self.ui_dynamic_parameters.rowCount()):
            param_name = self.ui_dynamic_parameters.item(row, 0).text()
            step_values = []
            
            # Collect values for each step
            for column in range(1, self.ui_dynamic_parameters.columnCount()):
                widget = self.ui_dynamic_parameters.cellWidget(row, column)
                value = self._getWidgetValue(widget)
                step_values.append(value)
            
            recipe_data['dynamic_parameters'][param_name] = step_values
            
        return recipe_data

    def showHeaderContextMenu(self, pos):
        """Show context menu for header"""
        # Get the column number
        column = self.ui_dynamic_parameters.horizontalHeader().logicalIndexAt(pos)
        header_width = sum(self.ui_dynamic_parameters.horizontalHeader().sectionSize(i) 
                          for i in range(self.ui_dynamic_parameters.columnCount()))
        
        # Show menu for step columns or when clicking past the last column
        if column > 0 or pos.x() > header_width:
            menu = QtWidgets.QMenu(self)
            
            # Initialize actions
            copy_action = None
            paste_action = None
            insert_action = None
            delete_action = None
            
            # Add copy action only for existing columns
            if column > 0:
                copy_action = menu.addAction("Copy Step")
            
            # Add paste and insert actions if we have clipboard data
            paste_action = menu.addAction("Paste Step")
            paste_action.setEnabled(self._step_clipboard is not None)
            
            insert_action = menu.addAction("Insert Step")
            
            # Add delete action only for existing columns
            if column > 0:
                delete_action = menu.addAction("Delete Step")
            
            # Show menu and get selected action
            action = menu.exec_(self.ui_dynamic_parameters.horizontalHeader().viewport().mapToGlobal(pos))
            
            if column > 0 and action == copy_action:
                self.copyStep(column)
            elif action == paste_action:
                # If clicking past last column, paste at end
                if pos.x() > header_width:
                    insert_pos = self.ui_dynamic_parameters.columnCount()
                    self.insertStep(insert_pos)
                    self.pasteStep(insert_pos)
                else:
                    self.pasteStep(column)
            elif action == insert_action:
                # If clicking past last column, insert at end
                insert_pos = self.ui_dynamic_parameters.columnCount() if pos.x() > header_width else column
                self.insertStep(insert_pos)
            elif action == delete_action:
                self.deleteStep(column)
                
                


    def copyStep(self, column=None):
        """Copy all parameter values from a step as a dictionary"""
        # Use provided column or get from spinbox
        copy_pos = column if column is not None else self.ui_step.value()
        
        # Ensure copy position is valid
        if copy_pos < 1 or copy_pos >= self.ui_dynamic_parameters.columnCount():
            return
            
        step_data = {}
        for row in range(self.ui_dynamic_parameters.rowCount()):
            param_name = self.ui_dynamic_parameters.item(row, 0).text()
            widget = self.ui_dynamic_parameters.cellWidget(row, copy_pos)
            if widget:
                value = self._getWidgetValue(widget)
                step_data[param_name] = value
        self._step_clipboard = step_data

    def pasteStep(self, column=None):
        """Paste copied step data into the specified column"""
        if not self._step_clipboard:
            return
            
        # Use provided column or get from spinbox
        paste_pos = column if column is not None else self.ui_step.value()
        
        # Ensure paste position is valid
        if paste_pos < 1 or paste_pos >= self.ui_dynamic_parameters.columnCount():
            return
            
        # Verify parameters match
        current_params = set()
        for row in range(self.ui_dynamic_parameters.rowCount()):
            param_name = self.ui_dynamic_parameters.item(row, 0).text()
            current_params.add(param_name)
            
        clipboard_params = set(self._step_clipboard.keys())
        
        if current_params != clipboard_params:
            QtWidgets.QMessageBox.warning(
                self,
                "Invalid Paste",
                "Clipboard parameters do not match current parameters."
            )
            return
            
        # Paste values into widgets
        for row in range(self.ui_dynamic_parameters.rowCount()):
            param_name = self.ui_dynamic_parameters.item(row, 0).text()
            widget = self.ui_dynamic_parameters.cellWidget(row, paste_pos)
            if widget and param_name in self._step_clipboard:
                self.setWidgetValue(widget, self._step_clipboard[param_name])
        
        # Update recipe data and modified state
        self.recipeModified()

    def closeRecipe(self):
        """Close the currently selected recipe"""
        if not self._current_node:
            return
            
        current_item = self.ui_recipes.currentItem()
        if not current_item:
            return
            
        file_path = current_item.data(QtCore.Qt.UserRole)
        node_id = id(self._current_node)
        
        # Find the recipe
        if node_id in self._node_recipes:
            for i, (name, data, path, modified) in enumerate(self._node_recipes[node_id]):
                if path == file_path:
                    # Check if recipe needs saving
                    if modified:
                        reply = QtWidgets.QMessageBox.question(
                            self,
                            "Save Changes",
                            f"Do you want to save changes to {name}?",
                            QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel
                        )
                        
                        if reply == QtWidgets.QMessageBox.Save:
                            try:
                                with open(file_path, 'w') as f:
                                    json.dump(data, f, indent=4)
                            except Exception as e:
                                QtWidgets.QMessageBox.critical(
                                    self,
                                    "Error",
                                    f"Failed to save recipe: {str(e)}"
                                )
                                return
                        elif reply == QtWidgets.QMessageBox.Cancel:
                            return
                    
                    # Remove recipe from list
                    self._node_recipes[node_id].pop(i)
                    if not self._node_recipes[node_id]:
                        del self._node_recipes[node_id]
                    
                    # Update recipe list
                    self.updateRecipeList()
                    self.ui_recipes.setCurrentRow(0)
                    break

    def recipeModified(self, modified=True):
        """Set the current recipe as modified and update UI"""
        if not self._allow_parameter_changed:
            return
            
        if not self._current_node:
            return
            
        current_item = self.ui_recipes.currentItem()
        if not current_item:
            return
            
        file_path = current_item.data(QtCore.Qt.UserRole)
        node_id = id(self._current_node)
        
        # Find and update the recipe data
        if node_id in self._node_recipes:
            for i, (name, data, path, _) in enumerate(self._node_recipes[node_id]):
                if path == file_path:
                    # Update recipe data with current values if being modified
                    if modified:
                        data = self.getCurrentRecipeData()
                    self._node_recipes[node_id][i] = (name, data, path, modified)
                    current_item.setText(f"{name}*" if modified else name)
                    break

    def enableEditRecipe(self, enable):
        pass

    def openRecipe(self):
        """Open a recipe file and add it to the current node's recipe list"""
        if not self._current_node:
            return
            
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open Recipe", "", "Recipe Files (*.rcp);;All Files (*)"
        )
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    recipe_data = json.load(f)
                
                # Validate recipe against node parameters
                if self.validateRecipe(recipe_data):
                    node_id = id(self._current_node)
                    recipe_name = Path(filename).name
                    
                    # Check if recipe is already open
                    if node_id in self._node_recipes:
                        for i, (existing_name, existing_data, existing_path, modified) in enumerate(self._node_recipes[node_id]):
                            if existing_path == filename:
                                # Recipe is already open, check if data is different
                                if existing_data != recipe_data:
                                    reply = QtWidgets.QMessageBox.question(
                                        self,
                                        "Recipe Already Open",
                                        f"Recipe '{recipe_name}' is already open with different data. Do you want to overwrite the current version?",
                                        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                        QtWidgets.QMessageBox.No
                                    )
                                    
                                    if reply == QtWidgets.QMessageBox.Yes:
                                        # Update existing recipe data
                                        self._node_recipes[node_id][i] = (recipe_name, recipe_data, filename, False)
                                        self.updateRecipeList()
                                        # Select the updated recipe
                                        for row in range(self.ui_recipes.count()):
                                            item = self.ui_recipes.item(row)
                                            if item.data(QtCore.Qt.UserRole) == filename:
                                                self.ui_recipes.setCurrentRow(row)
                                                break
                                return
                    
                    # Recipe not already open, add it
                    if node_id not in self._node_recipes:
                        self._node_recipes[node_id] = []
                    self._node_recipes[node_id].append((recipe_name, recipe_data, filename, False))
                    
                    # Update recipe list
                    self.updateRecipeList()
                    
                    # Select the newly added recipe
                    last_row = self.ui_recipes.count() - 1
                    self.ui_recipes.setCurrentRow(last_row)
                else:
                    QtWidgets.QMessageBox.warning(
                        self,
                        "Invalid Recipe",
                        "Recipe parameters do not match the selected node's parameters."
                    )
                    
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to open recipe: {str(e)}"
                )

    def validateRecipe(self, recipe_data):
        """Validate recipe parameters against current node parameters"""
        if not self._current_node:
            return False
            
        node_vars = self._current_node.data(col.RECIPE_VARIABLES)
        if not node_vars:
            return False
            
        # Get sets of parameter names from node and recipe
        node_static = {var['name'] for var in node_vars if not var.get('dynamic', False)}
        node_dynamic = {var['name'] for var in node_vars if var.get('dynamic', False)}
        
        recipe_static = set(recipe_data.get('static_parameters', {}).keys())
        recipe_dynamic = set(recipe_data.get('dynamic_parameters', {}).keys())
        
        # Check if parameter sets match exactly
        return (node_static == recipe_static and 
                node_dynamic == recipe_dynamic)

    def updateRecipeList(self):
        """Update the recipe list for the current node"""
        self.ui_recipes.itemSelectionChanged.disconnect(self.recipeSelectionChanged)

        self.ui_recipes.clear()
        if self._current_node:
            node_id = id(self._current_node)
            if node_id in self._node_recipes:
                for recipe_name, _, file_path, modified in self._node_recipes[node_id]:
                    # Add asterisk to modified recipes
                    display_name = f"{recipe_name}*" if modified else recipe_name
                    item = QtWidgets.QListWidgetItem(display_name)
                    item.setData(QtCore.Qt.UserRole, file_path)  # Store full path in item data
                    item.setToolTip(file_path)  # Keep tooltip for visibility on hover
                    self.ui_recipes.addItem(item)

        self.ui_recipes.itemSelectionChanged.connect(self.recipeSelectionChanged)

    def recipeSelectionChanged(self):
        """Handle recipe selection change"""
        current_item = self.ui_recipes.currentItem()
        if current_item and self._current_node:
            file_path = current_item.data(QtCore.Qt.UserRole)
            node_id = id(self._current_node)
            
            # Find the recipe data
            recipe_data = None
            if node_id in self._node_recipes:
                for name, data, path, _ in self._node_recipes[node_id]:
                    if path == file_path:
                        recipe_data = data
                        break
            
            if recipe_data:
                self.displayRecipe(recipe_data)

    def displayRecipe(self, recipe_data):
        self._allow_parameter_changed = False
        """Display the recipe data in the parameter tables"""
        # Handle static parameters
        static_params = recipe_data.get('static_parameters', {})
        for row in range(self.ui_static_parameters.rowCount()):
            param_name = self.ui_static_parameters.item(row, 0).text()
            if param_name in static_params:
                widget = self.ui_static_parameters.cellWidget(row, 1)
                self.setWidgetValue(widget, static_params[param_name])
        
        # Handle dynamic parameters
        dynamic_params = recipe_data.get('dynamic_parameters', {})
        
        # Clear all step columns, keeping only the Parameter column
        while self.ui_dynamic_parameters.columnCount() > 1:
            self.ui_dynamic_parameters.removeColumn(1)
            
        # Add the needed number of step columns
        max_steps = max((len(steps) for steps in dynamic_params.values()), default=0)
        for i in range(max_steps):
            self.ui_dynamic_parameters.insertColumn(self.ui_dynamic_parameters.columnCount())
            
        # Update headers after column changes
        self.updateStepHeaders()
        
        # Update spinbox maximum
        self.ui_step.setMaximum(self.ui_dynamic_parameters.columnCount())
        
        # Now populate the values
        for row in range(self.ui_dynamic_parameters.rowCount()):
            param_name = self.ui_dynamic_parameters.item(row, 0).text()
            if param_name in dynamic_params:
                step_values = dynamic_params[param_name]
                
                # Set values for each step
                for column, value in enumerate(step_values, start=1):
                    widget = self.ui_dynamic_parameters.cellWidget(row, column)
                    if not widget:
                        # Create widget if it doesn't exist
                        recipe_vars = self._current_node.data(col.RECIPE_VARIABLES)
                        var = next((v for v in recipe_vars if v.get('name') == param_name), None)
                        if var:
                            widget = self.createEditorForVariable(var, self.ui_dynamic_parameters)
                            if widget:
                                self.ui_dynamic_parameters.setCellWidget(row, column, widget)
                    if widget:
                        self.setWidgetValue(widget, value)
        self._allow_parameter_changed = True

    def setWidgetValue(self, widget, value):
        """Set a widget's value based on its type"""
        if isinstance(widget, QtWidgets.QDoubleSpinBox):
            widget.setValue(float(value))
        elif isinstance(widget, QtWidgets.QSpinBox):
            widget.setValue(int(value))
        elif isinstance(widget, QtWidgets.QCheckBox):
            widget.setChecked(bool(value))
        elif isinstance(widget, QtWidgets.QComboBox):
            index = widget.findText(str(value))
            if index >= 0:
                widget.setCurrentIndex(index)

    def saveRecipe(self):
        """Save the current recipe to its file"""
        if not self._current_node:
            return
            
        current_item = self.ui_recipes.currentItem()
        if not current_item:
            return
            
        file_path = current_item.data(QtCore.Qt.UserRole)
        node_id = id(self._current_node)
        
        # Find the recipe data and file path
        if node_id in self._node_recipes:
            for i, (name, data, path, modified) in enumerate(self._node_recipes[node_id]):
                if path == file_path:
                    # Get current data
                    recipe_data = self.getCurrentRecipeData()
                    
                    # Save to file
                    try:
                        with open(file_path, 'w') as f:
                            json.dump(recipe_data, f, indent=4)
                            self.recipeModified(False)
                    except Exception as e:
                        QtWidgets.QMessageBox.critical(
                            self,
                            "Error",
                            f"Failed to save recipe: {str(e)}"
                        )
                    break

    def saveRecipeAs(self):
        """Save the recipe parameters to a JSON file"""
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save Recipe", "", "Recipe Files (*.rcp);;All Files (*)"
        )
        
        if filename:
            # Add .rcp extension if not present
            if not filename.endswith('.rcp'):
                filename += '.rcp'
            
            recipe_data = {
                'static_parameters': {},
                'dynamic_parameters': {}
            }
            
            # Collect static parameters
            for row in range(self.ui_static_parameters.rowCount()):
                param_name = self.ui_static_parameters.item(row, 0).text()
                widget = self.ui_static_parameters.cellWidget(row, 1)
                value = self._getWidgetValue(widget)
                recipe_data['static_parameters'][param_name] = value
            
            # Collect dynamic parameters
            for row in range(self.ui_dynamic_parameters.rowCount()):
                param_name = self.ui_dynamic_parameters.item(row, 0).text()
                step_values = []
                
                # Collect values for each step
                for column in range(1, self.ui_dynamic_parameters.columnCount()):
                    widget = self.ui_dynamic_parameters.cellWidget(row, column)
                    value = self._getWidgetValue(widget)
                    step_values.append(value)
                
                recipe_data['dynamic_parameters'][param_name] = step_values
            
            # Save to file
            try:
                with open(filename, 'w') as f:
                    json.dump(recipe_data, f, indent=4)
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to save recipe: {str(e)}"
                )

    def _getWidgetValue(self, widget):
        """Helper method to get the value from a widget based on its type"""
        if isinstance(widget, QtWidgets.QDoubleSpinBox):
            return widget.value()
        elif isinstance(widget, QtWidgets.QSpinBox):
            return widget.value()
        elif isinstance(widget, QtWidgets.QCheckBox):
            return widget.isChecked()
        elif isinstance(widget, QtWidgets.QComboBox):
            return widget.currentText()
        return None

    def insertStep(self, column=None):
        """Insert a new step column at the specified position or the one from ui_step spinbox"""
        current_cols = self.ui_dynamic_parameters.columnCount()
        
        # Use provided column or get from spinbox
        insert_pos = column if column is not None else self.ui_step.value()
        
        # Ensure insert position is valid
        if insert_pos < 1 or insert_pos > current_cols:
            return
            
        # Insert new column
        self.ui_dynamic_parameters.insertColumn(insert_pos)
        
        # Update column headers and spinbox maximum
        self.updateStepHeaders()
        self.ui_step.setMaximum(self.ui_dynamic_parameters.columnCount())
        
        # Create editors for each row in the new column
        for row in range(self.ui_dynamic_parameters.rowCount()):
            # Get the variable type from the first column's item
            var_name = self.ui_dynamic_parameters.item(row, 0).text()
            # Find the variable in recipe_vars
            recipe_vars = self._current_node.data(col.RECIPE_VARIABLES)
            if recipe_vars:
                var = next((v for v in recipe_vars if v.get('name') == var_name), None)
                if var:
                    var_type = var.get('type', '')
                    editor = self.createEditorForVariable(var, self.ui_dynamic_parameters)
                    if editor:
                        self.ui_dynamic_parameters.setCellWidget(row, insert_pos, editor)
        
        # Update recipe data and modified state
        self.recipeModified()

    def deleteStep(self, column=None):
        """Delete the specified step column or the one specified by ui_step spinbox"""
        current_cols = self.ui_dynamic_parameters.columnCount()
        
        # Use provided column or get from spinbox
        delete_pos = column if column is not None else self.ui_step.value()
        
        # Ensure delete position is valid (can't delete parameter column)
        if delete_pos < 1 or delete_pos >= current_cols:
            return
            
        # Remove column
        self.ui_dynamic_parameters.removeColumn(delete_pos)
        
        # Update column headers and spinbox maximum
        self.updateStepHeaders()
        self.ui_step.setMaximum(self.ui_dynamic_parameters.columnCount())
        
        # Update recipe data and modified state
        self.recipeModified()

    def updateStepHeaders(self):
        """Update the column headers to maintain proper step numbering"""
        headers = ["Parameter"]
        for i in range(1, self.ui_dynamic_parameters.columnCount()):
            headers.append(f"Step {i}")
        self.ui_dynamic_parameters.setHorizontalHeaderLabels(headers)

    def createEditorForVariable(self, var, parent_widget):
        """Create an editor widget based on the variable type and configuration"""
        var_type = var.get('type', '')
        editor = None
        
        if var_type == 'Float':
            editor = QtWidgets.QDoubleSpinBox(parent_widget)
            editor.setMinimum(float(var.get('min', -999999)))
            editor.setMaximum(float(var.get('max', 999999)))
            editor.setValue(float(var.get('value', 0)))
            editor.valueChanged.connect(self.recipeModified)
        elif var_type == 'Integer':
            editor = QtWidgets.QSpinBox(parent_widget)
            editor.setMinimum(int(var.get('min', -999999)))
            editor.setMaximum(int(var.get('max', 999999)))
            editor.setValue(int(var.get('value', 0)))
            editor.valueChanged.connect(self.recipeModified)
        elif var_type == 'Boolean':
            editor = QtWidgets.QCheckBox(parent_widget)
            editor.setChecked(var.get('value', False))
            editor.stateChanged.connect(self.recipeModified)
        elif var_type == 'List':
            editor = QtWidgets.QComboBox(parent_widget)
            list_values = var.get('list_values', [])
            if isinstance(list_values, str):
                list_values = [x.strip() for x in list_values.split(',') if x.strip()]
            elif isinstance(list_values, list):
                list_values = [str(x).strip() for x in list_values if str(x).strip()]
            editor.addItems(list_values)
            current_value = var.get('value', '')
            index = editor.findText(str(current_value))
            if index >= 0:
                editor.setCurrentIndex(index)
            editor.currentTextChanged.connect(self.recipeModified)
        
        return editor


