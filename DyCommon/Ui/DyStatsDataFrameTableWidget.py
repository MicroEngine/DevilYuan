from PyQt5 import QtCore

import pandas as pd

from DyCommon.Ui.DyStatsTableWidget import *


class DyStatsDataFrameTableWidget(DyStatsTableWidget):
    """
        只显示DF的列，index需要用户自己转换成列
    """
    def __init__(self, df, parent=None):
        super().__init__(parent=parent, readOnly=True, index=False, floatCut=True, autoScroll=False)

        self._initDf(df)

    def _initDf(self, df):
        self.setColNames(list(df.columns))
        self.fastAppendRows(df.values.tolist())
