from PyQt5 import QtCore
from PyQt5.QtWidgets import QTabWidget, QFileDialog

from .DyStockSelectStrategySelectResultWidget import *
from EventEngine.DyEvent import *


class DyStockSelectSelectResultWidget(QTabWidget):

    stockSelectStrategySelectAckSignal = QtCore.pyqtSignal(type(DyEvent()))

    def __init__(self, eventEngine, paramWidget, registerSelectAckEvent=True):
        super().__init__()

        self._eventEngine = eventEngine
        self._paramWidget = paramWidget
        self._registerSelectAckEvent = registerSelectAckEvent

        self._strategyWidgets = {}
        self._windows = [] # only for show
        
        self._registerEvent()

        # 窗口事件相关
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self._closeTab)

    def _addTab(self, tabName, widget):
        self.addTab(widget, tabName)
        self._strategyWidgets[tabName] = widget

    def _refactory(self, tableWidget, params, newWindow):
        newRows = tableWidget.refactory(params)

        if newWindow:
            window = DyStockSelectSelectResultWidget(self._eventEngine, None, False)

            widget = DyStockSelectStrategySelectResultWidget(self._dataViewer, tableWidget.baseDate, tableWidget.strategyName, self._widgetParam, tableWidget.strategyClsName)
            widget.append(newRows, tableWidget.getColNames(), tableWidget.getAutoForegroundColName())

            window._addTab(tableWidget.strategyName, widget)

            window.setWindowTitle(tableWidget.strategyName)
            window.showMaximized()

            self._newWindows.append(window)
        else:
            tableWidget.append(newRows, tableWidget.getColNames())

    def _filter(self, tableWidget, filter, newWindow, highlight):
        filterRows = tableWidget.filter(filter, highlight)

        if newWindow:
            window = DyStockSelectSelectResultWidget(self._eventEngine, None, False)

            widget = DyStockSelectStrategySelectResultWidget(self._dataViewer, tableWidget.baseDate, tableWidget.strategyName, self._widgetParam, tableWidget.strategyClsName)
            widget.append(filterRows, tableWidget.getColNames(), tableWidget.getAutoForegroundColName())

            window._addTab(tableWidget.strategyName, widget)

            window.setWindowTitle(tableWidget.strategyName)
            window.showMaximized()

            self._newWindows.append(window)

    def _stockSelectStrategySelectAckHandler(self, event):
        # unpack
        strategyCls = event.data['class']
        result = event.data['result']
        baseDate = event.data['baseDate']
        if result is None: return

        # show result
        if strategyCls.chName in self._strategyWidgets:
            self._strategyWidgets[strategyCls.chName].setBaseDate(baseDate)
        else:
            # create a new widget
            widget = DyStockSelectStrategySelectResultWidget(self._eventEngine, strategyCls, baseDate, self._paramWidget)
            self._addTab(strategyCls.chName, widget)
            
        self._strategyWidgets[strategyCls.chName].appendStocks(result[1:], result[0])

        self.parentWidget().raise_()

    def _stockSelectStrategySelectAckSignalEmitWrapper(self, event):
        self.stockSelectStrategySelectAckSignal.emit(event)

    def _registerEvent(self):
        if self._registerSelectAckEvent:
            self.stockSelectStrategySelectAckSignal.connect(self._stockSelectStrategySelectAckHandler)
            self._eventEngine.register(DyEventType.stockSelectStrategySelectAck, self._stockSelectStrategySelectAckSignalEmitWrapper)

    def _unregisterEvent(self):
        if self._registerSelectAckEvent:
            self.stockSelectStrategySelectAckSignal.disconnect(self._stockSelectStrategySelectAckHandler)
            self._eventEngine.unregister(DyEventType.stockSelectStrategySelectAck, self._stockSelectStrategySelectAckSignalEmitWrapper)

    def _closeTab(self, index):
        tabName = self.tabText(index)
        self._strategyWidgets[tabName].close()

        del self._strategyWidgets[tabName]

        self.removeTab(index)

    def closeEvent(self, event):
        self._unregisterEvent()

        return super().closeEvent(event)

    def load(self, data, strategyCls):
        """
            @data: JSON data
        """
        className = data.get('class')
        if not className:
            return False

        if className != 'DyStockSelectStrategySelectResultWidget':
            return False

        window = DyStockSelectStrategySelectResultWidget(self._eventEngine, strategyCls, data['baseDate'])
        window.appendStocks(data['data']['rows'], data['data']['colNames'], autoForegroundColName=data['autoForegroundColName'])

        window.setWindowTitle('{0}[{1}]'.format(strategyCls.chName, data['baseDate']))
        window.showMaximized()

        self._windows.append(window)

        return True