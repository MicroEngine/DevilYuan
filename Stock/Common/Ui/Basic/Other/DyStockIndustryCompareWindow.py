from PyQt5.QtWidgets import QTabWidget


class DyStockIndustryCompareWindow(QTabWidget):
    """ 股票行业比较窗口 """

    def __init__(self, eventEngine, tableCls, targetCode, targetName, baseDate):
        """
            @tableCls: DyStockTableWidget class, 这么做是防止import递归
            @targetCode, @targetName: 跟哪个股票进行行业比较
        """
        super().__init__()

        self._eventEngine = eventEngine
        self._tableCls = tableCls
        self._targetCode = targetCode
        self._targetName = targetName
        self._baseDate = baseDate

    def addCategorys(self, dfs):
        for category, df in dfs.items():
            header = list(df.columns)
            data = df.values.tolist()

            widget = self._tableCls(self._eventEngine, name=category, baseDate=self._baseDate)
            widget.appendStocks(data, header, autoForegroundColName=header[-1])

            widget.markByData('名称', self._targetName)

            self.addTab(widget, category)




