from PyQt5.QtWidgets import QDockWidget

from DyCommon.Ui.DyBasicMainWindow import *
from .DyStockDataJaccardIndexCodeSetWidgets import *
from .DyStockDataJaccardIndexWidgets import *
from .DyStockDataJaccardIndexPlotDlg import *


class DyStockDataJaccardIndexMainWindow(DyBasicMainWindow):
    name = 'DyStockDataJaccardIndexMainWindow'

    def __init__(self, orgDfs, jaccardDfs, codeSetDfs, codeIncreaseDfDicts, codeTable, dataViewer, parent=None):
        super().__init__(None, None, parent)
        
        self._orgDfs = orgDfs
        self._jaccardDfs = jaccardDfs
        self._codeSetDfs = codeSetDfs
        self._codeIncreaseDfDicts = codeIncreaseDfDicts
        self._codeTable = codeTable
        self._dataViewer = dataViewer

        self._initUi()

    def _initUi(self):
        """初始化界面"""
        self.setWindowTitle('杰卡德指数')

        self._initCentral()
        self._initToolBar()

        self._loadWindowSettings()

    def _initCentral(self):
        """初始化中心区域"""
        widgetJaccardIndexCodeSet, dockJaccardIndexCodeSet = self._createDock(DyStockDataJaccardIndexCodeSetWidgets, '代码交集', Qt.TopDockWidgetArea, self._dataViewer, self._orgDfs, self._codeSetDfs, self._codeIncreaseDfDicts, self._codeTable)
        self._widgetJaccardIndex, dockJaccardIndex = self._createDock(DyStockDataJaccardIndexWidgets, '杰卡德指数', Qt.BottomDockWidgetArea, self._jaccardDfs)

        widgetJaccardIndexCodeSet.setJaccardIndexWidgets(self._widgetJaccardIndex)
        self._widgetJaccardIndex.setCodeSetWidgets(widgetJaccardIndexCodeSet)

    def _initToolBar(self):
        """ 初始化工具栏 """
        # 添加工具栏
        toolBar = self.addToolBar('工具栏')
        toolBar.setObjectName('工具栏')

        # 创建操作
        action = QAction('画图', self)
        action.triggered.connect(self._plotAct)
        toolBar.addAction(action)

    def closeEvent(self, event):
        """关闭事件"""
        return super().closeEvent(event)

    def _plotAct(self):
        index, jaccardDf = self._widgetJaccardIndex.getActiveIndexJaccardDf()
        if jaccardDf.empty: return

        data = {}
        if DyStockDataJaccardIndexPlotDlg(data, list(jaccardDf.columns), self).exec_():
            self._dataViewer.plotJaccardIndex(index, jaccardDf, data['data'])
