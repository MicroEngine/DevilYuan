from datetime import *

from EventEngine.DyEvent import *
from ..DyStockTradeCommon import *
from ..Strategy.DyStockCtaBase import *
from ...Common.DyStockCommon import *
from .DyStockSinaQuotation import *


class DyStockMarketEngine(object):
    """
        Real time monitor stock market
        成交额数据问题：
            - 创小板指数成交金额错误
            - 深证成指个股累加成交金额错误
    """

    # 深市是3秒一次更新，沪市是5秒一次更新
    # 由于可能会交错更新，所以只要哪个有更新，则推入所有Ticks
    shIndexSinaCode = 'sh000001'
    szIndexSinaCode = 'sz399001'

    openStableCount = 90 # 集合竞价后的1分半时的Ticks作为稳定的开盘Ticks


    def __init__(self, eventEngine, info):
        self._eventEngine = eventEngine
        self._info = info

        self._sinaQuotation = DyStockSinaQuotation(self._eventEngine, self._info)
        self._curDay = None

        self._registerEvent()

        self._curInit()

    def _curInit(self):
        # 防止一键挂机后，重复初始化
        curDay = datetime.now().strftime("%Y-%m-%d")
        if curDay == self._curDay:
            return False

        self._curDay = curDay

        # init sina
        self._sinaQuotation.init()
        self._sinaQuotation.addIndexes(list(DyStockCommon.indexes) + [DyStockCommon.cybzIndex, DyStockCommon.zxbzIndex])

        self._monitoredStocks = [] # exclude indexes
        self._latestShIndexSinaTick = None # 最新上证指数Sina Tick
        self._latestSzIndexSinaTick = None # 最新深证成指Sina Tick

        # 交易日9:25:00 ~ 9:30:00之间是比较特别的时间
		# 市场引擎只推送集合竞价后的一个稳定的Ticks
		# 原则上这部分应该由CTA引擎负责，但市场引擎Ticks推送优化后，CTA引擎没法知道集合竞价后的哪一个Ticks是稳定的。
		# 所以引入开盘计数器，以推送一个稳定的Ticks。
        self._openCount = 0

        return True

    def _stockMarketMonitorHandler(self, event):
        """ 添加要监控的股票, 不含指数
            @event.data: [code]
        """
        newCodes = []
        for code in event.data:
            if code not in self._monitoredStocks and code not in DyStockCommon.indexes:
                self._monitoredStocks.append(code)
                newCodes.append(code)

        if newCodes:
            self._sinaQuotation.add(newCodes)

    def _isNeedPut(self, stockSinaTickData):
        """
            check if need to put ticks into event egnine
        """
        if not DyStockTradeCommon.enableSinaTickOptimization:
            return True

        # 深证成指
        # 由于深市更新频率高，所以先判断深市
        szIndexSinaTick = stockSinaTickData.get(self.szIndexSinaCode)

        # check if time of SZ index tick changed
        if szIndexSinaTick is not None:
            if self._latestSzIndexSinaTick is None:
                self._latestSzIndexSinaTick = szIndexSinaTick
                return True

            else:
                # 处理集合竞价后和开盘之间的Ticks，只推送这段时间的一个稳定的Ticks
                if '09:25:00' <= szIndexSinaTick['time'] < '09:30:00':
                    self._openCount += 1
                    if self._openCount != self.openStableCount:
                        return False

                if self._latestSzIndexSinaTick['time'] != szIndexSinaTick['time']:
                    self._latestSzIndexSinaTick = szIndexSinaTick
                    return True

        # 上证指数
        shIndexSinaTick = stockSinaTickData.get(self.shIndexSinaCode)

        # check if time of SH index tick changed
        if shIndexSinaTick is not None:
            if self._latestShIndexSinaTick is None:
                self._latestShIndexSinaTick = shIndexSinaTick
                return True

            else:
                if self._latestShIndexSinaTick['time'] != shIndexSinaTick['time']:
                    self._latestShIndexSinaTick = shIndexSinaTick
                    return True

        return False

    #@DyTime.instanceTimeitWrapper
    def _timerHandler(self, event):
        try:
            if DyStockTradeCommon.enableTimerLog:
                print('@DyStockMarketEngine._timerHandler')

            # get ticks from Sina
            try:
                stockSinaTickData = self._sinaQuotation.get()
            except Exception as ex:
                self._info.print("self._sinaQuotation.get()异常: {}".format(repr(ex)), DyLogData.warning)
                return

            if DyStockTradeCommon.enableTimerLog:
                print('Get {} codes from Sina'.format(len(stockSinaTickData)))
                if self.szIndexSinaCode in stockSinaTickData:
                    print(stockSinaTickData[self.szIndexSinaCode])

            # If need to put changed ticks into Engine
            if self._isNeedPut(stockSinaTickData):
                # convert
                ctaTickDatas = self._convert(stockSinaTickData)

                self._putTickEvent(ctaTickDatas)

        except Exception as ex:
            self._info.print("{}._timerHandler异常: {}".format(self.__class__.__name__, repr(ex)), DyLogData.warning)

    #@DyTime.instanceTimeitWrapper
    def _convert(self, stockSinaTickData):
        """
            convert Sina stock tick data to DyStockCtaTickData
        """
        ctaTickDatas = {} # {code: DyStockCtaTickData}
        for code, data in stockSinaTickData.items():
            if data['now'] > 0: # 去除停牌股票。对于开盘，有些股票可能没有任何成交，但有当前价格。
                ctaTickData = DyStockCtaTickData(code, data)
                ctaTickDatas[ctaTickData.code] = ctaTickData

        return ctaTickDatas

    def _registerEvent(self):
        self._eventEngine.register(DyEventType.stockMarketMonitor, self._stockMarketMonitorHandler, DyStockTradeEventHandType.stockSinaQuotation)
        self._eventEngine.registerTimer(self._timerHandler, DyStockTradeEventHandType.stockSinaQuotation, 1)

        self._eventEngine.register(DyEventType.beginStockTradeDay, self._beginStockTradeDayHandler, DyStockTradeEventHandType.stockSinaQuotation)
        self._eventEngine.register(DyEventType.endStockTradeDay, self._endStockTradeDayHandler, DyStockTradeEventHandType.stockSinaQuotation)

    def _putTickEvent(self, ctaTickDatas):
        if not ctaTickDatas:
            return

        event = DyEvent(DyEventType.stockMarketTicks)
        event.data = ctaTickDatas

        self._eventEngine.put(event)

    def _beginStockTradeDayHandler(self, event):
        if self._curInit():
            self._info.print('股票行情引擎: 开始交易日[{}]'.format(self._curDay), DyLogData.ind2)

            self._eventEngine.registerTimer(self._timerHandler, DyStockTradeEventHandType.stockSinaQuotation, 1)

    def _endStockTradeDayHandler(self, event):
        self._info.print('股票行情引擎: 结束交易日[{}]'.format(self._curDay), DyLogData.ind2)

        self._curDay = None

        self._eventEngine.unregisterTimer(self._timerHandler, DyStockTradeEventHandType.stockSinaQuotation, 1)
