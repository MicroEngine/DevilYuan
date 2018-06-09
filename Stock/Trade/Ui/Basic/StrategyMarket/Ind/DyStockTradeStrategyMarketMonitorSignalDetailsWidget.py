from DyCommon.Ui.DyTableWidget import *


class DyStockTradeStrategyMarketMonitorSignalDetailsWidget(DyTableWidget):
    """ 股票实盘策略信号明细窗口 """

    def __init__(self, strategyCls):
        super().__init__(None, True, False, floatRound=3)

        self._strategyCls = strategyCls

        self.setColNames(strategyCls.signalDetailsHeader)

    def update(self, data):
        """ @data: [[col0, col1, ...]] """

        self.setSortingEnabled(False)

        rowKeys = []
        for row in data:
            rowPos = self.appendRow(row, disableSorting=False)

            rowKeys.append(rowPos)

        self.setItemsForeground(rowKeys, (('买入', Qt.red), ('卖出', Qt.darkGreen)))

        self.setSortingEnabled(True)
