from ....Common.DyStockCommon import *
from DyCommon.Ui.DyStatsDataFrameTableWidget import *


class DyStockDataIndexConsecutiveDayLineStatsWidget(DyStatsDataFrameTableWidget):

    def __init__(self, dataWindow, indexCode, df, parent=None):
        super().__init__(df, parent)

        self._indexCode = indexCode
        self._dataWindow = dataWindow

        self.itemDoubleClicked.connect(self._itemDoubleClicked)

        # set foreground of item
        cols = []
        for i, name in enumerate(self.getColNames()):
            if '(%)' in name:
                cols.append(i)

        for row in range(self.rowCount()):
            for col in cols:
                value = self[row, col]
                if value is None: continue

                if value > 0:
                    self.setItemForeground(row, col, Qt.red)
                elif value < 0:
                    self.setItemForeground(row, col, Qt.darkGreen)
        
    def _itemDoubleClicked(self, item):
        # get start date
        row = self.row(item)
        startDate = self[row, '开始时间']
        
        # plot candle stick
        self._dataWindow.dataViewer.plotCandleStick(self._indexCode, [-DyStockCommon.dayKChartPeriodNbr, startDate, DyStockCommon.dayKChartPeriodNbr])
