# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtGui, uic, QtWidgets
import os

from opentoolcontroller.views.widgets.tool_tree_view import ToolTreeView
from opentoolcontroller.tool_model import LeafFilterProxyModel

tool_manual_view_base, tool_manual_view_form  = uic.loadUiType("opentoolcontroller/views/ToolManualView.ui")

class ToolManualView(tool_manual_view_base, tool_manual_view_form):
    def __init__(self, model, parent=None):
        super(tool_manual_view_base, self).__init__(parent)
        self.setupUi(self)

        self._model = model
        self._proxy_model =  LeafFilterProxyModel(self) #maybe not self?

        """VIEW <------> PROXY MODEL <------> DATA MODEL"""
        self._proxy_model.setSourceModel(self._model)
        self._proxy_model.setDynamicSortFilter(True)
        self._proxy_model.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.ui_filter.textChanged.connect(self._proxy_model.setFilterRegExp)


        self.ui_tree.setModel(self._proxy_model)
        self.ui_tree.selectionModel().currentChanged.connect(self.setGraphicSelection)
        self.ui_system_manual_view.setModel(self._model) #TODO Used to be _proxy_mode
        self.ui_system_manual_view.selectionModel().currentChanged.connect(self.setTreeSelection)

        self.ui_button_group.setModel(self._model)
        self.ui_button_group.show()

        self.ui_splitter_horizontal.setSizes([self.width()*0.6, self.width()*0.4])
        self.ui_splitter_vertical.setSizes([self.height()*0.4, self.height()*0.6])
        self.ui_tree.setColumnWidth(0,200)
        self.vlayout = QtWidgets.QVBoxLayout()


    def setTreeSelection(self, index):
        if not hasattr(index.model(), 'mapToSource'):
            index = self._proxy_model.mapFromSource(index)

        self.ui_tree.setCurrentIndex(index)
        self.ui_button_group.setSelection(index)

    def setGraphicSelection(self, index):
        self.ui_button_group.setSelection(index) #TODO make sure this isn't causing a loop of selection
        self.ui_system_manual_view.setSelection(index)

    def enableRunDeviceBehaviors(self, enable):
        self.ui_button_group.enableRunDeviceBehaviors(enable)
        pass

    def enableRunSystemBehaviors(self, enable):
        pass

    def enableRunToolBehaviors(self, enable):
        pass

    def enableEditBehaviors(self, enable):
        self.ui_button_group.enableEditBehaviors(enable)

