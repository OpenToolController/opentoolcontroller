#!/usr/bin/python3
# -*- coding: utf-8 -*-
from PyQt5 import QtGui, QtCore, QtWidgets, QtSvg
from opentoolcontroller.strings import typ, col
from opentoolcontroller.views.widgets.device_icon_widget import DeviceIconWidget

#TODO Change name to SystemGraphicView ???
class SystemControlView(QtWidgets.QAbstractItemView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene_box = QtCore.QRectF(0, 0, 1000, 1000)
        self._previous_index = None
        self._scene = QtWidgets.QGraphicsScene(self)
        self._renderers = []
        self._device_icons = []

        #UI Stuff
        self._view = QtWidgets.QGraphicsView(self)
        self._view.setScene(self._scene)
        self._view.scale(1, 1)

        #Layout
        self.h_layout = QtWidgets.QHBoxLayout()
        self.h_layout.addWidget(self._view)
        self.h_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.h_layout)

        self._current_system_index = None
        self._movable_icons = False

    def setMovableIcons(self, value):
        self._movable_icons = bool(value)
        self.setSelection(self._current_system_index)

    def movableIcons(self):
        return self._movable_icons

    def resizeEvent(self, event):
        self._view.fitInView(self._scene_box, QtCore.Qt.KeepAspectRatio)


    def dataChanged(self, index_top_left, index_bottom_right, roles):
        index = index_top_left #TODO
        tool_model = self.model()

        try:
            #TODO not quite sure why the index isn't the same as the current_system_index, but they point to the same place
            if index.internalPointer() == self._current_system_index.internalPointer():
                if index.column() == col.BACKGROUND_SVG:
                    self.setBackground(tool_model.data(index, QtCore.Qt.DisplayRole))



            elif index.internalPointer().typeInfo() == typ.DEVICE_ICON_NODE and  index.parent().parent() == self._current_system_index:
                if index.column() == col.SVG:
                    icon_node = index.internalPointer()
                    wid = self._device_icons[index.parent().row()]
                    wid.renderer().load(icon_node.svgFullPath())
                    wid.setElementId(icon_node.layer())

                elif index.column() == col.LAYER:
                    icon_node = index.internalPointer()
                    wid = self._device_icons[index.parent().row()]
                    wid.setElementId(icon_node.layer())

                elif index.column() in [col.X, col.Y, col.SCALE, col.ROTATION, col.ROTATION, col.TEXT_X, col.TEXT_Y, col.FONT_SIZE]:
                    icon_node = index.internalPointer()

                    #Since each device has to have a single icon the parents row is the same as this index
                    wid = self._device_icons[index.parent().row()]
                    wid.setPos(float(icon_node.x) , float(icon_node.y))
                    wid.setRotation(float(icon_node.rotation))
                    wid.setScale(float(icon_node.scale))


                    if wid.text_wid:
                        wid.text_wid.setPos(float(icon_node.x + icon_node.textX) , float(icon_node.y + icon_node.textY))
                        wid.text_wid.setDefaultTextColor(icon_node.fontColor())
                        font = QtGui.QFont("Helvetica", icon_node.fontSize)
                        wid.text_wid.setFont(font)


                elif index.column() in [col.TEXT]:
                    icon_node = index.internalPointer()
                    wid = self._device_icons[index.parent().row()]
                    if wid.text_wid:
                        wid.text_wid.setPlainText(icon_node.text())


                elif index.column() in [col.HAS_TEXT]:
                    icon_node = index.internalPointer()
                    wid = self._device_icons[index.parent().row()]

                    if icon_node.hasText:
                        if not wid.text_wid:
                            font = QtGui.QFont("Helvetica", icon_node.fontSize)
                            text_wid = self._scene.addText(icon_node.text(), font)
                            text_wid.setPos(float(icon_node.x + icon_node.textX) , float(icon_node.y + icon_node.textY))
                            text_wid.setDefaultTextColor(icon_node.fontColor())
                            wid.text_wid = text_wid

                    else:
                        if wid.text_wid:
                            self._scene.removeItem(wid.text_wid)
                            wid.text_wid = None


        except:
            pass



    def rowsAboutToBeRemoved(self, parent_index, start, end):
        if hasattr(parent_index.model(), 'mapToSource'):
            parent_index = parent_index.model().mapToSource(parent_index)

        if parent_index == self._current_system_index:
            model = parent_index.model()

            device_indexes = []
            for i in range(start, end+1):
                device_indexes.append(model.index(i, 0, parent_index))

            for device_index in device_indexes:
                wid = self._device_icons[device_index.row()]
                self._scene.removeItem(wid)

            del self._device_icons[start:end+1]


    def rowsInserted(self, parent_index, start, end):
        self.displaySystem(self._current_system_index)

    #This abstract view needs to emit a currentChanged(
    def setSelection(self, index):
        if index is None:
            return
        if hasattr(index.model(), 'mapToSource'):
            index = index.model().mapToSource(index)

        #this gets a double call if you select it via the graphic icon right now
        model = index.model()
        node  = index.internalPointer()

        type_info = None
        if node is not None:
            type_info = node.typeInfo()

        if type_info == typ.SYSTEM_NODE:
            self._current_system_index = index
            self.displaySystem(self._current_system_index)

        elif type_info == typ.DEVICE_NODE:
            if index.parent() != self._current_system_index:
                self._current_system_index = index.parent()
                self.displaySystem(self._current_system_index)

            for icon in self._device_icons:
                icon.clearSelected()

            self._device_icons[index.row()].setSelected()

        self.setCurrentIndex(index)

    def setIconPosition(self, index, pos):
        self.model().setData(index.siblingAtColumn(col.POS), pos, QtCore.Qt.EditRole)

    def displaySystem(self, system_index):
        self._view.resetTransform() #Needed?
        self._scene.clear()
        self._device_icons = []

        if system_index == None:
            return

        system_node = system_index.internalPointer()
        svg_image = system_node.backgroundSVGFullPath()
        movable = self.movableIcons()

        #Border line around background image
        rectangle = QtWidgets.QGraphicsRectItem(self._scene_box)
        self._scene.addItem(rectangle)

        background = QtGui.QPixmap(svg_image)
        background = background.scaled(int(self._scene_box.width()), int(self._scene_box.height()), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        self._scene.addPixmap(background)


        #Add the Device Icons
        icon_indexes = self.model().indexesOfType(typ.DEVICE_ICON_NODE, system_index)

        for icon_index in icon_indexes:

            icon_node = icon_index.internalPointer()

            renderer = QtSvg.QSvgRenderer(self)
            renderer.load(icon_node.svgFullPath())

            wid = DeviceIconWidget(renderer)
            wid.setCallback(self.setSelection)
            wid.setPosCallback(self.setIconPosition)
            wid.setIndex(icon_index)
            wid.setElementId(icon_node.layer())
            wid.setMovable(movable)

            #wid.setPos(float(icon_node.x) , float(icon_node.y))
            wid.setPos(icon_node.pos())
            wid.setRotation(float(icon_node.rotation))
            wid.setScale(float(icon_node.scale))

            self._device_icons.append(wid)
            self._scene.addItem(wid)

            if icon_node.hasText:
                #text_wid = self._scene.addWidget(QtWidgets.QLabel(icon_node.text()))
                #text_wid.setPos(float(icon_node.x + icon_node.textX) , float(icon_node.y + icon_node.textY))

                #font = text_wid.font()
                #font.setPointSize(icon_node.fontSize)
                #text_wid.setFont(font)
                #wid.text_wid = text_wid


                font = QtGui.QFont("Helvetica", icon_node.fontSize)
                text_wid = self._scene.addText(icon_node.text(), font)
                text_wid.setPos(float(icon_node.x + icon_node.textX) , float(icon_node.y + icon_node.textY))
                text_wid.setDefaultTextColor(icon_node.fontColor())
                wid.text_wid = text_wid

        #Resize the view
        self._view.fitInView(self._scene_box, QtCore.Qt.KeepAspectRatio)



    # TODO : No idea what this should do.
    def visualRegionForSelection(self, selection):
        return QtGui.QRegion()

    # TODO : No idea what this should do.
    def scrollTo(self, index, hint):
        return

    # TODO : No idea what this should do.
    def visualRect(self, index):
        return QtCore.QRect()

    # TODO : No idea what this should do.
    def verticalOffset(self):
        return 0

    # TODO : No idea what this should do.
    def horizontalOffset(self):
        return 0

    # TODO : No idea what this should do.
    def moveCursor(self, action, modifier):
        return QtCore.QModelIndex()
