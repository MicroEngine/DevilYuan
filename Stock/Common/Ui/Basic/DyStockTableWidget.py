import threading
import os
import struct
import requests
from bs4 import BeautifulSoup
import re

try:
    from PyQt5.QtWebKitWidgets import QWebView as DyWebView
except ImportError:
    from PyQt5.QtWebEngineWidgets import QWebEngineView as DyWebView

from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QApplication, QFileDialog
from PyQt5 import QtCore

from EventEngine.DyEvent import *
from DyCommon.Ui.DyStatsTableWidget import *
from ....Data.Viewer.DyStockDataViewer import DyStockDataViewer
from ....Data.Utility.DyStockDataSpider import DyStockDataSpider
from ...DyStockCommon import *
from ..Deal.DyStockDealDetailsMainWindow import *
from .Other.DyStockIndustryCompareWindow import *
from ....Data.Engine.DyStockDataEngine import *
from ....Data.Utility.DyStockDataAssembler import *
from .Dlg.DyStockTableAddColumnsDlg import *
from .Dlg.DyStockInfoDlg import *
from .Dlg.DyStockTableFilterDlg import *
from .Dlg.DyStockTableSelectDlg import *
from .Dlg.DyStockIndustryCompareDlg import *
from .Dlg.DyStockTableColumnOperateDlg import DyStockTableColumnOperateDlg


class DyStockTableWidget(DyStatsTableWidget):
    """
        股票基类窗口
        默认每行以‘代码’，‘名称’开始
        提供关于股票所有相关的操作和信息展示
        决定股票表的两个因子：name和baseDate
    """
    # header signal
    stockTableAddColumnsActAckSignal = QtCore.pyqtSignal(type(DyEvent()))

    # item signal
    stockTableIndustryCompareActAckSignal = QtCore.pyqtSignal(type(DyEvent()))

    def __init__(self,
                 eventEngine,
                 parent=None,
                 name=None,
                 baseDate=None,
                 readOnly=True,
                 index=False,
                 autoScroll=False,
                 floatRound=2
                 ):
        super().__init__(parent=parent,
                         readOnly=readOnly,
                         index=index,
                         autoScroll=autoScroll,
                         floatRound=floatRound
                         )

        self._name = name
        self._baseDate = baseDate
        self._eventEngine = eventEngine

        self._windows = []
        self._curActionOngoing = False

        self._initDataViewer()

        self._registerEevent()

        self.itemDoubleClicked.connect(self._itemDoubleClicked)

    def _registerEevent(self):
        # header
        self.stockTableAddColumnsActAckSignal.connect(self._stockTableAddColumnsActAckHandler)
        self._eventEngine.register(DyEventType.stockTableAddColumnsActAck, self._stockTableAddColumnsActAckSignalEmitWrapper)

        # item
        self.stockTableIndustryCompareActAckSignal.connect(self._stockTableIndustryCompareActAckHandler)
        self._eventEngine.register(DyEventType.stockTableIndustryCompareActAck, self._stockTableIndustryCompareActAckSignalEmitWrapper)

    def _unregisterEevent(self):
        # header
        self.stockTableAddColumnsActAckSignal.disconnect(self._stockTableAddColumnsActAckHandler)
        self._eventEngine.unregister(DyEventType.stockTableAddColumnsActAck, self._stockTableAddColumnsActAckSignalEmitWrapper)

        # item
        self.stockTableIndustryCompareActAckSignal.disconnect(self._stockTableIndustryCompareActAckHandler)
        self._eventEngine.unregister(DyEventType.stockTableIndustryCompareActAck, self._stockTableIndustryCompareActAckSignalEmitWrapper)

    def closeEvent(self, event):
        self._unregisterEevent()

        return super().closeEvent(event)

    def _initDataViewer(self):
        # 省去非错误log的输出
        errorInfo = DyErrorInfo(self._eventEngine)
        self._dataEngine = DyStockDataEngine(self._eventEngine, errorInfo, registerEvent=False)
        self._dataViewer = DyStockDataViewer(self._dataEngine, errorInfo)
        self._daysEngine = self._dataEngine.daysEngine
        self._ticksEngine = self._dataEngine.ticksEngine

        self._errorProgressInfo = DyErrorProgressInfo(self._eventEngine)

    def _initHeaderMenu(self):
        """
            初始化表头右键菜单
            子类可以改写添加定制菜单
        """
        super()._initHeaderMenu()

        self._headerMenu.addSeparator()

        action = QAction('新窗口', self)
        action.triggered.connect(self._newWindowAct)
        self._headerMenu.addAction(action)

        self._headerMenu.addSeparator()

        # '添加列'
        menu = self._headerMenu.addMenu('添加列')

        action = QAction('个股资料...', self)
        action.triggered.connect(self._addStockInfoColumnsAct)
        menu.addAction(action)

        menu.addSeparator()

        action = QAction('涨幅...', self)
        action.triggered.connect(self._addIncreaseColumnsAct)
        menu.addAction(action)

        action = QAction('最大最小涨幅...', self)
        action.triggered.connect(self._addMaxMinIncreaseColumnsAct)
        menu.addAction(action)

        action = QAction('最大振幅...', self)
        action.triggered.connect(self._addMaxAmplitudeColumnsAct)
        menu.addAction(action)

        action = QAction('分钟涨幅(ETF)...', self) # 本来应该添加当日大盘开盘开始的分钟涨幅，主要为了T+1的策略。由于没有大盘指数的分笔数据，所以使用对应的ETF。
        action.triggered.connect(self._addMinuteIncreaseColumnsAct)
        menu.addAction(action)

        action = QAction('开盘缺口...', self) # 添加开盘缺口，0代表是当日
        action.triggered.connect(self._addOpenGapColumnsAct)
        menu.addAction(action)

        action = QAction('开盘涨幅', self)
        action.triggered.connect(self._addOpenIncreaseColumnsAct)
        menu.addAction(action)

        menu.addSeparator()

        action = QAction('ER(效率系数)...', self)
        action.triggered.connect(self._addErColumnsAct)
        menu.addAction(action)

        action = QAction('波动率...', self)
        action.triggered.connect(self._addVolatilityColumnsAct)
        menu.addAction(action)

        action = QAction('日收益率大盘相关系数...', self)
        action.triggered.connect(self._addDayReturnIndexCorrColumnsAct)
        menu.addAction(action)

        menu.addSeparator()

        action = QAction('列运算...', self)
        action.triggered.connect(self._addColumnOperateColumnsAct)
        menu.addAction(action)

        # '列操作'
        menu = self._headerMenu.addMenu('列操作')

        self._upDownRatioAction = QAction('涨跌比', self)
        self._upDownRatioAction.triggered.connect(self._upDownRatioAct)
        menu.addAction(self._upDownRatioAction)

        self._limitUpRatioAction = QAction('涨停比', self)
        self._limitUpRatioAction.triggered.connect(self._limitUpRatioAct)
        menu.addAction(self._limitUpRatioAction)

        action = QAction('过滤...', self)
        action.triggered.connect(self._filterAct)
        self._headerMenu.addAction(action)

        self._headerMenu.addSeparator()

        action = QAction('导出到同花顺...', self)
        action.triggered.connect(self._export2JqkaAct)
        self._headerMenu.addAction(action)

        action = QAction('保存...', self)
        action.triggered.connect(self._saveAsAct)
        self._headerMenu.addAction(action)

    def _initItemMenu(self):
        """
            初始化Item右键菜单
            子类可以改写添加定制菜单
        """
        super()._initItemMenu()

        self._itemMenu.addSeparator()

        # 分时图
        self._timeShareChartMenu = self._itemMenu.addMenu('分时图')

        actions = [QAction('基准日期', self)] + [QAction('向前{0}日'.format(day), self) for day in range(1, 10)]
        for action in actions:
            action.triggered.connect(self._timeShareChartAct)
            action.setCheckable(True)
            self._timeShareChartMenu.addAction(action)

        # 成交分布
        self._dealsDistMenu = self._itemMenu.addMenu('成交分布')

        actions = [QAction('基准日期', self)] + [QAction('向前{0}日'.format(day), self) for day in [5, 10, 20, 30, 60, 90, 120]]
        for action in actions:
            action.triggered.connect(self._dealsDistAct)
            action.setCheckable(True)
            self._dealsDistMenu.addAction(action)

        # 成交明细
        action = QAction('成交明细', self)
        action.triggered.connect(self._dealDetailsAct)
        self._itemMenu.addAction(action)

        # 日内K线图
        self._intraDayKLineMenu = self._itemMenu.addMenu('日内K线图')

        actions = [QAction('{0}秒'.format(s), self) for s in range(5, 60, 5)] + [QAction('{0}分'.format(m), self) for m in range(1, 16)]
        for action in actions:
            action.triggered.connect(self._intraDayKLineAct)
            action.setCheckable(True)
            self._intraDayKLineMenu.addAction(action)

        self._itemMenu.addSeparator()

        # 个股资料
        action = QAction('个股资料', self)
        action.triggered.connect(self._stockInfoAct)
        self._itemMenu.addAction(action)

        # 行业对比
        action = QAction('行业对比...', self)
        action.triggered.connect(self._industryCompareAct)
        self._itemMenu.addAction(action)

        self._itemMenu.addSeparator()

        # 水平支撑和阻力
        action = QAction('水平支撑和阻力', self)
        action.triggered.connect(self._hsarsAct)
        self._itemMenu.addAction(action)

        # Swing
        action = QAction('Swing', self)
        action.triggered.connect(self._swingAct)
        self._itemMenu.addAction(action)

        # Trend channel
        action = QAction('趋势通道', self)
        action.triggered.connect(self._trendChannelAct)
        self._itemMenu.addAction(action)

        # 波动分布
        action = QAction('波动分布...', self)
        action.triggered.connect(self._volatilityDistAct)
        self._itemMenu.addAction(action)

        # ATR Extreme通道
        action = QAction('ATR Extreme', self)
        action.triggered.connect(self._atrExtremeAct)
        self._itemMenu.addAction(action)

        # 波动率
        action = QAction('波动率', self)
        action.triggered.connect(self._volatilityAct)
        self._itemMenu.addAction(action)

    #------------------------------------------- Item Actions -------------------------------------------
    def _intraDayKLineAct(self):
        code, date = self.getRightClickCodeDate()
        if code is None: return

        # get triggered action
        for action in self._intraDayKLineMenu.actions():
            if action.isChecked():
                action.setChecked(False)

                text = action.text()
                barUnit = 'min' if text[-1] == '分' else 'S'
                bar = text[:-1] + barUnit
                break

        self._dataViewer.plotIntraDayCandleStick(code, [0, date, 0], bar)

    def _dealsDistAct(self):
        code, date = self.getRightClickCodeDate()
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
        code, date = self.getRightClickCodeDate()
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

    def _dealDetailsAct(self):
        code, date = self.getRightClickCodeDate()
        if code is None: return

        window = DyStockDealDetailsMainWindow(self._dataViewer, self)
        window.set(code, date)

        window.show()

    def _stockInfoAct(self):
        code, name = self.getRightClickCodeName()
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

        self._windows.append(browser)

    def _newIndustryCompareWindow(self, code, name, baseDate, dfs):
        window = DyStockIndustryCompareWindow(self._eventEngine, DyStockTableWidget, code, name, baseDate)

        window.addCategorys(dfs)

        window.setWindowTitle('行业对比[{0}]-基准日期[{1}]'.format(name, baseDate))
        window.showMaximized()

        self._windows.append(window)

    def _stockTableIndustryCompareActAckSignalEmitWrapper(self, event):
        self.stockTableIndustryCompareActAckSignal.emit(event)

    def _stockTableIndustryCompareActAckHandler(self, event):
        if self is not event.data['self']:
            return

        code, name, baseDate, categoryDfs = event.data['args']
        if not categoryDfs:
            return

        self._newIndustryCompareWindow(code, name, baseDate, categoryDfs)

        self._curActionOngoing = False

    def _industryCompareAct(self):
        def _func(self, code, name, baseDate, forwardNTDays, industry2, industry3):
            categoryDfs = self._getIndustryCompare(code, baseDate, forwardNTDays, industry2, industry3)

            self._actAck(DyEventType.stockTableIndustryCompareActAck, code, name, baseDate, categoryDfs)

        code, date = self.getRightClickCodeDate()
        if code is None: return

        code, name = self.getRightClickCodeName()

        data = {}
        if not DyStockIndustryCompareDlg(name, date, data).exec_():
            return

        self._curActionOngoing = True
        t = threading.Thread(target=_func, args=(self, code, name, date, data['forwardNTDays'], data['industry2'], data['industry3']))
        t.start()

    def _hsarsAct(self):
        code, date = self.getRightClickCodeDate()
        if code is None: return

        self._dataViewer.plotHSARs(code, [-DyStockCommon.dayKChartPeriodNbr, date, DyStockCommon.dayKChartPeriodNbr])

    def _swingAct(self):
        code, date = self.getRightClickCodeDate()
        if code is None: return

        self._dataViewer.plotSwingChart(code, [-DyStockCommon.dayKChartPeriodNbr, date, DyStockCommon.dayKChartPeriodNbr])

    def _trendChannelAct(self):
        code, date = self.getRightClickCodeDate()
        if code is None: return

        self._dataViewer.plotTrendChannelChart(code, [-DyStockCommon.dayKChartPeriodNbr, date, DyStockCommon.dayKChartPeriodNbr])

    def _volatilityDistAct(self):
        code, date = self.getRightClickCodeDate()
        if code is None: return

        code, name = self.getRightClickCodeName()

        data = {}
        if not DySingleEditDlg(data, '波动分布[{0}]'.format(name), '基准日期[{0}]向前N日(不包含基准日期)'.format(date), 90).exec_():
            return

        self._dataViewer.plotVolatilityDist(code, date, data['data'])

    def _atrExtremeAct(self):
        code, date = self.getRightClickCodeDate()
        if code is None: return

        self._dataViewer.plotAtrExtreme(code, [-DyStockCommon.dayKChartPeriodNbr, date, DyStockCommon.dayKChartPeriodNbr])

    def _volatilityAct(self, item):
        code, date = self.getRightClickCodeDate()
        if code is None:
            return

        data = {}
        if DySingleEditDlg(data, '波动率*√量比(%)', '均值周期', default=20).exec_():
            volatilityVolumePeriod = int(data['data'])

            self._dataViewer.plotVolatilityChart(code, [-DyStockCommon.dayKChartPeriodNbr, date, DyStockCommon.dayKChartPeriodNbr], volatilityVolumePeriod)

    def _itemDoubleClicked(self, item):
        code, baseDate = self.getCodeDate(item)
        if code is None or baseDate is None:
            return

        self._dataViewer.plotCandleStick(code, [-DyStockCommon.dayKChartPeriodNbr, baseDate, DyStockCommon.dayKChartPeriodNbr])

    def _export2Jqka(self, file, stocks):
        """
            @file: 要保存的绝对路径文件名
        """
        if not stocks: return

        now = datetime.now().strftime("%Y_%m_%d %H-%M-%S")

        f = open(file, 'wb')

        nbr = struct.pack('<H', len(stocks))
        f.write(nbr)

        for stock in stocks:
            prefix = bytearray.fromhex('0721')
            f.write(prefix)

            code = stock[:-3]
            code = code.encode('ascii')
            f.write(code)

        f.close()

    #---------------------------------------------- Header Actions ----------------------------------------------
    def _limitUpRatioAct(self):
        colData = self.getColumnsData([self._rightClickHeaderItem.text()])

        limitUpNbr, nonLimitUpNbr = 0, 0
        for row in colData:
            if row is None:
                continue

            value = row[0]

            try:
                value = float(value)
            except Exception:
                continue

            if value >= DyStockCommon.limitUpPct:
                limitUpNbr += 1
            else:
                nonLimitUpNbr += 1

        totalNbr = limitUpNbr + nonLimitUpNbr

        table = DyTableWidget(readOnly=True, index=False)
        table.setColNames(['涨停', '非涨停', '涨停占比(%)'])
        table.appendRow([limitUpNbr, nonLimitUpNbr, limitUpNbr/totalNbr*100])

        table.setWindowTitle('涨停比')
        table.resize(QApplication.desktop().size().width()//2, QApplication.desktop().size().height()//3)
        table.show()

        self._windows.append(table)

    def _upDownRatioAct(self):
        colData = self.getColumnsData([self._rightClickHeaderItem.text()])

        upNbr, downNbr, noChangeNbr = 0, 0, 0
        for row in colData:
            if row is None:
                continue
            value = row[0]

            try:
                value = float(value)
            except Exception:
                continue

            if value > 0:
                upNbr += 1
            elif value < 0:
                downNbr += 1
            else:
                noChangeNbr += 1

        totalNbr = upNbr + downNbr + noChangeNbr

        table = DyTableWidget(readOnly=True, index=False)
        table.setColNames(['涨', '跌', '平', '上涨占比(%)', '下跌占比(%)', '平占比(%)'])
        table.appendRow([upNbr, downNbr, noChangeNbr, upNbr/totalNbr*100, downNbr/totalNbr*100, noChangeNbr/totalNbr*100])

        table.setWindowTitle('涨跌比')
        table.resize(QApplication.desktop().size().width()//2, QApplication.desktop().size().height()//3)
        table.show()

        self._windows.append(table)

    def _actAck(self, eventType, *args):
        event = DyEvent(eventType)
        event.data['self'] = self
        event.data['args'] = args

        self._eventEngine.put(event)

    def _stockTableAddColumnsActAckSignalEmitWrapper(self, event):
        self.stockTableAddColumnsActAckSignal.emit(event)

    def _addIncreaseColumnsAct(self):
        def _func(self, dateCodeList, data):
            dateCodeIncreaseList = DyStockDataAssembler.getStockIndexIncrease(self._daysEngine, dateCodeList, data['days'], data['backward'], DyProgress(self._errorProgressInfo))
            if dateCodeIncreaseList is None:
                self._actAck(DyEventType.stockTableAddColumnsActAck, None, None)
                return

            colNames, colData = DyStockDataAssembler.flatStockIndexIncrease(dateCodeIncreaseList, data['days'], data['backward'])

            self._actAck(DyEventType.stockTableAddColumnsActAck, colNames, colData)

        data = {}
        if not DyStockTableAddColumnsDlg(data, '涨幅').exec_():
            return

        dateCodeList = self.getDateCodeList()
        if not dateCodeList:
            return

        self._curActionOngoing = True
        t = threading.Thread(target=_func, args=(self, dateCodeList, data))
        t.start()

    def _addMaxMinIncreaseColumnsAct(self):
        def _func(self, dateCodeList, data):
            dateCodeIncreaseList = DyStockDataAssembler.getStockIndexMaxMinIncrease(self._daysEngine, dateCodeList, data['days'], data['backward'], DyProgress(self._errorProgressInfo))
            if dateCodeIncreaseList is None:
                self._actAck(DyEventType.stockTableAddColumnsActAck, None, None)
                return

            colNames, colData = DyStockDataAssembler.flatStockIndexMaxMinIncrease(dateCodeIncreaseList, data['days'], data['backward'])

            self._actAck(DyEventType.stockTableAddColumnsActAck, colNames, colData)

        data = {}
        if not DyStockTableAddColumnsDlg(data, '最大最小涨幅').exec_():
            return

        dateCodeList = self.getDateCodeList()
        if not dateCodeList:
            return

        self._curActionOngoing = True
        t = threading.Thread(target=_func, args=(self, dateCodeList, data))
        t.start()

    def _addMaxAmplitudeColumnsAct(self):
        def _func(self, dateCodeList, data):
            dateCodeIncreaseList = DyStockDataAssembler.getStockIndexMaxAmplitude(self._daysEngine, dateCodeList, data['days'], data['backward'], DyProgress(self._errorProgressInfo))
            if dateCodeIncreaseList is None:
                self._actAck(DyEventType.stockTableAddColumnsActAck, None, None)
                return

            colNames, colData = DyStockDataAssembler.flatStockIndexMaxAmplitude(dateCodeIncreaseList, data['days'], data['backward'])

            self._actAck(DyEventType.stockTableAddColumnsActAck, colNames, colData)

        data = {}
        if not DyStockTableAddColumnsDlg(data, '振幅').exec_():
            return

        dateCodeList = self.getDateCodeList()
        if not dateCodeList:
            return

        self._curActionOngoing = True
        t = threading.Thread(target=_func, args=(self, dateCodeList, data))
        t.start()

    def _addOpenGapColumnsAct(self):
        """
            添加开盘缺口列，0代表是当日。若T日没有缺口，则T日是None。正值是向上缺口，负值是向下缺口。
        """
        def _func(self, dateCodeList, data):
            rows = DyStockDataAssembler.getStockOpenGap(self._daysEngine, dateCodeList, data['days'], data['backward'], DyProgress(self._errorProgressInfo))
            if rows is None:
                self._actAck(DyEventType.stockTableAddColumnsActAck, None, None)
                return

            colNames, colData = DyStockDataAssembler.flatStockOpenGap(rows, data['days'], data['backward'])

            self._actAck(DyEventType.stockTableAddColumnsActAck, colNames, colData)

        data = {'days': [0, 1]}
        if not DyStockTableAddColumnsDlg(data, '开盘缺口(0只能出现在向前)', backward=False).exec_():
            return

        dateCodeList = self.getDateCodeList()
        if not dateCodeList:
            return

        self._curActionOngoing = True
        t = threading.Thread(target=_func, args=(self, dateCodeList, data))
        t.start()

    def _stockTableAddColumnsActAckHandler(self, event):
        if self is not event.data['self']:
            return

        colNames, colData = event.data['args']
        if colNames is None:
            return

        self.fastAppendColumns(colNames, colData)

        self._curActionOngoing = False

    def _addErColumnsAct(self):
        def _func(self, dateCodeList, data):
            dateCodeErList = DyStockDataAssembler.getStockIndexEr(self._daysEngine, dateCodeList, data['days'], data['backward'], DyProgress(self._errorProgressInfo))
            if dateCodeErList is None:
                self._actAck(DyEventType.stockTableAddColumnsActAck, None, None)
                return

            colNames, colData = DyStockDataAssembler.flatStockIndexEr(dateCodeErList, data['days'], data['backward'])

            self._actAck(DyEventType.stockTableAddColumnsActAck, colNames, colData)

        data = {'days': [20, 30, 40, 50, 60]}
        if not DyStockTableAddColumnsDlg(data, 'Efficiency Ratio', backward=False).exec_():
            return

        dateCodeList = self.getDateCodeList()
        if not dateCodeList:
            return

        self._curActionOngoing = True
        t = threading.Thread(target=_func, args=(self, dateCodeList, data))
        t.start()

    def _addVolatilityColumnsAct(self):
        def _func(self, dateCodeList, data):
            dateCodeVolatilityList = DyStockDataAssembler.getStockIndexVolatility(self._daysEngine, dateCodeList, data['days'], data['backward'], DyProgress(self._errorProgressInfo))
            if dateCodeVolatilityList is None:
                self._actAck(DyEventType.stockTableAddColumnsActAck, None, None)
                return

            colNames, colData = DyStockDataAssembler.flatStockIndexVolatility(dateCodeVolatilityList, data['days'], data['backward'])

            self._actAck(DyEventType.stockTableAddColumnsActAck, colNames, colData)

        data = {'days': [20, 30, 40, 50, 60]}
        if not DyStockTableAddColumnsDlg(data, '波动率', backward=False).exec_():
            return

        dateCodeList = self.getDateCodeList()
        if not dateCodeList:
            return

        self._curActionOngoing = True
        t = threading.Thread(target=_func, args=(self, dateCodeList, data))
        t.start()

    def _addMinuteIncreaseColumnsAct(self):
        def _func(self, dateCodeList, data):
            retData = DyStockDataAssembler.getStockEtfMinuteIncrease(self._dataEngine, dateCodeList, data['data'], DyProgress(self._errorProgressInfo))
            if retData is None:
                self._actAck(DyEventType.stockTableAddColumnsActAck, None, None)
                return

            colNames, colData = DyStockDataAssembler.flatStockEtfMinuteIncrease(retData, data['data'])

            self._actAck(DyEventType.stockTableAddColumnsActAck, colNames, colData)

        data = {'data': '5,10,15'}
        if not DySingleEditDlg(data, '分钟涨幅(%)', '基准日期开盘几分钟涨幅(%)').exec_():
            return
        
        if isinstance(data['data'], str):
            data['data'] = [int(x) for x in data['data'].split(',')]
        else:
            data['data'] = [data['data']]

        dateCodeList = self.getDateCodeList()
        if not dateCodeList:
            return

        self._curActionOngoing = True
        t = threading.Thread(target=_func, args=(self, dateCodeList, data))
        t.start()

    def _addOpenIncreaseColumnsAct(self):
        def _func(self, dateCodeList):
            retData = DyStockDataAssembler.getStockIndexOpenIncrease(self._daysEngine, dateCodeList, DyProgress(self._errorProgressInfo))
            if retData is None:
                self._actAck(DyEventType.stockTableAddColumnsActAck, None, None)
                return

            colNames, colData = DyStockDataAssembler.flatStockIndexOpenIncrease(retData)

            self._actAck(DyEventType.stockTableAddColumnsActAck, colNames, colData)

        dateCodeList = self.getDateCodeList()
        if not dateCodeList:
            return

        self._curActionOngoing = True
        t = threading.Thread(target=_func, args=(self, dateCodeList))
        t.start()

    def _addDayReturnIndexCorrColumnsAct(self):
        def _func(self, dateCodeList, data):
            colNames, colData = DyStockDataAssembler.getStockIndexDayReturnCorr(self._daysEngine, dateCodeList, data['days'], data['backward'], DyProgress(self._errorProgressInfo))

            self._actAck(DyEventType.stockTableAddColumnsActAck, colNames, colData)

        data = {'days': [20, 30, 40, 50, 60]}
        if not DyStockTableAddColumnsDlg(data, '股票大盘日收益率相关系数', backward=False).exec_():
            return

        dateCodeList = self.getDateCodeList()
        if not dateCodeList:
            return

        self._curActionOngoing = True
        t = threading.Thread(target=_func, args=(self, dateCodeList, data))
        t.start()

    def _newWindowAct(self):
        self._newWindow()

    def _newWindow(self, rows=None):
        """
            子类可改写
        """
        window = DyStockTableWidget(self._eventEngine,
                                    name=self._name,
                                    baseDate=self._baseDate,
                                    readOnly=True,
                                    index=False,
                                    autoScroll=False,
                                    floatRound=2
                                    )

        if rows is None:
            rows = self.getAll()

        window.appendStocks(rows, self.getColNames(), self.getAutoForegroundColName())

        window.setWindowTitle(window.name)
        window.showMaximized()

        self._windows.append(window)

    def _addStockInfoColumnsAct(self):
        def _func(self, codePrices, indicators):
            progress = DyProgress(self._errorProgressInfo)
            progress.init(len(codePrices))

            # get data from Spider
            names = []
            data = []
            first = True
            for code, price in codePrices:
                rowData = []

                # 公司资料
                colNames, colData = DyStockDataSpider.getCompanyInfo(code, indicators)
                if first:
                    names += colNames

                rowData += colData

                #　股本
                if '实际流通股(亿)' in indicators:
                    freeShares, type = DyStockDataSpider.getLatestRealFreeShares(code)
                    if first:
                        names += ['实际流通股(亿)', '股份类型']

                    rowData += [freeShares, type]

                if '实际流通市值(亿元)' in indicators:
                    if '实际流通股(亿)' not in indicators:
                        freeShares, type = DyStockDataSpider.getLatestRealFreeShares(code)

                    if first:
                        names += ['实际流通市值(亿元)']

                    rowData += [freeShares*price]

                if '机构占比流通(%)' in indicators:
                    fundPosRatio, fundNbr = DyStockDataSpider.getLatestFundPositionsRatio(code)

                    if first:
                        names += ['机构占比流通(%)']

                    rowData += [fundPosRatio]
                
                # post process
                if rowData:
                    data.append(rowData)

                first = False
                progress.update()

            self._actAck(DyEventType.stockTableAddColumnsActAck, names, data)

        codePrices = self.getCodePriceList()
        if not codePrices: return

        data = {}
        if not DyStockInfoDlg(data).exec_():
            return

        indicators = data['indicators']

        self._curActionOngoing = True
        t = threading.Thread(target=_func, args=(self, codePrices, indicators))
        t.start()

    def _addColumnOperateColumnsAct(self):
        data = {}
        if DyStockTableColumnOperateDlg(data, self.getColNames()).exec_():
            self.addColumnOperateColumns(data['exp'])

    def _filterAct(self):
        data = {}
        if DyStockTableFilterDlg(data, self.getColNames()).exec_():
            self._filter(data['filter'], data['newWindow'], data['highlight'])

    def _filter(self, filter, newWindow, highlight):
        filterRows = self.filter(filter, highlight)

        if newWindow:
            self._newWindow(rows=filterRows)

    def _export2JqkaAct(self):
        data = {}
        if not DyStockTableSelectDlg(data, '{0}导出到同花顺'.format(self.getUniqueName())).exec_():
            return

        defaultFileName = '{0}.sel' if data['all'] else '{0}_高亮.sel'
        defaultFileName = defaultFileName.format(self.getUniqueName())

        defaultDir = DyCommon.createPath('Stock/User/Save/Strategy/同花顺')
        fileName, _ = QFileDialog.getSaveFileName(self, '导出到同花顺', os.path.join(defaultDir, defaultFileName), "同花顺files (*.sel);;all files(*.*)")
        if fileName:
            self.export2Jqka(fileName)

    def _saveAsAct(self):
        data = {}
        if not DyStockTableSelectDlg(data, '{0}保存'.format(self.getUniqueName())).exec_():
            return

        defaultFileName = '{0}.json' if data['all'] else '{0}_高亮.json'
        defaultFileName = defaultFileName.format(self.getUniqueName())

        defaultDir = DyCommon.createPath('Stock/User/Save/Strategy')
        fileName, _ = QFileDialog.getSaveFileName(self, '保存股票表', os.path.join(defaultDir, defaultFileName), "JSON files (*.json);;all files(*.*)")
        if fileName:
            self._saveAs(fileName, data['all'])

    def _saveAs(self, fileName, all=True):
        """
            重载@getCustomSaveData定义自己的保存格式
            共同数据:
            {
            'autoForegroundColName': autoForegroundColName,
            'data': {'colNames': colNames, 'rows': rows}
            }
        """
        rows = self.getAll() if all else self.getHighlights()
        colNames, autoForegroundColName = self.getColNames(), self.getAutoForegroundColName()
        
        # 子类可以重载@getCustomSaveData
        customData = self.getCustomSaveData()

        data = {'name': self._name,
                'autoForegroundColName': autoForegroundColName,
                'baseDate': self._baseDate,
                'data': {'colNames': colNames, 'rows': rows}
               }

        data.update(**customData)

        with open(fileName, 'w') as f:
            f.write(json.dumps(data, indent=4))

    #-------------------------------------- 股票行业比较 --------------------------------------
    # !!!原则上应该放到@DyStockDataSpider，但改动比较大，暂时先这么实现
    def _toFloat(self, value):
        try:
            value = float(value)
        except:
            try:
                value = float(value[:-1]) # e.g value like '15.06%'
            except:
                value = 0

        return value

    def _getCompanyFinanceOutline1(self, code, indicators):
        """
            从财务报表获取指定的指标
            @indicators: []
        """
        mainLink = 'http://basic.10jqka.com.cn/{0}/flash/main.txt'.format(code[:-3])
        r = requests.get(mainLink)

        table = dict(json.loads(r.text))

        values = {}
        for indicator in indicators:
            # get @indicator position
            pos = None
            for i, e in enumerate(table['title']):
                if isinstance(e, list):
                    if e[0] == indicator:
                        pos = i
                        break

            # 指标最近的值
            value = self._toFloat(table['report'][pos][0])
            values[indicator] = value

        return values

    def _getCompanyFinanceOutline(self, code):
        """
            从同花顺'最新动态'网页获取财务概要信息
        """
        def getIndex(x):
            for i, name in enumerate(colNames):
                if x in name:
                    return i

            return None

        colNames = ['市盈率(动态)', '市净率', '每股收益', '每股现金流', '每股净资产', '净资产收益率(%)', '营业收入YoY(%)', '净利润YoY(%)', '流通A股(亿股)', '总股本(亿股)']
        colData = [None]*len(colNames)

        # 缺失的数据从财务报表里获取
        latest2FinanceMap = {'营业收入YoY(%)': '营业总收入同比增长率', '净利润YoY(%)': '净利润同比增长率'}
        finance2LatestMap = {value: key for key, value in latest2FinanceMap.items()}

        try:
            r = requests.get('http://basic.10jqka.com.cn/16/{0}/'.format(code[:-3]))

            soup = BeautifulSoup(r.text, 'lxml')

            table = soup.find('table', class_="m_table m_table_db mt10")
            tds = table.find_all('td')

            for td in tds:
                spans = td.find_all('span')

                indicator = str(spans[0].string)[:-1]
                index = getIndex(indicator)
                if index is None: continue

                value = None
                if '%' in colNames[index]:
                    for span in spans[1:]:
                        if '%' in str(span.string):
                            value = str(span.string)
                            break
                else:
                    value = str(spans[1].string)

                if value is not None:
                    positive = True if '下降' not in value else False

                    value = re.findall(r"-?\d+\.?\d*", value)
                    if value:
                        value = float(value[0]) if positive else -float(value[0])
                        colData[index] = value

            # 处理缺失数据
            indicators = []
            for key, value in latest2FinanceMap.items():
                index = colNames.index(key)
                if colData[index] is None:
                    indicators.append(value)

            # 从财务报表获取缺失数据的最新值
            if indicators:
                data = self._getCompanyFinanceOutline1(code, indicators)
                for key, value in data.items():
                    index = colNames.index(finance2LatestMap[key])
                    colData[index] = value

        except Exception as ex:
            pass

        return colNames, colData

    def _getIndustryCompareTable(self, div, id):
        colNames = ['销售毛利率']
        colNamesForReturn = ['销售毛利率(%)']
        colPoses = {}
        colData = {}

        try:
            table = div.find('table', class_='m_table m_hl', id=id)

            # 获取每个指标的位置
            tag = table.find('thead')
            ths = tag.find_all('th')

            for i, th in enumerate(ths):
                indicator = str(th.contents[0])
                if indicator in colNames:
                    colPoses[indicator] = i

            assert(len(colNames) == len(colPoses))

            # 获取指定date的指标值
            tag = table.find('tbody')
            trs = tag.find_all('tr')

            for tr in trs:
                tds = tr.find_all('td')
                code = DyStockCommon.getDyStockCode(str(tds[0].string))
                name = str(tds[1].string)

                data = [code, name]
                for indicator in colNames:
                    data.append(self._toFloat(tds[colPoses[indicator]].string))

                colData[code] = data

        except Exception as ex:
            pass

        return ['代码', '名称'] + colNamesForReturn, colData

    def _getIndustryComparePartly(self, code, industry2, industry3):
        totalData = {}
        tableColNames = []

        try:
            r = requests.get('http://basic.10jqka.com.cn/16/{0}/field.html'.format(code[:-3]))

            soup = BeautifulSoup(r.text, 'lxml')

            divIds = {"hy3_div": industry3, "hy2_div": industry2}
            pTexts = {"hy3_div": '三级行业分类：', "hy2_div": '二级行业分类：'}
            tableIds = {"hy3_div": ["hy3_table_1", "hy3_table_2"], "hy2_div": ["hy2_table_1", "hy2_table_2"]}
        
            for divId, bool in divIds.items():
                if not bool: continue

                div = soup.find('div', id=divId)
                if div is None: continue

                # 行业分类
                category = div.parent.find(text=pTexts[divId])
                category = category.parent
                categoryHead = str(category.contents[0])
                span = category.find('span')
                categoryBody = str(span.contents[0][:-3])

                category = categoryHead + categoryBody

                # table
                tableColDataTotal = {}
                for tableId in tableIds[divId]:
                    tableColNames, tableColData = self._getIndustryCompareTable(div, tableId)

                    for code in tableColData:
                        if code not in tableColDataTotal:
                            tableColDataTotal[code] = tableColData[code]

                totalData[category] = tableColDataTotal
        except Exception as ex:
            pass

        return tableColNames, totalData

    def _calcIndustryCompareScore(self, categoryDfs):
        for category, df in categoryDfs.items():
            # rank for each indicator, think rank as score that the high score is the better is
            seriesList = []

            series = df['市盈率(动态)'].rank(ascending=False)
            seriesList.append(series)

            series = df['市净率'].rank(ascending=False)
            seriesList.append(series)

            series = df['净资产收益率(%)'].rank()
            seriesList.append(series)

            series = df['每股现金流'].rank()
            seriesList.append(series)

            series = df['营业收入YoY(%)'].rank()
            seriesList.append(series)

            series = df['净利润YoY(%)'].rank()
            seriesList.append(series)

            series = df['销售毛利率(%)'].rank()
            seriesList.append(series)

            rankDf = pd.concat(seriesList, axis=1)

            # total rank
            series = rankDf.sum(axis=1)*100/(len(seriesList) * rankDf.shape[0])
            series.name = '得分'

            df = pd.concat([df, series], axis=1)
            columns = list(df.columns)
            df = df.reindex(columns=columns[:2] + columns[-1:] + columns[2:-1])

            categoryDfs[category] = df

    def _getIndustryCompare(self, code, baseDate, forwardNTDays, industry2, industry3):
        # 获取同行业的数据
        name, data = self._getIndustryComparePartly(code, industry2, industry3)

        # 合并代码表
        codes = set()
        for _, data_ in data.items():
            codes.update(list(data_.keys()))
        codes = list(codes)

        # 获取股票的基本财务信息
        progress = DyProgress(self._errorProgressInfo)
        progress.init(len(codes))

        financeOutline = {}
        for code in codes:
            outlineNames, outlineData = self._getCompanyFinanceOutline(code)
            financeOutline[code] = outlineData

            progress.update()

        financeOutlineDf = pd.DataFrame(financeOutline, index=outlineNames).T

        # 根据行业分级合并数据
        categoryDfs = {}
        for category, data_ in data.items():
            df = pd.DataFrame(data_, index=name).T
            df = pd.concat([df, financeOutlineDf], axis=1)
            df = df[df[name[0]].notnull()]

            df = df.reindex(columns=name[:2] + outlineNames[:-2] + name[2:] + outlineNames[-2:])

            categoryDfs[category] = df

        # 计算得分
        self._calcIndustryCompareScore(categoryDfs)

        # 获取前N日涨幅
        daysEngine = self._daysEngine
        if not daysEngine.load([baseDate, -forwardNTDays], codes=codes):
            return categoryDfs

        # 计算前N日涨幅
        autoForegroundColName = '前{0}日涨幅(%)'.format(forwardNTDays)
        pcts = {}
        for code in codes:
            df = daysEngine.getDataFrame(code)
            if df is not None and not df.empty:
                pct = (df.ix[-1, 'close'] - df.ix[0, 'close'])*100/df.ix[0, 'close']
                pcts[code] = [df.ix[-1, 'close'], pct]
            
        # 获取指定周期内停牌股票的最新收盘价
        for code in codes:
            if code not in pcts:
                # 同花顺可能会含有终止上市的股票或者没有上市的股票
                if daysEngine.loadCode(code, [baseDate, 0]):
                    df = daysEngine.getDataFrame(code)
                    pcts[code] = [df.ix[-1, 'close'], None]

        pctDf = pd.DataFrame(pcts, index=['当日价格', autoForegroundColName]).T

        # 根据行业分级合并数据
        for category, df in categoryDfs.items():
            df = pd.concat([df, pctDf], axis=1)
            df = df[df.ix[:,0].notnull()]

            df.sort_values('得分', axis=0, ascending=False, inplace=True)

            # 添加市值
            df['流通市值(亿元)'] = df['流通A股(亿股)'] * df['当日价格']
            df['总市值(亿元)'] = df['总股本(亿股)'] * df['当日价格']

            columns = list(df.columns)
            df = df.reindex(columns=columns[:-4] + columns[-2:] + columns[-4:-2])

            categoryDfs[category] = df
         
        return categoryDfs

    #---------------------------------------------- interfaces ----------------------------------------------
    def export2Jqka(self, fileName):
        self._export2Jqka(fileName, self.getCodeList())

    def setBaseDate(self, baseDate):
        self._baseDate = baseDate

    def appendStocks(self, rows, header=None, autoForegroundColName=None, new=False):
        if header is not None:
            self.setColNames(header)

        self.fastAppendRows(rows, autoForegroundColName=autoForegroundColName, new=new)

    #---------------------------------------------- 由子类根据自己的Table格式改写 ----------------------------------------------
    def getDateCodeList(self):
        if self._baseDate is None:
            raise AttributeError

        codes = self.getColumnsData(['代码'])

        return [[self._baseDate, code[0]] for code in codes]

    def getCodeList(self):
        codes = self.getColumnsData(['代码'])

        return [code[0] for code in codes]

    def getCodePriceList(self):
        return self.getColumnsData(['代码', '当日价格'])

    def getRightClickCodeDate(self):
        item = self.itemAt(self._rightClickPoint)
        if item is None:
            return None, None

        code = self[item.row(), '代码']

        return code, self._baseDate

    def getRightClickCodeName(self):
        item = self.itemAt(self._rightClickPoint)
        if item is None:
            return None, None

        code = self[item.row(), '代码']
        name = self[item.row(), '名称']

        return code, name

    def getCodeDate(self, item):
        row = self.row(item)
        code = self[row, '代码']

        return code, self._baseDate

    def getUniqueName(self):
        """
            Get unique name of this table. Usually it's combined with name + baseDate
        """
        return '{0}_{1}'.format(self._name, self._baseDate)

    def getCustomSaveData(self):
        """
            获取每个类的定制保存数据
            @return: dict
        """
        return {}

    def customizeHeaderContextMenu(self, headerItem):
        """
            子类改写
        """
        self._upDownRatioAction.setEnabled('涨幅' in headerItem.text())
        self._limitUpRatioAction.setEnabled('涨幅' in headerItem.text())

    #---------------------------------------------- 属性 ----------------------------------------------
    @property
    def dataViewer(self):
        return self._dataViewer

    @property
    def name(self):
        return self._name

    @property
    def eventEngine(self):
        return self._eventEngine

    @property
    def baseDate(self):
        return self._baseDate

