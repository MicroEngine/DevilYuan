from PyQt5 import QtCore

from DyCommon.Ui.DyTableWidget import *
from EventEngine.DyEvent import *


class DyStockTradeCurEntrustsWidget(DyTableWidget):
    """ 股票交易账户当日委托窗口 """

    signal = QtCore.pyqtSignal(type(DyEvent()))


    def __init__(self, eventEngine, broker):
        super().__init__(None, True, False, floatRound=3)

        self._eventEngine = eventEngine
        self._broker = broker

        self._headerSet = False

        self._registerEvent()

    def _signalEmitWrapper(self, event):
        """ !!!Note: The value of signal.emit will always be changed each time you getting.
        """
        self.signal.emit(event)

    def _registerEvent(self):
        self.signal.connect(self._stockCurEntrustsUpdateHandler)
        self._eventEngine.register(DyEventType.stockCurEntrustsUpdate + self._broker, self._signalEmitWrapper)

    def _unregisterEvent(self):
        self.signal.disconnect(self._stockCurEntrustsUpdateHandler)
        self._eventEngine.unregister(DyEventType.stockCurEntrustsUpdate + self._broker, self._signalEmitWrapper)
        
    def _stockCurEntrustsUpdateHandler(self, event):
        header = event.data['header']
        rows = event.data['rows']

        if not self._headerSet:
            self.setColNames(header)
            self._headerSet = True

        # strip
        for row in rows:
            row[0] = row[0].strip()

        self.fastAppendRows(rows, new=True)

        self.setItemsForeground(range(self.rowCount()), (('买入', Qt.red), ('卖出', Qt.darkGreen)))

    def closeEvent(self, event):
        self._unregisterEvent()

        return super().closeEvent(event)
