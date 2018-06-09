from PyQt5.QtGui import QColor

from DyCommon.Ui.DyStatsDataFrameTableWidget import *
from .DyStockDataJaccardIndexCodeSetDetailsWidget import *


class DyStockDataJaccardIndexCodeSetWidget(DyStatsDataFrameTableWidget):
    """ 杰卡德指数代码交集窗口 """

    def __init__(self, dataViewer, orgDf, codeSetDf, codeIncreaseDfDict, codeTable, parent=None):
        self._dataViewer = dataViewer
        self._orgDf = orgDf
        self._codeSetDf = codeSetDf
        self._codeIncreaseDfDict = codeIncreaseDfDict
        self._codeTable = codeTable

        self._windows = []

        df = codeSetDf
        if not df.empty:
            df = df.applymap(lambda x: ','.join(x) if len(x) <= 5 else ','.join(list(x)[:5]) + ',...总共{0}'.format(len(x)))

            # change index to column
            df.reset_index(inplace=True)
            df.rename(columns={'index':'日期'}, inplace=True)

        super().__init__(df, parent)

        self.itemDoubleClicked.connect(self._itemDoubleClicked)

    def _itemDoubleClicked(self, item):
        row = item.row()
        date = self[row, '日期']

        window = DyStockDataJaccardIndexCodeSetDetailsWidget(self._dataViewer, date, self._orgDf, self._codeSetDf, self._codeIncreaseDfDict, self._codeTable)
        
        rect = QApplication.desktop().availableGeometry()
        taskBarHeight = QApplication.desktop().height() - rect.height()

        window.resize(rect.width()//3 * 2, rect.height() - taskBarHeight)
        window.move((rect.width() - window.width())//2, 0)

        window.show()

        self._windows.append(window)
