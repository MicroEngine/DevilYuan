from PyQt5.QtWidgets import QDockWidget

from DyCommon.Ui.DyLogWidget import *
from DyCommon.Ui.DyProgressWidget import *
from DyCommon.Ui.DyBasicMainWindow import *
from .Basic.DyStockBackTestingStrategyWidget import *
from .Basic.DyStockBackTestingResultWidget import *
from ...Select.Ui.Basic.Param.DyStockSelectParamWidget import *
from ..DyStockBackTestingCommon import *
from EventEngine.DyEvent import *
from ..Engine.DyStockBackTestingMainEngine import *
from ...Select.Ui.Other.DyStockSelectTestedStocksDlg import *
from ...Common.Ui.DyStockMaViewerIndicatorMenu import *
from .Other.DyStockBackTestingSettingDlg import *


class DyStockBackTestingMainWindow(DyBasicMainWindow):
    name = 'DyStockBackTestingMainWindow'

    def __init__(self, parent=None):
        
        self._mainEngine = DyStockBackTestingMainEngine()

        super().__init__(self._mainEngine.eventEngine, self._mainEngine.info, parent)
        
        self._initUi()

    def _initUi(self):
        """初始化界面"""
        self.setWindowTitle('股票策略回测')

        self._initCentral()
        self._initMenu()
        self._initToolBar()

        self._loadWindowSettings()

        # at last, raise log dock widget
        self._dockLog.raise_()
        
    def _initCentral(self):
        """初始化中心区域"""
        widgetParam, dockParam = self._createDock(DyStockSelectParamWidget, '策略参数', Qt.RightDockWidgetArea)

        self._widgetStrategy, dockStrategy = self._createDock(DyStockBackTestingStrategyWidget, '策略', Qt.LeftDockWidgetArea, widgetParam)
        widgetProgress, dockProgress = self._createDock(DyProgressWidget, '进度', Qt.LeftDockWidgetArea, self._mainEngine.eventEngine)
        widgetLog, self._dockLog = self._createDock(DyLogWidget, '日志', Qt.RightDockWidgetArea, self._mainEngine.eventEngine)
        self._widgetResult, dockResult = self._createDock(DyStockBackTestingResultWidget, '回测结果', Qt.RightDockWidgetArea, self._mainEngine.eventEngine)
        
        self.tabifyDockWidget(self._dockLog, dockResult)

    def _initMenu(self):
        """初始化菜单"""

        # 创建菜单
        menuBar = self.menuBar()

        # '数据'菜单
        menu = menuBar.addMenu('数据')

        # 打开策略选股/回归结果
        action = QAction('打开策略回测成交结果...', self)
        action.triggered.connect(self._openBackTestingStrategyResultDealsAct)
        menu.addAction(action)

        # '设置'菜单
        self._settingMenu = menuBar.addMenu('设置')
        self._maViewerIndicatorMenu = DyStockMaViewerIndicatorMenu(self)

        menu = self._settingMenu.addMenu('回测模式')

        self._backTestingModeActions = []

        action = QAction('线程模式', self)
        action.triggered.connect(self._backTestingModeAct)
        action.setCheckable(True)
        menu.addAction(action)

        self._curBackTestingModeAction = action
        self._curBackTestingModeAction.setChecked(True) # default

        self._backTestingModeActions.append(action)

        menu = menu.addMenu('进程模式')

        for action in [QAction(x, self) for x in ['参数组合', '周期']]:
            action.triggered.connect(self._backTestingModeAct)
            action.setCheckable(True)
            menu.addAction(action)

            self._backTestingModeActions.append(action)

        # '测试'菜单
        menu = menuBar.addMenu('测试')

        self._testedStocksAction = QAction('调试股票...', self)
        self._testedStocksAction.triggered.connect(self._testedStocks)
        self._testedStocksAction.setCheckable(True)
        menu.addAction(self._testedStocksAction)
        
    def getMaViewerIndicatorParentMenu(self):
        return self._settingMenu

    def setMaViewerIndicator(self, indicator):
        DyStockBackTestingCommon.maViewerIndicator = indicator

    def _backTestingModeAct(self):
        self._curBackTestingModeAction.setChecked(False)

        for action in self._backTestingModeActions:
            if action.isChecked():
                self._curBackTestingModeAction = action
                break

        if not self._curBackTestingModeAction.isChecked():
            self._curBackTestingModeAction.setChecked(True)

        text = self._curBackTestingModeAction.text()
        if text == '线程模式':
            self._mainEngine.setThreadMode()
        else:
            self._mainEngine.setProcessMode(text)

    def _backTesting(self):
        strategyCls, param = self._widgetStrategy.getStrategy()
        if strategyCls is None: return

        data = {}
        if not DyStockBackTestingSettingDlg(data).exec_():
            return

        # change UI
        self._startRunningMutexAction(self._backTestingAction)

        event = DyEvent(DyEventType.stockStrategyBackTestingReq)
        event.data = DyStockBackTestingStrategyReqData(strategyCls, [data['startDate'], data['endDate']], data, param)

        self._mainEngine.eventEngine.put(event)
        
    def closeEvent(self, event):
        """ 关闭事件 """
        self._mainEngine.exit()

        return super().closeEvent(event)

    def _testedStocks(self):
        isTested =  self._testedStocksAction.isChecked()

        codes = None
        if isTested:
            data = {}
            if DyStockSelectTestedStocksDlg(data).exec_():
                codes = data['codes']
            else:
                self._testedStocksAction.setChecked(False)

        # put event
        event = DyEvent(DyEventType.stockSelectTestedCodes)
        event.data = codes

        self._mainEngine.eventEngine.put(event)

    def _openBackTestingStrategyResultDealsAct(self):
        defaultDir = DyCommon.createPath('Stock/User/Save/Strategy/股票策略回测')
        fileName, _ = QFileDialog.getOpenFileName(self, "打开策略回测成交结果...", defaultDir, "JSON files (*.json)")

        # open
        try:
            with open(fileName) as f:
                data = json.load(f)
        except Exception:
            return

        if not data:
            return

        # create strategy class
        strategyClsName = data.get('strategyCls')
        if not strategyClsName:
            return

        strategyCls = eval(strategyClsName)

        # load
        self._widgetResult.loadDeals(data, strategyCls)

    def _initToolBar(self):
        """ 初始化工具栏 """
        # 创建操作
        self._backTestingAction = QAction('回测', self)
        self._backTestingAction.setEnabled(False)
        self._backTestingAction.triggered.connect(self._backTesting)
        self._addMutexAction(self._backTestingAction)

        # 添加工具栏
        toolBar = self.addToolBar('工具栏')
        toolBar.setObjectName('工具栏')
        toolBar.addAction(self._backTestingAction)
        self._widgetStrategy.setRelatedActions([self._backTestingAction])

    
