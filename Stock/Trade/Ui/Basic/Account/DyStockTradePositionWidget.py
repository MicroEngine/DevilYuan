from PyQt5 import QtCore

from DyCommon.Ui.DyTableWidget import *
from EventEngine.DyEvent import *


class DyStockTradePositionWidget(DyTableWidget):
    """
        股票交易账户持仓窗口
        !!!券商接口推送的原始数据
    """
    signal = QtCore.pyqtSignal(type(DyEvent()))


    def __init__(self, eventEngine, broker):
        super().__init__(None, True, False, floatRound=3)

        self._eventEngine = eventEngine
        self._broker = broker

        self._headerSet = False

        self._registerEvent()

    def _signalEmitWrapper(self, event):
        self.signal.emit(event)

    def _registerEvent(self):
        self.signal.connect(self._stockPositionUpdateHandler)
        self._eventEngine.register(DyEventType.stockPositionUpdate + self._broker, self._signalEmitWrapper)
        self._eventEngine.register(DyEventType.stockPositionTickUpdate + self._broker, self._signalEmitWrapper)

    def _unregisterEvent(self):
        self.signal.disconnect(self._stockPositionUpdateHandler)
        self._eventEngine.unregister(DyEventType.stockPositionUpdate + self._broker, self._signalEmitWrapper)
        self._eventEngine.unregister(DyEventType.stockPositionTickUpdate + self._broker, self._signalEmitWrapper)
        
    def _stockPositionUpdateHandler(self, event):
        header = event.data['header']
        rows = event.data['rows']
        autoForegroundColName = event.data['autoForegroundHeaderName']

        if not self._headerSet:
            self.setColNames(header)
            self._headerSet = True

        self.fastAppendRows(rows, autoForegroundColName=autoForegroundColName, new=True)

    def closeEvent(self, event):
        self._unregisterEvent()

        return super().closeEvent(event)