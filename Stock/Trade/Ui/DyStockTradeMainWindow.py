import datetime
import threading

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMainWindow, QDockWidget, QTabWidget

from .Basic.DyStockMarketIndexMonitorWidget import *
from .Basic.DyStockMarketStrengthWidget import *
from .Basic.StrategyMarket.DyStockTradeStrategiesMarketMonitorWidget import *
from .Basic.DyStockTradeStrategyWidget import *
from .Basic.Account.DyStockTradeAccountWidget import *
from DyCommon.Ui.DyLogWidget import *
from DyCommon.Ui.DyBasicMainWindow import *
from DyCommon.Ui.DySingleEditDlg import *
from ..Engine.DyStockTradeMainEngine import *
from ..DyStockTradeCommon import *
from .DyStockTradeOneKeyHangUp import DyStockTradeOneKeyHangUp


class DyStockTradeMainWindow(DyBasicMainWindow):
    name = 'DyStockTradeMainWindow'


    def __init__(self, parent=None):
        self._mainEngine = DyStockTradeMainEngine()

        super().__init__(self._mainEngine.eventEngine, self._mainEngine.info, parent)
        
        self._initUi()
        self._initOthers()

    def _initOthers(self):
        self._oneKeyHangUp = DyStockTradeOneKeyHangUp(self._mainEngine.eventEngine, self._mainEngine.info)
        
    def _initUi(self):
        """ 初始化界面 """
        self.setWindowTitle('股票交易')

        self._initCentral()
        self._initMenu()
        self._initToolBar()

        self._loadWindowSettings()
        
    def _initCentral(self):
        """ 初始化中心区域 """
        widgetStrategyMarket, dockStrategyMarket = self._createDock(DyStockTradeStrategiesMarketMonitorWidget, '策略行情', Qt.RightDockWidgetArea, self._mainEngine.eventEngine)
        widgetStrategy, dockStrategy = self._createDock(DyStockTradeStrategyWidget, '策略', Qt.LeftDockWidgetArea, self._mainEngine.eventEngine)
        widgetMarketStrength, dockMarketStrength = self._createDock(DyStockMarketStrengthWidget, '市场强度', Qt.LeftDockWidgetArea, self._mainEngine.eventEngine)
        widgetMarketIndex, dockMarketIndex = self._createDock(DyStockMarketIndexMonitorWidget, '指数行情', Qt.LeftDockWidgetArea, self._mainEngine.eventEngine)
        widgetLog, dockLog = self._createDock(DyLogWidget, '日志', Qt.RightDockWidgetArea, self._mainEngine.eventEngine)
        widgeAccount, dockAccount = self._createDock(DyStockTradeAccountWidget, '账户', Qt.RightDockWidgetArea, self._mainEngine.eventEngine)

        self.tabifyDockWidget(dockLog, dockAccount)
    
    def _enableProxy(self):
        enableProxy =  self._proxyAction.isChecked()

        # put event
        event = DyEvent(DyEventType.enableProxy)
        event.data = enableProxy

        self._mainEngine.eventEngine.put(event)

    def _strategyDataPrepareDateAct(self):
        data = {}
        if DySingleEditDlg(data, '策略数据准备日期', '策略数据准备日期', datetime.now().strftime("%Y-%m-%d"), self).exec_():
            date = data['data']
            if not date: date = None

            DyStockTradeCommon.strategyPreparedDataDay = date

    def _initMenu(self):
        """ 初始化菜单 """
        # 创建操作
        self._proxyAction = QAction('代理', self)
        self._proxyAction.triggered.connect(self._enableProxy)
        self._proxyAction.setCheckable(True)

        strategyDataPrepareDateAction = QAction('策略数据准备日期...', self)
        strategyDataPrepareDateAction.triggered.connect(self._strategyDataPrepareDateAct)

        # 创建菜单
        menuBar = self.menuBar()
        
        # 添加菜单
        settingsMenu = menuBar.addMenu('设置')
        settingsMenu.addAction(self._proxyAction)
        settingsMenu.addAction(strategyDataPrepareDateAction)

    def closeEvent(self, event):
        """ 关闭事件 """
        self._mainEngine.exit()

        return super().closeEvent(event)

    def _initToolBar(self):
        """ 初始化工具栏 """
        # 添加工具栏
        toolBar = self.addToolBar('工具栏')
        toolBar.setObjectName('工具栏')

        # WeChat
        self._wxAction = QAction('开启微信提醒', self)
        self._wxAction.triggered.connect(self._wxAct)
        toolBar.addAction(self._wxAction)

        self._wxTestAction = QAction('发送测试微信', self)
        self._wxTestAction.triggered.connect(self._wxTestAct)
        toolBar.addAction(self._wxTestAction)

        toolBar.addSeparator()

        # QQ
        self._QQMsgAction = QAction('开启QQ提醒', self)
        self._QQMsgAction.triggered.connect(self._QQMsgAct)
        #toolBar.addAction(self._QQMsgAction)

        # '开启QQ提醒'菜单
        self._enableQQMsgMenu = QMenu(self)

        # '开启QQ提醒'菜单的操作
        action = QAction('通过GUI登陆二维码', self)
        action.triggered.connect(self._enableQQMsgByGUIAct)
        self._enableQQMsgMenu.addAction(action)

        action = QAction('通过邮箱登陆二维码', self)
        action.triggered.connect(self._enableQQMsgByMailAct)
        self._enableQQMsgMenu.addAction(action)

        self._QQMsgTestAction = QAction('发送QQ测试消息', self)
        self._QQMsgTestAction.triggered.connect(self._QQMsgTestAct)
        #toolBar.addAction(self._QQMsgTestAction)

        self._enableTimerLogAction = QAction('打开Timer日志', self)
        self._enableTimerLogAction.triggered.connect(self._enableTimerLogAct)
        toolBar.addAction(self._enableTimerLogAction)

        self._enableSinaTickOptimizationAction = QAction('关闭新浪Tick优化', self)
        self._enableSinaTickOptimizationAction.triggered.connect(self._enableSinaTickOptimizationAct)
        toolBar.addAction(self._enableSinaTickOptimizationAction)

        self._enableCtaEngineTickOptimizationAction = QAction('关闭CTA引擎Tick优化', self)
        self._enableCtaEngineTickOptimizationAction.triggered.connect(self._enableCtaEngineTickOptimizationAct)
        toolBar.addAction(self._enableCtaEngineTickOptimizationAction)

        toolBar.addSeparator()

        self._t1Action = QAction('T+1', self)
        self._t1Action.triggered.connect(self._t1Act)
        toolBar.addAction(self._t1Action)

        toolBar.addSeparator()

        # RPC
        self._rpcAction = QAction('开启RPC', self)
        self._rpcAction.triggered.connect(self._rpcAct)
        toolBar.addAction(self._rpcAction)

        self._rpcAction.setEnabled(False)

        # '开启RPC'菜单
        self._rpcMenu = QMenu(self)

        # '开启RPC'菜单的操作
        action = QAction('本机', self)
        action.triggered.connect(self._startRpcWithLocalHostAct)
        self._rpcMenu.addAction(action)

        action = QAction('远程服务器', self)
        action.triggered.connect(self._startRpcWithRemoteServerAct)
        self._rpcMenu.addAction(action)

        self._rpcTestAction = QAction('开启RPC测试', self)
        self._rpcTestAction.triggered.connect(self._startRpcTestAct)
        toolBar.addAction(self._rpcTestAction)

        self._rpcTestAction.setEnabled(False)

        toolBar.addSeparator()

        self._oneKeyHangUpAction = QAction('开启一键挂机', self)
        self._oneKeyHangUpAction.triggered.connect(self._oneKeyHangUpAct)
        toolBar.addAction(self._oneKeyHangUpAction)

    def _startRpcTestAct(self):
        DyStockTradeCommon.testRpc = not DyStockTradeCommon.testRpc

        if DyStockTradeCommon.testRpc:
            self._rpcTestAction.setText('关闭RPC测试')
        else:
            self._rpcTestAction.setText('开启RPC测试')

    def _startRpcWithLocalHostAct(self):
        self._rpcAction.setText('停止RPC:本机')

        # put event
        event = DyEvent(DyEventType.startStockRpc)
        event.data = 'localhost'

        self._mainEngine.eventEngine.put(event)

    def _startRpcWithRemoteServerAct(self):
        self._rpcAction.setText('停止RPC:远程服务器')

        # put event
        event = DyEvent(DyEventType.startStockRpc)
        event.data = 'remoteServer'

        self._mainEngine.eventEngine.put(event)

    def _rpcAct(self):
        text = self._rpcAction.text()

        if text == '开启RPC':
            self._rpcMenu.popup(QCursor.pos())

        else:
            self._rpcAction.setText('开启RPC')

            # put event
            event = DyEvent(DyEventType.stopStockRpc)
            self._mainEngine.eventEngine.put(event)

    def _oneKeyHangUpAct(self):
        """
            !!!一键挂机，务必启动好所有的策略执行此操作。
        """
        def _run(self):
            if self._oneKeyHangUp.start():
                self._oneKeyHangUpAction.setText('关闭一键挂机')
            else:
                self._oneKeyHangUpAction.setText('开启一键挂机')

            self._oneKeyHangUpAction.setEnabled(True)

        text = self._oneKeyHangUpAction.text()

        if text == '开启一键挂机':
            self._oneKeyHangUpAction.setEnabled(False)

            threading.Thread(target=_run, args=(self,)).start()
        else:
            self._oneKeyHangUp.stop()

            self._oneKeyHangUpAction.setText('开启一键挂机')

    def _enableQQMsgByGUIAct(self):
        self._QQMsgAction.setText('停止QQ提醒')

        # put event
        event = DyEvent(DyEventType.startStockQQMsg)
        event.data = 'gui'

        self._mainEngine.eventEngine.put(event)

    def _enableQQMsgByMailAct(self):
        self._QQMsgAction.setText('停止QQ提醒')

        # put event
        event = DyEvent(DyEventType.startStockQQMsg)
        event.data = 'mail'

        self._mainEngine.eventEngine.put(event)

    def _QQMsgAct(self):
        text = self._QQMsgAction.text()

        if text == '开启QQ提醒':
            self._enableQQMsgMenu.popup(QCursor.pos())

        else:
            self._QQMsgAction.setText('开启QQ提醒')

            # put event
            event = DyEvent(DyEventType.stopStockQQMsg)
            self._mainEngine.eventEngine.put(event)

    def _QQMsgTestAct(self):
        text = '测试消息:\n{0}'.format(datetime.now())

        # put event
        event = DyEvent(DyEventType.sendStockTestQQMsg)
        event.data = text

        self._mainEngine.eventEngine.put(event)

    def _wxAct(self):
        text = self._wxAction.text()

        if text == '开启微信提醒':
            self._wxAction.setText('停止微信提醒')

            # put event
            event = DyEvent(DyEventType.startStockWx)
            self._mainEngine.eventEngine.put(event)

        else:
            self._wxAction.setText('开启微信提醒')

            # put event
            event = DyEvent(DyEventType.stopStockWx)
            self._mainEngine.eventEngine.put(event)

    def _wxTestAct(self):
        text = '测试消息:\n{0}'.format(datetime.now())

        # put event
        event = DyEvent(DyEventType.sendStockTestWx)
        event.data = text

        self._mainEngine.eventEngine.put(event)

    def _enableTimerLogAct(self):
        text = self._enableTimerLogAction.text()

        if text == '打开Timer日志':
            self._enableTimerLogAction.setText('关闭Timer日志')

            DyEventEngine.enableTimerLog = True
            DyStockTradeCommon.enableTimerLog = True

        else:
            self._enableTimerLogAction.setText('打开Timer日志')

            DyEventEngine.enableTimerLog = False
            DyStockTradeCommon.enableTimerLog = False

    def _enableSinaTickOptimizationAct(self):
        text = self._enableSinaTickOptimizationAction.text()

        if text == '关闭新浪Tick优化':
            self._enableSinaTickOptimizationAction.setText('打开新浪Tick优化')

            DyStockTradeCommon.enableSinaTickOptimization = False

        else:
            self._enableSinaTickOptimizationAction.setText('关闭新浪Tick优化')

            DyStockTradeCommon.enableSinaTickOptimization = True

    def _enableCtaEngineTickOptimizationAct(self):
        text = self._enableCtaEngineTickOptimizationAction.text()

        if text == '关闭CTA引擎Tick优化':
            self._enableCtaEngineTickOptimizationAction.setText('打开CTA引擎Tick优化')

            DyStockTradeCommon.enableCtaEngineTickOptimization = False

        else:
            self._enableCtaEngineTickOptimizationAction.setText('关闭CTA引擎Tick优化')

            DyStockTradeCommon.enableCtaEngineTickOptimization = True

    def _t1Act(self):
        text = self._t1Action.text()

        if text == 'T+1':
            self._t1Action.setText('T+0')

            DyStockTradeCommon.T1 = False

        else:
            self._t1Action.setText('T+1')

            DyStockTradeCommon.T1 = True