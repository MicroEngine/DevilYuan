from PyQt5 import QtCore
from PyQt5.QtWidgets import QTabWidget

from EventEngine.DyEvent import *
from DyCommon.Ui.DyTableWidget import *
from .DyStockTradeStrategyMarketMonitorWidget import *
from .Other.DyStockTradeStrategyBuyDlg import *
from .Other.DyStockTradeStrategySellDlg import *


class DyStockTradeStrategiesMarketMonitorWidget(QTabWidget):
    """
        所有策略的实时监控窗口
    """
    signalStartStockCtaStrategy = QtCore.pyqtSignal(type(DyEvent()))
    signalStopStockCtaStrategy = QtCore.pyqtSignal(type(DyEvent()))

    def __init__(self, eventEngine):
        super().__init__()

        self._eventEngine = eventEngine

        self._strategyMarketMonitorWidgets = {} # {strategy name: (widget instance, strategyCls)}

        self._initTabBarMenu()

        self._registerEvent()

    def _initTabBarMenu(self):
        """ 初始化表头右键菜单 """
        # 设置Tab右键菜单事件
        tabBar = self.tabBar()
        tabBar.setContextMenuPolicy(Qt.CustomContextMenu)
        tabBar.customContextMenuRequested.connect(self._showTabContextMenu)

        # 创建TabBar菜单
        self._tabBarMenu = QMenu(self)
        
        action = QAction('买入...', self)
        action.triggered.connect(self._buyAct)
        self._tabBarMenu.addAction(action)

        action = QAction('卖出...', self)
        action.triggered.connect(self._sellAct)
        self._tabBarMenu.addAction(action)

    def _showTabContextMenu(self, position):
        self._rightClickedTabIndex = self.tabBar().tabAt(position)

        self._tabBarMenu.popup(QCursor.pos())

    def _buyAct(self):
        tabText = self.tabText(self._rightClickedTabIndex)

        strategyCls = self._strategyMarketMonitorWidgets[tabText][1]

        DyStockTradeStrategyBuyDlg(self._eventEngine, strategyCls).exec_()

    def _sellAct(self):
        tabText = self.tabText(self._rightClickedTabIndex)

        strategyCls = self._strategyMarketMonitorWidgets[tabText][1]

        DyStockTradeStrategySellDlg(self._eventEngine, strategyCls).exec_()

    def _startStockCtaStrategyHandler(self, event):
        strategyCls = event.data['class']
        strategyState = event.data['state']

        # 添加策略行情窗口到Tab窗口
        widget = DyStockTradeStrategyMarketMonitorWidget(self._eventEngine, strategyCls, strategyState)
        self.addTab(widget, strategyCls.chName)

        # save
        self._strategyMarketMonitorWidgets[strategyCls.chName] = (widget, strategyCls)

    def _stopStockCtaStrategyHandler(self, event):
        strategyCls = event.data['class']

        widget = self._strategyMarketMonitorWidgets[strategyCls.chName][0]
        widget.close()

        self.removeTab(self.indexOf(widget))

        del self._strategyMarketMonitorWidgets[strategyCls.chName]

    def _registerEvent(self):
        self.signalStartStockCtaStrategy.connect(self._startStockCtaStrategyHandler)
        self._eventEngine.register(DyEventType.startStockCtaStrategy, self.signalStartStockCtaStrategy.emit)

        self.signalStopStockCtaStrategy.connect(self._stopStockCtaStrategyHandler)
        self._eventEngine.register(DyEventType.stopStockCtaStrategy, self.signalStopStockCtaStrategy.emit)


