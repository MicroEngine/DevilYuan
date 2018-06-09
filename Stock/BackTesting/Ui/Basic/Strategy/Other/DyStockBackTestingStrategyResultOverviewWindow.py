from DyCommon.Ui.DyStatsTableWidget import *


class DyStockBackTestingStrategyResultOverviewWindow(DyStatsTableWidget):

    def __init__(self, strategyResultWidget, strategyParamGroupWidgets, header, rows, autoForegroundColName):
        super().__init__(None, True, True)

        self._strategyResultWidget = strategyResultWidget
        self._strategyParamGroupWidgets = strategyParamGroupWidgets
        
        self.setColNames(header)
        self.fastAppendRows(rows, autoForegroundColName)
        
        self.itemDoubleClicked.connect(self._itemDoubleClicked)

    def _itemDoubleClicked(self, item):
        self._strategyResultWidget.setCurrentWidget(self._strategyParamGroupWidgets[self.org(item.row())-1])