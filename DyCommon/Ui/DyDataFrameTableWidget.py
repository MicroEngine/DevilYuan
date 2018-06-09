from PyQt5 import QtCore

import pandas as pd

from DyCommon.Ui.DyTableWidget import *


class DyDataFrameTableWidget(DyTableWidget):

    def __init__(self, df, parent=None):
        super().__init__(parent=parent, readOnly=True, index=False, floatCut=True, autoScroll=False)

        self.verticalHeader().setVisible(True)

        self._initDf(df)

    def _setRowNames(self, names):
        self.setRowCount(len(names))

        self.setVerticalHeaderLabels(names)

    def _initDf(self, df):
        self.setColNames(list(df.columns))
        self.fastAppendRows(df.values.tolist())

        self._setRowNames(list(df.index))

        self.setSortingEnabled(False)