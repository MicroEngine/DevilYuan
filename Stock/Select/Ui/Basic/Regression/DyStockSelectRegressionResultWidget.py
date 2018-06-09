from PyQt5 import QtCore
from PyQt5.QtWidgets import QTabWidget

from .DyStockSelectStrategyRegressionResultWidget import *
from EventEngine.DyEvent import *


class DyStockSelectRegressionResultWidget(QTabWidget):

    signal = QtCore.pyqtSignal(type(DyEvent()))

    def __init__(self, eventEngine, paramWidget):
        super().__init__()

        self._eventEngine = eventEngine
        self._paramWidget = paramWidget

        self._newRegressionStrategyCls = None
        self._strategyWidgets = {}

        self._windows = [] # only for show
        
        self._registerEvent()

        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self._closeTab)

        self._initTabBarMenu()

    def _initTabBarMenu(self):
        """ 初始化表头右键菜单 """
        # 设置Tab右键菜单事件
        tabBar = self.tabBar()
        tabBar.setContextMenuPolicy(Qt.CustomContextMenu)
        tabBar.customContextMenuRequested.connect(self._showTabContextMenu)
        
        # 创建TabBar菜单
        self._tabBarMenu = QMenu(self)

        action = QAction('合并周期', self)
        action.triggered.connect(self._mergePeriodAct)
        self._tabBarMenu.addAction(action)

        action = QAction('描述统计', self)
        action.triggered.connect(self._describeAct)
        self._tabBarMenu.addAction(action)

        action = QAction('散布图矩阵', self)
        action.triggered.connect(self._scatterMatrixAct)
        self._tabBarMenu.addAction(action)

        self._tabBarMenu.addSeparator()

        # 初始化二级菜单
        self._probDistMenu = None

    def _showTabContextMenu(self, position):
        self._rightClickedTabIndex = self.tabBar().tabAt(position)

        # 如果二级菜单没有添加，动态添加二级菜单
        if self._probDistMenu is None:
            colNames = self.widget(self._rightClickedTabIndex).getNumberColNames()
            if colNames:
                self._probDistMenu = self._tabBarMenu.addMenu('概率分布')

                # 创建操作
                for name in colNames:
                    probDistAction = QAction(name, self)
                    probDistAction.triggered.connect(self._probDistAct)
                    probDistAction.setCheckable(True)

                    self._probDistMenu.addAction(probDistAction)

        self._tabBarMenu.popup(QCursor.pos())

    def _probDistAct(self):
        # get triggered action
        for action in self._probDistMenu.actions():
            if action.isChecked():
                action.setChecked(False)
                self.widget(self._rightClickedTabIndex).probDistAct(action.text())
                return

    def _describeAct(self):
        self.widget(self._rightClickedTabIndex).describe()

    def _mergePeriodAct(self):
        self.widget(self._rightClickedTabIndex).mergePeriod(self.tabText(self._rightClickedTabIndex))

    def _scatterMatrixAct(self):
        self.widget(self._rightClickedTabIndex).scatterMatrix()

    def _stockSelectStrategyRegressionAckHandler(self, event):
        # unpack
        strategyCls = event.data['class']
        result = event.data['result']
        period = event.data['period']
        day = event.data['day']
        if result is None: return

        tabName = strategyCls.chName

        # remove tab window's tabs if existing
        if self._newRegressionStrategyCls == strategyCls and tabName in self._strategyWidgets:
            self._strategyWidgets[tabName].removeAll()

        # create new strategy result tab
        if tabName not in self._strategyWidgets:
            widget = DyStockSelectStrategyRegressionResultWidget(self._eventEngine, strategyCls, self._paramWidget)
            self.addTab(widget, tabName)

            # save
            self._strategyWidgets[tabName] = widget

        self._newRegressionStrategyCls = None

        self._strategyWidgets[tabName].append(period, day, result)

        self.parentWidget().raise_()

    def _registerEvent(self):
        self.signal.connect(self._stockSelectStrategyRegressionAckHandler)
        self._eventEngine.register(DyEventType.stockSelectStrategyRegressionAck, self.signal.emit)

        self._eventEngine.register(DyEventType.stockSelectStrategyRegressionReq, self._stockSelectStrategyRegressionReqHandler)

    def _closeTab(self, index):
        tabName = self.tabText(index)
        self._strategyWidgets[tabName].close()

        del self._strategyWidgets[tabName]

        self.removeTab(index)

    def _stockSelectStrategyRegressionReqHandler(self, event):
        self._newRegressionStrategyCls = event.data['class']

    def load(self, data, strategyCls):
        """
            @data: JSON data
        """
        className = data.get('class')
        if not className:
            return False

        if className != 'DyStockSelectStrategyRegressionResultWidget':
            return False

        window = DyStockSelectStrategyRegressionPeriodResultWidget(self._eventEngine, data['name'], strategyCls)
        window.rawSetColNames(data['data']['colNames'])
        window.rawAppend(data['data']['rows'], data['autoForegroundColName'])

        window.setWindowTitle('{0}{1}'.format(strategyCls.chName, data['name']))
        window.showMaximized()

        self._windows.append(window)

        return True

