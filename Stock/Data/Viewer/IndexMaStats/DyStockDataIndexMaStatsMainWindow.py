from PyQt5.QtWidgets import QDockWidget

from .DyStockDataIndexMaStatsWidget import *
from DyCommon.Ui.DyBasicMainWindow import *
from .DyStockDataIndexMaKChartStatsDlg import *


class DyStockDataIndexMaStatsMainWindow(DyBasicMainWindow):
    name = 'DyStockDataIndexMaStatsMainWindow'

    def __init__(self, dataViewer, indexCode, indexName, df, parent=None):
        super().__init__(None, None, parent)
        
        self._dataViewer = dataViewer
        self._indexCode = indexCode
        self._indexName = indexName
        self._df = df

        self._initUi()

    def _initUi(self):
        """ 初始化界面 """
        self.setWindowTitle('指数均线统计')

        self._initCentral()
        self._initToolBar()

        self._loadWindowSettings()

    def _initCentral(self):
        """ 初始化中心区域 """
        widgetStats, dockStats = self._createDock(DyStockDataIndexMaStatsWidget, self._indexName, Qt.BottomDockWidgetArea, self._indexCode, self._indexName, self._df)

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
        data = {}
        if DyStockDataIndexMaKChartStatsDlg(data, self).exec_():
            self._dataViewer.plotIndexMaKChartStats(self._indexCode, self._df, data)