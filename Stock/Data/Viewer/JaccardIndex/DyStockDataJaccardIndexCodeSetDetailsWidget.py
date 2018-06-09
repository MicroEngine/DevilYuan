import operator

from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QTabWidget

from ....Common.Ui.Basic.DyStockTableWidget import *


class DyStockDataJaccardIndexCodeSetDetailsWidget(QTabWidget):

    def __init__(self, dataViewer, baseDate, orgDf, codeSetDf, codeIncreaseDfDict, codeTable):
        super().__init__()

        self._dataViewer = dataViewer
        self._baseDate = baseDate

        self._orgDf = orgDf
        self._codeSetDf = codeSetDf
        self._codeIncreaseDfDict = codeIncreaseDfDict
        self._codeTable = codeTable

        self._initUi()

        self._setColor()

    def _initUi(self):
        self.setWindowTitle('代码集明细[{0}]'.format(self._baseDate))

        for column in self._codeSetDf.columns:
            codeSet = self._codeSetDf.ix[self._baseDate, column]

            newColumn = column[2:-1]

            # get days of A set and B set
            a, b = newColumn.split(';')
            aDays, _ = a.split(',')
            bDays, _ = b.split(',')
            aDays, bDays = int(aDays), int(bDays)

            # get corresponding increase for each code
            header = ['代码', '名称', '最前{0}涨幅(%)'.format(aDays), '前{0}涨幅(%)'.format(bDays)]
            rows = []
            for code in codeSet:
                # 最前{0}涨幅(%) position
                baseDatePos = self._orgDf.index.get_loc(self._baseDate)
                pos = baseDatePos - (bDays - aDays)
                posDate = self._orgDf.index[pos]

                row = [code, self._codeTable[code],
                       self._codeIncreaseDfDict[code].ix[posDate, a],
                       self._codeIncreaseDfDict[code].ix[self._baseDate, b]
                       ]

                rows.append(row)

            rows.sort(key=operator.itemgetter(3), reverse=True)

            widget = DyStockSelectStrategySelectResultWidget(self._dataViewer, self._baseDate)
            widget.append(rows, header)

            self.addTab(widget, column)

    def _setColor(self):
        for i in range(self.count()):
            widget = self.widget(i)

            for row in range(widget.rowCount()):
                if widget[row, 2] < widget[row, 3]:
                    widget.setRowForeground(row, QColor('#4169E1'))