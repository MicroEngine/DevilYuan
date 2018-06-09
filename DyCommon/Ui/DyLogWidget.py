from PyQt5 import QtCore
from PyQt5.QtGui import QColor

from .DyTableWidget import *
from EventEngine.DyEvent import *


class DyLogWidget(DyTableWidget):

    signal = QtCore.pyqtSignal(type(DyEvent()))

    header = ['时间','类型(错误:0,警告:0)','描述']

    def __init__(self, eventEngine=None):
        super().__init__(None, True, True)

        self._eventEngine = eventEngine

        self._errorCount = 0
        self._warningCount = 0

        self.setColNames(self.header)

        self._registerEvent()

    def _setRowForeground(self, row, data):
        if data.type == data.ind:
            self.setRowForeground(row, Qt.darkGreen)

        elif data.type == data.ind1:
            self.setRowForeground(row, QColor("#4169E1"))

        elif data.type == data.ind2:
            self.setRowForeground(row, QColor("#C71585"))

        elif data.type == data.error:
            self._errorCount += 1
            self.setRowForeground(row, Qt.red)

        elif data.type == data.warning:
            self._warningCount += 1
            self.setRowForeground(row, QColor("#FF6100"))

    def _logHandler(self, event):
        data = event.data

        savedErrorCount = self._errorCount
        savedWarningCount = self._warningCount

        self.setSortingEnabled(False)

        row = self.appendRow([data.time, data.type, data.description], disableSorting=False)

        self._setRowForeground(row, data)

        self.setSortingEnabled(True)

        # check if need to change 类型 header name
        if self._errorCount != savedErrorCount or self._warningCount != savedWarningCount:
            self.setColName(1, '类型(错误:{0},警告:{1})'.format(self._errorCount, self._warningCount))

    def _registerEvent(self):
        """ 注册GUI更新相关的事件监听 """

        if self._eventEngine is None: return

        self.signal.connect(self._logHandler)
        self._eventEngine.register(DyEventType.log, self.signal.emit)

    def append(self, logData):
        rows = [[data.time, data.type, data.description] for data in logData]
        self.fastAppendRows(rows)

        for row, data in enumerate(logData):
            self._setRowForeground(row, data)

        self.setColName(1, '类型(错误:{0},警告:{1})'.format(self._errorCount, self._warningCount))
