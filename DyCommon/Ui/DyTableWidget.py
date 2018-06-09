import re

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QAbstractItemView, QMenu, QMessageBox
from PyQt5.Qt import QAction, QCursor
import numpy as np
import pandas as pd

from DyCommon.DyCommon import *
from .DySingleEditDlg import *


class DyTableWidgetItem(QTableWidgetItem):

    def __init__(self, role):
        super().__init__()

        self._role = role

    def __lt__(self, other):
        try:
            value = float(self.data(self._role))
            otherValue = float(other.data(self._role))

            return value < otherValue
        except Exception as ex:
            return super().__lt__(other)


class DyTableWidget(QTableWidget):
    highlightBackground = QColor('#FFD700')

    def __init__(self, parent=None, readOnly=False, index=True, floatCut=True, autoScroll=True, floatRound=2):
        """
            @index: 是否要插入默认行索引（Org.）
            @floatRound: 小数点后格式化成几位, 只在@floatCut is True时有效
        """
        super().__init__(parent)

        self.setSortingEnabled(True)
        self.verticalHeader().setVisible(False)

        if readOnly:
            self.setEditTriggers(QTableWidget.NoEditTriggers)
            self.setSelectionBehavior(QAbstractItemView.SelectRows) 

        self._role = Qt.DisplayRole if readOnly else Qt.EditRole
        self.__index = index # 原始插入的行索引
        self._floatCut = floatCut
        self._floatRoundFormat = '%.{0}f'.format(floatRound)

        self._autoForegroundCol = None # 指定前景色关键列，如果此列对应的值改变时，将改变所对应行的前景色。包含'Org.'列
        self._enableAutoScroll = autoScroll

        self.setColNames([])

        self._initItemMenu()

        self._initRows()

    def _initRows(self):
        self._itemsMap = {} # 由行关键字建立的item的字典, {key: [item]}

        # mark
        self._markedItem = None
        self._markedItemOriginalBackground = None
        self._markedItemsOriginalForeground = []

        # highlight, item is one of item in one row
        self._highlightedItems = [] # [[item, [highlightedItemsOriginalForeground], [highlightedItemsOriginalBackground]]]

        # find
        self._findItems = []
        self._curFindItemPos = 0

    def _clearHighlight(self):
        # reproduce highlighed items because during cancel highlight procedure element will be deleted from @self._highlightedItems
        highlightedItems = [item[0] for item in self._highlightedItems]

        for item in highlightedItems:
            self._highlight(item)

    def _clearVisualEffects(self):
        self._mark(self._markedItem)

        self._clearHighlight()

    def __getitem__(self, indices):
        row, col = indices

        item = self._getItem(row, col)
        if item is None:
            return None

        return DyCommon.toNumber(item.data(self._role))

    def _getItem(self, row, col):
        # row
        if isinstance(row, str):
            item = None
            if row in self._itemsMap:
                item = self._itemsMap[row][0]
            if item is None:
                return None

            row = item.row()

        # column
        if isinstance(col, int):
            if self.__index:
                col += 1
        else:
            col = self._getColPos(col)

        # get item
        try:
            item = self.item(row, col)
        except:
            item = None

        return item

    def _updateItemsMap(self, rowKey, col, item):
        if rowKey not in self._itemsMap:
            self._itemsMap[rowKey] = []

        rowLen = len(self._itemsMap[rowKey])

        for i in range(rowLen, col + 1):
            self._itemsMap[rowKey].append(None)

        self._itemsMap[rowKey][col] = item

    def _getColPos(self, colName):
        for i in range(self.columnCount()):
            item = self.horizontalHeaderItem(i)

            if colName == item.text():
                return i

        return None

    def _updateItem(self, row, col, value):
        """
            Update one item, @row and @col can be string or integer. It's gengeral function.
            @col is included Org. for @col is integer, i.e. it's absolute updating.
        """
        if isinstance(row, str):
            self._updateItemByRowKey(row, col, value)
        else:
            self._updateItemByRowPos(row, col, value)

    def _updateItemByRowPos(self, row, col, value):
        if isinstance(col, str):
            colPos = self._getColPos(col)

            if colPos is None: # insert a new column with column name
                colPos = self.columnCount()

                item = QTableWidgetItem(col)
                self.setHorizontalHeaderItem(colPos, item)

            col = colPos

        # now we take it by positions
        self._updateItemByPos(row, col, value)

    def _getColPosWithCreation(self, colName):
        colPos = self._getColPos(col)

        if colPos is None: # insert a new column with column name
            colPos = self.columnCount()

            item = QTableWidgetItem(col)
            self.setHorizontalHeaderItem(colPos, item)

        return colPos

    def _setAutoRowForeground(self, item):
        if self._autoForegroundCol is None:
            return

        # ignore 'Org.' column
        if self.__index and item.column() == 0:
            return

        # get forground of reference item
        row = item.row()

        refItem = self.item(row, self._autoForegroundCol)

        if not refItem:
            return

        # set forground same as reference item
        item.setForeground(refItem.foreground())

        # we still need to go through row if value of reference item changed
        if item.column() == self._autoForegroundCol:
            # get foreground for row
            color = self.getForegroundOverride(item.data(self._role))
            if color is None:
                if item.background() == Qt.white: # for qdarkstyle
                    color = Qt.black
                else:
                    color = Qt.white

            # no foreground changed
            if item.foreground() == color:
                return

            for i in range(self.columnCount()):
                if self.__index and i == 0: continue

                item = self.item(row, i)
                if item:
                    item.setForeground(color)

    def _setItemData(self, item, value):
        """
            设置Item的值和相应的格式
            string值将会保持原始格式
        """
        assert value is None or isinstance(value, float) or isinstance(value, int) or isinstance(value, str), 'type(value) is {0}'.format(type(value))

        # set data
        if isinstance(value, float):
            if not np.isnan(value):
                if self._floatCut:
                    value = self._floatRoundFormat%value
            else:
                value = None

        item.setData(self._role, value)

        # set auto row color
        self._setAutoRowForeground(item)

        if self._enableAutoScroll:
            self.scrollToItem(item)

    def _setItemDataFast(self, item, value):
        """
            快速设置Item的值
            string值将会保持原始格式
        """
        assert value is None or isinstance(value, float) or isinstance(value, int) or isinstance(value, str), 'type(value) is {0}'.format(type(value))

        # set data
        if isinstance(value, float):
            if not np.isnan(value):
                if self._floatCut:
                    value = self._floatRoundFormat%value
            else:
                value = None

        item.setData(self._role, value)

    def _newItemByRowKey(self, rowKey, col, value):
        if rowKey in self._itemsMap:
            row = self._itemsMap[rowKey][0].row()
        else:
            row = self.rowCount()

        if isinstance(col, str):
            col = self._getColPosWithCreation(col)

        # now we take it by positions
        item = self._updateItemByPos(row, col, value)

        # update to items map
        self._updateItemsMap(rowKey, col, item)

    def _updateItemByRowKey(self, rowKey, col, value):

        isExistingItem = False

        if rowKey in self._itemsMap:
            if isinstance(col, str):
                colPos = self._getColPos(col)
            else:
                colPos = col

            if colPos is not None:
                if colPos < len(self._itemsMap[rowKey]):
                    if self._itemsMap[rowKey][colPos] is not None: # item existing
                        self._setItemData(self._itemsMap[rowKey][colPos], value)

                        isExistingItem = True

        if not isExistingItem:
            self._newItemByRowKey(rowKey, col, value)

    def _updateItemByPos(self, row, col, value):
        # get item if existing
        item = self.item(row, col)

        # new item
        if item is None:
            # enlarge
            rowCount = self.rowCount()
            colCount = self.columnCount()

            if row >= rowCount:
                self.setRowCount(row + 1)

            if col >= colCount:
                self.setColumnCount(col + 1)

            # add new item
            item = DyTableWidgetItem(self._role)
            self.setItem(row, col, item)

        # Should call @setItem firstly, then set data
        self._setItemData(item, value)

        return item
        
    def _update(self, indices, value):
        """
            Update one row by @indices is row key or row position, @value is [x, x, x, ...]
            or one item by @indices is (row key or row position, column name or column position), @value is x.
            position is from 0.
        """
        if isinstance(indices, tuple):
            row, col = indices
        else:
            row, col = indices, None # add one row

        # update Org.
        if self.__index:
            if isinstance(row, str): # row key
                if row not in self._itemsMap: # first updating
                    self._updateItem(row, 0, self.rowCount() + 1)
            else:
                if not self.item(row, 0): # first updating
                    self._updateItem(row, 0, row + 1) # value is row No. from 1
            
            offset = 1 # offset for column
        else:
            offset = 0 # offset for column

        if col is None: # row
            for col, v in enumerate(value, offset):
                self._updateItem(row, col, v)
        else: # one item
            self._updateItem(row, (col + offset) if isinstance(col, int) else col, value)

    def __setitem__(self, indices, value):
        """ add one row like obj[x] = [v,v,..]
            add one like obj[x,y] = v
        """
        self.setSortingEnabled(False)

        self._update(indices, value)

        self.resizeColumnsToContents()
        self.resizeRowsToContents()

        self.setSortingEnabled(True)

    def addColNames(self, names):

        colStart = self.columnCount()
        self.setColumnCount(colStart + len(names))

        for col, name in enumerate(names, colStart):

            colItem = self.horizontalHeaderItem(col)
            if colItem is None:
                colItem = QTableWidgetItem(col)
                self.setHorizontalHeaderItem(col, colItem)

            colItem.setText(name)

        #self.resizeColumnsToContents()

    def hasIndex(self):
        return self.__index

    def addColName(self, col, name):

        if self.__index:
            col += 1

        if col >= self.columnCount():
            self.setColumnCount(col + 1)

        colItem = self.horizontalHeaderItem(col)
        if colItem is None:
            colItem = QTableWidgetItem(col)
            self.setHorizontalHeaderItem(col, colItem)

        colItem.setText(name)
        #self.resizeColumnsToContents()

    def setHeaderForeground(self, color):
        """
            只能设置整个header
            http://stackoverflow.com/questions/36196988/color-individual-horizontal-headers-of-qtablewidget-in-pyqt
            @color: string, like 'red'
        """
        self.horizontalHeader().setStyleSheet('color:' + color)

    def setColName(self, col, name):

        if self.__index:
            col += 1

        colItem = self.horizontalHeaderItem(col)

        if colItem:
            colItem.setText(name)
            self.resizeColumnsToContents()

    def setColNames(self, names=None):
        """ @names:[name1, name2] """

        if names is None:
            return

        if self.__index:
            newNames = ['Org.'] + names
        else:
            newNames = names

        self.setColumnCount(len(newNames))

        self.setHorizontalHeaderLabels(newNames)
        self.resizeColumnsToContents()

    def setItemForeground(self, row, col, color):
        if self.__index: col += 1

        try:
            self.item(row, col).setForeground(color)
        except Exception as ex:
            pass

    def setItemBackground(self, row, col, color):
        if self.__index: col += 1

        try:
            self.item(row, col).setBackground(color)
        except Exception as ex:
            pass

    def setRowForeground(self, row, color):
        try:
            colCount = self.columnCount()

            start, end = (1, colCount) if self.__index else (0, colCount)

            for col in range(start, end):
                self.item(row, col).setForeground(color)
        except Exception as ex:
            pass

    def setRowBackground(self, row, color):
        try:
            colCount = self.columnCount()

            start, end = (1, colCount) if self.__index else (0, colCount)

            for col in range(start, end):
                self.item(row, col).setBackground(color)
        except Exception as ex:
            pass

    def append(self, rows, header=None, autoForegroundColName=None):
        """ @rows: [[x,x,x],[x,x,x],...]
            @header: [x,x,x]
        """
        self.setSortingEnabled(False)

        if header:
            self.setColNames(header)

        if autoForegroundColName:
            self.setAutoForegroundCol(autoForegroundColName)

        rowCount = self.rowCount()

        self.setRowCount(rowCount + len(rows))
        
        for rowIndex, rowData in enumerate(rows, rowCount):
            self._update(rowIndex, rowData)

        self.resizeColumnsToContents()
        self.resizeRowsToContents()

        self.setSortingEnabled(True)

    def appendRow(self, row, new=False, disableSorting=True):
        """
            @row: [x,x,x]
            @return: row position of added row(starting from 0)
        """
        if disableSorting:
            self.setSortingEnabled(False)

        if new:
            self.clearAllRows()

        rowCount = self.rowCount()
        self._update(rowCount, row)

        self.resizeColumnsToContents()
        self.resizeRowsToContents()

        if disableSorting:
            self.setSortingEnabled(True)

        return rowCount

    def setAutoForegroundCol(self, colName):
        self._autoForegroundCol = self._getColPos(colName)

    def getAutoForegroundColName(self):
        if self._autoForegroundCol is None:
            return None

        autoForegroundCol = self._autoForegroundCol - 1 if self.__index else self._autoForegroundCol

        return self.getColName(autoForegroundCol)

    def _autoScrollAct(self):
        self._enableAutoScroll = not self._enableAutoScroll

        if self._enableAutoScroll:
            self._autoScrollAction.setText('关闭自动滚动')
        else:
            self._autoScrollAction.setText('开启自动滚动')

    def _visibleMarkAct(self):
        if self._markedItem is not None:
            self.scrollToItem(self._markedItem)

    def _isInHighlight(self, item):
        row = item.row()

        for highlightedItems in self._highlightedItems:
            if highlightedItems[0].row() == row:
                return True

        return False

    def _setMark(self):
        row = self._markedItem.row()

        markBg = QColor(Qt.yellow)
        self.setRowBackground(row, markBg)

        for col in range(self.columnCount()):
            if self.__index and col == 0:
                self._markedItemsOriginalForeground.append(None)
                continue

            item = self.item(row, col)
            fg = item.foreground().color()
            
            # only change qdarkstyle default foreground
            if fg == QColor(0, 0, 0) or fg == QColor(192, 192, 192):
                item.setForeground(QColor(0, 0, 0))

            # for qdarkstyle default foreground
            if fg == QColor(0, 0, 0):
                fg = QColor(192, 192, 192)

            # save
            self._markedItemsOriginalForeground.append(fg)

    def _setHighlight(self, item):
        row = item.row()

        highlightedItemsForeground = []
        highlightedItemsBackground = []
        self._highlightedItems.append([item, highlightedItemsForeground, highlightedItemsBackground])
        for col in range(self.columnCount()):
            if self.__index and col == 0:
                highlightedItemsForeground.append(None)
                highlightedItemsBackground.append(None)
                continue

            item = self.item(row, col)
            fg = item.foreground().color()
            bg = item.background()
            
            # only change qdarkstyle default foreground
            if fg == QColor(0, 0, 0) or fg == QColor(192, 192, 192):
                item.setForeground(QColor(0, 0, 0))

            # for qdarkstyle default foreground
            if fg == QColor(0, 0, 0):
                fg = QColor(192, 192, 192)

            item.setBackground(self.highlightBackground)

            # save
            highlightedItemsForeground.append(fg)
            highlightedItemsBackground.append(bg)

    def _resetMark(self):
        row = self._markedItem.row()
        self.setRowBackground(row, self._markedItemOriginalBackground)

        for col in range(self.columnCount()):
            if self.__index and col == 0:
                continue

            item = self.item(row, col)
            # 如果标记后添加列，可能会导致超出
            if col < len(self._markedItemsOriginalForeground):
                item.setForeground(self._markedItemsOriginalForeground[col])

    def _resetHighlight(self, highlightItem):
        row = highlightItem[0].row()

        for col in range(self.columnCount()):
            if self.__index and col == 0:
                continue

            item = self.item(row, col)
            # 如果标记后添加列，可能会导致超出
            if col < len(highlightItem[1]):
                item.setForeground(highlightItem[1][col])

            # 如果标记后添加列，可能会导致超出
            if col < len(highlightItem[2]):
                item.setBackground(highlightItem[2][col])

    def markByData(self, colName, itemData):
        """
            @colName: 指定item所在的列名
            @itemData: item的数据
        """
        col = self._getColPos(colName)
        if col is None:
            return

        for row in range(self.rowCount()):
            if self[row, col] == itemData:
                item = self.item(row, col)
                self._mark(item)
                break

    def _highlightSameItemContent(self, item, clearHightlight=True):
        """
            @clearHightlight: 是否清除先前的高亮
        """
        if item is None:
            return

        if clearHightlight:
            self._clearHighlight()

        text = item.text()
        col = item.column()
        for row in range(self.rowCount()):
            item = self.item(row, col)
            if item.text() == text:
                self._highlight(item, withCancel=False)
        
    def _highlight(self, item, withCancel=True):
        """
            @withCancel: True-对已经高亮的item高亮，则清除该高亮
        """
        if item is None:
            return

        row = item.row()

        if self._markedItem is not None and self._markedItem.row() == row:
            return
        
        # 取消鼠标所在行的高亮
        cancelHighlight = False
        for i, highlightedItem in enumerate(self._highlightedItems):
            if highlightedItem[0].row() == row: # 已经高亮过了
                if not withCancel:
                    return

                self._resetHighlight(highlightedItem)
                cancelHighlight = True
                break

        if cancelHighlight:
            del self._highlightedItems[i]
            return

        # highlight
        self._setHighlight(item)

    def _mark(self, item):
        if item is None:
            return

        if self._isInHighlight(item):
            return
        
        # 取消鼠标所在行的标记
        if self._markedItem is not None and self._markedItem.row() == item.row():
            self._resetMark()
            
            self._markedItem = None
            self._markedItemsOriginalForeground = []
            return

        # unmark previous
        if self._markedItem is not None:
            self._resetMark()

            self._markedItem = None
            self._markedItemsOriginalForeground = []

        # save for new mark
        self._markedItemOriginalBackground = item.background()
        self._markedItem = item
        
        self._setMark()

    def _markAct(self):
        item = self.itemAt(self._rightClickPoint)
        
        self._mark(item)

    def _highlightAct(self):
        item = self.itemAt(self._rightClickPoint)
        
        self._highlight(item)

    def _highlightSameItemContentAct(self):
        item = self.itemAt(self._rightClickPoint)

        clearAction, notClearAction = self._highlightSameItemContentActions
        if notClearAction.isChecked():
            notClearAction.setChecked(False)
            clearHighlight = False

        else:
            clearAction.setChecked(False)
            clearHighlight = True
        
        self._highlightSameItemContent(item, clearHighlight)

    def _initItemMenu(self):
        """ 初始化Item右键菜单 """

        self._itemMenu = QMenu(self)

        self._tableCountAction = QAction('', self)
        self._itemMenu.addAction(self._tableCountAction)

        self._itemMenu.addSeparator()
        
        self._autoScrollAction = QAction('关闭自动滚动' if self._enableAutoScroll else '开启自动滚动', self)
        self._autoScrollAction.triggered.connect(self._autoScrollAct)
        self._itemMenu.addAction(self._autoScrollAction)

        self._markAction = QAction('标记', self)
        self._markAction.triggered.connect(self._markAct)
        self._itemMenu.addAction(self._markAction)

        self._visibleMarkAction = QAction('定位到标记', self)
        self._visibleMarkAction.triggered.connect(self._visibleMarkAct)
        self._itemMenu.addAction(self._visibleMarkAction)

        # item只有一种状态，要不是标记，要不就是高亮
        self._highlightAction = QAction('高亮', self)
        self._highlightAction.triggered.connect(self._highlightAct)
        self._itemMenu.addAction(self._highlightAction)

        # 高亮所有同列相同内容的item
        menu = self._itemMenu.addMenu('高亮同列相同内容的表项')
        self._highlightSameItemContentActions = [QAction('清除先前高亮', self), QAction('保留先前高亮', self)]
        for action in self._highlightSameItemContentActions:
            action.triggered.connect(self._highlightSameItemContentAct)
            action.setCheckable(True)

            menu.addAction(action)

        action = QAction('查找...', self)
        action.triggered.connect(self._findAct)
        self._itemMenu.addAction(action)

    def _findAct(self):
        data = {}
        if DySingleEditDlg(data, '查找', '要查找的内容').exec_():
            text = str(data['data'])
            
            self._findItems = self.findItems(text, Qt.MatchContains)
            self._curFindItemPos = 0

            if self._findItems:
                self.scrollToItem(self._findItems[self._curFindItemPos])
                self.setCurrentItem(self._findItems[self._curFindItemPos])
            else:
                QMessageBox.warning(self, '警告', '没有找到要查找的内容!')

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F3:
            if not self._findItems:
                QMessageBox.warning(self, '警告', '没有找到要查找的内容!')
                return

            self._curFindItemPos += 1
            self._curFindItemPos = self._curFindItemPos%len(self._findItems)

            self.scrollToItem(self._findItems[self._curFindItemPos])
            self.setCurrentItem(self._findItems[self._curFindItemPos])

    def contextMenuEvent(self, event):
        """ Item右键点击事件 """
        self._rightClickPoint = event.pos()
        item = self.itemAt(self._rightClickPoint)

        self._tableCountAction.setText('行: {0}, 列: {1}'.format(self.rowCount(), self.columnCount()))

        if item is None:
            self._markAction.setEnabled(False)
            self._highlightAction.setEnabled(False)
        
        else:
            itemState = 0 # 0: not marked or highlighted, 1: marked, 2: highlighted

            if self._markedItem is not None and self._markedItem.row() == item.row():
                itemState = 1
            else:
                for highlightedItem in self._highlightedItems:
                    if highlightedItem[0].row() == item.row():
                        itemState = 2

            if itemState == 0:
                self._markAction.setText('标记')
                self._markAction.setEnabled(True)
                self._highlightAction.setText('高亮')
                self._highlightAction.setEnabled(True)

            elif itemState == 1:
                self._markAction.setText('取消标记')
                self._markAction.setEnabled(True)
                self._highlightAction.setEnabled(False)

            else:
                self._highlightAction.setText('取消高亮')
                self._highlightAction.setEnabled(True)

                self._markAction.setEnabled(False)

        # at last, set visible mark action
        if self._markedItem is not None:
            self._visibleMarkAction.setText('定位标记')
            self._visibleMarkAction.setEnabled(True)
        else:
            self._visibleMarkAction.setEnabled(False)

        self._itemMenu.popup(QCursor.pos())

    def removeRow(self, row):
        """ remove row, which can be by index or key """

        self.setSortingEnabled(False)

        if isinstance(row, int): # remove by index

            # find item in map
            delRowKey = None
            for rowKey, items in self._itemsMap.items():
                if items[0].row() == row:
                    delRowKey = rowKey
                    break

            # remove from map
            if delRowKey is not None:
                del self._itemsMap[delRowKey]

            # remove from table widget
            super().removeRow(row)

        else: # remove by key

            # remove from map
            if row in self._itemsMap:
                delRow = self._itemsMap[row][0].row()

                del self._itemsMap[row]

                # remove from table widget
                super().removeRow(delRow)

        self.setSortingEnabled(True)

    def removeAll(self):

        rowCount = self.rowCount()

        for _ in range(rowCount):
            self.removeRow(0)

    def getAll(self):
        """ 以列表方式返回table的所有值，Org.列除外 """

        tableItems = []
        for row in range(self.rowCount()):
            rowItems = []

            colCount = (self.columnCount() - 1) if self.__index else self.columnCount()
            for col in range(colCount):
                rowItems.append(self[row, col])

            tableItems.append(rowItems)

        return tableItems

    def getHighlights(self):
        """ 以列表方式返回table所有高亮的值，Org.列除外 """

        # get sorted highlighed rows
        highlightedRows = [item[0].row() for item in self._highlightedItems]
        highlightedRows.sort()

        tableItems = []
        for row in highlightedRows:
            rowItems = []

            colCount = (self.columnCount() - 1) if self.__index else self.columnCount()
            for col in range(colCount):
                rowItems.append(self[row, col])

            tableItems.append(rowItems)

        return tableItems

    def toDataFrame(self):
        colNames = self.getColNames()
        rows = self.getAll()

        df = pd.DataFrame(rows, columns=colNames)

        return df

    def getColNames(self):
        colNames = []
        for col in range(self.columnCount()):
            headerItem = self.horizontalHeaderItem(col)
            colName = headerItem.text()
            if colName == 'Org.':
                continue

            colNames.append(colName)

        return colNames if colNames else None

    def getColName(self, col):
        if self.__index:
            col += 1

        headerItem = self.horizontalHeaderItem(col)
        if headerItem:
            return headerItem.text()

        return None
            
    def getColumnsData(self, colNames):
        """ 以列表方式返回指定列名的所有值
            @colNames: [colName]
            @return: [[data]]
        """
        # get postions of column names
        colPos = [self._getColPos(x) for x in colNames]
        colPos = [((x - 1) if self.__index else x) for x in colPos]

        tableItems = []
        for row in range(self.rowCount()):
            rowItems = []

            for col in colPos:
                rowItems.append(self[row, col])

            tableItems.append(rowItems)

        return tableItems

    def appendColumns(self, columnNames, columnsData):
        """
            @columnNames: [column name]
            @columnsData: [[column data]]
        """
        self.setSortingEnabled(False)

        # adjust start column postion for appended columns
        colStart = (self.columnCount() - 1) if self.__index else self.columnCount()

        # append column names
        for col, name in enumerate(columnNames, colStart):
            self.addColName(col, name)

        # append columns data
        for row, rowData in enumerate(columnsData):
            for col, data in enumerate(rowData, colStart):
                self._update((row, col), data)

        self.resizeColumnsToContents()
        self.resizeRowsToContents()

        # 重新设置标记
        self._renewMark()

        # 重新设置高亮
        self._renewHighlight()

        self.setSortingEnabled(True)

    def _updateAutoForegroundColForeground(self, row):
        item = self.item(row, self._autoForegroundCol)
        if item is None: return

        try:
            value = float(item.data(self._role))
        except Exception as ex:
            value = 0 # if referenced item doesn't have value or not number, think it as default 0.

        if value > 0:
            color = Qt.red
        elif value < 0:
            color = Qt.darkGreen
        else:
            if item.background() == Qt.white: # for qdarkstyle
                color = Qt.black
            else:
                color = QColor('#C0C0C0')

        item.setForeground(color)

    def updateAutoForegroundCol(self, colAbs):
        """
            @colAbs: 更新自动前景色关键列，包含'Org.' column
        """
        if isinstance(colAbs, str):
            self._autoForegroundCol = self._getColPos(colAbs)
        else:
            self._autoForegroundCol = colAbs

        if self._autoForegroundCol is None: return

        for row in range(self.rowCount()):
            # upate foreground of auto foreground column item
            self._updateAutoForegroundColForeground(row)

            refItem = self.item(row, self._autoForegroundCol)
            if refItem is None: continue

            for col in range(self.columnCount()):
                if self.__index and col == 0: # ignore 'Org.' column
                    continue

                item = self.item(row, col)
                if item is None: continue

                item.setForeground(refItem.foreground())

    def getForegroundOverride(self, value):
        """
            可由子类重载，这样可以根据不同的值设置不同的前景色
        """
        try:
            value = float(value)

            if value > 0:
                color = Qt.red
            elif value < 0:
                color = Qt.darkGreen
            else:
                color = None # default

        except Exception as ex:
            color = None

        return color

    def _getForeground(self, rowData, autoForegroundCol, item):

        # 如果@rowData的item个数小于等于@autoForegroundCol
        # 支持row数据比header少的状况
        try:
            value = rowData[autoForegroundCol]

            color = self.getForegroundOverride(value)
        except Exception as ex:
            color = None
        
        if color is None:
            if item.background() == Qt.white:
                color = Qt.black

            else: # for qdarkstyle
                color = QColor(192, 192, 192)
            
        return color

    def _updateOrg(self, row):
        if not self.__index: return

        item = self.item(row, 0)
        if item is None:
            item = DyTableWidgetItem(self._role)
            self.setItem(row, 0, item)

            item.setData(self._role, row + 1)

    def clearAllRows(self):
        self._clearVisualEffects()

        self.setRowCount(0)
        self._initRows()

    def fastAppendRows(self, rows, autoForegroundColName=None, new=False):
        """
            快速批量添加行数据，忽略细节
            调用之前，必须先设置header
            @new: 新建还是添加
        """
        self.setSortingEnabled(False)

        if new:
            self._clearVisualEffects()

            self.setRowCount(len(rows))
            rowStart = 0

            self._initRows()
        else:
            rowStart = self.rowCount()
            self.setRowCount(rowStart + len(rows))

        if autoForegroundColName is not None:
            self._autoForegroundCol = self._getColPos(autoForegroundColName)

            # column position in input raw data(@rows)
            if self._autoForegroundCol is not None:
                autoForegroundCol = self._autoForegroundCol - 1 if self.__index else self._autoForegroundCol

        offset = 1 if self.__index else 0
        item = None
        for row, rowData in enumerate(rows, rowStart):
            self._updateOrg(row)

            for col, value in enumerate(rowData, offset):
                # create new if not existing
                item = self.item(row, col)
                if item is None:
                    item = DyTableWidgetItem(self._role)
                    self.setItem(row, col, item)

                # set item data
                self._setItemDataFast(item, value)

                # set foreground
                if autoForegroundColName is not None and self._autoForegroundCol is not None:
                    if col == offset: # only get auto foreground when begining of row
                        color = self._getForeground(rowData, autoForegroundCol, item)

                    item.setForeground(color)
        
        self.resizeColumnsToContents()
        self.resizeRowsToContents()

        self.setSortingEnabled(True)

        if self._enableAutoScroll and item is not None:
            self.scrollToItem(item)

    def fastAppendColumns(self, columnNames, columnsData):
        """
            快速批量添加列数据，忽略细节
            @columnNames: [column name]
            @columnsData: [[column data]]
        """
        self.setSortingEnabled(False)

        # adjust start column postion for appended columns
        colStart = self.columnCount()

        # append column names
        self.addColNames(columnNames)

        # append columns data
        for row, rowData in enumerate(columnsData):
            for col, value in enumerate(rowData, colStart):
                # create new if not existing
                item = self.item(row, col)
                if item is None:
                    item = DyTableWidgetItem(self._role)
                    self.setItem(row, col, item)

                # set item data
                self._setItemDataFast(item, value)

                # get item of auto foreground
                if self._autoForegroundCol is None: continue
                refItem = self.item(row, self._autoForegroundCol)
                if not refItem: continue

                # set forground same as reference item
                item.setForeground(refItem.foreground())

        self.resizeColumnsToContents()
        self.resizeRowsToContents()

        # 重新设置标记
        self._renewMark()

        # 重新设置高亮
        self._renewHighlight()

        self.setSortingEnabled(True)

    def _renewMark(self):
        """
            重新设置标记
        """
        markedItem = self._markedItem

        # 先取消标记
        self._mark(markedItem)

        # 设置标记
        self._mark(markedItem)

    def _renewHighlight(self):
        """
            重新设置高亮
        """
        # reproduce highlighed items because during cancel highlight procedure element will be deleted from @self._highlightedItems
        highlightedItems = [item[0] for item in self._highlightedItems]

        for item in highlightedItems:
            # 先取消高亮
            self._highlight(item)

            # 设置高亮
            self._highlight(item)

    def setItemsForeground(self, rowKeys, colors):
        """
            @rowKeys: [rowKey] or [row number]
            @colors: ((text, color)) or [[text, color]]
        """
        for key in rowKeys:
            for col in range(self.columnCount()):

                item = self._getItem(key, col)
                if item is None: continue

                itemData = item.data(self._role)
                for text, color in colors:
                    if isinstance(itemData, str) and text in itemData:
                        item.setForeground(color)
                        break

    def filter(self, filter, highlight=False):
        """
            根据filter表达式选取行数据，filter表达式是对列进行操作。对应的列为x[0], x[1], ...
            @return: 过滤出来的数据列表
        """
        # 取消高亮
        self._clearHighlight()

        tableItems = []
        for row in range(self.rowCount()):
            rowItems = []

            colCount = (self.columnCount() - 1) if self.__index else self.columnCount()
            for col in range(colCount):
                rowItems.append(self[row, col])

            # execute filter
            try:
                x = rowItems
                if not eval(filter): # some of elements are None
                    continue
            except Exception as ex:
                continue

            if highlight:
                self._highlight(self.item(row, col))

            tableItems.append(rowItems)

        return tableItems

    def org(self, row):
        if self.__index:
            return self[row, 'Org.']

        return None

    def addColumnOperateColumns(self, exp):
        """
            根据exp表达式进行列运算（类似于Pandas），并添加列到table widget
            x代表table widget对应的DataFrame
        """
        newColumnData = []
        for row in range(self.rowCount()):
            rowItems = []

            colCount = (self.columnCount() - 1) if self.__index else self.columnCount()
            for col in range(colCount):
                rowItems.append(self[row, col])

            # execute exp
            x = rowItems
            try:
                value = eval(exp)
            except:
                value = None

            newColumnData.append([value])

        # get column name
        x = self.getColNames()
        try:
            p = re.compile('x\[\d+\]')
            elements = p.findall(exp)

            elements_ = []
            for v in elements:
                elements_.append('[' + eval(v) + ']')

            expFormat = p.sub('{}', exp)

            newColumnName = expFormat.format(*elements_)
        except:
            newColumnName = exp

        # add columns into table widget
        self.fastAppendColumns([newColumnName], newColumnData)