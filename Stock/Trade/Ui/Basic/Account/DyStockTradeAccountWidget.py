from PyQt5.QtWidgets import QTabWidget

from .DyStockTradeBrokerAccountWidget import *
from ....DyStockTradeCommon import *


class DyStockTradeAccountWidget(QTabWidget):
    """ 股票交易账户窗口, 管理所有券商的账户窗口 """

    signalLogin = QtCore.pyqtSignal(type(DyEvent()))
    signalLogout = QtCore.pyqtSignal(type(DyEvent()))


    def __init__(self, eventEngine):
        super().__init__()

        self._eventEngine = eventEngine

        self._brokerAccountWidgets = {}

        self._registerEvent()

    def _registerEvent(self):
        self.signalLogin.connect(self._stockLoginHandler)
        self._eventEngine.register(DyEventType.stockLogin, self.signalLogin.emit)

        self.signalLogout.connect(self._stockLogoutHandler)
        self._eventEngine.register(DyEventType.stockLogout, self.signalLogout.emit)

    def _stockLoginHandler(self, event):
        broker = event.data['broker']

        # create broker account widget
        widget = DyStockTradeBrokerAccountWidget(self._eventEngine, broker)
        self.addTab(widget, DyStockTradeCommon.accountMap[broker])

        self._brokerAccountWidgets[broker] = widget

    def _stockLogoutHandler(self, event):
        broker = event.data['broker']

        widget = self._brokerAccountWidgets[broker]
        widget.close()

        self.removeTab(self.indexOf(widget))

        del self._brokerAccountWidgets[broker]
        