from PyQt5.QtWidgets import QTabWidget

from EventEngine.DyEvent import *
from .DyStockBackTestingStrategyParamResultWidget import *


class DyStockBackTestingStrategyParamsResultWidget(QTabWidget):
    """ 策略多个参数组合的回测窗口 """

    def __init__(self, strategyCls, eventEngine, dataEngine, dataViewer, parent=None):
        super().__init__(parent)

        self._strategyCls = strategyCls
        self._eventEngine = eventEngine
        self._dataEngine = dataEngine
        self._dataViewer = dataViewer

        # 每个回测策略会被分成多个参数组合运行，每个参数组合的回归结果会生成一个参数组合窗口
        self._strategyParamWidgets = {}

        self._initTabBarMenu()

    def update(self, ackData):
        """ 更新策略参数组合一个回测周期的回测结果 """
        # unpack
        paramGroupNo = ackData.paramGroupNo

        tabName = '参数' + str(paramGroupNo)
        self._strategyParamWidgets[tabName].update(ackData)

    def removeAll(self):
        for _, widget in self._strategyParamWidgets.items():
            widget.removeAll()

        self._strategyParamWidgets = {}

        count = self.count()
        for _ in range(count):
            self.removeTab(0)

    def newParam(self, event):
        # unpack
        paramGroupNo = event.data['param']['groupNo']
        param = event.data['param']['data']

        # tab window title
        tabName = '参数' + str(paramGroupNo)

        assert(tabName not in self._strategyParamWidgets)

        widget = DyStockBackTestingStrategyParamResultWidget(self._strategyCls, paramGroupNo, param, self._eventEngine, self._dataEngine, self._dataViewer)
            
        self.addTab(widget, tabName)

        # save
        self._strategyParamWidgets[tabName] = widget

    def newPeriod(self, event):
        paramGroupNo = event.data['paramGroupNo']

        tabName = '参数' + str(paramGroupNo)

        self._strategyParamWidgets[tabName].newPeriod(event)

    def _initTabBarMenu(self):
        """初始化表头右键菜单"""

        # 设置Tab右键菜单事件
        tabBar = self.tabBar()
        tabBar.setContextMenuPolicy(Qt.CustomContextMenu)
        tabBar.customContextMenuRequested.connect(self._showTabContextMenu)
        
        # 创建操作
        mergePeriodAction = QAction('合并周期', self)
        mergePeriodAction.triggered.connect(self._mergePeriodAct)
        
        # 创建TabBar菜单
        self._tabBarMenu = QMenu(self) 

        # 添加菜单
        self._tabBarMenu.addAction(mergePeriodAction)

    def _showTabContextMenu(self, position):
        self._rightClickedTabIndex = self.tabBar().tabAt(position)

        self._tabBarMenu.popup(QCursor.pos())

    def _mergePeriodAct(self):
        self.widget(self._rightClickedTabIndex)

    def sort(self, ascending=True):
        widgets = {}
        for tabName, widget in self._strategyParamWidgets():
            curPnlRatio = widget.getCurPnlRatio()
            widgets[curPnlRatio] = [tabName, widget]

        count = self.count()
        for _ in range(count):
            self.removeTab(0)

        curPnlRatios = sorted(widgets, reverse=not ascending)
        for curPnlRatio in curPnlRatios:
            self.addTab(widgets[curPnlRatio][1], widgets[curPnlRatio][0])
