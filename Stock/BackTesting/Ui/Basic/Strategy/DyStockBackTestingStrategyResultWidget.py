from PyQt5.QtWidgets import QTabWidget

from .DyStockBackTestingStrategyParamGroupResultWidget import *
from .Other.DyStockBackTestingStrategyResultOverviewWindow import *


class DyStockBackTestingStrategyResultWidget(QTabWidget):
    """ 策略多个参数组合的回测窗口 """

    def __init__(self, strategyCls, eventEngine, dataEngine, dataViewer):
        super().__init__()

        self._strategyCls = strategyCls
        self._eventEngine = eventEngine
        self._dataEngine = dataEngine
        self._dataViewer = dataViewer

        # 每个回测策略会被分成多个参数组合运行，每个参数组合的回归结果会生成一个参数组合窗口
        self._paramGroupWidgets = {}

        self._windows = []

        self._initTabBarMenu()

    def update(self, ackData):
        """ 更新策略参数组合一个回测周期的回测结果 """
        # unpack
        paramGroupNo = ackData.paramGroupNo

        tabName = '参数' + str(paramGroupNo)
        self._paramGroupWidgets[tabName].update(ackData)

    def removeAll(self):
        for _, widget in self._paramGroupWidgets.items():
            widget.removeAll()

        self._paramGroupWidgets = {}

        count = self.count()
        for _ in range(count):
            self.removeTab(0)

    def newParam(self, event):
        # unpack
        paramGroupNo = event.data['param']['groupNo']
        param = event.data['param']['data']

        # tab window title
        tabName = '参数' + str(paramGroupNo)

        assert(tabName not in self._paramGroupWidgets)

        widget = DyStockBackTestingStrategyParamGroupResultWidget(self._strategyCls, paramGroupNo, param, self._eventEngine, self._dataEngine, self._dataViewer)
            
        self.addTab(widget, tabName)

        # save
        self._paramGroupWidgets[tabName] = widget

        self.setCurrentWidget(widget)

        #self._getDockWidget().raise_()

    def newPeriod(self, event):
        paramGroupNo = event.data['paramGroupNo']

        tabName = '参数' + str(paramGroupNo)

        self._paramGroupWidgets[tabName].newPeriod(event)

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
        # 按盈亏作为键值建立参数窗口字典
        widgets = {}
        for tabName, widget in self._paramGroupWidgets.items():
            curPnlRatio = widget.getCurPnlRatio() # 盈亏可能会相同
            widgets.setdefault(curPnlRatio, [])
            widgets[curPnlRatio].append([tabName, widget])

        # 删除所有Tab
        count = self.count()
        for _ in range(count):
            self.removeTab(0)

        # 按盈亏重新排列Tab
        curPnlRatios = sorted(widgets, reverse=not ascending)
        for curPnlRatio in curPnlRatios:
            for tabName, widget in widgets[curPnlRatio]:
                self.addTab(widget, tabName)

    def _getDockWidget(self):
        parent = self.parentWidget()
        while not isinstance(parent, QDockWidget):
            parent = parent.parentWidget()

        return parent

    def paramGroupStatsOverview(self):
        # get overview data
        data = []
        widgets = []
        for i in range(self.count()):
            tabName = self.tabText(i)
            widget = self.widget(i)

            columns, rowData = widget.overview()
            data.append([tabName] + rowData)

            widgets.append(widget)

        if data:
            columns = ['参数组合'] + columns

        # show window
        window = DyStockBackTestingStrategyResultOverviewWindow(self, widgets, columns, data, '盈亏(%)')

        window.setWindowTitle(self._strategyCls.chName)

        rect = QApplication.desktop().availableGeometry()
        taskBarHeight = QApplication.desktop().height() - rect.height()

        window.resize(rect.width()//3 * 2, rect.height() - taskBarHeight)
        window.move((rect.width() - window.width())//2, 0)

        window.show()

        self._windows.append(window)

        