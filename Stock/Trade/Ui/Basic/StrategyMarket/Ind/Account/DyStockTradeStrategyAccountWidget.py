from PyQt5.QtWidgets import QTabWidget

from .DyStockTradeStrategyDealsWidget import *
from .DyStockTradeStrategyEntrustsWidget import *
from .DyStockTradeStrategyPosWidget import *
from ......DyStockTradeCommon import *


class DyStockTradeStrategyAccountWidget(QTabWidget):
    """ 策略账户窗口 """

    def __init__(self, eventEngine, strategyCls):
        super().__init__()

        self._posWidget = DyStockTradeStrategyPosWidget(eventEngine, strategyCls)
        self.addTab(self._posWidget, '账户:%s'%DyStockTradeCommon.accountMap[strategyCls.broker])

        self._entrustsWidget = DyStockTradeStrategyEntrustsWidget()
        self.addTab(self._entrustsWidget, '委托')

        self._dealsWidget = DyStockTradeStrategyDealsWidget()
        self.addTab(self._dealsWidget, '成交')

    def closeEvent(self, event):
        self._posWidget.close()
        self._entrustsWidget.close()
        self._dealsWidget.close()

        return super().closeEvent(event)

    def updatePos(self, event):
        self._posWidget.update(event.data)

    def updateEntrusts(self, event):
        self._entrustsWidget.update(event.data)

    def updateDeals(self, event):
        self._dealsWidget.update(event.data)


