from PyQt5.QtWidgets import QTabWidget

from ....Common.DyStockCommon import *
from .DyStockDataJaccardIndexWidget import *


class DyStockDataJaccardIndexWidgets(QTabWidget):
    
    def __init__(self, jaccardDfs):
        super().__init__()

        self._jaccardDfs = jaccardDfs

        self._initUi()

        self.currentChanged.connect(self._onChange)

    def _initUi(self):
        for index in sorted(self._jaccardDfs):
            widget = DyStockDataJaccardIndexWidget(index, self._jaccardDfs[index])

            self.addTab(widget, DyStockCommon.indexes[index])

    def getActiveIndexJaccardDf(self):
        indexName = self.tabText(self.currentIndex())
        index = DyStockCommon.getIndexByName(indexName)

        return index, self._jaccardDfs[index]

    def setCodeSetWidgets(self, codeSetWidgets):
        self._codeSetWidgets = codeSetWidgets

    def _onChange(self):
        self._codeSetWidgets.blockSignals(True)
        self._codeSetWidgets.setCurrentIndex(self.currentIndex())
        self._codeSetWidgets.blockSignals(False)
