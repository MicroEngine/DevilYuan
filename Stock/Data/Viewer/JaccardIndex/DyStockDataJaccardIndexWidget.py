from PyQt5.QtGui import QColor

from DyCommon.Ui.DyStatsDataFrameTableWidget import *


class DyStockDataJaccardIndexWidget(DyStatsDataFrameTableWidget):
    """ 杰卡德指数窗口 """

    def __init__(self, stockIndex, jaccardDf, parent=None):

        self._jaccardDf = jaccardDf
        self._stockIndex = stockIndex

        df = jaccardDf
        if not df.empty:
            # change index to column
            df = jaccardDf.reset_index()
            df.rename(columns={'index':'日期'}, inplace=True)

        super().__init__(df, parent)

        # set color
        self._setColor()

    def _setColor(self):
        pass