from PyQt5.QtWidgets import QDockWidget
from PyQt5.QtGui import QFont

from DyCommon.Ui.DyLogWidget import *
from DyCommon.Ui.DyProgressWidget import *
from DyCommon.Ui.DyBasicMainWindow import *
from DyCommon.Ui.DyDateDlg import *
from DyCommon.Ui.DyProcessNbrDlg import *

from .Basic.Param.DyStockSelectParamWidget import *
from .Basic.Select.DyStockSelectSelectResultWidget import *
from .Basic.Regression.DyStockSelectRegressionResultWidget import *
from .Basic.DyStockSelectStrategyWidget import *

from .Other.DyStockSelectTestedStocksDlg import *
from .Other.DyStockSelectBBandsStatsDlg import *
from .Other.DyStockSelectDayKChartPeriodDlg import *
from .Other.DyStockSelectIndexMaKChartStatsDlg import *
from .Other.DyStockSelectIndexMaStatsDlg import *
from .Other.DyStockSelectJaccardIndexDlg import *

from ...Common.DyStockCommon import *
from EventEngine.DyEvent import *
from ..Engine.DyStockSelectMainEngine import *
from ..Engine.Regression.DyStockSelectRegressionEngine import *


class DyStockSelectMainWindow(DyBasicMainWindow):
    name = 'DyStockSelectMainWindow'

    signalPlot = QtCore.pyqtSignal(type(DyEvent()))

    def __init__(self, parent=None):
        
        self._mainEngine = DyStockSelectMainEngine()

        super().__init__(self._mainEngine.eventEngine, self._mainEngine.info, parent)
        
        self._initUi()

        self._registerEvent()

    def _initUi(self):
        """ 初始化界面 """
        self.setWindowTitle('选股')

        self._initCentral()
        self._initMenu()
        self._initToolBar()

        self._loadWindowSettings()

        # at last, raise log dock widget
        self._dockLog.raise_()
        
    def _initCentral(self):
        """ 初始化中心区域 """
        widgetParam, dockParam = self._createDock(DyStockSelectParamWidget, '策略参数', Qt.RightDockWidgetArea)

        self._widgetStrategy, dockStrategy = self._createDock(DyStockSelectStrategyWidget, '策略', Qt.LeftDockWidgetArea, widgetParam)
        widgetProgress, dockProgress = self._createDock(DyProgressWidget, '进度', Qt.LeftDockWidgetArea, self._mainEngine.eventEngine)

        widgetLog, self._dockLog = self._createDock(DyLogWidget, '日志', Qt.RightDockWidgetArea, self._mainEngine.eventEngine)
        self._widgetSelectResult, dockSelectResult = self._createDock(DyStockSelectSelectResultWidget, '选股结果', Qt.RightDockWidgetArea, self._mainEngine.eventEngine, widgetParam)
        self._widgetRegressionResult, dockRegressionResult = self._createDock(DyStockSelectRegressionResultWidget, '回归结果', Qt.RightDockWidgetArea, self._mainEngine.eventEngine, widgetParam)

        self.tabifyDockWidget(self._dockLog, dockSelectResult)
        self.tabifyDockWidget(self._dockLog, dockRegressionResult)

    def _initMenu(self):
        """ 初始化菜单 """
        # 创建菜单
        menuBar = self.menuBar()
        
        # ----- 添加'数据'菜单 -----
        menu = menuBar.addMenu('数据')

        # 测试操作
        action = QAction('测试', self)
        action.triggered.connect(self._test)
        menu.addAction(action)

        # 打开策略选股/回归结果
        action = QAction('打开策略选股/回归结果...', self)
        action.triggered.connect(self._openStrategySelectResultAct)
        menu.addAction(action)

        # 布林统计操作
        action = QAction('布林统计...', self)
        action.triggered.connect(self._bBandsStats)
        menu.addAction(action)

        # 杰拉德指数操作
        action = QAction('杰卡德指数...', self)
        action.triggered.connect(self._jaccardIndexAct)
        menu.addAction(action)

        # 指数连续日阴线或者阳线统计
        lineStatsMenu = menu.addMenu('指数连续日K线统计')

        self._greenLineStatsAction = QAction('指数连续日阴线统计...', self)
        self._greenLineStatsAction.triggered.connect(self._indexConsecutiveDayLineStatsAct)
        lineStatsMenu.addAction(self._greenLineStatsAction)
        self._greenLineStatsAction.setCheckable(True)

        self._redLineStatsAction = QAction('指数连续日阳线统计...', self)
        self._redLineStatsAction.triggered.connect(self._indexConsecutiveDayLineStatsAct)
        lineStatsMenu.addAction(self._redLineStatsAction)
        self._redLineStatsAction.setCheckable(True)

        # 封板率统计
        action = QAction('封板率统计...', self)
        action.triggered.connect(self._limitUpStatsAct)
        menu.addAction(action)

        # 热点分析
        action = QAction('热点分析...', self)
        action.triggered.connect(self._focusAnalysisAct)
        menu.addAction(action)

        # 股票日内最高和最低价分布
        action = QAction('最高和最低价分布...', self)
        action.triggered.connect(self._highLowDistAct)
        menu.addAction(action)
        
        # ----- 添加'设置'菜单 -----
        menu = menuBar.addMenu('设置')

        self._setProcessNbrAction = QAction('回归进程数...', self)
        self._setProcessNbrAction.triggered.connect(self._setProcessNbr)
        menu.addAction(self._setProcessNbrAction)

        self._setDayKChartPeriodNbrAction = QAction('日K线前后周期数...', self)
        self._setDayKChartPeriodNbrAction.triggered.connect(self._setDayKChartPeriodNbr)
        menu.addAction(self._setDayKChartPeriodNbrAction)

        self._enableSelectEngineExceptionAction = QAction('选股引擎的异常捕捉', self)
        self._enableSelectEngineExceptionAction.triggered.connect(self._enableSelectEngineExceptionAct)
        menu.addAction(self._enableSelectEngineExceptionAction)
        self._enableSelectEngineExceptionAction.setCheckable(True)

        # ----- 添加'测试'菜单 -----
        menu = menuBar.addMenu('测试')

        self._testedStocksAction = QAction('调试股票...', self)
        self._testedStocksAction.triggered.connect(self._testedStocks)
        menu.addAction(self._testedStocksAction)
        self._testedStocksAction.setCheckable(True)

    def _enableSelectEngineExceptionAct(self):
        DyStockSelectCommon.enableSelectEngineException = self._enableSelectEngineExceptionAction.isChecked()

    def _test(self):
        event = DyEvent(DyEventType.plotReq)
        event.data['type'] = 'test'

        self._mainEngine.eventEngine.put(event)

    def _openStrategySelectResultAct(self):
        defaultDir = DyCommon.createPath('Stock/User/Save/Strategy/选股')
        fileName, _ = QFileDialog.getOpenFileName(self, "打开策略选股/回归结果", defaultDir, "JSON files (*.json)")

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
        if self._widgetSelectResult.load(data, strategyCls):
            return

        self._widgetRegressionResult.load(data, strategyCls)

    def _indexConsecutiveDayLineStatsAct(self):
        if self._greenLineStatsAction.isChecked():
            greenLine = True
            self._greenLineStatsAction.setChecked(False)
        else:
            greenLine = False
            self._redLineStatsAction.setChecked(False)

        data = {}
        if not DyDateDlg(data).exec_():
            return

        event = DyEvent(DyEventType.plotReq)
        event.data =  data
        event.data['type'] = 'indexConsecutiveDayLineStats'
        event.data['greenLine'] = greenLine

        self._mainEngine.eventEngine.put(event)

    def _limitUpStatsAct(self):
        data = {}
        if not DyDateDlg(data).exec_():
            return

        event = DyEvent(DyEventType.plotReq)
        event.data =  data
        event.data['type'] = 'limitUpStats'

        self._mainEngine.eventEngine.put(event)

    def _highLowDistAct(self):
        data = {}
        if not DyDateDlg(data).exec_():
            return

        event = DyEvent(DyEventType.plotReq)
        event.data =  data
        event.data['type'] = 'highLowDist'

        self._mainEngine.eventEngine.put(event)

    def _focusAnalysisAct(self):
        data = {}
        if not DyDateDlg(data).exec_():
            return

        event = DyEvent(DyEventType.plotReq)
        event.data =  data
        event.data['type'] = 'focusAnalysis'

        self._mainEngine.eventEngine.put(event)

    def _jaccardIndexAct(self):
        data = {}
        if not DyStockSelectJaccardIndexDlg(data).exec_():
            return

        event = DyEvent(DyEventType.plotReq)
        event.data =  data
        event.data['type'] = 'jaccardIndex'

        self._mainEngine.eventEngine.put(event)

    def _bBandsStats(self):
        data = {}
        if not DyStockSelectBBandsStatsDlg(data).exec_():
            return

        event = DyEvent(DyEventType.plotReq)
        event.data =  data
        event.data['type'] = 'bBandsStats'

        self._mainEngine.eventEngine.put(event)

    def _setProcessNbr(self):
        data = {'nbr':DyStockSelectRegressionEngine.periodNbr}
        if DyProcessNbrDlg(data, self).exec_():
            DyStockSelectRegressionEngine.periodNbr = data['nbr']

            self._mainEngine._info.print('回归进程数设为{0}'.format(data['nbr']), DyLogData.ind)

    def _setDayKChartPeriodNbr(self):
        data = {'periodNbr': DyStockCommon.dayKChartPeriodNbr}
        if DyStockSelectDayKChartPeriodDlg(data, self).exec_():
            DyStockCommon.dayKChartPeriodNbr = data['periodNbr']

            self._mainEngine._info.print('股票(指数)日K线前后交易日周期设为{0}'.format(data['periodNbr']), DyLogData.ind)

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

    def _stockSelect(self):
        strategyCls, param = self._widgetStrategy.getStrategy()
        if strategyCls is None: return

        # change UI
        self._startRunningMutexAction(self._stockSelectAction)

        event = DyEvent(DyEventType.stockSelectStrategySelectReq)
        event.data['class'] = strategyCls
        event.data['param'] = param

        self._mainEngine.eventEngine.put(event)

    def _stockSelectForTrade(self):
        strategyCls, param = self._widgetStrategy.getStrategy()
        if strategyCls is None: return

        # change UI
        self._startRunningMutexAction(self._stockSelectForTradeAction)

        event = DyEvent(DyEventType.stockSelectStrategySelectReq)
        event.data['class'] = strategyCls
        event.data['param'] = param
        event.data['param']['forTrade'] = None

        self._mainEngine.eventEngine.put(event)

    def _stockRegression(self):
        strategyCls, param = self._widgetStrategy.getStrategy()
        if strategyCls is None: return

        data = {}
        if not DyDateDlg(data).exec_():
            return

        # change UI
        self._startRunningMutexAction(self._stockRegressionAction)

        event = DyEvent(DyEventType.stockSelectStrategyRegressionReq)
        event.data['class'] = strategyCls
        event.data['param'] = param
        event.data['startDate'] = data['startDate']
        event.data['endDate'] = data['endDate']

        self._mainEngine.eventEngine.put(event)

    def _initToolBar(self):
        """ 初始化工具栏 """
        # 操作工具栏
        toolBar = self.addToolBar('选股和回归')
        toolBar.setObjectName('选股和回归')

        # 创建操作工具栏的操作
        self._stockSelectAction = QAction('选股', self)
        self._stockSelectAction.setEnabled(False)
        self._stockSelectAction.triggered.connect(self._stockSelect)
        self._addMutexAction(self._stockSelectAction)
        toolBar.addAction(self._stockSelectAction)

        self._stockRegressionAction = QAction('回归', self)
        self._stockRegressionAction.setEnabled(False)
        self._stockRegressionAction.triggered.connect(self._stockRegression)
        self._addMutexAction(self._stockRegressionAction)
        toolBar.addAction(self._stockRegressionAction)

        """
        self._stockSelectForTradeAction = QAction('实盘选股', self)
        self._stockSelectForTradeAction.setEnabled(False)
        self._stockSelectForTradeAction.triggered.connect(self._stockSelectForTrade)
        self._addMutexAction(self._stockSelectForTradeAction)
        toolBar.addAction(self._stockSelectForTradeAction)
        """

        #self._widgetStrategy.setRelatedActions([self._stockSelectAction, self._stockRegressionAction, self._stockSelectForTradeAction])
        self._widgetStrategy.setRelatedActions([self._stockSelectAction, self._stockRegressionAction])

        # K线工具栏
        toolBar = self.addToolBar('K线')
        toolBar.setObjectName('K线')

        # K线周期菜单Action
        self._kPeriodMenuAction = QAction('K线周期', self)
        toolBar.addAction(self._kPeriodMenuAction)
        self._kPeriodMenuAction.triggered.connect(self._kPeriodMenuAct)

        # K线周期菜单
        self._kPeriodMenu = QMenu(self)

        # 创建K线周期菜单的操作
        actions = [QAction('{0}'.format(x), self) for x in [60, 90, 120, 180, 250, 500]]
        for action in actions:
            action.setCheckable(True)
            action.triggered.connect(self._kPeriodAct)
            self._kPeriodMenu.addAction(action)

            # set default K period
            if int(action.text()) == DyStockCommon.dayKChartPeriodNbr:
                action.setChecked(True)
                self._curKPeriodAction = action
                self._kPeriodMenuAction.setText('K线周期:{0}'.format(DyStockCommon.dayKChartPeriodNbr))

        # 滑动窗口(w)菜单Action
        self._rollingWindowWMenuAction = QAction('滑动窗口(w)', self)
        toolBar.addAction(self._rollingWindowWMenuAction)
        self._rollingWindowWMenuAction.triggered.connect(self._rollingWindowWMenuAct)

        # 滑动窗口(w)菜单
        self._rollingWindowWMenu = QMenu(self)

        # 创建滑动窗口(w)菜单的操作
        actions = [QAction('{0}'.format(x), self) for x in [1, 2, 3, 4, 5, 6, 7, 8, 9]]
        for action in actions:
            action.setCheckable(True)
            action.triggered.connect(self._rollingWindowWAct)
            self._rollingWindowWMenu.addAction(action)

            # set default rolling window w
            if int(action.text()) == DyStockCommon.rollingWindowW:
                action.setChecked(True)
                self._curRollingWindowWAction = action
                self._rollingWindowWMenuAction.setText('滑动窗口(w):{0}'.format(DyStockCommon.rollingWindowW))

        # 支撑和阻力菜单Action
        self._hsarMenuAction = QAction('支撑和阻力', self)
        toolBar.addAction(self._hsarMenuAction)
        self._hsarMenuAction.triggered.connect(self._hsarMenuAct)

        # 支撑和阻力菜单
        self._hsarMenu = QMenu(self)

        actions = [QAction(x, self) for x in ['成本', '极值平均', '极值之极']]
        for action in actions:
            action.setCheckable(True)
            action.triggered.connect(self._hsarsAct)
            self._hsarMenu.addAction(action)

            if action.text() == DyStockCommon.hsarMode:
                action.setChecked(True)
                self._curHsarAction = action
                self._hsarMenuAction.setText('支撑和阻力:{0}'.format(DyStockCommon.hsarMode))

        # 趋势线周期菜单Action
        self._trendLinePeriodMenuAction = QAction('趋势线周期', self)
        toolBar.addAction(self._trendLinePeriodMenuAction)
        self._trendLinePeriodMenuAction.triggered.connect(self._trendLinePeriodMenuAct)

        # 趋势线周期菜单
        self._trendLinePeriodMenu = QMenu(self)

        # 清除所有Action
        action = QAction('清除所有', self)
        action.triggered.connect(self._trendLinePeriodClearAllAct)
        self._trendLinePeriodMenu.addAction(action)

        # 创建趋势线周期菜单的操作
        actions = [QAction('{0}'.format(x), self) for x in list(range(10, 121, 5)) + [180, 250, 500]]
        for action in actions:
            action.setCheckable(True)
            action.triggered.connect(self._trendLinePeriodAct)
            self._trendLinePeriodMenu.addAction(action)

            # set default trend line periods
            if int(action.text()) in DyStockCommon.trendLinePeriods:
                action.setChecked(True)
                self._trendLinePeriodMenuAction.setText('趋势线周期:{0}'.format(','.join([str(x) for x in DyStockCommon.trendLinePeriods])))

    def _kPeriodMenuAct(self):
        self._kPeriodMenu.popup(QCursor.pos())

    def _trendLinePeriodMenuAct(self):
        self._trendLinePeriodMenu.popup(QCursor.pos())

    def _rollingWindowWMenuAct(self):
        self._rollingWindowWMenu.popup(QCursor.pos())

    def _hsarMenuAct(self):
        self._hsarMenu.popup(QCursor.pos())

    def _trendLinePeriodAct(self):
        periods = []
        for action in self._trendLinePeriodMenu.actions():
            if action.isChecked():
                periods.append(int(action.text()))

        DyStockCommon.trendLinePeriods = periods
        self._trendLinePeriodMenuAction.setText('趋势线周期:{0}'.format(','.join([str(x) for x in DyStockCommon.trendLinePeriods])))

    def _trendLinePeriodClearAllAct(self):
        # clear all
        for action in self._trendLinePeriodMenu.actions():
            if action.isChecked():
                action.setChecked(False)

        DyStockCommon.trendLinePeriods = []
        self._trendLinePeriodMenuAction.setText('趋势线周期:{0}'.format(','.join([str(x) for x in DyStockCommon.trendLinePeriods])))

    def _kPeriodAct(self):
        self._curKPeriodAction.setChecked(False)

        # get triggered action
        for action in self._kPeriodMenu.actions():
            if action.isChecked():
                # 设置K线周期
                DyStockCommon.dayKChartPeriodNbr = int(action.text())

                self._curKPeriodAction = action
                self._kPeriodMenuAction.setText('K线周期:{0}'.format(DyStockCommon.dayKChartPeriodNbr))
                break

        if not self._curKPeriodAction.isChecked():
            self._curKPeriodAction.setChecked(True)

    def _hsarsAct(self):
        self._curHsarAction.setChecked(False)

        # get triggered action
        for action in self._hsarMenu.actions():
            if action.isChecked():
                # 设置支撑和阻力
                DyStockCommon.hsarMode = action.text()

                self._curHsarAction = action
                self._hsarMenuAction.setText('支撑和阻力:{0}'.format(DyStockCommon.hsarMode))
                break

        if not self._curHsarAction.isChecked():
            self._curHsarAction.setChecked(True)

    def _rollingWindowWAct(self):
        self._curRollingWindowWAction.setChecked(False)

        # get triggered action
        for action in self._rollingWindowWMenu.actions():
            if action.isChecked():
                # 设置rolling window w
                DyStockCommon.rollingWindowW = int(action.text())

                self._curRollingWindowWAction = action
                self._rollingWindowWMenuAction.setText('滑动窗口(w):{0}'.format(DyStockCommon.rollingWindowW))
                break

        if not self._curRollingWindowWAction.isChecked():
            self._curRollingWindowWAction.setChecked(True)

    def closeEvent(self, event):
        """ 关闭事件 """
        self._mainEngine.exit()

        return super().closeEvent(event)
            
    def _plotAckHandler(self, event):
        # unpack
        plot = event.data['plot']

        # plot
        plot(event)

    def _registerEvent(self):
        """ 注册GUI更新相关的事件监听 """
        self.signalPlot.connect(self._plotAckHandler)

        self._mainEngine.eventEngine.register(DyEventType.plotAck, self.signalPlot.emit)
