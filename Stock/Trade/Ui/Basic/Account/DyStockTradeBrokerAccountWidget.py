from PyQt5.QtWidgets import QTabWidget

from .DyStockTradeCapitalWidget import *
from .DyStockTradeCurDealsWidget import *
from .DyStockTradeCurEntrustsWidget import *
from .DyStockTradePositionWidget import *


class DyStockTradeBrokerAccountWidget(QTabWidget):
    """ 券商股票交易账户窗口 """


    def __init__(self, eventEngine, broker):
        super().__init__()

        self._eventEngine = eventEngine
        self._broker = broker

        self._initUi()

    def _initUi(self):
        self._widgets = []

        widget = DyStockTradeCapitalWidget(self._eventEngine, self._broker)
        self.addTab(widget, '资金')
        self._widgets.append(widget)

        widget = DyStockTradePositionWidget(self._eventEngine, self._broker)
        self.addTab(widget, '持仓')
        self._widgets.append(widget)

        widget = DyStockTradeCurEntrustsWidget(self._eventEngine, self._broker)
        self.addTab(widget, '当日委托')
        self._widgets.append(widget)

        widget = DyStockTradeCurDealsWidget(self._eventEngine, self._broker)
        self.addTab(widget, '当日成交')
        self._widgets.append(widget)

    def closeEvent(self, event):
        for widget in self._widgets:
            widget.close()

        return super().closeEvent(event)
