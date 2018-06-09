from PyQt5.QtWidgets import QTabWidget

from ....Common.DyStockCommon import *
from .DyStockDataIndexConsecutiveDayLineStatsWidget import *


class DyStockDataIndexConsecutiveDayLineStatsTabWidget(QTabWidget):

    def __init__(self, dataWindow, startDate, endDate, indexCountedDfs, greenLine=True):
        super().__init__()

        for index, df in indexCountedDfs.items():
            self.addTab(DyStockDataIndexConsecutiveDayLineStatsWidget(dataWindow, index, df),
                        DyStockCommon.indexes[index]
                        )

        self.setWindowTitle('指数连续日{0}线统计[{1},{2}]'.format('阴' if greenLine else '阳', startDate, endDate))