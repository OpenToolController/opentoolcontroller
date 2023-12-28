# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtGui, uic, QtWidgets
import os

from opentoolcontroller.views.widgets.tool_tree_view import ToolTreeView
from opentoolcontroller.tool_model import LeafFilterProxyModel

tool_control_view_base, tool_control_view_form  = uic.loadUiType("opentoolcontroller/views/ToolControlView.ui")

class ToolControlView(tool_control_view_base, tool_control_view_form):
    def __init__(self, model, parent=None):
        super(tool_control_view_base, self).__init__(parent)
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
        self.ui_tree.setEnableContextMenu(False)
        self.ui_system_control_view.setModel(self._model) #TODO Used to be _proxy_mode
        self.ui_system_control_view.selectionModel().currentChanged.connect(self.setTreeSelection)

        self.ui_node_control_view.setModel(self._model)
        self.ui_node_control_view.show()

        self.ui_splitter_horizontal.setSizes([self.width()*0.6, self.width()*0.4])
        self.ui_splitter_vertical.setSizes([self.height()*0.4, self.height()*0.6])
        self.ui_tree.setColumnWidth(0,200)
        self.ui_tree.expandToDepth(1)
        self.ui_tree.setColumnHidden(1, True)
        #self.ui_tree.setItemsExpandable(False)
        self.vlayout = QtWidgets.QVBoxLayout()


    def setTreeSelection(self, index):
        if not hasattr(index.model(), 'mapToSource'):
            index = self._proxy_model.mapFromSource(index)

        self.ui_tree.setCurrentIndex(index)
        self.ui_node_control_view.setSelection(index)

    def setGraphicSelection(self, index):
        self.ui_node_control_view.setSelection(index) #TODO make sure this isn't causing a loop of selection
        self.ui_system_control_view.setSelection(index)

    def enableRunDeviceBehaviors(self, enable):
        self.ui_node_control_view.enableRunDeviceBehaviors(enable)
        pass

    def enableRunSystemBehaviors(self, enable):
        pass

    def enableRunToolBehaviors(self, enable):
        pass

    def enableEditBehaviors(self, enable):
        self.ui_node_control_view.enableEditBehaviors(enable)

    def setMovableIcons(self, value):
        self.ui_system_control_view.setMovableIcons(value)
        self.ui_system_control_view.reset()

    def movableIcons(self):
        return self.ui_system_control_view.movableIcons()
