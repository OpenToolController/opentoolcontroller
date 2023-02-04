# -*- coding: utf-8 -*-
from PyQt5 import QtGui, QtCore, QtSvg, QtWidgets

class DeviceIconWidget(QtSvg.QGraphicsSvgItem):
    def __init__(self, renderer=None):
        super().__init__()

        if renderer is not None:
            self.setSharedRenderer(renderer)
        self.setAcceptHoverEvents(True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, False)

        self._callback = None #This method gets called on click to make the parents tree change index
        self._pos_callback = None #This method gets called to set the new icon position from draging
        self._index = None #index of this icon

        self._hovering = False
        self._selected = False

    def setCallback(self, value):
        self._callback = value

    def setPosCallback(self, value):
        self._pos_callback = value

    def setIndex(self, value):
        self._index = value

    def setMovable(self, value):
        if value:
            self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        else:
            self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, False)

    def paint(self, painter, option, wid):
        super().paint(painter, option, wid)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        if self._hovering:
            painter.setPen(QtGui.QPen(QtGui.QBrush(QtCore.Qt.cyan), 4, QtCore.Qt.DotLine))
            painter.drawRect(self.boundingRect())

        if self._selected:
            painter.setPen(QtGui.QPen(QtGui.QBrush(QtCore.Qt.cyan), 4, QtCore.Qt.SolidLine))
            painter.drawRect(self.boundingRect())


    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self._callback(self._index.parent())
        self._pos_callback(self._index, self.scenePos())
        event.accept()

    def setSelected(self):
        self._selected = True
        self.update()

    def clearSelected(self):
        self._selected = False
        self.update()

    def hoverEnterEvent(self, event):
        self._hovering = True
        self.update()
        event.accept()

    def hoverLeaveEvent(self, event):
        self._hovering = False
        self.update()
        event.accept()
