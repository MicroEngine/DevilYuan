"""
    本文件中包含的是CTA模块的回测引擎，回测引擎的API和CTA引擎一致，
    可以使用和实盘相同的代码进行回测。
"""
import types
import copy
from collections import OrderedDict

from DyCommon.DyCommon import *
from ....Data.Engine.DyStockDataEngine import *
from ....Trade.DyStockStrategyBase import *
from ....Trade.Strategy.DyStockCtaBase import *
from ....Trade.Strategy.DyStockCtaEngineExtra import *
from ....Trade.Market.DyStockMarketFilter import *
from ..DyStockBackTestingAccountManager import *
from ....Common.DyStockCommon import *


class DyStockBackTestingCtaEngine(object):
    """
        CTA回测引擎
        函数接口和策略引擎保持一样，从而实现同一套代码从回测到实盘。
        一天回测完，回测UI才会显示当日的交易相关的数据。
        !!!只支持单策略的回测。
    """


    def __init__(self, eventEngine, info, dataEngine, reqData):
        # unpack
        strategyCls = reqData.strategyCls
        settings = reqData.settings # 回测参数设置
        self._testCodes = reqData.codes
        self._strategyParam = reqData.param
        self._strategyParamGroupNo = reqData.paramGroupNo
        self._strategyPeriod = [reqData.tDays[0], reqData.tDays[-1]] # 回测周期
        
        self._eventEngine = eventEngine
        self._info = info
        self._dataEngine = dataEngine

        # print策略参数（类参数）
        self._printStrategyClsParams(strategyCls)

        # 初始化账户和策略实例
        self._accountManager = DyStockBackTestingAccountManager(self._eventEngine, self._info, self._dataEngine, settings)
        self._accountManager.setParamGroupNoAndPeriod(self._strategyParamGroupNo, self._strategyPeriod)

        self._strategy = strategyCls(self, self._info, DyStockStrategyState(DyStockStrategyState.backTesting), self._strategyParam)
        self._strategySavedData = None # 策略收盘后保存的数据
        self._strategyMarketFilter = DyStockMarketFilter()

        # 设置滑点
        self.setSlippage(settings['slippage'])
        self._info.print('滑点(‰): {}'.format(settings['slippage']), DyLogData.ind2)

        self._progress = DyProgress(self._info)

        # for easy access
        self._daysEngine = self._dataEngine.daysEngine
        self._ticksEngine = self._dataEngine.ticksEngine

        # error DataEngine
        # 有时策略@prepare需要独立载入大量个股数据，避免输出大量log
        errorInfo = DyErrorInfo(eventEngine)
        self._errorDataEngine = DyStockDataEngine(eventEngine, errorInfo, registerEvent=False)
        self._errorDaysEngine = self._errorDataEngine.daysEngine

        self._curInit()

    def _printStrategyClsParams(self, strategyCls):
        """
            print策略参数（类参数），不是用户通过界面配置的参数。界面配置的参数，通过界面显示。
        """
        self._info.print('回测策略[{}]，参数如下-->'.format(strategyCls.chName), DyLogData.ind1)

        for k, v in strategyCls.__dict__.items():
            if type(v) is types.FunctionType or type(v) is types.MethodType or type(v) is classmethod:
                continue

            if k[:2] == '__' and k[-2:] == '__': # python internal attributes
                continue

            if k in strategyCls.__base__.__dict__ and k != 'backTestingMode':
                continue

            self._info.print('{}: {}'.format(k, v), DyLogData.ind1)

    def _curInit(self, tDay=None):
        """ 当日初始化 """

        self._curTDay = tDay

        self._curTicks = {} # 当日监控股票的当日所有ticks, {code: {time: DyStockCtaTickData}}
        self._curLatestTicks = {} # 当日监控股票的当日最新tick, {code: DyStockCtaTickData}

        self._curBars = {} # 当日监控股票的当日所有Bars, 日内{code: {time: DyStockCtaBarData}}，日线{code: DyStockCtaBarData}

        self.__etf300Tick = None
        self.__etf500Tick = None

    def _loadPreCloseOpen(self, code):
        self._info.enable(False)

        # 为了获取前日收盘价，向前一日获取股票日线数据，前复权方式基于当日
        # !!!回测不考虑股票上市日起
        if not self._daysEngine.loadCode(code, [self._curTDay, -1], latestAdjFactorInDb=False):
            self._info.enable(True)
            return None, None

        # get previous close
        df = self._daysEngine.getDataFrame(code)
        preTDay = self._daysEngine.codeTDayOffset(code, self._curTDay, -1)
        if preTDay is None: # 股票首次上市日
            self._info.enable(True)
            return None, None 

        preClose = df.ix[preTDay, 'close']

        # 获取当日开盘价
        try:
            open = df.ix[self._curTDay, 'open']
        except:
            self._info.enable(True)
            self._info.print('{}:{}没有{}交易数据'.format(code, self._daysEngine.stockAllCodesFunds[code], self._curTDay), DyLogData.warning)
            return None, None

        self._info.enable(True)
        return preClose, open

    def _loadTicks(self, codes):
        self._info.print('开始载入{0}只监控股票Ticks数据[{1}]...'.format(len(codes), self._curTDay))
        self._progress.init(len(codes), 100)

        count = 0
        for code in codes:
            # 获取昨日收盘和当日开盘
            preClose, open = self._loadPreCloseOpen(code)
            if open is None:
                self._progress.update()
                continue

            # load ticks
            if not self._ticksEngine.loadCode(code, self._curTDay):
                # 由于新浪分笔数据有时会缺失，所以不返回错误，只打印警告
                self._info.print('{0}:{1}Ticks数据[{2}]载入失败'.format(code, self._daysEngine.stockCodes[code], self._curTDay), DyLogData.warning)
                self._progress.update()
                continue

            # to dict for fast access
            df = self._ticksEngine.getDataFrame(code)

            # 累积值，因为从新浪抓取的实时数据是累积值
            df['volume'] = df['volume'].cumsum()*100
            df['amount'] = df['amount'].cumsum()

            data = df.reset_index().values.tolist()

            # load to memory
            ticks = {}
            high, low = None, None
            for datetime, price, volume, amount, type in data:
                tick = DyStockCtaTickData()

                tick.code = code
                tick.name = self._daysEngine.stockCodesFunds[code]

                tick.date = self._curTDay
                tick.time = datetime.strftime('%H:%M:%S')
                tick.datetime = datetime

                tick.price = price
                tick.volume = volume # 累积值
                tick.amount = amount # 累积值

                # from Days data
                tick.preClose = preClose
                tick.open = open

                low = tick.price if low is None else min(low, tick.price)
                high = tick.price if high is None else max(high, tick.price)

                tick.low = low
                tick.high = high

                # set
                ticks[tick.time] = tick

            self._curTicks[code] = ticks

            count += 1
            self._progress.update()

        self._info.print('{0}只监控股票Ticks数据[{1}]载入完成'.format(count, self._curTDay))

        return True

    def _getTime(self, seconds):
        h = seconds // 3600
        m = (seconds % 3600 ) // 60
        s = (seconds % 3600 ) % 60

        return h, m, s

    def _getCtaTicks(self, h, m, s):
        """
            获取推送到策略的Ticks
        """
        time = '{0}:{1}:{2}'.format(h if h > 9 else ('0' + str(h)), m if m > 9 else ('0' + str(m)), s if s > 9 else ('0' + str(s)))

        ticks = {}
        for code in self._curTicks:
            if time in self._curTicks[code]:
                tick = self._curTicks[code][time]

                ticks[code] = tick

                # save copy of latest tick of current trade day
                self._curLatestTicks[code] = copy.copy(tick)
            else:
                if code in self._curLatestTicks:
                    # copy it and change to latest time
                    tick = copy.copy(self._curLatestTicks[code])
                    tick.time = time
                    tick.datetime = datetime.strptime(self._curTDay + ' ' + time, '%Y-%m-%d %H:%M:%S')

                    ticks[code] = tick

        return ticks

    def _getCtamBars(self, h, m):
        """
            获取推送到策略的分钟Bars
            缺失的Bar将不会推送
        """
        time = '{0}:{1}:{2}'.format(h if h > 9 else ('0' + str(h)), m if m > 9 else ('0' + str(m)), '00')

        bars = {}
        for code in self._curBars:
            if time in self._curBars[code]:
                bar = self._curBars[code][time]

                bars[code] = bar

        return bars

    def _onPushAccount(self):
        """
            向策略推送账户相关的数据
        """
        # 委托回报
        entrusts = self._accountManager.popCurWaitingPushEntrusts()
        for entrust in entrusts:
            self._strategy.onEntrust(entrust)

        # 成交回报
        deals = self._accountManager.popCurWaitingPushDeals()
        for deal in deals:
            self._strategy.onDeal(deal)

        # 持仓回报，每次都推送，这个跟实盘引擎有区别。实盘引擎只在持仓变化时推送。
        if self._accountManager.curPos:
            self._strategy.onPos(self._accountManager.curPos)

    def _setTicks(self, ticks):
        """
            设置ETF300和ETF500 Tick，也适用于bars
        """
        etf300Tick = ticks.get(DyStockCommon.etf300)
        if etf300Tick:
            self.__etf300Tick = etf300Tick

        etf500Tick = ticks.get(DyStockCommon.etf500)
        if etf500Tick:
            self.__etf500Tick = etf500Tick

    def _runTicks(self):
        self._info.print('开始回测Ticks数据[{0}]...'.format(self._curTDay))
        self._progress.init(4*60*60, 100, 20)

        # 集合竞价

        # 上午和下午交易开始时间
        startTime = [(9,30), (13,0)]

        for startTimeH, startTimeM in startTime:
            for i in range(60*60*2 + 1): # 时间右边界是闭合的
                h, m, s = self._getTime(startTimeM*60 + i) # plus minute offset for calculation
                h += startTimeH

                ticks = self._getCtaTicks(h, m, s)

                # onTicks, 引擎不统一catch策略中的任何异常，策略必须处理异常
                if ticks:
                    self._accountManager.onTicks(ticks) # update current positions firstly

                    self._accountManager.syncStrategyPos(self._strategy) # 同步策略持仓

                    self._setTicks(ticks)

                    filteredTicks = self._strategyMarketFilter.filter(ticks)
                    if filteredTicks:
                        self._strategy.onTicks(filteredTicks)

                    self._onPushAccount()

                self._progress.update()

        self._info.print('Ticks数据[{0}]回测完成'.format(self._curTDay))

    def _load1dBars(self, codes):
        """ 载入日线数据 """
        self._info.print('开始载入{0}只监控股票日线数据[{1}]...'.format(len(codes), self._curTDay))

        # 日线bar基于当日复权因子，这样保证整个逻辑跟日内和tick回测一样
        if not self._daysEngine.load([self._curTDay, -1], codes=codes, latestAdjFactorInDb=False):
            return False

        count = 0
        for code in codes:
            df = self._daysEngine.getDataFrame(code)
            if df is None:
                continue

            # get preClose if 昨日停牌
            if df.shape[0] < 2:
                # 当日停牌
                if self._curTDay != df.index[0].strftime("%Y-%m-%d"):
                    continue

                # 载入当日和昨日数据
                if not self._errorDaysEngine.loadCode(code, [self._curTDay, -1], latestAdjFactorInDb=False):
                    continue

                df = self._errorDaysEngine.getDataFrame(code)
                if df.shape[0] < 2:
                    continue

            # convert to BarData
            barData = DyStockCtaBarData('1d')

            barData.code = code
            barData.name = self._daysEngine.stockAllCodesFunds[code]

            # OHLCV
            barData.open = df.ix[-1, 'open']
            barData.high = df.ix[-1, 'high']
            barData.low = df.ix[-1, 'low']
            barData.close = df.ix[-1, 'close']
            barData.volume = df.ix[-1, 'volume']

            barData.curOpen = barData.open
            barData.curHigh = barData.high
            barData.curLow = barData.low

            barData.preClose = df.ix[0, 'close']
            
            # datetime
            barData.date = self._curTDay
            barData.time = '15:00:00'
            barData.datetime = datetime.strptime(self._curTDay + ' 15:00:00', '%Y-%m-%d %H:%M:%S')

            self._curBars[code] = barData

            count += 1

        self._info.print('{0}只监控股票日线数据[{1}]载入完成'.format(count, self._curTDay))

        return True

    def _loadmBars(self, codes, m):
        """ 载入分钟Bar数据
            @m: 分钟
        """
        self._info.print('开始载入{0}只监控股票{1}分钟K线数据[{2}]...'.format(len(codes), m, self._curTDay))
        self._progress.init(len(codes), 100)

        count = 0
        for code in codes:
            # 获取昨日收盘和当日开盘
            preClose, curOpen = self._loadPreCloseOpen(code)
            if curOpen is None: # 停牌或者未上市
                self._progress.update()
                continue

            # load ticks
            if not self._ticksEngine.loadCode(code, self._curTDay):
                # 由于新浪分笔数据有时会缺失，所以不返回错误，只打印警告
                self._info.print('{0}:{1}Ticks数据[{2}]载入失败'.format(code, self._daysEngine.stockCodes[code], self._curTDay), DyLogData.warning)
                self._progress.update()
                continue

            df = self._ticksEngine.getDataFrame(code)

            # 合成分钟Bar, 右闭合
            # 缺失的Bar设为NaN
            df = df.resample(str(m) + 'min', closed='right', label='right')[['price', 'volume']].agg(OrderedDict([('price', 'ohlc'), ('volume', 'sum')]))
            df.dropna(inplace=True) # drop缺失的Bars

            data = df.reset_index().values.tolist()

            # load to memory
            bars = {}
            curHigh, curLow = None, None
            for datetime, open, high, low, close, volume in data: # DF is MultiIndex
                # convert to BarData
                barData = DyStockCtaBarData('%sm'%m)

                barData.code = code
                barData.name = self._daysEngine.stockAllCodesFunds[code]

                # OHLCV
                barData.open = open
                barData.high = high
                barData.low = low
                barData.close = close
                barData.volume = int(volume*100)
                barData.preClose = preClose
                barData.curOpen = curOpen

                curLow = low if curLow is None else min(curLow, low)
                curHigh = high if curHigh is None else max(curHigh, high)

                barData.curHigh = curHigh
                barData.curLow = curLow
            
                # datetime
                barData.date = self._curTDay
                barData.time = datetime.strftime('%H:%M:%S')
                barData.datetime = datetime

                bars[barData.time] = barData

            self._curBars[code] = bars

            count += 1
            self._progress.update()

        self._info.print('{0}只监控股票{1}分钟K线数据[{2}]载入完成'.format(count, m, self._curTDay))

        return True

    def _loadBars(self, barMode, codes):
        if barMode == 'bar1d':
            ret = self._load1dBars(codes)

        else: # 分钟Bar, like 'bar1m', 'bar5m', ...
            ret = self._loadmBars(codes, int(barMode[3:-1]))

        if not ret:
            self._info.print('策略载入[{0}]数据[{1}]失败'.format(barMode, self._curTDay), DyLogData.error)

        return ret

    def _loadData(self, codes):
        if 'bar' in self._strategy.backTestingMode:
            if not self._loadBars(self._strategy.backTestingMode, codes):
                return False

        else: # default is Tick Mode
            if not self._loadTicks(codes):
                self._info.print('策略载入Ticks数据[{0}]失败'.format(self._curTDay), DyLogData.error)
                return False

        return True

    def _run1dBars(self):
        self._info.print('开始回测日线数据[{0}]...'.format(self._curTDay))

        # onBars, 引擎不统一catch策略中的任何异常，策略必须处理异常
        if self._curBars:
            self._accountManager.onBars(self._curBars) # update current positions firstly

            self._accountManager.syncStrategyPos(self._strategy) # 同步策略持仓

            self._setTicks(self._curBars)

            filteredBars = self._strategyMarketFilter.filter(self._curBars)
            if filteredBars:
                self._strategy.onBars(filteredBars)

            self._onPushAccount()

        self._info.print('日线数据[{0}]回测完成'.format(self._curTDay))

    def _runmBars(self, barM):
        self._info.print('开始回测{0}分钟K线数据[{1}]...'.format(barM, self._curTDay))
        self._progress.init(int(4*60/barM), 100, 20)

        # 集合竞价

        # 上午和下午交易开始时间
        startTime = [(9, 30), (13, 0)]

        for startTimeH, startTimeM in startTime:
            for i in range(0, 60*60*2 + 1, barM*60):
                h, m, s = self._getTime(startTimeM*60 + i) # plus minute offset for calculation
                h += startTimeH

                bars = self._getCtamBars(h, m)

                # onBars, 引擎不统一catch策略中的任何异常，策略必须处理异常
                if bars:
                    self._accountManager.onBars(bars) # update current positions firstly

                    self._accountManager.syncStrategyPos(self._strategy) # 同步策略持仓

                    self._setTicks(bars)

                    filteredBars = self._strategyMarketFilter.filter(bars)
                    if filteredBars:
                        self._strategy.onBars(filteredBars)

                    self._onPushAccount()

                self._progress.update()

        self._info.print('{0}分钟K线数据[{1}]回测完成'.format(barM, self._curTDay))

    def _runBars(self, barMode):
        if barMode == 'bar1d':
            self._run1dBars()

        else:
            self._runmBars(int(barMode[3:-1]))

    def _runData(self):
        if 'bar' in self._strategy.backTestingMode:
            self._runBars(self._strategy.backTestingMode)

        else: # default is Tick Mode
            self._runTicks()

    def _verifyParams(self, tDay):
        if 'bar' in self._strategy.backTestingMode:
            if self._strategy.backTestingMode != 'bar1d':
                m = int(self._strategy.backTestingMode[3:-1])
                if math.ceil(4*60/m) != int(4*60/m):
                    return False

        return True

    def run(self, tDay):
        """ 运行指定交易日回测 """
        
        # 检查参数合法性
        if not self._verifyParams(tDay):
            self._info.print('策略[{0}]分钟Bar模式错误: {1}'.format(tDay, self._strategy.backTestingMode), DyLogData.error)
            return False

        # 当日初始化
        self._curInit(tDay)

        # 策略开盘前准备
        onOpenCodes = self._strategy.onOpenCodes()
        if onOpenCodes is None: # 策略指定的开盘股票代码优先于测试股票代码
            onOpenCodes = self._testCodes

        if not self._strategy.onOpen(tDay, onOpenCodes):
            self._info.print('策略[{0}]开盘前准备失败'.format(tDay), DyLogData.error)
            return False

        # 账户管理开盘前准备
        self._info.enable(False)
        ret = self._accountManager.onOpen(tDay)
        self._info.enable(True)
        if not ret:
            self._info.print('账户管理[{0}]开盘前准备失败'.format(tDay), DyLogData.error)
            return False

        # 设置策略行情过滤器
        self._strategyMarketFilter.addFilter(self._strategy.onMonitor())

        # 得到策略要监控的股票池
        monitoredCodes = self._strategy.onMonitor() + self._accountManager.onMonitor() + [DyStockCommon.etf300, DyStockCommon.etf500]
        monitoredCodes = set(monitoredCodes) # 去除重复的股票
        monitoredCodes -= set(DyStockCommon.indexes.keys()) # 新浪没有指数的Tick数据
        monitoredCodes = list(monitoredCodes)

        # 载入监控股票池的回测数据
        if not self._loadData(monitoredCodes):
            return False

        # 运行回测数据
        self._runData()

        # 收盘后的处理
        self._strategy.onClose()
        self._accountManager.onClose()

        return True

    def setSlippage(self, slippage):
        """ 设置滑点（成交价的千分之） """
        DyStockCtaTickData.slippage = slippage
        DyStockCtaBarData.slippage = slippage

    def loadPreparedData(self, date, strategyCls):
        return None

    def loadPreparedPosData(self, date, strategyCls):
        return None

    def loadOnClose(self, date, strategyCls):
        return self._strategySavedData

    def saveOnClose(self, date, strategyCls, savedData=None):
        self._strategySavedData = savedData

    def tLatestDayInDb(self):
        return self._dataEngine.daysEngine.tLatestDayInDb()

    def tDaysOffsetInDb(self, base, n=0):
        return self._dataEngine.daysEngine.tDaysOffsetInDb(base, n)

    def putStockMarketMonitorUiEvent(self, strategyCls, data=None, newData=False, op=None, signalDetails=None, datetime_=None):
        pass

    def putStockMarketStrengthUpdateEvent(self, strategyCls, time, marketStrengthInfo):
        pass

    def putEvent(self, type, data):
        pass

    @property
    def marketTime(self):
        return self.__etf300Tick.time if self.__etf300Tick else None

    @property
    def marketDatetime(self):
        return self.__etf300Tick.datetime if self.__etf300Tick else None

    @property
    def indexTick(self):
        return self.__etf300Tick

    @property
    def etf300Tick(self):
        return self.__etf300Tick

    @property
    def etf500Tick(self):
        return self.__etf500Tick

    @property
    def dataEngine(self):
        return self._dataEngine

    @property
    def errorDataEngine(self):
        return self._errorDataEngine

    def getCurPos(self, strategyCls):
        return self._accountManager.curPos

    def getCurCash(self, strategyCls):
        return self._accountManager.curCash

    def getCurCapital(self, strategyCls):
        return self._accountManager.getCurCapital()

    def getCurCodePosMarketValue(self, strategyCls, code):
        return self._accountManager.getCurCodePosMarketValue(code)

    def getCurPosMarketValue(self, strategyCls):
        return self._accountManager.getCurPosMarketValue()

    def getCurAckData(self):
        return self._accountManager.getCurAckData(self._strategy.__class__)

    def getBuyVol(self, cash, code, price):
        return DyStockTradeCommon.getBuyVol(cash, code, price)

    def buy(self, strategyCls, tick, volume, signalInfo=None):
        datetime = tick.datetime
        code = tick.code
        name = tick.name
        price = getattr(tick, strategyCls.buyPrice)

        return self._accountManager.buy(datetime, strategyCls, code, name, price, volume, signalInfo, tick)
    
    def sell(self, strategyCls, tick, volume, sellReason=None, signalInfo=None):
        datetime = tick.datetime
        code = tick.code
        price = getattr(tick, strategyCls.sellPrice)

        return self._accountManager.sell(datetime, strategyCls, code, price, volume, sellReason, signalInfo, tick)

    def buyByRatio(self, strategyCls, tick, ratio, ratioMode, signalInfo=None):
        return DyStockCtaEngineExtra.buyByRatio(self, self._accountManager, strategyCls, tick, ratio, ratioMode, signalInfo)

    def sellByRatio(self, strategy, tick, ratio, ratioMode, sellReason=None, signalInfo=None):
        return DyStockCtaEngineExtra.sellByRatio(self, self._accountManager, strategy, tick, ratio, ratioMode, sellReason, signalInfo)

    def closePos(self, strategyCls, tick, volume, sellReason, signalInfo=None):
        """
            注释参照DyStockCtaEngine
        """
        datetime = tick.datetime
        code = tick.code
        price = getattr(tick, strategyCls.sellPrice)

        return self._accountManager.sell(datetime, strategyCls, code, price, volume, sellReason, signalInfo, tick)

    def cancel(self, strategyCls, cancelEntrust):
        """
            策略撤销委托
        """
        return False