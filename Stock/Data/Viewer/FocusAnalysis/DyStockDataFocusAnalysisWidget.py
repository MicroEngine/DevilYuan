from DyCommon.Ui.DyStatsDataFrameTableWidget import *
from .DyStockDataFocusInfoPoolWidget import *


class DyStockDataFocusAnalysisWidget(DyStatsDataFrameTableWidget):
    """ 热点分析窗口 """

    def __init__(self, dataWindow, focusStrengthDf, focusInfoPoolDict):
        # change index to string
        focusStrengthDf.index = focusStrengthDf.index.map(lambda x: x.strftime('%Y-%m-%d'))

        # change index to column
        focusStrengthDf.reset_index(inplace=True)
        focusStrengthDf.rename(columns={'index':'日期'}, inplace=True)

        super().__init__(focusStrengthDf)

        self._dataWindow = dataWindow
        self._focusInfoPoolDict = focusInfoPoolDict

        self._windows = []

        self.itemDoubleClicked.connect(self._itemDoubleClicked)

    def _itemDoubleClicked(self, item):
        row = self.row(item)
        date = self[row, 0]

        window = DyStockDataFocusInfoPoolWidget(self._dataWindow.dataViewer, date, self._focusInfoPoolDict[date])
        window.showMaximized()

        self._windows.append(window)

