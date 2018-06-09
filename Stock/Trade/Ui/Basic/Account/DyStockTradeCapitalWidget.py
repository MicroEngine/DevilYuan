from PyQt5 import QtCore

from DyCommon.Ui.DyTableWidget import *
from EventEngine.DyEvent import *


class DyStockTradeCapitalWidget(DyTableWidget):
    """
        股票交易账户资金状况窗口
        !!!券商接口推送的原始数据
    """
    signal = QtCore.pyqtSignal(type(DyEvent()))


    def __init__(self, eventEngine, broker):
        super().__init__(None, True, False)

        self._eventEngine = eventEngine
        self._broker = broker

        self._headerSet = False

        self._registerEvent()

    def _signalEmitWrapper(self, event):
        self.signal.emit(event)

    def _registerEvent(self):
        self.signal.connect(self._stockCapitalUpdateHandler)
        self._eventEngine.register(DyEventType.stockCapitalUpdate + self._broker, self._signalEmitWrapper)
        self._eventEngine.register(DyEventType.stockCapitalTickUpdate + self._broker, self._signalEmitWrapper)

    def _unregisterEvent(self):
        self.signal.disconnect(self._stockCapitalUpdateHandler)
        self._eventEngine.unregister(DyEventType.stockCapitalUpdate + self._broker, self._signalEmitWrapper)
        self._eventEngine.unregister(DyEventType.stockCapitalTickUpdate + self._broker, self._signalEmitWrapper)
        
    def _stockCapitalUpdateHandler(self, event):
        header = event.data['header']
        rows = event.data['rows']

        if not self._headerSet:
            self.setColNames(header)
            self._headerSet = True

        # strip
        for row in rows:
            if isinstance(row[0], str):
                row[0] = row[0].strip()

        self[0] = rows[0]

    def closeEvent(self, event):
        self._unregisterEvent()

        return super().closeEvent(event)
