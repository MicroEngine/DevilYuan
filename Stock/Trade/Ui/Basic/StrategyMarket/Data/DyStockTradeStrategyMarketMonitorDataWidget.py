from DyCommon.Ui.DyTableWidget import *


class DyStockTradeStrategyMarketMonitorDataWidget(DyTableWidget):
    """ 股票实盘策略数据窗口 """

    def __init__(self, strategyCls):
        super().__init__(None, True, False)

        self._strategyCls = strategyCls

        self.setColNames(strategyCls.dataHeader)
        self.setAutoForegroundCol('涨幅(%)')

    def update(self, data, newData=False):
        """ @data: [[col0, col1, ...]] """

        if newData: # !!!new, without considering keys
            self.fastAppendRows(data, autoForegroundColName='涨幅(%)', new=True)

        else: # updating by keys
            rowKeys = []
            for row in data:
                code = row[0] # pos 0 is code, date or something else, but should be key for one row
                self[code] = row

                rowKeys.append(code)

            self.setItemsForeground(rowKeys, (('买入', Qt.red), ('卖出', Qt.darkGreen)))
