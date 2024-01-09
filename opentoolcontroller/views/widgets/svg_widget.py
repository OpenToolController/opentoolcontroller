# -*- coding: utf-8 -*-
from PyQt5 import QtSvg, QtGui, QtCore

class SVGWidget(QtSvg.QSvgWidget):
    def __init__(self, parent=None):
        QtSvg.QSvgWidget.__init__(self, parent)
        self._element_id = None

    def setElementId(self, element_id):
        self._element_id = element_id
        self.repaint()

    def paintEvent(self, event):
        renderer = self.renderer()
        if renderer is not None:
            painter = QtGui.QPainter(self)
            size = renderer.defaultSize()
            ratio = size.height()/size.width()
            #length = min(self.width(), self.height())
            length = self.width()
            self.setMinimumHeight(int(ratio * length))
            if renderer.elementExists(self._element_id):
                renderer.render(painter, self._element_id, QtCore.QRectF(0, 0, length, ratio * length))
            else:
                renderer.render(painter, QtCore.QRectF(0, 0, length, ratio * length))
            painter.end()
