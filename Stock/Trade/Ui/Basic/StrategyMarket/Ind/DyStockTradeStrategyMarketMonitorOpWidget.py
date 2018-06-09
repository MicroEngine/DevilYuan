from DyCommon.Ui.DyTableWidget import *


class DyStockTradeStrategyMarketMonitorOpWidget(DyTableWidget):
    """ 股票实盘策略操作窗口 """

    def __init__(self, strategyCls):
        super().__init__(readOnly=True, index=False, floatRound=3)

        self._strategyCls = strategyCls

        self.setColNames(strategyCls.opHeader)

        self._pnlColPos = []
        for i, name in enumerate(strategyCls.opHeader, 1 if self.hasIndex() else 0):
            if '盈亏' in name:
                self._pnlColPos.append(i)

    def update(self, data):
        """ @data: [[col0,col1,...]] """

        self.setSortingEnabled(False)

        rowKeys = []
        for row in data:
            rowPos = self.appendRow(row, disableSorting=False)
            rowKeys.append(rowPos)

            # 设置盈亏前景色
            for col in self._pnlColPos:
                item = self.item(rowPos, col)
                itemData = item.data(self._role)

                try:
                    if itemData > 0:
                        item.setForeground(Qt.red)
                    elif itemData < 0:
                        item.setForeground(Qt.darkGreen)
                except:
                    pass

        self.setItemsForeground(rowKeys, (('买入', Qt.red), ('卖出', Qt.darkGreen)))

        self.setSortingEnabled(True)
