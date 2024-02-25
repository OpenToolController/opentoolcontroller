#!/usr/bin/python3
# -*- coding: utf-8 -*-
from PyQt5 import QtGui, QtCore, QtWidgets
from opentoolcontroller.strings import bt, col, typ
import math
from opentoolcontroller.message_box import MessageBox
from opentoolcontroller.views.widgets.scientific_spin import ScientificDoubleSpinBox, PercentDoubleSpinBox
from opentoolcontroller.views.widgets.svg_widget import SVGWidget

from string import Formatter

import pprint
pp = pprint.PrettyPrinter(width=82, compact=True)



class Path(QtWidgets.QGraphicsPathItem):
    def __init__(self, start_pos, end_pos):
        super().__init__()
        self._start_pos = start_pos
        self._end_pos = end_pos
        self._drop = 40 #diameter of fillet
        self._diam = 20 #fixed verticle drop

        self.setPen(QtGui.QPen(QtCore.Qt.darkGray, 2.0))
        self.updateElements()

    def startPos(self):
        return self._start_pos

    def setStartPos(self, pos):
        self._start_pos = pos
        self.updateElements()

    def endPos(self):
        return self._end_pos

    def setEndPos(self, pos):
        self._end_pos = pos
        self.updateElements()

    def minChildY(self):
        return self._start_pos.y() + self._drop*2

    def updateElements(self):
        start = self._start_pos
        end = self._end_pos

        d = self._diam
        drop = self._drop

        path = QtGui.QPainterPath()
        path.moveTo(start)
        path.lineTo(start.x(), start.y() + drop)
        d = min(d, abs(start.x()-end.x()))

        if end.x() > start.x():
            path.lineTo(end.x()-d, start.y() + drop)
            path.arcTo(end.x()-d, start.y() + drop, d, d, 90, -90)

        elif end.x() < start.x():
            path.lineTo(end.x()+d, start.y()+drop)
            path.arcTo(end.x(), start.y()+drop, d, d, -270, 90)

        else:
            path.lineTo(end.x(), start.y() + drop)

        path.lineTo(end)
        self.setPath(path)

class DragSquare(QtWidgets.QGraphicsRectItem):
    def __init__(self, x, y, w, h, parent=None):
        super().__init__(x, y, w, h, parent)
        self.setBrush(QtCore.Qt.white)
        self.setAcceptHoverEvents(True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges)

        self._parent = parent
        self._hovered = False
        self._editable = True

    def setEditable(self, value):
        self._editable = bool(value)

    def hoverEnterEvent(self, event):
        if self._editable:
            self._hovered = True
            self._parent.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, False)
            self.setBrush(QtCore.Qt.cyan)
            self.update()

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self._parent.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable)
        self.setBrush(QtCore.Qt.white)
        self.update()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if self._editable:
            if event.button() == QtCore.Qt.LeftButton:
                self._parent.addTempLine(event.scenePos())

class NodeGraphicsItem(QtWidgets.QGraphicsItem):
    def __init__(self, type=typ.SEQUENCE_NODE):
        super().__init__()
        # init our flags
        self._type_info = type
        self._status = None
        self._allow_delete = True
        self._editable = True

        self.hovered = False
        self._was_moved = False
        self._last_selected_state = False
        self._index = None

        self._callback = None
        self._index_pos = None

        self._lines = []

        self._is_branch = False

        self.initSizes()
        self.initAssets()
        self.initUI()
        self.initTitle()

        self._tmp_line = None


    def boxWidth(self):
        if hasattr(self, '_wid'):
            return self._wid.width() + 30
        else:
            return 200
    
    def boxHeight(self):
        if hasattr(self, '_wid'):
            return self._wid.height() + 60
        else:
            return 100

    def setIsBranch(self):
        self._is_branch = True
        self._drag_square = DragSquare(30, self.boxHeight()-20, self.boxWidth()-60, 20, self)
        self._drag_square.setEditable(self._editable)

    def setEditable(self, value):
        self._editable = bool(value)
        self.setEnabled(self._editable)

        try:
            self._drag_square.setEditable(self._editable)
        except:
            pass

        if self._editable:
            self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable)
        else:
            self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, False)

    def addTempLine(self, pos):
        self._tmp_line = Path(self.centerBottomPos(), pos)
        self.scene().addItem(self._tmp_line)

    def centerTopPos(self):
        return QtCore.QPoint(int(self.x() + self.boxWidth()*0.5), int(self.y()))

    def centerBottomPos(self):
        return QtCore.QPoint(int(self.x() + self.boxWidth()*0.5), int(self.y() + self.boxHeight()))

    def setDeleteCallback(self, value):
        self._delete_callback = value

    def setCutCallback(self, value):
        self._cut_callback = value

    def setAddCallback(self, value):
        self._add_callback = value

    def setCallback(self, value):
        self._callback = value

    def setIndexPos(self, value):
        self._index_pos = value

    def setAllowDelete(self, value):
        self._allow_delete = bool(value)


    def initUI(self):
        #Set up this ``QGraphicsItem`
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable)

        if self._editable:
            self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable)
        else:
            self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, False)

        self.setAcceptHoverEvents(True)


    def initTitle(self):
        self.title_item = QtWidgets.QGraphicsTextItem(self)
        self.title_item.setDefaultTextColor(self._title_color)
        self.title_item.setPos(self.title_horizontal_padding, 0)
        self.title_item.setFont(self._title_font)
        self.title_item.setTextWidth(self.boxWidth() - 2 * self.title_horizontal_padding)
        self.title_item.setPlainText(self._type_info)



    def initSizes(self):
        #Set up internal attributes like `width`, `height`, etc.
        self.edge_roundness = 10.0
        self.edge_padding = 10.0
        self.title_height = 24.0
        self.title_horizontal_padding = 4.0
        self.title_vertical_padding = 4.0

    def initAssets(self):
        #Initialize ``QObjects`` like ``QColor``, ``QPen`` and ``QBrush``
        self._title_color = QtCore.Qt.white
        self._title_font = QtGui.QFont("Ubuntu", 10)
        self._title_font2 = QtGui.QFont("Ubuntu", 20)

        self._color = QtGui.QColor("#7F000000")
        self._color_selected = QtGui.QColor("#FFFFA637")
        self._color_hovered = QtGui.QColor("#FF37A6FF")

        self._pen_default = QtGui.QPen(self._color)
        self._pen_default.setWidthF(2.0)
        self._pen_selected = QtGui.QPen(self._color_selected)
        self._pen_selected.setWidthF(2.0)
        self._pen_hovered = QtGui.QPen(self._color_hovered)
        self._pen_hovered.setWidthF(3.0)

        self._brush_title = QtGui.QBrush(QtGui.QColor("#FF313131"))
        self._brush_background = QtGui.QBrush(QtGui.QColor("#E3212121"))


    def boundingRect(self):
        return QtCore.QRectF(0, 0, self.boxWidth(), self.boxHeight()).normalized()

    def setStatus(self, status):
        self._status = status
        if status == None:
            self._brush_background = QtGui.QBrush(QtGui.QColor("#E3212121"))
        elif status == bt.RUNNING:
            self._brush_background = QtGui.QBrush(QtGui.QColor("#64abed"))
        elif status == bt.SUCCESS:
            self._brush_background = QtGui.QBrush(QtGui.QColor("#32a852"))
        elif status == bt.FAILURE:
            self._brush_background = QtGui.QBrush(QtGui.QColor("#a3103a"))


    def drawCustomShape(self, painter):
        return

    def paint(self, painter, QStyleOptionGraphicsItem, widget=None):
        #Painting the rounded rectanglar `Node`
        width = self.boxWidth()
        height = self.boxHeight() 
        r = 10 #radius of edge

        # title
        path_title = QtGui.QPainterPath()
        path_title.setFillRule(QtCore.Qt.WindingFill)
        path_title.addRoundedRect(0, 0, width, self.title_height, r, r)
        path_title.addRect(0, self.title_height - r, r,r)
        path_title.addRect(width - r, self.title_height - r, r, r)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(self._brush_title)
        painter.drawPath(path_title.simplified())


        # content
        path_content = QtGui.QPainterPath()
        path_content.setFillRule(QtCore.Qt.WindingFill)
        path_content.addRoundedRect(0, self.title_height, width, height - self.title_height, r, r)
        path_content.addRect(0, self.title_height, r, r)
        path_content.addRect(width - r, self.title_height, r, r)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(self._brush_background)
        painter.drawPath(path_content.simplified())


        #Draws the center shape if used
        self.drawCustomShape(painter)


        # outline
        path_outline = QtGui.QPainterPath()
        path_outline.addRoundedRect(-1, -1, width+2, height+2, r, r)
        painter.setBrush(QtCore.Qt.NoBrush)
        if self.hovered:
            painter.setPen(self._pen_hovered)
            painter.drawPath(path_outline.simplified())
            painter.setPen(self._pen_default)
            painter.drawPath(path_outline.simplified())
        else:
            painter.setPen(self._pen_default if not self.isSelected() else self._pen_selected)
            painter.drawPath(path_outline.simplified())

        #update drag square
        if self._is_branch: 
            self._drag_square.setRect(30, height-20, width-60, 20)

    def hoverEnterEvent(self, event):
        self.hovered = True
        self.update()

    def hoverLeaveEvent(self, event):
        self.hovered = False
        self.update()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self._temp_pos = self.pos()


    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if self._tmp_line:
            self._tmp_line.setEndPos(self.mapToScene(event.pos()))

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self._tmp_line:
            self.scene().removeItem(self._tmp_line)
            self._tmp_line= None

            pos = self.mapToScene(event.pos())
            pos += QtCore.QPointF(-self.boxWidth()/2, 0)
            self._add_callback(self, pos)


        else: #If we just added the object the model is going to be reset and the linked objet wont be there
            if self.pos() != self._temp_pos:
                self._callback(self._index_pos, (self.x(),self.y()))

    def updateLines(self):
        #Move all the lines
        for line in self._lines:
            o, index = line[0], line[1]

            if index == 0:
                o.setStartPos(self.centerBottomPos())
            else:
                o.setEndPos(self.centerTopPos())
                min_y = o.minChildY()


    def itemChange(self, change, value):
        min_y = -32000

        if change == QtWidgets.QGraphicsItem.ItemPositionChange:


            for line in self._lines:
                o, index = line[0], line[1]

                if index == 0:
                    o.setStartPos(self.centerBottomPos())
                else:
                    o.setEndPos(self.centerTopPos())
                    min_y = o.minChildY()


            #Prevent it from going above it's parent
            if value.y() < min_y:
                return QtCore.QPointF(value.x(), min_y)


        return super().itemChange(change, value)

    def addLine(self, line, pt_index):
        self._lines.append((line, pt_index))

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu()
        if self._allow_delete:
            delete_action = menu.addAction("Delete")
            cut_action = menu.addAction("Cut")

        selected = menu.exec(event.screenPos())

        if self._allow_delete:
            if selected == delete_action:
                self._delete_callback(self)
            if selected == cut_action:
                self._cut_callback(self)

class SequenceNodeGraphicsItem(NodeGraphicsItem):
    def __init__(self, type=typ.SEQUENCE_NODE):
        super().__init__(type)
    
    def drawCustomShape(self, painter):
        width = self.boxWidth()
        height = self.boxHeight() 

        my_pen = QtGui.QPen()
        my_pen.setWidth(5)
        my_pen.setCosmetic(False)
        my_pen.setCapStyle(QtCore.Qt.RoundCap)
        my_pen.setColor(QtGui.QColor('#DDDDDD'))
        painter.setPen(my_pen)

        border = 50
        v_center = (height + self.title_height)/2
        v_center = (height )/2

        #paint shape
        painter.setPen(my_pen)
        painter.drawPolyline(QtCore.QPointF(border,v_center), QtCore.QPointF(width-border, v_center))
        
        #arrow head
        painter.drawPolyline(QtCore.QPointF(width-border-10, v_center-10),
                             QtCore.QPointF(width-border, v_center),
                             QtCore.QPointF(width-border-10, v_center+10))

class SelectorNodeGraphicsItem(NodeGraphicsItem):
    def __init__(self, type=typ.SELECTOR_NODE):
        super().__init__(type)
    
    def drawCustomShape(self, painter):
        width = self.boxWidth()
        height = self.boxHeight() 

        pen, pen2 = QtGui.QPen(), QtGui.QPen()
        pen.setWidth(7)
        pen2.setWidth(7)
        pen.setCosmetic(False)
        pen2.setCosmetic(False)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        pen2.setCapStyle(QtCore.Qt.SquareCap)
        pen.setColor(QtGui.QColor('#DDDDDD'))
        pen2.setColor(QtGui.QColor('#DDDDDD'))
        painter.setPen(pen)

        border = 50
        v_center = (height )/2
        h_center = width/2

        #paint shape
        painter.drawArc(int(h_center-10), 30, 20, 20, -35*16, 225*16)

        painter.setPen(pen2)
        painter.drawPolyline(QtCore.QPointF(h_center+6,v_center-1.8),
                             QtCore.QPointF(h_center,v_center+5),
                             QtCore.QPointF(h_center, v_center+10))

        painter.drawPoint(QtCore.QPointF(h_center, v_center+22))

class SuccessNodeGraphicsItem(NodeGraphicsItem):
    def __init__(self, type=typ.SUCCESS_NODE):
        super().__init__(type)
    
    def drawCustomShape(self, painter):
        width = self.boxWidth()
        height = self.boxHeight() 

        pen = QtGui.QPen()
        pen.setWidth(7)
        pen.setCosmetic(False)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        pen.setColor(QtGui.QColor('#2A2'))
        painter.setPen(pen)

        border = 50
        v_center = (height )/2
        h_center = width/2

        #paint shape
        painter.drawPolyline(QtCore.QPointF(h_center-20,v_center+10),
                             QtCore.QPointF(h_center,v_center+30),
                             QtCore.QPointF(h_center+20, v_center-10))

class FailureNodeGraphicsItem(NodeGraphicsItem):
    def __init__(self, type=typ.FAILURE_NODE):
        super().__init__(type)
    
    def drawCustomShape(self, painter):
        width = self.boxWidth()
        height = self.boxHeight() 

        pen = QtGui.QPen()
        pen.setWidth(7)
        pen.setCosmetic(False)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        pen.setColor(QtGui.QColor('#d56'))
        painter.setPen(pen)

        v_center = height/2 + 10
        h_center = width/2 

        #paint shape
        painter.drawPolyline(QtCore.QPointF(h_center-20,v_center-20),
                             QtCore.QPointF(h_center+20, v_center+20))

        painter.drawPolyline(QtCore.QPointF(h_center+20,v_center-20),
                             QtCore.QPointF(h_center-20, v_center+20))




class RepeatNodeGraphicsItem(NodeGraphicsItem):
    def __init__(self, type=typ.SELECTOR_NODE):
        super().__init__(type)
    
    def drawCustomShape(self, painter):
        width = self.boxWidth()
        height = self.boxHeight() 

        pen, pen2 = QtGui.QPen(), QtGui.QPen()
        pen.setWidth(7)
        pen2.setWidth(7)
        pen.setCosmetic(False)
        pen2.setCosmetic(False)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        pen2.setCapStyle(QtCore.Qt.SquareCap)
        pen.setColor(QtGui.QColor('#DDDDDD'))
        pen2.setColor(QtGui.QColor('#DDDDDD'))
        painter.setPen(pen)

        border = 50
        v_center = (height )/2
        h_center = width/2

        #paint shape
        #arc: x,y,w,h,start,stop
        shape_rect = QtCore.QRectF(int(h_center-20), 30, 40, 40)
        painter.drawArc(shape_rect, 45*16, 300*16)

        #Separate arrow lines for curved center
        painter.drawPolyline(QtCore.QPointF(h_center+10,v_center+8),
                             QtCore.QPointF(h_center+19.2,v_center+5))
        
        painter.drawPolyline(QtCore.QPointF(h_center+19.2,v_center+5),
                             QtCore.QPointF(h_center+23,v_center+13))


class RepeatNumberNodeGraphicsItem(NodeGraphicsItem):
    def __init__(self, type=typ.REPEAT_NODE, children_indexes=None):
        super().__init__(type)
        self._mapper = QtWidgets.QDataWidgetMapper()
        self._grid = QtWidgets.QGridLayout() #setLayout sets parent
        self._grid.setVerticalSpacing(2)
        self._wid = QtWidgets.QWidget()
        self._wid.setLayout(self._grid)

        #Number Repeats
        ui_row = 0
        self._grid.addWidget(QtWidgets.QLabel('Number of Repeats', self._wid), ui_row, 0)
        self._ui_number_repeats = QtWidgets.QSpinBox(self._wid)
        self._ui_number_repeats.setMinimum(0)
        self._ui_number_repeats.setMaximum(1000)
        self._ui_number_repeats.valueChanged.connect(self._mapper.submit)
        self._grid.addWidget(self._ui_number_repeats, ui_row, 1)

        #Ignore Failure
        ui_row += 1
        self._ui_ignore_failure = QtWidgets.QCheckBox("Ignore Failure")
        self._ui_ignore_failure.stateChanged.connect(self._mapper.submit)
        self._grid.addWidget(self._ui_ignore_failure, ui_row, 1)


        #Have to make the proxy after the wid otherwise size wont update right
        self._prox = QtWidgets.QGraphicsProxyWidget(self)
        self._prox.setWidget(self._wid)
        self._prox.setPos(15, 40)

    def setModelAndIndex(self, model, index):
        if hasattr(model, 'sourceModel'):model = model.sourceModel()
        self._mapper.setModel(model)
        self._mapper.addMapping(self._ui_number_repeats, col.NUMBER_REPEATS)
        self._mapper.addMapping(self._ui_ignore_failure, col.IGNORE_FAILURE)
        self._mapper.setRootIndex(index.parent())
        self._mapper.setCurrentModelIndex(index)



class RootSequenceNodeGraphicsItem(NodeGraphicsItem):
    def __init__(self, type=typ.ROOT_SEQUENCE_NODE, children_indexes=None):
        super().__init__(type)
        self._mapper = QtWidgets.QDataWidgetMapper()
        self._grid = QtWidgets.QGridLayout() #setLayout sets parent
        self._grid.setVerticalSpacing(2)
        self._wid = QtWidgets.QWidget()
        self._wid.setLayout(self._grid)

        #Name
        ui_row = 0
        self._grid.addWidget(QtWidgets.QLabel('Name', self._wid), ui_row, 0)
        self._ui_name = QtWidgets.QLineEdit('')
        self._ui_name.textChanged.connect(self._mapper.submit)
        self._grid.addWidget(self._ui_name, ui_row, 1)

        #Tick Rate
        ui_row += 1
        self._grid.addWidget(QtWidgets.QLabel('Tick Rate (ms)', self._wid), ui_row, 0)
        self._ui_tick_rate = QtWidgets.QSpinBox(self._wid)
        self._ui_tick_rate.setMinimum(100)
        self._ui_tick_rate.setMaximum(10000)
        self._ui_tick_rate.setSingleStep(100)
        self._ui_tick_rate.valueChanged.connect(self._mapper.submit)
        self._grid.addWidget(self._ui_tick_rate, ui_row, 1)

        #Manual Button New Line
        ui_row += 1
        self._ui_man_btn_new_line = QtWidgets.QCheckBox("Manual Button New Line")
        self._ui_man_btn_new_line.stateChanged.connect(self._mapper.submit)
        self._grid.addWidget(self._ui_man_btn_new_line, ui_row, 1)

        #Manual Button Span Column End
        ui_row += 1
        self._ui_man_btn_span_col_end = QtWidgets.QCheckBox("Manual Button Span Column End")
        self._ui_man_btn_span_col_end.stateChanged.connect(self._mapper.submit)
        self._grid.addWidget(self._ui_man_btn_span_col_end, ui_row, 1)

        #ui_row += 1
        #self._grid.addWidget(QtWidgets.QLabel("Set when starting behavior"), ui_row, 0, 1, 2)

        #Parameters
        #self._children = children
        #self._wids = {}
        #for child_index in children_indexes:
        #    child = child_index.internalPointer()
        #    ui_row += 1
        #    name = child.nodeName
        #    item = MappedBehaviorInput()

        #    print("child_index:", child_index, " - ", name)
        #    self._grid.addWidget(QtWidgets.QLabel(name), ui_row, 0)
        #    self._grid.addWidget(item, ui_row, 1)
        #    self._wids[name] = item


        #Have to make the proxy after the wid otherwise size wont update right
        self._prox = QtWidgets.QGraphicsProxyWidget(self)
        self._prox.setWidget(self._wid)
        self._prox.setPos(15, 40)

    def setModelAndIndex(self, model, index):
        if hasattr(model, 'sourceModel'):model = model.sourceModel()
        self._mapper.setModel(model)
        self._mapper.addMapping(self._ui_name, col.NAME)
        self._mapper.addMapping(self._ui_tick_rate, col.TICK_RATE_MS)
        self._mapper.addMapping(self._ui_man_btn_new_line, col.MAN_BTN_NEW_LINE)
        self._mapper.addMapping(self._ui_man_btn_span_col_end, col.MAN_BTN_SPAN_COL_END)
        self._mapper.setCurrentModelIndex(index)

        node = index.internalPointer()
        #self._mappers = []
        #for key in self._wids:
        #    wid = self._wids[key]

        #    for row in range(model.rowCount(index)):
        #        if hasattr(model.index(row, 0, index).internalPointer(), 'nodeName'):
        #            if key == model.index(row, 0, index).internalPointer().nodeName: #FIXME HERE

        #                mapper_1 = QtWidgets.QDataWidgetMapper()
        #                mapper_2 = QtWidgets.QDataWidgetMapper()
        #                mapper_3 = QtWidgets.QDataWidgetMapper()

        #                mapper_1.setModel(model)
        #                mapper_2.setModel(model)
        #                mapper_3.setModel(model)

        #                mapper_1.addMapping(wid, col.SET_TYPE, bytes('setType', 'ascii'))
        #                mapper_2.addMapping(wid, col.TEXT, bytes('text', 'ascii'))
        #                mapper_3.addMapping(wid, col.NEW_LINE, bytes('newLine', 'ascii'))

        #                mapper_1.setRootIndex(index)
        #                mapper_2.setRootIndex(index)
        #                mapper_3.setRootIndex(index)

        #                mapper_1.setCurrentModelIndex(model.index(row, col.SET_TYPE, index))
        #                mapper_2.setCurrentModelIndex(model.index(row, col.TEXT, index))
        #                mapper_3.setCurrentModelIndex(model.index(row, col.NEW_LINE, index))

        #                self._mappers.append(mapper_1)
        #                self._mappers.append(mapper_2)
        #                self._mappers.append(mapper_3)
        pass


class SetNodeGraphicsItem(NodeGraphicsItem):
    def __init__(self, type=typ.SET_NODE, children=None):
        super().__init__(type)
        #UI Stuff
        self._grid = QtWidgets.QGridLayout() #setLayout sets parent
        self._grid.setVerticalSpacing(1)
        self._wid = QtWidgets.QWidget()
        self._wid.setLayout(self._grid)

        self._children = children
        self._setpoints = []
        for i, child in enumerate(children):
            name = child.setName
            item = None

            if child.setIndex().internalPointer().typeInfo() in [typ.D_OUT_NODE, typ.BOOL_VAR_NODE]:
                item = MappedTriStateBoolSet(self._wid)

            elif child.setIndex().internalPointer().typeInfo() in [typ.A_OUT_NODE, typ.FLOAT_VAR_NODE]:
                item = MappedTriStateFloatSet(self._wid)


            if item:
                self._grid.addWidget(QtWidgets.QLabel(name, self._wid), i, 0)
                self._grid.addWidget(item, i, 1)
                self._setpoints.append(item)

        #Have to make the proxy after the wid otherwise size wont update right
        self._prox = QtWidgets.QGraphicsProxyWidget(self)
        self._prox.setWidget(self._wid)
        self._prox.setPos(15, 40)


    def setModelAndIndex(self, model, index):
        if hasattr(model, 'sourceModel'):model = model.sourceModel()

        #Need to populate the node list before mapping the value
        node = index.internalPointer()
        self._mappers = []

        for row in range(model.rowCount(index)):
            setpoint_wid = self._setpoints[row]
            tool_node = self._children[row].setIndex().internalPointer()
            var_node_names = []

            if tool_node.typeInfo() in [typ.D_OUT_NODE, typ.BOOL_VAR_NODE]:
                var_indexes = model.toolModel().indexesOfTypes([typ.D_IN_NODE, typ.D_OUT_NODE, typ.BOOL_VAR_NODE], model.toolIndex())
                var_node_names = [x.internalPointer().name for x in var_indexes]
                setpoint_wid.setValues([tool_node.offName, tool_node.onName])


            elif tool_node.typeInfo() in [typ.A_OUT_NODE, typ.FLOAT_VAR_NODE]:
                var_indexes = model.toolModel().indexesOfTypes([typ.A_IN_NODE, typ.A_OUT_NODE, typ.FLOAT_VAR_NODE], model.toolIndex())
                var_node_names = [x.internalPointer().name for x in var_indexes]
                setpoint_wid.setMinimum(tool_node.min)
                setpoint_wid.setMaximum(tool_node.max)


            if self._children[row].setName in var_node_names:
                var_node_names.remove(self._children[row].setName)
            setpoint_wid.setVars(var_node_names)

            mapper_1 = QtWidgets.QDataWidgetMapper()
            mapper_2 = QtWidgets.QDataWidgetMapper()
            mapper_3 = QtWidgets.QDataWidgetMapper()

            mapper_1.setModel(model)
            mapper_2.setModel(model)
            mapper_3.setModel(model)

            mapper_1.addMapping(setpoint_wid, col.SET_TYPE, bytes('setType', 'ascii'))
            mapper_2.addMapping(setpoint_wid, col.VALUE, bytes('value', 'ascii'))
            mapper_3.addMapping(setpoint_wid, col.VAR_NODE_NAME, bytes('varNodeName', 'ascii'))

            mapper_1.setRootIndex(index) #TODO why this has to be like that???
            mapper_2.setRootIndex(index)
            mapper_3.setRootIndex(index)

            mapper_1.setCurrentModelIndex(model.index(row, col.SET_TYPE, index))
            mapper_2.setCurrentModelIndex(model.index(row, col.VALUE, index))
            mapper_3.setCurrentModelIndex(model.index(row, col.VAR_NODE_NAME, index))

            self._mappers.append(mapper_1)
            self._mappers.append(mapper_2)
            self._mappers.append(mapper_3)

class WaitNodeGraphicsItem(NodeGraphicsItem):
    def __init__(self, type=typ.WAIT_NODE, children=None):
        super().__init__(type)
        #UI Stuff
        self._grid = QtWidgets.QGridLayout() #setLayout sets parent
        self._grid.setVerticalSpacing(1)
        self._wid = QtWidgets.QWidget()
        self._wid.setLayout(self._grid)
        self._timeout_mapper = QtWidgets.QDataWidgetMapper()

        ui_row = 0

        #Timeout Sec
        self._grid.addWidget(QtWidgets.QLabel('Timeout (sec)', self._wid), ui_row, 0)
        self._ui_timeout_sec = QtWidgets.QDoubleSpinBox(self._wid)
        self._ui_timeout_sec.setMinimum(0)
        self._ui_timeout_sec.setMaximum(3600)
        self._ui_timeout_sec.setSingleStep(1)
        self._ui_timeout_sec.valueChanged.connect(self._timeout_mapper.submit)
        self._grid.addWidget(self._ui_timeout_sec, ui_row, 1)


        ui_row += 1
        divider_line = QtWidgets.QFrame()
        divider_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        divider_line.setFrameShape(QtWidgets.QFrame.HLine)
        divider_line.setFixedHeight(20)
        self._grid.addWidget(divider_line, ui_row, 0,1,-1)

        ui_row += 1

        self._children = children
        self._setpoints = []
        for i, child in enumerate(children):
            name = child.setName

            if child.setIndex().internalPointer().typeInfo() in [typ.D_IN_NODE, typ.D_OUT_NODE, typ.BOOL_VAR_NODE]:
                item = MappedTriStateBoolWait(self._wid)

            elif child.setIndex().internalPointer().typeInfo() in [typ.A_IN_NODE, typ.A_OUT_NODE, typ.FLOAT_VAR_NODE]:
                item = MappedTriStateFloatWait(self._wid)

            else:
                pass #TODO raise error, generic wid??


            self._grid.addWidget(QtWidgets.QLabel(name, self._wid), ui_row, 0)
            self._grid.addWidget(item, ui_row, 1)
            self._setpoints.append(item)
            ui_row += 1


        #Have to make the proxy after the wid otherwise size wont update right
        self._prox = QtWidgets.QGraphicsProxyWidget(self)
        self._prox.setWidget(self._wid)
        self._prox.setPos(15, 40)


    def setModelAndIndex(self, model, index):
        if hasattr(model, 'sourceModel'):model = model.sourceModel()

        self._timeout_mapper.setModel(model)
        self._timeout_mapper.setRootIndex(index.parent())
        self._timeout_mapper.addMapping(self._ui_timeout_sec, col.TIMEOUT_SEC)
        self._timeout_mapper.setCurrentModelIndex(index)

        #Need to populate the node list before mapping the value
        node = index.internalPointer()
        self._mappers = []

        for row in range(model.rowCount(index)):
            setpoint_wid = self._setpoints[row]
            tool_node = self._children[row].setIndex().internalPointer()
            var_node_names = []

            if tool_node.typeInfo() in [typ.D_IN_NODE, typ.D_OUT_NODE, typ.BOOL_VAR_NODE]:
                var_indexes = model.toolModel().indexesOfTypes([typ.D_IN_NODE, typ.D_OUT_NODE, typ.BOOL_VAR_NODE], model.toolIndex())
                var_node_names = [x.internalPointer().name for x in var_indexes]
                setpoint_wid.setValues([tool_node.offName, tool_node.onName])

            elif tool_node.typeInfo() in [typ.A_IN_NODE, typ.A_OUT_NODE, typ.FLOAT_VAR_NODE]:
                var_indexes = model.toolModel().indexesOfTypes([typ.A_IN_NODE, typ.A_OUT_NODE, typ.FLOAT_VAR_NODE], model.toolIndex())
                var_node_names = [x.internalPointer().name for x in var_indexes]
                setpoint_wid.setMinimum(-100000) #TODO FIXME
                setpoint_wid.setMaximum(100000)


            if self._children[row].setName in var_node_names:
                var_node_names.remove(self._children[row].setName)
            setpoint_wid.setVars(var_node_names)

            mapper_1 = QtWidgets.QDataWidgetMapper()
            mapper_2 = QtWidgets.QDataWidgetMapper()
            mapper_3 = QtWidgets.QDataWidgetMapper()

            mapper_1.setModel(model)
            mapper_2.setModel(model)
            mapper_3.setModel(model)

            mapper_1.addMapping(setpoint_wid, col.SET_TYPE, bytes('setType', 'ascii'))
            mapper_2.addMapping(setpoint_wid, col.VALUE, bytes('value', 'ascii'))
            mapper_3.addMapping(setpoint_wid, col.VAR_NODE_NAME, bytes('varNodeName', 'ascii'))

            mapper_1.setRootIndex(index) #TODO why this has to be like that???
            mapper_2.setRootIndex(index)
            mapper_3.setRootIndex(index)

            mapper_1.setCurrentModelIndex(model.index(row, col.SET_TYPE, index))
            mapper_2.setCurrentModelIndex(model.index(row, col.VALUE, index))
            mapper_3.setCurrentModelIndex(model.index(row, col.VAR_NODE_NAME, index))

            self._mappers.append(mapper_1)
            self._mappers.append(mapper_2)
            self._mappers.append(mapper_3)





class RunBehaviorNodeGraphicsItem(NodeGraphicsItem):
    def __init__(self, type=typ.RUN_BEHAVIOR_NODE, children=[]):
        super().__init__(type)
        #UI Stuff
        self._grid = QtWidgets.QGridLayout() #setLayout sets parent
        self._grid.setVerticalSpacing(1)
        self._wid = QtWidgets.QWidget()
        self._wid.setLayout(self._grid)

        #check its a list?
        self._children = children
        self._runpoints = []

        #for each device make the stuf
        for i, child in enumerate(children):
            name = child.setName #deviceName
            item = MappedDualStateListSet(self._wid)

            self._grid.addWidget(QtWidgets.QLabel(name, self._wid), i, 0)
            self._grid.addWidget(item, i, 1)
            self._runpoints.append(item)

        #Have to make the proxy after the wid otherwise size wont update right
        self._prox = QtWidgets.QGraphicsProxyWidget(self)
        self._prox.setWidget(self._wid)
        self._prox.setPos(15, 40)


    def setModelAndIndex(self, model, index):
        if hasattr(model, 'sourceModel'):model = model.sourceModel()

        #Need to populate the node list before mapping the value
        node = index.internalPointer()
        self._mappers = []

        for row in range(model.rowCount(index)):
            runpoint_wid = self._runpoints[row]
            device_node = self._children[row].setIndex().internalPointer()


            behavior_names =  [behavior.name() for behavior in device_node.behaviors()]
            runpoint_wid.setValues(behavior_names)
            

            mapper_1 = QtWidgets.QDataWidgetMapper()
            mapper_2 = QtWidgets.QDataWidgetMapper()

            mapper_1.setModel(model)
            mapper_2.setModel(model)

            mapper_1.addMapping(runpoint_wid, col.SET_TYPE, bytes('setType', 'ascii'))
            mapper_2.addMapping(runpoint_wid, col.BEHAVIOR_NAME, bytes('value', 'ascii'))

            mapper_1.setRootIndex(index) 
            mapper_2.setRootIndex(index)

            mapper_1.setCurrentModelIndex(model.index(row, col.SET_TYPE, index))
            mapper_2.setCurrentModelIndex(model.index(row, col.BEHAVIOR_NAME, index))

            self._mappers.append(mapper_1)
            self._mappers.append(mapper_2)

class WaitStateNodeGraphicsItem(NodeGraphicsItem):
    def __init__(self, type=typ.WAIT_STATE_NODE, children=[]):
        super().__init__(type)
        #UI Stuff
        self._grid = QtWidgets.QGridLayout() #setLayout sets parent
        self._grid.setVerticalSpacing(1)
        self._wid = QtWidgets.QWidget()
        self._wid.setLayout(self._grid)
        self._timeout_mapper = QtWidgets.QDataWidgetMapper()

        ui_row = 0

        #Timeout Sec
        self._grid.addWidget(QtWidgets.QLabel('Timeout (sec)', self._wid), ui_row, 0)
        self._ui_timeout_sec = QtWidgets.QDoubleSpinBox(self._wid)
        self._ui_timeout_sec.setMinimum(0)
        self._ui_timeout_sec.setMaximum(3600)
        self._ui_timeout_sec.setSingleStep(1)
        self._ui_timeout_sec.valueChanged.connect(self._timeout_mapper.submit)
        self._grid.addWidget(self._ui_timeout_sec, ui_row, 1)


        ui_row += 1
        divider_line = QtWidgets.QFrame()
        divider_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        divider_line.setFrameShape(QtWidgets.QFrame.HLine)
        divider_line.setFixedHeight(20)
        self._grid.addWidget(divider_line, ui_row, 0,1,-1)

        ui_row += 1

        #check its a list?
        self._children = children
        self._runpoints = []

        #for each device make the stuf
        for i, child in enumerate(children):
            name = child.setName #deviceName
            item = MappedDualStateListWait(self._wid)

            self._grid.addWidget(QtWidgets.QLabel(name, self._wid), ui_row+i, 0)
            self._grid.addWidget(item, ui_row+i, 1)
            self._runpoints.append(item)

        #Have to make the proxy after the wid otherwise size wont update right
        self._prox = QtWidgets.QGraphicsProxyWidget(self)
        self._prox.setWidget(self._wid)
        self._prox.setPos(15, 40)


    def setModelAndIndex(self, model, index):
        if hasattr(model, 'sourceModel'):model = model.sourceModel()

        self._timeout_mapper.setModel(model)
        self._timeout_mapper.setRootIndex(index.parent())
        self._timeout_mapper.addMapping(self._ui_timeout_sec, col.TIMEOUT_SEC)
        self._timeout_mapper.setCurrentModelIndex(index)

        #Populate the node list before mapping the value

        node = index.internalPointer()
        self._mappers = []

        for row in range(model.rowCount(index)):
            runpoint_wid = self._runpoints[row]
            device_node = self._children[row].setIndex().internalPointer()

            runpoint_wid.setValues(device_node.states)
            
            mapper_1 = QtWidgets.QDataWidgetMapper()
            mapper_2 = QtWidgets.QDataWidgetMapper()

            mapper_1.setModel(model)
            mapper_2.setModel(model)

            mapper_1.addMapping(runpoint_wid, col.SET_TYPE, bytes('setType', 'ascii'))
            mapper_2.addMapping(runpoint_wid, col.STATE_SETPOINT, bytes('value', 'ascii'))

            mapper_1.setRootIndex(index) 
            mapper_2.setRootIndex(index)

            mapper_1.setCurrentModelIndex(model.index(row, col.SET_TYPE, index))
            mapper_2.setCurrentModelIndex(model.index(row, col.BEHAVIOR_NAME, index))

            self._mappers.append(mapper_1)
            self._mappers.append(mapper_2)

#TODO we dont use all the children hereeee
class ToleranceNodeGraphicsItem(NodeGraphicsItem):
    def __init__(self, type=typ.WAIT_NODE, children=None):
        super().__init__(type)
        #UI Stuff
        self._grid = QtWidgets.QGridLayout() #setLayout sets parent
        self._grid.setVerticalSpacing(1)
        self._wid = QtWidgets.QWidget()
        self._wid.setLayout(self._grid)
        self._timeout_mapper = QtWidgets.QDataWidgetMapper()

        ui_row = 0

        #Timeout Sec
        self._grid.addWidget(QtWidgets.QLabel('Timeout (sec)', self._wid), ui_row, 0)
        self._ui_timeout_sec = QtWidgets.QDoubleSpinBox(self._wid)
        self._ui_timeout_sec.setMinimum(0)
        self._ui_timeout_sec.setMaximum(3600)
        self._ui_timeout_sec.setSingleStep(1)
        self._ui_timeout_sec.valueChanged.connect(self._timeout_mapper.submit)
        self._grid.addWidget(self._ui_timeout_sec, ui_row, 1)

        ui_row += 1
        divider_line = QtWidgets.QFrame()
        divider_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        divider_line.setFrameShape(QtWidgets.QFrame.HLine)
        divider_line.setFixedHeight(20)
        self._grid.addWidget(divider_line, ui_row, 0,1,-1)

        ui_row += 1
        self._grid.addWidget(QtWidgets.QLabel('value,  compared_with, tolerance_scale, tolernace_offset', self._wid), ui_row, 0, 1, -1)

        ui_row += 1

        self._children = children
        self._tolerancepoints = []
        for i, child in enumerate(children):
            name = child.compare1Name

            if child.compare1Index().internalPointer().typeInfo() in [typ.A_IN_NODE, typ.A_OUT_NODE, typ.FLOAT_VAR_NODE]:
                item = MappedDualStateTolerance(self._wid)
                self._grid.addWidget(QtWidgets.QLabel(name, self._wid), ui_row, 0)
                self._grid.addWidget(item, ui_row, 1)
                self._tolerancepoints.append(item)
                ui_row += 1


        #Have to make the proxy after the wid otherwise size wont update right
        self._prox = QtWidgets.QGraphicsProxyWidget(self)
        self._prox.setWidget(self._wid)
        self._prox.setPos(15, 40)


    def setModelAndIndex(self, model, index):
        if hasattr(model, 'sourceModel'):model = model.sourceModel()

        self._timeout_mapper.setModel(model)
        self._timeout_mapper.setRootIndex(index.parent())
        self._timeout_mapper.addMapping(self._ui_timeout_sec, col.TIMEOUT_SEC)
        self._timeout_mapper.setCurrentModelIndex(index)

        #Need to populate the node list before mapping the value
        node = index.internalPointer()
        self._mappers = []

        for row in range(model.rowCount(index)):
            tool_node = self._children[row].compare1Index().internalPointer()

            if tool_node.typeInfo() in [typ.A_IN_NODE, typ.A_OUT_NODE, typ.FLOAT_VAR_NODE]:
                tolerancepoint_wid = self._tolerancepoints[row]
                var_node_names = []


                var_indexes = model.toolModel().indexesOfTypes([typ.A_IN_NODE, typ.A_OUT_NODE, typ.FLOAT_VAR_NODE], model.toolIndex())
                var_node_names = [x.internalPointer().name for x in var_indexes]


                if self._children[row].compare1Name in var_node_names:
                    var_node_names.remove(self._children[row].compare1Name)
                tolerancepoint_wid.setVars(var_node_names)

                mapper_1 = QtWidgets.QDataWidgetMapper()
                mapper_2 = QtWidgets.QDataWidgetMapper()
                mapper_3 = QtWidgets.QDataWidgetMapper()
                mapper_4 = QtWidgets.QDataWidgetMapper()
                mapper_5 = QtWidgets.QDataWidgetMapper()
                mapper_6 = QtWidgets.QDataWidgetMapper()
                mapper_7 = QtWidgets.QDataWidgetMapper()
                mapper_8 = QtWidgets.QDataWidgetMapper()

                mapper_1.setModel(model)
                mapper_2.setModel(model)
                mapper_3.setModel(model)
                mapper_4.setModel(model)
                mapper_5.setModel(model)
                mapper_6.setModel(model)
                mapper_7.setModel(model)
                mapper_8.setModel(model)

                mapper_1.addMapping(tolerancepoint_wid, col.SET_TYPE, bytes('setType', 'ascii'))
                mapper_2.addMapping(tolerancepoint_wid, col.SET_TYPE_SCALE, bytes('setTypeScale', 'ascii'))
                mapper_3.addMapping(tolerancepoint_wid, col.SET_TYPE_OFFSET, bytes('setTypeOffset', 'ascii'))
                mapper_4.addMapping(tolerancepoint_wid, col.COMPARE_2_NAME, bytes('compare2NodeName', 'ascii'))
                mapper_5.addMapping(tolerancepoint_wid, col.TOLERANCE_SCALE_VALUE, bytes('toleranceScaleValue', 'ascii'))
                mapper_6.addMapping(tolerancepoint_wid, col.TOLERANCE_SCALE_NAME, bytes('toleranceScaleNodeName', 'ascii'))
                mapper_7.addMapping(tolerancepoint_wid, col.TOLERANCE_OFFSET_VALUE, bytes('toleranceOffsetValue', 'ascii'))
                mapper_8.addMapping(tolerancepoint_wid, col.TOLERANCE_OFFSET_NAME, bytes('toleranceOffsetNodeName', 'ascii'))

                mapper_1.setRootIndex(index) 
                mapper_2.setRootIndex(index)
                mapper_3.setRootIndex(index)
                mapper_4.setRootIndex(index)
                mapper_5.setRootIndex(index)
                mapper_6.setRootIndex(index)
                mapper_7.setRootIndex(index)
                mapper_8.setRootIndex(index)

                mapper_1.setCurrentModelIndex(model.index(row, col.SET_TYPE, index))
                mapper_2.setCurrentModelIndex(model.index(row, col.SET_TYPE_SCALE, index))
                mapper_3.setCurrentModelIndex(model.index(row, col.SET_TYPE_OFFSET, index))
                mapper_4.setCurrentModelIndex(model.index(row, col.COMPARE_2_NAME, index))
                mapper_5.setCurrentModelIndex(model.index(row, col.TOLERANCE_SCALE_VALUE, index))
                mapper_6.setCurrentModelIndex(model.index(row, col.TOLERANCE_SCALE_NAME, index))
                mapper_7.setCurrentModelIndex(model.index(row, col.TOLERANCE_OFFSET_VALUE, index))
                mapper_8.setCurrentModelIndex(model.index(row, col.TOLERANCE_OFFSET_NAME, index))

                self._mappers.append(mapper_1)
                self._mappers.append(mapper_2)
                self._mappers.append(mapper_3)
                self._mappers.append(mapper_4)
                self._mappers.append(mapper_5)
                self._mappers.append(mapper_6)
                self._mappers.append(mapper_7)
                self._mappers.append(mapper_8)



class SetIconNodeGraphicsItem(NodeGraphicsItem):
    def __init__(self, type=typ.SET_ICON_NODE):
        super().__init__(type)

        self._grid = QtWidgets.QGridLayout() #setLayout sets parent
        self._grid.setVerticalSpacing(1)
        self._wid = QtWidgets.QWidget()
        self._wid.setLayout(self._grid)
        self._wid.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)

        ##Icon
        ui_row = 0
        self._setpoints = {}

        self._svg_wid = SVGWidget()
        self._svg_wid.setMinimumWidth(200)
        self._svg_wid.setMaximumWidth(400)
        self._grid.addWidget(self._svg_wid, ui_row, 0, 1, 3, alignment=QtCore.Qt.AlignCenter)

        #Icon Layer
        ui_row += 1
        self._ui_layer = MappedDualStateListSet()
        self._grid.addWidget(QtWidgets.QLabel('Icon Layer', self._wid), ui_row, 0)
        self._grid.addWidget(self._ui_layer, ui_row, 1)
        self._ui_layer.setValueCallback(self._svg_wid.setElementId) #sort of hacky
        self._setpoints['LAYER'] = self._ui_layer

        #X
        ui_row += 1
        self._ui_x = MappedTriStateIntSet(self._wid)
        self._ui_x.setMinimum(-10000)
        self._ui_x.setMaximum(10000)
        self._grid.addWidget(QtWidgets.QLabel('X Position', self._wid), ui_row, 0)
        self._grid.addWidget(self._ui_x, ui_row, 1)
        self._setpoints['X'] = self._ui_x

        #Y
        ui_row += 1
        self._ui_y = MappedTriStateIntSet(self._wid)
        self._ui_y.setMinimum(-10000)
        self._ui_y.setMaximum(10000)
        self._grid.addWidget(QtWidgets.QLabel('Y Position', self._wid), ui_row, 0)
        self._grid.addWidget(self._ui_y, ui_row, 1)
        self._setpoints['Y'] = self._ui_y

        #Scale
        ui_row += 1
        self._ui_scale = MappedTriStateFloatSet(self._wid)
        self._ui_scale.setMinimum(0.001)
        self._ui_scale.setMaximum(1000)
        self._grid.addWidget(QtWidgets.QLabel('Scale', self._wid), ui_row, 0)
        self._grid.addWidget(self._ui_scale, ui_row, 1)
        self._setpoints['SCALE'] = self._ui_scale

        #Rotation
        ui_row += 1
        self._ui_rotation = MappedTriStateFloatSet(self._wid)
        self._ui_rotation.setMinimum(-10000)
        self._ui_rotation.setMaximum(10000)
        self._grid.addWidget(QtWidgets.QLabel('Rotation', self._wid), ui_row, 0)
        self._grid.addWidget(self._ui_rotation, ui_row, 1)
        self._setpoints['ROTATION'] = self._ui_rotation

        #Has Text
        ui_row += 1
        self._ui_has_text = MappedTriStateBoolSet(self._wid)
        self._grid.addWidget(QtWidgets.QLabel('Has Text', self._wid), ui_row, 0)
        self._grid.addWidget(self._ui_has_text, ui_row, 1)
        self._setpoints['HAS_TEXT'] = self._ui_has_text

        ##Text
        ui_row += 1
        self._ui_text = MappedDualStateTextSet(self._wid)
        self._grid.addWidget(QtWidgets.QLabel('Text', self._wid), ui_row, 0)
        self._grid.addWidget(self._ui_text, ui_row, 1)
        self._setpoints['TEXT'] = self._ui_text

        #Text X
        ui_row += 1
        self._ui_text_x = MappedTriStateIntSet(self._wid)
        self._ui_text_x.setMinimum(-10000)
        self._ui_text_x.setMaximum(10000)
        self._grid.addWidget(QtWidgets.QLabel('Text X Position', self._wid), ui_row, 0)
        self._grid.addWidget(self._ui_text_x, ui_row, 1)
        self._setpoints['TEXT_X'] = self._ui_text_x

        #Text Y
        ui_row += 1
        self._ui_text_y = MappedTriStateIntSet(self._wid)
        self._ui_text_y.setMinimum(-10000)
        self._ui_text_y.setMaximum(10000)
        self._grid.addWidget(QtWidgets.QLabel('Text Y Position', self._wid), ui_row, 0)
        self._grid.addWidget(self._ui_text_y, ui_row, 1)
        self._setpoints['TEXT_Y'] = self._ui_text_y

        #Font Size
        ui_row += 1
        self._ui_font_size = MappedTriStateIntSet(self._wid)
        self._ui_font_size.setMinimum(1)
        self._ui_font_size.setMaximum(200)
        self._grid.addWidget(QtWidgets.QLabel('Font Size', self._wid), ui_row, 0)
        self._grid.addWidget(self._ui_font_size, ui_row, 1)
        self._setpoints['FONT_SIZE'] = self._ui_font_size
        self._grid.setRowStretch(ui_row+1,1)

        #Font Color
        #would need to build a MappedDualState___ that runs a color picker widget :/ 

        #Have to make the proxy after the wid otherwise size wont update right
        self._prox = QtWidgets.QGraphicsProxyWidget(self)
        self._prox.setWidget(self._wid)
        self._prox.setPos(15, 40)


    def setModelAndIndex(self, model, index):
        if hasattr(model, 'sourceModel'):model = model.sourceModel()

        #Need to populate the node list before mapping the value
        node = index.internalPointer()

        self._svg_wid.load(node.svg())
        self._ui_layer.setValues(node.layers())

        #ui_text needs the nodes, not just the names
        all_var_nodes = model.toolModel().indexesOfTypes([typ.A_IN_NODE, typ.A_OUT_NODE, typ.FLOAT_VAR_NODE, 
                                                          typ.D_IN_NODE, typ.D_OUT_NODE, typ.BOOL_VAR_NODE])

        float_var_indexes = model.toolModel().indexesOfTypes([typ.A_IN_NODE, typ.A_OUT_NODE, typ.FLOAT_VAR_NODE])
        bool_var_indexes = model.toolModel().indexesOfTypes([typ.D_IN_NODE, typ.D_OUT_NODE, typ.BOOL_VAR_NODE])

        float_var_node_names = [x.internalPointer().name for x in float_var_indexes]
        bool_var_node_names = [x.internalPointer().name for x in bool_var_indexes]

        self._ui_x.setVars(float_var_node_names)
        self._ui_y.setVars(float_var_node_names)
        self._ui_scale.setVars(float_var_node_names)
        self._ui_rotation.setVars(float_var_node_names)
        self._ui_text_x.setVars(float_var_node_names)
        self._ui_text_y.setVars(float_var_node_names)
        self._ui_text.setVars(float_var_node_names)

        self._ui_has_text.setVars(bool_var_node_names)
        self._ui_has_text.setValues(['No', 'Yes'])

        self._mappers = []

        for key in self._setpoints:
            setpoint_wid = self._setpoints[key]

            for row in range(model.rowCount(index)):
                if key == model.index(row, 0, index).internalPointer().name:

                    #A mapper can only map to a single widget
                    mapper_1 = QtWidgets.QDataWidgetMapper()
                    mapper_2 = QtWidgets.QDataWidgetMapper()
                    mapper_3 = QtWidgets.QDataWidgetMapper()

                    mapper_1.setModel(model)
                    mapper_2.setModel(model)
                    mapper_3.setModel(model)

                    mapper_1.addMapping(setpoint_wid, col.SET_TYPE, bytes('setType', 'ascii'))
                    mapper_2.addMapping(setpoint_wid, col.VALUE, bytes('value', 'ascii'))
                    mapper_3.addMapping(setpoint_wid, col.VAR_NODE_NAME, bytes('varNodeName', 'ascii'))

                    mapper_1.setRootIndex(index) #TODO why this has to be like that???
                    mapper_2.setRootIndex(index)
                    mapper_3.setRootIndex(index)

                    mapper_1.setCurrentModelIndex(model.index(row, col.SET_TYPE, index))
                    mapper_2.setCurrentModelIndex(model.index(row, col.VALUE, index))
                    mapper_3.setCurrentModelIndex(model.index(row, col.VAR_NODE_NAME, index))

                    self._mappers.append(mapper_1)
                    self._mappers.append(mapper_2)
                    self._mappers.append(mapper_3)


class AlertNodeGraphicsItem(NodeGraphicsItem):
    def __init__(self, type=typ.ALERT_NODE):
        super().__init__(type)
        self._mapper = QtWidgets.QDataWidgetMapper()

        self._grid = QtWidgets.QGridLayout()
        self._wid = QtWidgets.QWidget()
        self._wid.setLayout(self._grid)
        self._var_nodes = None

        ui_row = 0
        self._ui_text = QtWidgets.QPlainTextEdit()
        self._ui_text.setMinimumWidth(300)
        self._ui_text.setMaximumHeight(100)
        self._ui_text.textChanged.connect(self.updatePreview)
        self._grid.addWidget(self._ui_text, ui_row,0)

        ui_row += 1
        self._preview_box = QtWidgets.QTextEdit()
        self._preview_box.setMinimumWidth(300)
        self._preview_box.setMaximumHeight(100)
        self._preview_box.setReadOnly(True)
        self._grid.addWidget(self._preview_box, ui_row,0)

        ui_row += 1
        self._ui_alert_type = MappedButtonGroup()
        self._ui_alert_type.addButton("Message", 0)
        self._ui_alert_type.addButton("Warning", 1)
        self._ui_alert_type.addButton("Alarm", 2)
        self._grid.addWidget(self._ui_alert_type, ui_row,0)


        #Have to make the proxy after the wid otherwise size wont update right
        self._prox = QtWidgets.QGraphicsProxyWidget(self)
        self._prox.setWidget(self._wid)
        self._prox.setPos(15, 40)


    #FIXME need to post data
    def updatePreview(self):
        try:
            text = str(self._ui_text.toPlainText())
            evaled_dict = {}
            needed_vars = [fn for _, fn, _, _ in Formatter().parse(text) if fn is not None]

            for key in needed_vars:
                evaled_dict[key] = 123.456

            value = text.format(**evaled_dict)
            self._preview_box.setText(value)

        except (ValueError, IndexError, KeyError) as error:
            print(error) #TODO log and make sure we're catching everything we shoulld
            self._preview_box.setText('error')


    def setModelAndIndex(self, model, index):
        if hasattr(model, 'sourceModel'):model = model.sourceModel()
        self._mapper.setModel(model)
        self._mapper.setRootIndex(index.parent())
        self._mapper.addMapping(self._ui_text, col.TEXT)
        self._mapper.addMapping(self._ui_alert_type, col.ALERT_TYPE, bytes('data', 'ascii'))

        self._mapper.setCurrentModelIndex(index)

        self.updatePreview()



#pop up box with a message
class MessageNodeGraphicsItem(NodeGraphicsItem):
    def __init__(self, type=typ.MESSAGE_NODE):
        super().__init__(type)
        self._mapper = QtWidgets.QDataWidgetMapper()

        self._grid = QtWidgets.QGridLayout()
        self._wid = QtWidgets.QWidget()
        self._wid.setLayout(self._grid)
        self._var_nodes = None

        ui_row = 0
        self._ui_text = QtWidgets.QPlainTextEdit()
        self._ui_text.setMinimumWidth(300)
        self._ui_text.setMaximumHeight(100)
        self._ui_text.textChanged.connect(self.updatePreview)
        self._grid.addWidget(self._ui_text, ui_row,0)

        ui_row += 1
        self._preview_box = QtWidgets.QTextEdit()
        self._preview_box.setMinimumWidth(300)
        self._preview_box.setMaximumHeight(100)
        self._preview_box.setReadOnly(True)
        self._grid.addWidget(self._preview_box, ui_row,0)


        #Have to make the proxy after the wid otherwise size wont update right
        self._prox = QtWidgets.QGraphicsProxyWidget(self)
        self._prox.setWidget(self._wid)
        self._prox.setPos(15, 40)


    def updatePreview(self):
        try:
            text = str(self._ui_text.toPlainText())
            evaled_dict = {}
            needed_vars = [fn for _, fn, _, _ in Formatter().parse(text) if fn is not None]

            for key in needed_vars:
                evaled_dict[key] = 123.456

            value = text.format(**evaled_dict)
            self._preview_box.setText(value)

        except (ValueError, IndexError, KeyError) as error:
            print(error) #TODO log and make sure we're catching everything we shoulld
            self._preview_box.setText('error')


    def setModelAndIndex(self, model, index):
        if hasattr(model, 'sourceModel'):model = model.sourceModel()
        self._mapper.setModel(model)
        self._mapper.setRootIndex(index.parent())
        self._mapper.addMapping(self._ui_text, col.TEXT)
        self._mapper.setCurrentModelIndex(index)
        self.updatePreview()


#pop up box with a message and two buttons (returns success/fail)
class DialogNodeGraphicsItem(NodeGraphicsItem):
    def __init__(self, type=typ.DIALOG_NODE):
        super().__init__(type)
        self._mapper = QtWidgets.QDataWidgetMapper()

        self._grid = QtWidgets.QGridLayout()
        self._wid = QtWidgets.QWidget()
        self._wid.setLayout(self._grid)
        self._var_nodes = None

        ui_row = 0
        self._ui_text = QtWidgets.QPlainTextEdit()
        self._ui_text.setMinimumWidth(300)
        self._ui_text.setMaximumHeight(100)
        self._ui_text.textChanged.connect(self.updatePreview)
        self._grid.addWidget(self._ui_text, ui_row,0,1,2)

        ui_row += 1
        self._preview_box = QtWidgets.QTextEdit()
        self._preview_box.setMinimumWidth(300)
        self._preview_box.setMaximumHeight(100)
        self._preview_box.setReadOnly(True)
        self._grid.addWidget(self._preview_box, ui_row,0,1,2)

        ui_row += 1
        self._ui_success_text = QtWidgets.QLineEdit()
        self._grid.addWidget(QtWidgets.QLabel("Success Button"), ui_row,0)
        self._grid.addWidget(self._ui_success_text, ui_row,1)

        ui_row += 1
        self._ui_fail_text = QtWidgets.QLineEdit()
        self._grid.addWidget(QtWidgets.QLabel("Fail Button"), ui_row,0)
        self._grid.addWidget(self._ui_fail_text, ui_row,1)


        #Have to make the proxy after the wid otherwise size wont update right
        self._prox = QtWidgets.QGraphicsProxyWidget(self)
        self._prox.setWidget(self._wid)
        self._prox.setPos(15, 40)


    def updatePreview(self):
        try:
            text = str(self._ui_text.toPlainText())
            evaled_dict = {}
            needed_vars = [fn for _, fn, _, _ in Formatter().parse(text) if fn is not None]

            for key in needed_vars:
                evaled_dict[key] = 123.456

            value = text.format(**evaled_dict)
            self._preview_box.setText(value)

        except (ValueError, IndexError, KeyError) as error:
            print(error) #TODO log and make sure we're catching everything we shoulld
            self._preview_box.setText('error')


    def setModelAndIndex(self, model, index):
        if hasattr(model, 'sourceModel'):model = model.sourceModel()
        self._mapper.setModel(model)
        self._mapper.setRootIndex(index.parent())
        self._mapper.addMapping(self._ui_text, col.TEXT)
        self._mapper.addMapping(self._ui_success_text, col.SUCCESS_TEXT)
        self._mapper.addMapping(self._ui_fail_text, col.FAIL_TEXT)
        self._mapper.setCurrentModelIndex(index)
        self.updatePreview()




class WaitTimeNodeGraphicsItem(NodeGraphicsItem):
    def __init__(self, type=typ.WAIT_TIME_NODE):
        super().__init__(type)
        self._mapper = QtWidgets.QDataWidgetMapper()

        self._layout = QtWidgets.QHBoxLayout()
        self._wid = QtWidgets.QWidget()
        self._wid.setLayout(self._layout)

        self._layout.addWidget(QtWidgets.QLabel("Time (sec):"))
        self._ui_time = QtWidgets.QDoubleSpinBox()
        self._ui_time.setMinimum(0)
        self._ui_time.setMaximum(3600)
        self._layout.addWidget(self._ui_time)

        self._prox = QtWidgets.QGraphicsProxyWidget(self)
        self._prox.setWidget(self._wid)
        self._prox.setPos(15, 40)

        #Sometime figure out how to style this box with these
        #self.wait_time_item.setDefaultTextColor(self._title_color)
        #self.wait_time_item.setFont(self._title_font2)
        #self.wait_time_item.setTextWidth(self.width - 2 * self.title_horizontal_padding)


    def setModelAndIndex(self, model, index):
        if hasattr(model, 'sourceModel'):model = model.sourceModel()
        #self._wid = QtWidgets.QWidget()
        self._mapper.setModel(model)
        self._mapper.setRootIndex(index.parent())
        self._mapper.addMapping(self._ui_time, col.WAIT_TIME)
        self._mapper.setCurrentModelIndex(index)


class SetDeviceStateGraphicsItem(NodeGraphicsItem):
    def __init__(self, type=typ.SET_DEVICE_STATE_NODE):
        super().__init__(type)
        self._mapper = QtWidgets.QDataWidgetMapper()

        self._layout = QtWidgets.QHBoxLayout()
        self._wid = QtWidgets.QWidget()
        self._wid.setLayout(self._layout)

        self._ui_state = QtWidgets.QComboBox()
        self._ui_state.setMinimumWidth(200)
        self._ui_state.currentIndexChanged.connect(self._mapper.submit)
        self._layout.addWidget(self._ui_state)

        self._prox = QtWidgets.QGraphicsProxyWidget(self)
        self._prox.setWidget(self._wid)
        self._prox.setPos(15, 40)

    def setStates(self, states):
        self._ui_state.clear()
        self._ui_state.addItems(states)

    def setModelAndIndex(self, model, index):
        if hasattr(model, 'sourceModel'):model = model.sourceModel()

        node = index.internalPointer()
        self.setStates(node.states())
        self._mapper.setModel(model)
        self._mapper.setRootIndex(index.parent())
        self._mapper.addMapping(self._ui_state, col.DEVICE_STATE)
        self._mapper.setCurrentModelIndex(index)


class MappedBase(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.setupUI()

    def postData(self):
        QtWidgets.QApplication.postEvent(self, QtGui.QKeyEvent(QtCore.QEvent.KeyPress, QtCore.Qt.Key_Enter, QtCore.Qt.NoModifier))

    def addButton(self, text, id):
        btn = QtWidgets.QRadioButton(text)
        btn.clicked.connect(self.postData)
        self._layout.addWidget(btn)
        self._button_group.addButton(btn, id)

class MappedTriStateBoolSet(MappedBase):
    def __init__(self, parent=None):
        super().__init__(parent)

    def setupUI(self):
        self._button_group = QtWidgets.QButtonGroup()
        self._layout = QtWidgets.QHBoxLayout()

        self.addButton("", bt.NO_SET)
        self.addButton("", bt.VAL)
        self.addButton("", bt.VAR)

        self._value_box = QtWidgets.QComboBox()
        self._value_box.setMinimumWidth(150)
        self._value_box.currentIndexChanged.connect(self.postData)
        self._layout.addWidget(self._value_box)

        self._var_box = QtWidgets.QComboBox()
        self._var_box.setMinimumWidth(150)
        self._var_box.currentIndexChanged.connect(self.postData)
        self._layout.addWidget(self._var_box)
        self._layout.addStretch()

        self._layout.setContentsMargins(0,0,0,0)
        self.setLayout(self._layout)

    def setVars(self, value):
        self._var_box.clear()
        self._var_box.addItems(value)

    def setValues(self, value):
        self._value_box.clear()
        self._value_box.addItems(value)

    def getDataSetType(self):
        set_type = self._button_group.checkedId()
        return set_type

    def setDataSetType(self, set_type):
        self._value_box.setEnabled(False)
        self._value_box.setVisible(False)
        self._var_box.setEnabled(False)
        self._var_box.setVisible(False)

        if   bt.set_type(set_type) == bt.VAR:
            self._var_box.setEnabled(True)
            self._var_box.setVisible(True)
        elif bt.set_type(set_type) == bt.VAL:
            self._value_box.setEnabled(True)
            self._value_box.setVisible(True)

        self._button_group.button(bt.set_type(set_type)).setChecked(True)
        self.adjustSize()
        self.parent().adjustSize()

    def getDataValue(self):
        return self._value_box.currentIndex()

    def setDataValue(self, value):
        self._value_box.setCurrentIndex(value)

    def getDataVarNodeName(self):
        return self._var_box.currentText()

    def setDataVarNodeName(self, value):
        self._var_box.setCurrentText(value)

    setType = QtCore.pyqtProperty(QtCore.QVariant, getDataSetType, setDataSetType)
    value = QtCore.pyqtProperty(QtCore.QVariant, getDataValue, setDataValue)
    varNodeName = QtCore.pyqtProperty(QtCore.QVariant, getDataVarNodeName, setDataVarNodeName)

class MappedTriStateBoolWait(MappedTriStateBoolSet):
    def __init__(self, parent=None):
        super().__init__(parent)

    def setupUI(self):
        self._button_group = QtWidgets.QButtonGroup()
        self._layout = QtWidgets.QHBoxLayout()

        self.addButton("", bt.NO_SET)
        self.addButton("", bt.VAL)
        self.addButton("", bt.VAR)

        self._equality_box = QtWidgets.QComboBox()
        self._equality_box.currentIndexChanged.connect(self.postData)
        self._equality_box.addItem("=")
        self._equality_box.addItem("!=")
        self._layout.addWidget(self._equality_box)
        self._layout.addStretch()

        self._value_box = QtWidgets.QComboBox()
        self._value_box.setMinimumWidth(150)
        self._value_box.currentIndexChanged.connect(self.postData)
        self._layout.addWidget(self._value_box)

        self._var_box = QtWidgets.QComboBox()
        self._var_box.setMinimumWidth(150)
        self._var_box.currentIndexChanged.connect(self.postData)
        self._layout.addWidget(self._var_box)
        self._layout.addStretch()

        self._layout.setContentsMargins(0,0,0,0)
        self.setLayout(self._layout)


    def getDataSetType(self):
        set_type = self._button_group.checkedId()
        if set_type >= 0:
            if   self._equality_box.currentText() ==  "=": set_type += bt.EQUAL
            elif self._equality_box.currentText() == "!=": set_type += bt.NOT_EQUAL

        return set_type

    def setDataSetType(self, set_type):
        self._value_box.setEnabled(False)
        self._var_box.setEnabled(False)
        self._equality_box.setEnabled(False)
        self._value_box.setVisible(False)
        self._var_box.setVisible(False)
        self._equality_box.setVisible(False)

        if   bt.set_type(set_type) == bt.VAR:
            self._var_box.setEnabled(True)
            self._var_box.setVisible(True)
        elif bt.set_type(set_type) == bt.VAL:
            self._value_box.setEnabled(True)
            self._value_box.setVisible(True)

        self._button_group.button(bt.set_type(set_type)).setChecked(True)

        if bt.set_type(set_type) in [bt.VAL, bt.VAR]:
            self._equality_box.blockSignals(True)
            self._equality_box.setEnabled(True)
            self._equality_box.setVisible(True)

            equal_type = bt.equality(set_type)
            if   equal_type == bt.EQUAL              : self._equality_box.setCurrentText( "=")
            elif equal_type == bt.NOT_EQUAL          : self._equality_box.setCurrentText("!=")
            self._equality_box.blockSignals(False)

        self.adjustSize()
        self.parent().adjustSize()

    setType = QtCore.pyqtProperty(QtCore.QVariant, getDataSetType, setDataSetType)

class MappedTriStateFloatSet(MappedBase):
    def __init__(self, parent=None):
        super().__init__(parent)

    def setupUI(self):
        self._button_group = QtWidgets.QButtonGroup()
        self._layout = QtWidgets.QHBoxLayout()

        self.addButton("", bt.NO_SET)
        self.addButton("", bt.VAL)
        self.addButton("", bt.VAR)

        self._value_box = QtWidgets.QDoubleSpinBox()
        self._layout.addWidget(self._value_box)

        self._var_box = QtWidgets.QComboBox()
        self._var_box.setMinimumWidth(150)
        self._var_box.currentIndexChanged.connect(self.postData)
        self._layout.addWidget(self._var_box)
        self._layout.addStretch()

        self._layout.setContentsMargins(0,0,0,0)
        self.setLayout(self._layout)

    def setMinimum(self, value):
        self._value_box.setMinimum(value)

    def setMaximum(self, value):
        self._value_box.setMaximum(value)

    def setVars(self, value):
        self._var_box.clear()
        self._var_box.addItems(value)

    def getDataSetType(self):
        set_type = self._button_group.checkedId()
        return set_type


    def setDataSetType(self, set_type):
        self._value_box.setEnabled(False)
        self._value_box.setVisible(False)
        self._var_box.setEnabled(False)
        self._var_box.setVisible(False)

        if   bt.set_type(set_type) == bt.VAL:
            self._value_box.setEnabled(True)
            self._value_box.setVisible(True)
        elif bt.set_type(set_type) == bt.VAR:
            self._var_box.setEnabled(True)
            self._var_box.setVisible(True)

        self._button_group.button(bt.set_type(set_type)).setChecked(True)
        self.adjustSize()
        self.parent().adjustSize()

    def getDataValue(self):
        return self._value_box.value()

    def setDataValue(self, value):
        self._value_box.setValue(value)

    def getDataVarNodeName(self):
        return self._var_box.currentText()

    def setDataVarNodeName(self, value):
        self._var_box.setCurrentText(value)

    setType = QtCore.pyqtProperty(QtCore.QVariant, getDataSetType, setDataSetType)
    value = QtCore.pyqtProperty(QtCore.QVariant, getDataValue, setDataValue)
    varNodeName = QtCore.pyqtProperty(QtCore.QVariant, getDataVarNodeName, setDataVarNodeName)

class MappedTriStateIntSet(MappedTriStateFloatSet):
    def __init__(self, parent=None):
        super().__init__(parent)

    def setupUI(self):
        self._button_group = QtWidgets.QButtonGroup()
        self._layout = QtWidgets.QHBoxLayout()

        self.addButton("", bt.NO_SET)
        self.addButton("", bt.VAL)
        self.addButton("", bt.VAR)

        self._value_box = QtWidgets.QSpinBox()
        self._layout.addWidget(self._value_box)

        self._var_box = QtWidgets.QComboBox()
        self._var_box.setMinimumWidth(150)
        self._var_box.currentIndexChanged.connect(self.postData)
        self._layout.addWidget(self._var_box)
        self._layout.addStretch()

        self._layout.setContentsMargins(0,0,0,0)
        self.setLayout(self._layout)

class MappedTriStateFloatWait(MappedTriStateFloatSet):
    def __init__(self, parent=None):
        super().__init__(parent)

    def setupUI(self):
        self._button_group = QtWidgets.QButtonGroup()
        self._layout = QtWidgets.QHBoxLayout()

        self.addButton("", bt.NO_SET)
        self.addButton("", bt.VAL)
        self.addButton("", bt.VAR)

        self._equality_box = QtWidgets.QComboBox()
        self._equality_box.currentIndexChanged.connect(self.postData)
        self._equality_box.addItem("=")
        self._equality_box.addItem("!=")
        self._equality_box.addItem(">")
        self._equality_box.addItem("≥")
        self._equality_box.addItem("<")
        self._equality_box.addItem("≤")
        self._layout.addWidget(self._equality_box)


        self._value_box = QtWidgets.QDoubleSpinBox()
        #self._value_box.currentIndexChanged.connect(self.postData)
        self._layout.addWidget(self._value_box)

        self._var_box = QtWidgets.QComboBox()
        self._var_box.setMinimumWidth(150)
        self._var_box.currentIndexChanged.connect(self.postData)
        self._layout.addWidget(self._var_box)
        self._layout.addStretch()

        self._layout.setContentsMargins(0,0,0,0)
        self.setLayout(self._layout)


    def getDataSetType(self):
        set_type = self._button_group.checkedId()
        if set_type >= 0:
            if   self._equality_box.currentText() ==  "=": set_type += bt.EQUAL
            elif self._equality_box.currentText() == "!=": set_type += bt.NOT_EQUAL
            elif self._equality_box.currentText() ==  ">": set_type += bt.GREATER_THAN
            elif self._equality_box.currentText() ==  "≥": set_type += bt.GREATER_THAN_EQUAL
            elif self._equality_box.currentText() ==  "<": set_type += bt.LESS_THAN
            elif self._equality_box.currentText() ==  "≤": set_type += bt.LESS_THAN_EQUAL

        return set_type


    def setDataSetType(self, set_type):
        self._value_box.setEnabled(False)
        self._var_box.setEnabled(False)
        self._equality_box.setEnabled(False)
        self._value_box.setVisible(False)
        self._var_box.setVisible(False)
        self._equality_box.setVisible(False)

        if   bt.set_type(set_type) == bt.VAR:
            self._var_box.setEnabled(True)
            self._var_box.setVisible(True)
        elif bt.set_type(set_type) == bt.VAL:
            self._value_box.setEnabled(True)
            self._value_box.setVisible(True)

        self._button_group.button(bt.set_type(set_type)).setChecked(True)

        if bt.set_type(set_type) in [bt.VAL, bt.VAR]:
            self._equality_box.blockSignals(True)
            self._equality_box.setEnabled(True)
            self._equality_box.setVisible(True)

            equal_type = bt.equality(set_type)
            if   equal_type == bt.EQUAL              : self._equality_box.setCurrentText( "=")
            elif equal_type == bt.NOT_EQUAL          : self._equality_box.setCurrentText("!=")
            elif equal_type == bt.GREATER_THAN       : self._equality_box.setCurrentText( ">")
            elif equal_type == bt.GREATER_THAN_EQUAL : self._equality_box.setCurrentText( "≥")
            elif equal_type == bt.LESS_THAN          : self._equality_box.setCurrentText( "<")
            elif equal_type == bt.LESS_THAN_EQUAL    : self._equality_box.setCurrentText( "≤")
            self._equality_box.blockSignals(False)
        
        self.adjustSize()
        self.parent().adjustSize()

    setType = QtCore.pyqtProperty(QtCore.QVariant, getDataSetType, setDataSetType) #need this so it runs these get and sets

class MappedDualStateListSet(MappedBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value_callback = None

    def setupUI(self):
        self._button_group = QtWidgets.QButtonGroup()
        self._layout = QtWidgets.QHBoxLayout()

        self.addButton("", bt.NO_SET)
        self.addButton("", bt.VAL)
        third_button_spacer = QtWidgets.QSpacerItem(28, 1, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self._layout.addItem(third_button_spacer) #28 pixels seems clos3

        self._value_box = QtWidgets.QComboBox()
        self._value_box.setMinimumWidth(150)
        self._value_box.currentIndexChanged.connect(self.postData)
        self._layout.addWidget(self._value_box)
        self._layout.addStretch()

        self._layout.setContentsMargins(0,0,0,0)
        self.setLayout(self._layout)


    def setValueCallback(self, callback):
        self._value_callback = callback

    def setValues(self, value):
        self._value_box.clear()
        self._value_box.addItems(value)

    def getDataSetType(self):
        set_type = self._button_group.checkedId()
        return set_type

    def setDataSetType(self, set_type):
        self._value_box.setEnabled(False)
        self._value_box.setVisible(False)

        if bt.set_type(set_type) == bt.VAL:
            self._value_box.setEnabled(True)
            self._value_box.setVisible(True)

        self._button_group.button(bt.set_type(set_type)).setChecked(True)
        self.parent().adjustSize()

    def getDataValue(self):
        return self._value_box.currentText()

    def setDataValue(self, value):
        if self._value_box.findText(str(value)) >= 0:
            self._value_box.setCurrentText(value)

        if self._value_callback is not None:
            self._value_callback(str(self._value_box.currentText()))

    def getDataVarNodeName(self):
        return None

    def setDataVarNodeName(self, value):
        pass

    setType = QtCore.pyqtProperty(QtCore.QVariant, getDataSetType, setDataSetType)
    value = QtCore.pyqtProperty(QtCore.QVariant, getDataValue, setDataValue)
    varNodeName = QtCore.pyqtProperty(QtCore.QVariant, getDataVarNodeName, setDataVarNodeName)

class MappedDualStateListWait(MappedBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value_callback = None

    def setupUI(self):
        self._button_group = QtWidgets.QButtonGroup()
        self._layout = QtWidgets.QHBoxLayout()

        self.addButton("", bt.NO_SET)
        self.addButton("", bt.VAL)

        self._equality_box = QtWidgets.QComboBox()
        self._equality_box.currentIndexChanged.connect(self.postData)
        self._equality_box.addItem("=")
        self._equality_box.addItem("!=")
        self._layout.addWidget(self._equality_box)
        self._layout.addStretch()

        third_button_spacer = QtWidgets.QSpacerItem(28, 1, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self._layout.addItem(third_button_spacer) #28 pixels seems clos3

        self._value_box = QtWidgets.QComboBox()
        self._value_box.setMinimumWidth(150)
        self._value_box.currentIndexChanged.connect(self.postData)
        self._layout.addWidget(self._value_box)
        self._layout.addStretch()

        self._layout.setContentsMargins(0,0,0,0)
        self.setLayout(self._layout)


    def setValueCallback(self, callback):
        self._value_callback = callback

    def setValues(self, value):
        self._value_box.clear()
        self._value_box.addItems(value)

    def getDataSetType(self):
        set_type = self._button_group.checkedId()
        if set_type >= 0:
            if   self._equality_box.currentText() ==  "=": set_type += bt.EQUAL
            elif self._equality_box.currentText() == "!=": set_type += bt.NOT_EQUAL

        return set_type

    def setDataSetType(self, set_type):
        self._value_box.setEnabled(False)
        self._value_box.setVisible(False)
        self._equality_box.setEnabled(False)
        self._equality_box.setVisible(False)

        if bt.set_type(set_type) == bt.VAL:
            self._value_box.setEnabled(True)
            self._value_box.setVisible(True)

        self._button_group.button(bt.set_type(set_type)).setChecked(True)


        if bt.set_type(set_type) == bt.VAL:
            self._equality_box.blockSignals(True)
            self._equality_box.setEnabled(True)
            self._equality_box.setVisible(True)

            equal_type = bt.equality(set_type)
            if   equal_type == bt.EQUAL              : self._equality_box.setCurrentText( "=")
            elif equal_type == bt.NOT_EQUAL          : self._equality_box.setCurrentText("!=")
            self._equality_box.blockSignals(False)



        self.parent().adjustSize()

    def getDataValue(self):
        return self._value_box.currentText()

    def setDataValue(self, value):
        if self._value_box.findText(str(value)) >= 0:
            self._value_box.setCurrentText(value)

        if self._value_callback is not None:
            self._value_callback(str(self._value_box.currentText()))

    def getDataVarNodeName(self):
        return None

    def setDataVarNodeName(self, value):
        pass

    setType = QtCore.pyqtProperty(QtCore.QVariant, getDataSetType, setDataSetType)
    value = QtCore.pyqtProperty(QtCore.QVariant, getDataValue, setDataValue)
    varNodeName = QtCore.pyqtProperty(QtCore.QVariant, getDataVarNodeName, setDataVarNodeName)

class MappedDualStateTextSet(MappedBase):
    def __init__(self, parent=None):
        super().__init__(parent)

    def setupUI(self):
        self._button_group = QtWidgets.QButtonGroup()
        self._layout = QtWidgets.QHBoxLayout()

        self.addButton("", bt.NO_SET)
        self.addButton("", bt.VAL)
        third_button_spacer = QtWidgets.QSpacerItem(28, 1, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self._layout.addItem(third_button_spacer) #28 pixels seems clos3

        self._value_box = QtWidgets.QLineEdit()
        self._value_box.setMinimumWidth(50)
        self._value_box.editingFinished.connect(self.postData)
        self._value_box.textChanged.connect(self.updatePreview)
        self._layout.addWidget(self._value_box)

        self._preview_box = QtWidgets.QLabel()
        self._preview_box.setStyleSheet("border: 1px solid gray;")
        self._preview_box.setMinimumWidth(50)
        self._layout.addWidget(self._preview_box)
        self._layout.addStretch()

        self._layout.setContentsMargins(0,0,0,0)
        self.setLayout(self._layout)


    def updatePreview(self):
        try:
            text = str(self._value_box.text())
            evaled_dict = {}
            needed_vars = [fn for _, fn, _, _ in Formatter().parse(text) if fn is not None]

            for key in needed_vars:
                evaled_dict[key] = 123.456

            value = text.format(**evaled_dict)
            self._preview_box.setText(value)

        except (ValueError, IndexError, KeyError) as error:
            print(error) #TODO log and make sure we're catching everything we shoulld
            self._preview_box.setText('error')


    def setVars(self, value):
        self._vars = value


    def getDataSetType(self):
        set_type = self._button_group.checkedId()
        return set_type

    def setDataSetType(self, set_type):
        self._value_box.setEnabled(False)
        self._value_box.setVisible(False)
        self._preview_box.setVisible(False)

        if bt.set_type(set_type) == bt.VAL:
            self._value_box.setEnabled(True)
            self._value_box.setVisible(True)
            self._preview_box.setVisible(True)

        self._button_group.button(bt.set_type(set_type)).setChecked(True)
        self.adjustSize()
        self.parent().adjustSize()

    def getDataValue(self):
        return self._value_box.text()

    def setDataValue(self, value):
        self._value_box.setText(str(value))


    setType = QtCore.pyqtProperty(QtCore.QVariant, getDataSetType, setDataSetType)
    value = QtCore.pyqtProperty(QtCore.QVariant, getDataValue, setDataValue)
    varNodeName = QtCore.pyqtProperty(QtCore.QVariant, None, None)


class MappedButtonGroup(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)

        self._button_group = QtWidgets.QButtonGroup()
        self._layout = QtWidgets.QHBoxLayout()
        self._layout.setContentsMargins(0,0,0,0)
        self.setLayout(self._layout)

    def postData(self):
        QtWidgets.QApplication.postEvent(self, QtGui.QKeyEvent(QtCore.QEvent.KeyPress, QtCore.Qt.Key_Enter, QtCore.Qt.NoModifier))

    def addButton(self, text, id):
        btn = QtWidgets.QRadioButton(text)
        btn.clicked.connect(self.postData)
        self._layout.addWidget(btn)
        self._button_group.addButton(btn, id)

    def getData(self):
        return self._button_group.checkedId()

    def setData(self, button_id):
        self._button_group.button(button_id).setChecked(True)

    data = QtCore.pyqtProperty(QtCore.QVariant, getData, setData)


class MappedDualStateTolerance(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.setupUI()

    def postData(self):
        QtWidgets.QApplication.postEvent(self, QtGui.QKeyEvent(QtCore.QEvent.KeyPress, QtCore.Qt.Key_Enter, QtCore.Qt.NoModifier))

    def addButton(self, text, id, group, layout):
        btn = QtWidgets.QRadioButton(text)
        btn.clicked.connect(self.postData)
        layout.addWidget(btn)
        group.addButton(btn, id)


    def setupUI(self):
        self._has_tolerance = QtWidgets.QCheckBox()
        self._button_group_scale = QtWidgets.QButtonGroup()
        self._button_group_offset = QtWidgets.QButtonGroup()

        self._layout = QtWidgets.QHBoxLayout()

        self._has_tolerance.toggled.connect(self.postData)
        self._layout.addWidget(self._has_tolerance)

        self._compare_2_box = QtWidgets.QComboBox()
        self._compare_2_box.setMinimumWidth(150)
        self._compare_2_box.currentIndexChanged.connect(self.postData)
        self._layout.addWidget(self._compare_2_box)



        self._scale_wid = QtWidgets.QWidget()
        self._scale_layout = QtWidgets.QHBoxLayout()
        self._scale_wid.setLayout(self._scale_layout)
        self._layout.addWidget(self._scale_wid)

        self.addButton("", bt.NO_SET, self._button_group_scale, self._scale_layout)
        self.addButton("", bt.VAL, self._button_group_scale, self._scale_layout)
        self.addButton("", bt.VAR, self._button_group_scale, self._scale_layout)

        self._tolerance_scale_value_box = PercentDoubleSpinBox()
        #self._tolerance_value_box.valueChanged.connect(self.postData)
        self._scale_layout.addWidget(self._tolerance_scale_value_box)

        self._tolerance_scale_box = QtWidgets.QComboBox()
        self._tolerance_scale_box.setMinimumWidth(150)
        self._tolerance_scale_box.currentIndexChanged.connect(self.postData)
        self._scale_layout.addWidget(self._tolerance_scale_box)



        self._offset_wid = QtWidgets.QWidget()
        self._offset_layout = QtWidgets.QHBoxLayout()
        self._offset_wid.setLayout(self._offset_layout)
        self._layout.addWidget(self._offset_wid)

        self.addButton("", bt.NO_SET, self._button_group_offset, self._offset_layout)
        self.addButton("", bt.VAL, self._button_group_offset, self._offset_layout)
        self.addButton("", bt.VAR, self._button_group_offset, self._offset_layout)

        self._tolerance_offset_value_box = QtWidgets.QDoubleSpinBox()
        self._offset_layout.addWidget(self._tolerance_offset_value_box)

        self._tolerance_offset_box = QtWidgets.QComboBox()
        self._tolerance_offset_box.setMinimumWidth(150)
        self._tolerance_offset_box.currentIndexChanged.connect(self.postData)
        self._offset_layout.addWidget(self._tolerance_offset_box)



        self._layout.addStretch()
        self._layout.setContentsMargins(0,0,0,0)
        self.setLayout(self._layout)


    def setVars(self, value):
        self._compare_2_box.clear()
        self._compare_2_box.addItems(value)

        self._tolerance_scale_box.clear()
        self._tolerance_scale_box.addItems(value)

        self._tolerance_offset_box.clear()
        self._tolerance_offset_box.addItems(value)

    def getDataSetType(self):
        if self._has_tolerance.isChecked():
            return bt.VAL
        return bt.NO_SET

    def getDataSetTypeScale(self):
        set_type = self._button_group_scale.checkedId()
        return set_type

    def getDataSetTypeOffset(self):
        set_type = self._button_group_offset.checkedId()
        return set_type

    def setDataSetType(self, set_type):
        self._compare_2_box.setVisible(False)
        self._scale_wid.setVisible(False)
        self._offset_wid.setVisible(False)

        self._has_tolerance.blockSignals(True)
        self._has_tolerance.setChecked(False)

        if bt.set_type(set_type) is not bt.NO_SET:
            self._compare_2_box.setVisible(True)
            self._scale_wid.setVisible(True)
            self._offset_wid.setVisible(True)
            self._has_tolerance.setChecked(True)
        
        self._has_tolerance.blockSignals(False)

        #self._button_group.button(bt.set_type(set_type)).setChecked(True)
        self.adjustSize()
        self.parent().adjustSize()

    def setDataSetTypeScale(self, set_type):
        self._tolerance_scale_value_box.setEnabled(False)
        self._tolerance_scale_value_box.setVisible(False)
        self._tolerance_scale_box.setEnabled(False)
        self._tolerance_scale_box.setVisible(False)

        if bt.set_type(set_type) == bt.VAL:
            self._tolerance_scale_value_box.setEnabled(True)
            self._tolerance_scale_value_box.setVisible(True)
        elif bt.set_type(set_type) == bt.VAR:
            self._tolerance_scale_box.setEnabled(True)
            self._tolerance_scale_box.setVisible(True)

        self._button_group_scale.button(bt.set_type(set_type)).setChecked(True)
        self.adjustSize()
        self.parent().adjustSize()

    def setDataSetTypeOffset(self, set_type):
        self._tolerance_offset_value_box.setEnabled(False)
        self._tolerance_offset_value_box.setVisible(False)
        self._tolerance_offset_box.setEnabled(False)
        self._tolerance_offset_box.setVisible(False)

        if bt.set_type(set_type) == bt.VAL:
            self._tolerance_offset_value_box.setEnabled(True)
            self._tolerance_offset_value_box.setVisible(True)
        elif bt.set_type(set_type) == bt.VAR:
            self._tolerance_offset_box.setEnabled(True)
            self._tolerance_offset_box.setVisible(True)

        self._button_group_offset.button(bt.set_type(set_type)).setChecked(True)
        self.adjustSize()
        self.parent().adjustSize()

    def getDataCompare2NodeName(self):
        return self._compare_2_box.currentText()

    def setDataCompare2NodeName(self, value):
        self._compare_2_box.setCurrentText(value)


    def getDataToleranceScaleValue(self):
        return self._tolerance_scale_value_box.value()

    def setDataToleranceScaleValue(self, value):
        self._tolerance_scale_value_box.setValue(value)

    def getDataToleranceScaleNodeName(self):
        return self._tolerance_scale_box.currentText()

    def setDataToleranceScaleNodeName(self, value):
        self._tolerance_scale_box.setCurrentText(value)


    def getDataToleranceOffsetValue(self):
        return self._tolerance_offset_value_box.value()

    def setDataToleranceOffsetValue(self, value):
        self._tolerance_offset_value_box.setValue(value)

    def getDataToleranceOffsetNodeName(self):
        return self._tolerance_offset_box.currentText()

    def setDataToleranceOffsetNodeName(self, value):
        self._tolerance_offset_box.setCurrentText(value)


    setType = QtCore.pyqtProperty(QtCore.QVariant, getDataSetType, setDataSetType)
    setTypeScale = QtCore.pyqtProperty(QtCore.QVariant, getDataSetTypeScale, setDataSetTypeScale)
    setTypeOffset = QtCore.pyqtProperty(QtCore.QVariant, getDataSetTypeOffset, setDataSetTypeOffset)
    compare2NodeName = QtCore.pyqtProperty(QtCore.QVariant, getDataCompare2NodeName, setDataCompare2NodeName)

    toleranceScaleValue = QtCore.pyqtProperty(QtCore.QVariant, getDataToleranceScaleValue, setDataToleranceScaleValue)
    toleranceScaleNodeName = QtCore.pyqtProperty(QtCore.QVariant, getDataToleranceScaleNodeName, setDataToleranceScaleNodeName)
    toleranceOffsetValue = QtCore.pyqtProperty(QtCore.QVariant, getDataToleranceOffsetValue, setDataToleranceOffsetValue)
    toleranceOffsetNodeName = QtCore.pyqtProperty(QtCore.QVariant, getDataToleranceOffsetNodeName, setDataToleranceOffsetNodeName)






class MappedBehaviorInput(MappedBase):
    def __init__(self, parent=None):
        super().__init__(parent)

    def setupUI(self):
        self._button_group = QtWidgets.QButtonGroup()
        self._layout = QtWidgets.QHBoxLayout()

        self.addButton("", bt.NO_SET)
        self.addButton("", bt.VAL)
        self._layout.addStretch()

        self._new_line_box = QtWidgets.QCheckBox()
        self._new_line_box.stateChanged.connect(self.postData)

        self._layout.addWidget(self._new_line_box)

        self._text_box = QtWidgets.QLineEdit()
        self._text_box.setMinimumWidth(150)
        self._text_box.editingFinished.connect(self.postData)
        self._layout.addWidget(self._text_box)


        self._layout.setContentsMargins(0,0,0,0)
        self.setLayout(self._layout)

    def getDataSetType(self):
        set_type = self._button_group.checkedId()
        return set_type

    def setDataSetType(self, set_type):
        if bt.set_type(set_type) == bt.VAL:
            self._text_box.setEnabled(True)
            self._new_line_box.setEnabled(True)
        else:
            self._text_box.setEnabled(False)
            self._new_line_box.setEnabled(False)

        self._button_group.button(bt.set_type(set_type)).setChecked(True)
        self.parent().adjustSize()

    def getText(self):
        return self._text_box.text()

    def setText(self, value):
        self._text_box.setText(str(value))

    def getNewLine(self):
        return self._new_line_box.isChecked()

    def setNewLine(self, value):
        self._new_line_box.setChecked(bool(value))


    setType = QtCore.pyqtProperty(QtCore.QVariant, getDataSetType, setDataSetType)
    text = QtCore.pyqtProperty(QtCore.QVariant, getText, setText)
    newLine = QtCore.pyqtProperty(QtCore.QVariant, getNewLine, setNewLine)
