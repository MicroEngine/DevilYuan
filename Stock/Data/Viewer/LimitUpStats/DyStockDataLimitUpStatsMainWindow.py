from PyQt5.QtWidgets import QDockWidget

from DyCommon.Ui.DyBasicMainWindow import *
from DyCommon.Ui.DyDataFrameTableWidget import *
from ....Common.DyStockCommon import *


class DyStockDataLimitUpStatsMainWindow(DyBasicMainWindow):
    name = 'DyStockDataLimitUpStatsMainWindow'

    def __init__(self, dataWindow, df):
        super().__init__(None, None)
        
        self._dataWindow = dataWindow
        self._df = df

        self._initUi()

    def _initUi(self):
        """ 初始化界面 """
        self.setWindowTitle('封板率统计[{0}~{1}]'.format(self._df.index[0].strftime("%Y-%m-%d"), self._df.index[-1].strftime("%Y-%m-%d")))

        self._initCentral()
        self._initToolBar()

        self._loadWindowSettings()

    def _initCentral(self):
        """ 初始化中心区域 """
        # change index to string
        df = self._df.copy()
        df.index = df.index.map(lambda x: x.strftime('%Y-%m-%d'))

        widgetStats, dockStats = self._createDock(DyDataFrameTableWidget, '封板率统计', Qt.BottomDockWidgetArea, df)

    def _initToolBar(self):
        """ 初始化工具栏 """
        toolBar = self.addToolBar('工具栏')
        toolBar.setObjectName('工具栏')

        # 创建工具栏的操作
        action = QAction('画图', self)
        action.triggered.connect(self._plotAct)
        toolBar.addAction(action)

    def closeEvent(self, event):
        """ 关闭事件 """
        return super().closeEvent(event)

    def _plotAct(self):
        self._dataWindow.plotLimitUpStats(DyStockCommon.shIndex, self._df)