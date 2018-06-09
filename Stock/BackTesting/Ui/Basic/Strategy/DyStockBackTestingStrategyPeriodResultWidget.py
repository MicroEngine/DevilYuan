from PyQt5.QtWidgets import QWidget, QLabel
from PyQt5.Qt import QGridLayout

from DyCommon.Ui.DySubInfoWidget import *
from .DyStockBackTestingStrategyResultStatsWidget import *
from .DyStockBackTestingStrategyResultPositionWidget import *
from .DyStockBackTestingStrategyResultDealsWidget import *


class DyStockBackTestingStrategyPeriodResultWidget(QWidget):

    def __init__(self, strategyCls, paramGroupNo, period, eventEngine, dataEngine, dataViewer):
        super().__init__()

        self._strategyCls = strategyCls
        self._paramGroupNo = paramGroupNo
        self._period = period
        self._eventEngine = eventEngine
        self._dataEngine = dataEngine
        self._dataViewer = dataViewer
        
        self._initUi()

    def _initUi(self):
        self._statsWidget = DyStockBackTestingStrategyResultStatsWidget(self._dataEngine)
        self._posWidget = DyStockBackTestingStrategyResultPositionWidget(self._dataViewer)
        self._dealsWidget = DyStockBackTestingStrategyResultDealsWidget(self._eventEngine, str(self._period), self._strategyCls)
        self._subInfoWidget = DySubInfoWidget(self._eventEngine, self._paramGroupNo, self._period) # 由于线程并行问题，可能会丢掉开始的一些信息

        dealsLabel = QLabel('成交明细')
        posLabel = QLabel('当前持仓')
        statsLabel = QLabel('账户信息')

        grid = QGridLayout()
        grid.setSpacing(0)

        grid.addWidget(statsLabel, 0, 0)
        grid.addWidget(self._statsWidget, 1, 0)
        grid.addWidget(posLabel, 2, 0)
        grid.addWidget(self._posWidget, 3, 0)
        grid.addWidget(dealsLabel, 4, 0)
        grid.addWidget(self._dealsWidget, 5, 0)
        grid.addWidget(self._subInfoWidget, 6, 0)
        
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 4)
        grid.setRowStretch(2, 1)
        grid.setRowStretch(3, 25)
        grid.setRowStretch(4, 1)
        grid.setRowStretch(5, 30)
        grid.setRowStretch(6, 1)

        self.setLayout(grid)

        # 成交明细右键菜单
        self._dealsNewWindows = []
        dealsLabel.setContextMenuPolicy(Qt.CustomContextMenu)
        dealsLabel.customContextMenuRequested.connect(self._showDealsContextMenu)

        self._dealsMenu = QMenu(self) 
        
        action = QAction('新窗口', self)
        action.triggered.connect(self._newDealsWindow)
        self._dealsMenu.addAction(action)

    def update(self, ackData):
        self._statsWidget.update(ackData)
        self._dealsWidget.append(ackData.deals)
        self._posWidget.update(ackData.curPos)

    def _showDealsContextMenu(self, position):
        self._dealsMenu.popup(QCursor.pos())

    def _newDealsWindow(self):
        window = DyStockBackTestingStrategyResultDealsWidget(self._eventEngine, str(self._period), self._strategyCls)
        self._dealsNewWindows.append(window)

        for ackData in self._statsWidget.ackData:
            window.append(ackData.deals)

        window.setWindowTitle('成交明细')
        window.showMaximized()

    def getCurPnlRatio(self):
        return self._statsWidget.curPnlRatio

    def overview(self):
        return self._statsWidget.overview()
