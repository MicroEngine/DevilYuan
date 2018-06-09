from PyQt5.QtWidgets import QTabWidget

from ....Common.DyStockCommon import *
from .DyStockDataJaccardIndexCodeSetWidget import *


class DyStockDataJaccardIndexCodeSetWidgets(QTabWidget):
    
    def __init__(self, dataViewer, orgDfs, codeSetDfs, codeIncreaseDfDicts, codeTable):
        super().__init__()

        self._dataViewer = dataViewer
        self._orgDfs = orgDfs
        self._codeSetDfs = codeSetDfs
        self._codeIncreaseDfDicts = codeIncreaseDfDicts
        self._codeTable = codeTable

        self._initUi()

        self.currentChanged.connect(self._onChange)

    def _initUi(self):
        for index in sorted(self._orgDfs):
            widget = DyStockDataJaccardIndexCodeSetWidget(self._dataViewer, self._orgDfs[index], self._codeSetDfs[index], self._codeIncreaseDfDicts[index], self._codeTable)

            self.addTab(widget, DyStockCommon.indexes[index])

    def setJaccardIndexWidgets(self, jaccardIndexWidgets):
        self._jaccardIndexWidgets = jaccardIndexWidgets

    def _onChange(self):
        self._jaccardIndexWidgets.blockSignals(True)
        self._jaccardIndexWidgets.setCurrentIndex(self.currentIndex())
        self._jaccardIndexWidgets.blockSignals(False)
