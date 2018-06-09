from PyQt5.QtWidgets import QDockWidget

from .Basic.DyStockDealDetailsWidget import *
from .Basic.DyStockDealDetailsInfoWidget import *
from ....Data.Engine.DyStockDataEngine import *
from ...DyStockCommon import *
from DyCommon.Ui.DyBasicMainWindow import *


class DyStockDealDetailsMainWindow(DyBasicMainWindow):
    name = 'DyStockDealDetailsMainWindow'

    def __init__(self, dataViewer, parent=None):
        super().__init__(None, None, parent)
        
        self._dataViewer = dataViewer
        self._dataEngine = dataViewer.dataEngine
        
        self._initUi()

    def _initUi(self):
        """初始化界面"""
        self.setWindowTitle('股票成交明细')

        self._initCentral()
        self._initToolBar()

        self._loadWindowSettings()

    def _initCentral(self):
        """初始化中心区域"""
        self._widgetInfo, dockInfo = self._createDock(DyStockDealDetailsInfoWidget, '信息', Qt.TopDockWidgetArea, self._dataEngine.daysEngine)
        self._widgetDealDetails, dockDealDetails = self._createDock(DyStockDealDetailsWidget, '成交明细', Qt.BottomDockWidgetArea, self._dataEngine)

        # for turn
        self._widgetDealDetails.setInfoWidget(self._widgetInfo)

    def _initToolBar(self):
        """ 初始化工具栏 """
        # 创建操作
        dayKChartAction = QAction('日K线', self)
        dayKChartAction.triggered.connect(self._dayKChartAct)

        timeShareChartAction = QAction('分时图', self)
        timeShareChartAction.triggered.connect(self._timeShareChartAct)

        dealsDistAction = QAction('成交分布', self)
        dealsDistAction.triggered.connect(self._dealsDistAct)

        forwardAction = QAction('<', self)
        forwardAction.triggered.connect(self._forwardAct)

        backwardAction = QAction('>', self)
        backwardAction.triggered.connect(self._backwardAct)

        # 添加工具栏
        toolBar = self.addToolBar('工具栏')
        toolBar.setObjectName('工具栏')
        toolBar.addAction(dayKChartAction)
        toolBar.addAction(timeShareChartAction)
        toolBar.addAction(dealsDistAction)
        toolBar.addAction(forwardAction)
        toolBar.addAction(backwardAction)

    def closeEvent(self, event):
        """关闭事件"""
        return super().closeEvent(event)
            
    def _timeShareChartAct(self):
        code = self._widgetInfo.code
        day = self._widgetInfo.day

        self._dataViewer.plotTimeShareChart(code, day, 0)

    def _dayKChartAct(self):
        code = self._widgetInfo.code
        day = self._widgetInfo.day

        self._dataViewer.plotCandleStick(code, [-DyStockCommon.dayKChartPeriodNbr, day, DyStockCommon.dayKChartPeriodNbr])

    def _dealsDistAct(self):
        code = self._widgetInfo.code
        day = self._widgetInfo.day

        self._dataViewer.plotDealsDist(code, day, 0)

    def _forwardAct(self):
        self._widgetInfo.forward()
        self._widgetDealDetails.forward()

    def _backwardAct(self):
        self._widgetInfo.backward()
        self._widgetDealDetails.backward()

    def set(self, code, date):
        self._widgetInfo.set(code, date)
        self._widgetDealDetails.set(code, date)