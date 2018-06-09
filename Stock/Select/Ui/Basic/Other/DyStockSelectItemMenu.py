try:
    from PyQt5.QtWebKitWidgets import QWebView as DyWebView
except ImportError:
    from PyQt5.QtWebEngineWidgets import QWebEngineView as DyWebView
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QApplication

from ..Dlg.DyStockSelectIndustryCompareDlg import DyStockSelectIndustryCompareDlg
from DyCommon.Ui.DySingleEditDlg import *
from EventEngine.DyEvent import *
from .....Common.Ui.Deal.DyStockDealDetailsMainWindow import *
from ....Strategy.Stats.DySS_Correlation import *


class DyStockSelectItemMenu(object):

    def __init__(self, interface):
        """
            @interface provides below interfaces:
                getCodeDate
                getTargetCodeDateN
                strategyName
                dataViewer
                menu
        """
        self._interface = interface
        self._dataViewer = interface.dataViewer

        self._browsers = []

        self._initMenu()

    def _initStrategyMenu(self):
        if self._interface.strategyName == DySS_Correlation.chName:
            # 创建操作
            scatterChartAction = QAction('散列图', self._interface)
            scatterChartAction.triggered.connect(self._scatterChartAct)

            self._interface.menu.addAction(scatterChartAction)

    def _initMenu(self):
        menu = self._interface.menu

        menu.addSeparator()

        # 分时图
        timeShareChartActions = [QAction('基准日期', self._interface)] + [QAction('向前{0}日'.format(day), self._interface) for day in range(1,10)]

        # 添加二级菜单
        self._timeShareChartMenu = menu.addMenu('分时图')
        for timeShareChartAction in timeShareChartActions:
            timeShareChartAction.triggered.connect(self._timeShareChartAct)
            timeShareChartAction.setCheckable(True)

            self._timeShareChartMenu.addAction(timeShareChartAction)

        # 成交价格分布
        dealsDistActions = [QAction('基准日期', self._interface)] + [QAction('向前{0}日'.format(day), self._interface) for day in [5,10,20,30,60,90,120]]

        # 添加二级菜单
        self._dealsDistMenu = menu.addMenu('成交分布')
        for dealsDistAction in dealsDistActions:
            dealsDistAction.triggered.connect(self._dealsDistAct)
            dealsDistAction.setCheckable(True)

            self._dealsDistMenu.addAction(dealsDistAction)

        # 成交明细
        dealDetailsAction = QAction('成交明细', self._interface)
        dealDetailsAction.triggered.connect(self._dealDetailsAct)

        menu.addAction(dealDetailsAction)

        menu.addSeparator()

        # 个股资料
        action = QAction('个股资料', self._interface)
        action.triggered.connect(self._stockInfoAct)

        menu.addAction(action)

        # 行业对比
        action = QAction('行业对比...', self._interface)
        action.triggered.connect(self._industryCompareAct)

        menu.addAction(action)

        menu.addSeparator()

        # 技术分析
        action = QAction('技术分析', self._interface)
        action.triggered.connect(self._technicalAnalysisAct)

        menu.addAction(action)

        # 波动分布
        action = QAction('波动分布...', self._interface)
        action.triggered.connect(self._volatilityDistAct)

        menu.addAction(action)

        # ATR Extreme通道
        action = QAction('ATR Extreme', self._interface)
        action.triggered.connect(self._atrExtremeAct)

        menu.addAction(action)

        # 不同策略定制的菜单
        self._initStrategyMenu()

    def _dealsDistAct(self):
        code, date = self._interface.getCodeDate()
        if code is None: return

        # get triggered action
        for action in self._dealsDistMenu.actions():
            if action.isChecked():
                action.setChecked(False)

                text = action.text()
                try:
                    n = -int(text[2:-1]) + 1
                except Exception as ex:
                    n = 0

                break

        self._dataViewer.plotDealsDist(code, date, n)

    def _timeShareChartAct(self):
        code, date = self._interface.getCodeDate()
        if code is None: return

        # get triggered action
        for action in self._timeShareChartMenu.actions():
            if action.isChecked():
                action.setChecked(False)

                text = action.text()
                try:
                    n = -int(text[2:-1])
                except Exception as ex:
                    n = 0

                break

        self._dataViewer.plotTimeShareChart(code, date, n)

    def _scatterChartAct(self):
        target, code, date, n = self._interface.getTargetCodeDateN()
        if target is None: return

        self._dataViewer.plotScatterChart(target, code, date, n)

    def _dealDetailsAct(self):
        code, date = self._interface.getCodeDate()
        if code is None: return

        window = DyStockDealDetailsMainWindow(self._dataViewer, self._interface)
        window.set(code, date)

        window.show()

    def _stockInfoAct(self):
        code, name = self._interface.getCodeName()
        if code is None: return

        browser = DyWebView()
        url = 'http://basic.10jqka.com.cn/32/{0}/'.format(code[:-3])
        browser.load(QUrl(url))

        browser.setWindowTitle(name)
        
        rect = QApplication.desktop().availableGeometry()
        taskBarHeight = QApplication.desktop().height() - rect.height()

        browser.resize(rect.width()//3 * 2, rect.height() - taskBarHeight)
        browser.move((rect.width() - browser.width())//2, 0)

        browser.show()

        self._browsers.append(browser)

    def _industryCompareAct(self):
        code, date = self._interface.getCodeDate()
        if code is None: return

        code, name = self._interface.getCodeName()

        data = {}
        if not DyStockSelectIndustryCompareDlg(name, date, data).exec_():
            return

        event = DyEvent(DyEventType.getIndustryCompareReq)
        event.data['code'] = code
        event.data['name'] = name
        event.data['widget'] = self._interface
        event.data['baseDate'] = date
        event.data.update(data)

        self._interface.eventEngine.put(event)

    def _technicalAnalysisAct(self):
        code, date = self._interface.getCodeDate()
        if code is None: return

        self._interface.dataViewer.plotTA(code, [-DyStockCommon.dayKChartPeriodNbr, date, DyStockCommon.dayKChartPeriodNbr])

    def _volatilityDistAct(self):
        code, date = self._interface.getCodeDate()
        if code is None: return

        code, name = self._interface.getCodeName()

        data = {}
        if not DySingleEditDlg(data, '波动分布[{0}]'.format(name), '基准日期[{0}]向前N日(不包含基准日期)'.format(date), 90).exec_():
            return

        self._interface.dataViewer.plotVolatilityDist(code, date, data['data'])

    def _atrExtremeAct(self):
        code, date = self._interface.getCodeDate()
        if code is None: return

        self._interface.dataViewer.plotAtrExtreme(code, [-DyStockCommon.dayKChartPeriodNbr, date, DyStockCommon.dayKChartPeriodNbr])