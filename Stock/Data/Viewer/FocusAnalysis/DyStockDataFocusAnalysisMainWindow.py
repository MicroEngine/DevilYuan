from PyQt5.QtWidgets import QDockWidget

from .DyStockDataFocusAnalysisWidget import *
from DyCommon.Ui.DyBasicMainWindow import *
from ....Common.DyStockCommon import *


class DyStockDataFocusAnalysisMainWindow(DyBasicMainWindow):
    """ 热点分析主窗口 """

    name = 'DyStockDataFocusAnalysisMainWindow'

    def __init__(self, dataWindow, focusStrengthDf, focusInfoPoolDict):
        super().__init__(None, None)
        
        self._dataWindow = dataWindow
        self._focusStrengthDf = focusStrengthDf
        self._focusInfoPoolDict = focusInfoPoolDict

        self._initUi()

    def _initUi(self):
        """ 初始化界面 """
        self.setWindowTitle('热点分析')

        self._initCentral()
        self._initToolBar()

        self._loadWindowSettings()

    def _initCentral(self):
        """ 初始化中心区域 """
        widgetStats, dockStats = self._createDock(DyStockDataFocusAnalysisWidget, '热点强度', Qt.BottomDockWidgetArea, self._dataWindow, self._focusStrengthDf.copy(), self._focusInfoPoolDict)

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
        self._dataWindow.plotFocusStrength(DyStockCommon.shIndex, self._focusStrengthDf)