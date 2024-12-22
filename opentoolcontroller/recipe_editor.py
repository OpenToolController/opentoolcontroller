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


        self._settings = QtCore.QSettings('OpenToolController', 'test1')
        geometry = self._settings.value('recipe_editor_geometry', bytes('', 'utf-8'))
        state = self._settings.value('recipe_editor_state', bytes('', 'utf-8'))
        splitter_state = self._settings.value('recipe_editor_splitter_state', bytes('', 'utf-8'))

        self.restoreGeometry(geometry)
        self.restoreState(state)
        self.ui_splitter.restoreState(splitter_state)
        self.enableEditRecipe(False)


    #INPUTS: QModelIndex, QModelIndex
    def setSelection(self, current, old):
        model = current.model()

        if hasattr(model, 'mapToSource') : current_index = model.mapToSource(current)
        else                             : current_index = current

        node = current_index.internalPointer()


    def setModel(self, model):
        self._model = model
        self.ui_tree.setModel(self._model)
        self.ui_tree.selectionModel().currentChanged.connect(self.setSelection)
        self.ui_tree.collapseAll()
        self.ui_tree.hideColumn(1)

        #self._node_editor.setModel(self._proxy_model)
        #self._behavior_state_editor.setModel(self._proxy_model)
        #self._recipe_variable_editor.setModel(self._proxy_model)

        #for editor in self._specific_editors.values():
        #    editor.setModel(self._proxy_model)

    def closeEvent(self, event):
        geometry = self.saveGeometry()
        self._settings.setValue('recipe_editor_geometry', geometry)
        state = self.saveState()
        splitter_state = self.ui_splitter.saveState()
        self._settings.setValue('recipe_editor_state', state)
        self._settings.setValue('recipe_editor_splitter_state', splitter_state)
        super().closeEvent(event)


    def enableEditRecipe(self, enable):
        pass



