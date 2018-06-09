from DyCommon.DyCommon import *
from EventEngine.DyEvent import *
from ..DyStockDataCommon import *
from .Common.DyStockDataCommonEngine import *


class DyStockDataDaysEngine(object):
    """ 股票（指数）历史日线数据，包含股票代码表和交易日数据 """

    def __init__(self, eventEngie, mongoDbEngine, gateway, info, registerEvent=True):
        self._eventEngine = eventEngie
        self._mongoDbEngine = mongoDbEngine
        self._gateway = gateway
        self._info = info

        self._commonEngine = DyStockDataCommonEngine(self._mongoDbEngine, self._gateway, self._info)
        self._progress = DyProgress(self._info)

        self._updatedCodeCount = 0 # 更新日线数据的计数器
        self._codeDaysDf = {} # 股票的日线DataFrame
        self._codeAdjFactors = {} # 股票的复权因子
        
        if registerEvent:
            self._registerEvent()

    def _loadDays(self, startDate, endDate, indicators):
        self._info.print('开始载入{0}只股票(指数,基金)的日线数据[{1}, {2}]...'.format(len(self.stockAllCodesFunds), startDate, endDate))

        # init
        self._codeDaysDf = {}

        # 启用进度条显示
        self._progress.init(len(self.stockAllCodesFunds), 100, 5)

        for code, name in self.stockAllCodesFunds.items():
            df = self._mongoDbEngine.getOneCodeDays(code, startDate, endDate, indicators, name)

            if df is not None:
                self._codeDaysDf[code] = df

            self._progress.update()

        self._info.print('股票(指数,基金)的日线数据载入完成')
        return True

    def _getDaysNotInDb(self, tradeDays, codes, indicators):
        """ @tradeDays: [trade day]
            @codes: {code: name}
            @indicators: [indicator]
            @return: {code: {indicator: [trade day]}}
        """
        self._info.print('开始从数据库获取日线不存在的数据...')

        self._progress.init(len(codes), 100)

        data = {}
        for code in codes:
            temp = self._mongoDbEngine.getNotExistingDates(code, tradeDays, indicators)

            if temp:
                data[code] = temp

            self._progress.update()
        
        return data if data else None

    def _updateHistDaysBasic(self, startDate, endDate):
        """
            更新全部A股代码表，交易日数据及板块成分代码表
        """
        return self._commonEngine.updateCodes() and self._commonEngine.updateTradeDays(startDate, endDate)# and self._commonEngine.updateAllSectorCodes(startDate, endDate)

    def _getUpdatedCodes(self, startDate, endDate, indicators, isForced, codes=None):
        """
            @return: {code: {indicator: [trade day]}}
        """
        # get trade days
        tradeDays = self._commonEngine.getTradeDays(startDate, endDate)

        # get stock codes, including indexes and funds
        codes = self.stockAllCodesFunds if codes is None else codes

        # get not existing from DB
        if not isForced:
            codes = self._getDaysNotInDb(tradeDays, codes, indicators)
            if not codes:
                self._info.print("历史日线数据已经在数据库")
                self._progress.init(0)
                self._eventEngine.put(DyEvent(DyEventType.finish))
                return None
        else:
            newCodes = {}
            for code in codes:
                newCodes[code] = {}
                for indicator in indicators:
                    newCodes[code][indicator] = tradeDays

            codes = newCodes
            if not codes:
                self._info.print("没有日线数据需要更新")
                self._progress.init(0)
                self._eventEngine.put(DyEvent(DyEventType.finish))
                return None

        return codes

    def _updateHistDays(self, startDate, endDate, indicators, isForced=False, codes=None):

        # get updated codes data info
        codes = self._getUpdatedCodes(startDate, endDate, indicators, isForced, codes)
        if codes is None: return

        # init
        self._isStopped = False
        self._updatedCodeCount = 0
        self._progress.init(len(codes), 10)

        self._info.print("开始更新{0}只股票(指数,基金)的历史日线数据...".format(len(codes)))

        # send for updating
        event = DyEvent(DyEventType.updateStockHistDays_)
        event.data = codes

        self._eventEngine.put(event)

    def _update(self, startDate, endDate, indicators, isForced=False, codes=None):
        # update all stock A code table, trade day table and sector code table firstly
        if not self._updateHistDaysBasic(startDate, endDate):
            self._printCount()
            self._eventEngine.put(DyEvent(DyEventType.fail))
            return

        # put event for 一键更新
        event = DyEvent(DyEventType.stockDaysCommonUpdateFinish)
        event.data['startDate'] = startDate
        event.data['endDate'] = endDate

        self._eventEngine.put(event)

        # 更新日线数据
        self._updateHistDays(startDate, endDate, indicators, isForced, codes)

    def _autoUpdate(self):
        # get latest date from DB
        latestDate = self._commonEngine.getLatestDateInDb()

        if latestDate is None:
            self._info.print("数据库里没有日线数据", DyLogData.error)
            self._eventEngine.put(DyEvent(DyEventType.fail))
            return

        # 贪婪法获得最大的更新结束日期
        endDate = datetime.now().strftime("%Y-%m-%d")

        # check if now is after trading time
        ret = self._gateway.isNowAfterTradingTime()

        if ret is None: # error
            self._eventEngine.put(DyEvent(DyEventType.fail))
            return

        if ret is False: # now is trade day and before end of trading time
            self._info.print("今天是交易日, 请18:00后更新今日日线数据", DyLogData.error)
            self._eventEngine.put(DyEvent(DyEventType.fail))
            return

        startDate = DyTime.getDateStr(latestDate, 1) # next date after latest date in DB

        # compare dates
        if endDate < startDate:
            # update progress UI
            self._progress.init(0)

            self._info.print("数据库日线数据已经是最新", DyLogData.ind)
            self._eventEngine.put(DyEvent(DyEventType.finish))
            return

        self._update(startDate, endDate, DyStockDataCommon.dayIndicators)

    def _updateStockHistDaysHandler(self, event):

        self._progress.reset()

        if event.data is None:
            self._autoUpdate()

        else:
            # unpack
            startDate = event.data['startDate']
            endDate = event.data['endDate']
            indicators = event.data['indicators'] # list
            isForced = event.data['forced']
            codes = event.data['codes'] if 'codes' in event.data else None

            # update
            self._update(startDate, endDate, indicators, isForced, codes)

    def _stopReqHandler(self, event):
        self._isStopped = True

    def _updateStockSectorCodesHandler(self, event):
        sectorCodeList = event.data['sectorCode']
        startDate = event.data['startDate']
        endDate = event.data['endDate']

        self._progress.reset()

        for sectorCode in sectorCodeList:
            if not self._commonEngine.updateSectorCodes(sectorCode, startDate, endDate):
                self._eventEngine.put(DyEvent(DyEventType.fail))
                return
                
        self._eventEngine.put(DyEvent(DyEventType.finish))

    def _updateOneCode(self, code, data):

        # get max date range
        startDate, endDate = None, None
        for _, dates in data.items():
            if startDate is None:
                startDate = dates[0]
                endDate = dates[-1]
            else:
                if operator.lt(dates[0], startDate):
                    startDate = dates[0]

                if operator.gt(dates[-1], endDate):
                    endDate = dates[-1]

        # get from Gateway
        data = self._gateway.getDays(code, startDate, endDate, sorted(data), self.stockAllCodesFunds[code])
        if not data: # None(errors) or no data
            return

        # updat to DB
        if self._mongoDbEngine.updateDays(code, data):
            self._updatedCodeCount += 1 # 需要更新的股票（也就是在数据库里的数据不全），并且数据成功写入数据库

    def _printCount(self):
        self._info.print('由于股票停牌或者没有上市, 更新了{0}只股票(指数,基金)日线数据'.format(self._updatedCodeCount), DyLogData.ind)

    def _updateStockHistDays_Handler(self, event):
        # unpack
        codes = event.data

        # check stop flag firstly
        if self._isStopped:
            self._printCount()
            self._eventEngine.put(DyEvent(DyEventType.stopAck))
            return

        # update one code each time
        code = sorted(codes)[0]
        self._updateOneCode(code, codes[code])

        # update progress
        self._progress.update()

        # delete updated code
        del codes[code]

        if not codes: # all codes are are updated
            self._printCount()
            self._eventEngine.put(DyEvent(DyEventType.finish))
            return

        # send for next updating
        event = DyEvent(DyEventType.updateStockHistDays_)
        event.data = codes

        self._eventEngine.put(event)

    def _loadCommon(self, dates, codes):
        if not self._commonEngine.load(dates, codes):
            return None, None

        return self._commonEngine.tOldestDay(), self._commonEngine.tLatestDay()

    def _loadAdjFactors(self, date, latestAdjFactorInDb):
        """ 载入@date的复权因子"""
        self._info.print('开始载入复权因子...')

        # init
        self._codeAdjFactors = {}

        if latestAdjFactorInDb: # 获取数据库里日线数据的最新复权因子
            date = self._commonEngine.getLatestTradeDayInDb()
            if date is None: return False

        # init progress
        self._progress.init(len(self._codeDaysDf), 100, 10)

        # 载入复权因子, 基于载入的日线数据
        for code, _ in self._codeDaysDf.items():
            adjFactor = self._mongoDbEngine.getAdjFactor(code, date, self.stockAllCodesFunds[code])

            if adjFactor is not None:
                self._codeAdjFactors[code] = adjFactor
            else:
                self._info.print('{0}:{1}复权因子缺失[{2}]'.format(code, self.stockAllCodesFunds[code], date), DyLogData.warning)

            self._progress.update()

        self._info.print('复权因子载入完成')
        return True

    def _processAdj(self):
        """ 前复权 """
        self._info.print("开始前复权...")

        self._progress.init(len(self._codeDaysDf), 100, 20)

        for code, df in self._codeDaysDf.items():
            # 复权因子变换
            adjFactor = df['adjfactor']/self._codeAdjFactors[code]
            adjFactor = adjFactor.values.reshape((adjFactor.shape[0], 1))

            # 价格相关
            prices = df[['open', 'high', 'low', 'close']].values
            df[['open', 'high', 'low', 'close']] = prices * adjFactor

            # 成交量
            df[['volume']] = df[['volume']].values / adjFactor

            self._progress.update()

        self._info.print("前复权完成")

    def _unionDates(self, startDate, endDate, dates):
        for date in dates:
            if isinstance(date, str):
                if operator.lt(date, startDate):
                    startDate = date

                if operator.gt(date, endDate):
                    endDate = date

        return startDate, endDate

    def _loadOneCodeDays(self, code, dates, indicators):
        """
            载入个股日线数据，个股对应的指数数据也被载入
            个股上市可能早于指数
        """
        # 载入个股日线数据
        df = self._mongoDbEngine.getOneCodeDaysUnified(code, dates, indicators, self.stockAllCodesFundsSectors[code])
        if df is None:
            return None, None

        # init
        self._codeDaysDf = {}

        # set stock DF
        self._codeDaysDf[code] = df

        # new days
        startDay = df.index[0].strftime("%Y-%m-%d")
        endDay = df.index[-1].strftime("%Y-%m-%d")

        # 载入对应的指数日线数据
        index = self.getIndex(code)
        df = self._mongoDbEngine.getOneCodeDays(index, startDay, endDay, indicators, self.stockIndexes[index])

        #!!! 个股上市可能早于指数
        if df is not None:
            self._codeDaysDf[index] = df

        # 获取日期并集for trade days loading
        return self._unionDates(startDay, endDay, dates)

    def _registerEvent(self):
        self._eventEngine.register(DyEventType.updateStockHistDays, self._updateStockHistDaysHandler, DyStockDataEventHandType.daysEngine)
        self._eventEngine.register(DyEventType.updateStockHistDays_, self._updateStockHistDays_Handler, DyStockDataEventHandType.daysEngine)
        self._eventEngine.register(DyEventType.stopUpdateStockHistDaysReq, self._stopReqHandler, DyStockDataEventHandType.daysEngine)

        self._eventEngine.register(DyEventType.updateStockSectorCodes, self._updateStockSectorCodesHandler, DyStockDataEventHandType.daysEngine)

    ####################################################
    # -------------------- 公共接口 --------------------
    ####################################################
    def test(self):
        pass

    def tDaysOffset(self, base, n=0):
        return self._commonEngine.tDaysOffset(base, n)

    def tDays(self, start, end):
        return self._commonEngine.tDays(start, end)
     
    def tLatestDay(self):
        return self._commonEngine.tLatestDay()

    def tLatestDayInDb(self):
        return self._commonEngine.getLatestTradeDayInDb()

    def tDaysCountInDb(self, start, end):
        return self._commonEngine.tDaysCountInDb(start, end)

    def tDaysOffsetInDb(self, base, n=0):
        return self._commonEngine.tDaysOffsetInDb(base, n)

    def codeTDayOffset(self, code, baseDate, n=0, strict=True):
        """ 根据偏移获取个股的交易日
            @strict: 严格方式，非严格方式，则获取股票在数据库里的最大偏移
        """
        return self._mongoDbEngine.codeTDayOffset(code, baseDate, n, strict)

    def getCode(self, name):
        """
            根据股票名称获取股票代码
        """
        return self._commonEngine.getCode(name)

    @property
    def shIndex(self):
        return self._commonEngine.shIndex

    @property
    def szIndex(self):
        return self._commonEngine.szIndex

    @property
    def cybIndex(self):
        return self._commonEngine.cybIndex

    @property
    def zxbIndex(self):
        return self._commonEngine.zxbIndex

    @property
    def etf50(self):
        return self._commonEngine.etf50

    @property
    def etf300(self):
        return self._commonEngine.etf300

    @property
    def etf500(self):
        return self._commonEngine.etf500

    @property
    def stockFunds(self):
        return self._commonEngine.stockFunds

    @property
    def stockCodesFunds(self):
        return self._commonEngine.stockCodesFunds

    @property
    def stockAllCodesFunds(self):
        return self._commonEngine.stockAllCodesFunds

    @property
    def stockAllCodesFundsSectors(self):
        return self._commonEngine.stockAllCodesFundsSectors

    @property
    def stockCodes(self):
        return self._commonEngine.stockCodes

    @property
    def stockAllCodes(self):
        return self._commonEngine.stockAllCodes

    @property
    def stockIndexes(self):
        """
            大盘指数
        """
        return self._commonEngine.stockIndexes

    @property
    def stockIndexesSectors(self):
        """
            大盘指数和板块指数
        """
        return self._commonEngine.stockIndexesSectors

    def getIndex(self, code):
        """
            获取个股对应的大盘指数
        """
        return self._commonEngine.getIndex(code)

    def getIndexStockCodes(self, index=None):
        """
            获取大盘指数包含的股票代码表
        """
        return self._commonEngine.getIndexStockCodes(index)

    def getIndexSectorStockCodes(self, index=None):
        """
            获取大盘指数或者板块指数包含的股票代码表
        """
        return self._commonEngine.getIndexSectorStockCodes(index)

    def loadCodeTable(self, codes=None):
        return self._commonEngine.loadCodeTable(codes)

    def loadSectorCodeTable(self, sectorCode, date, codes=None):
        """
            载入板块的成份股代码表
        """
        return self._commonEngine.loadSectorCodeTable(sectorCode, date, codes)

    def getSectorCodes(self, sectorCode):
        """
            获取板块的成份股代码表
            call after @loadSectorCodeTable
            @return: {code: name}
        """
        return self._commonEngine.getSectorCodes(sectorCode)

    def loadTradeDays(self, dates):
        return self._commonEngine.loadTradeDays(dates)

    def loadCommon(self, dates, codes=None):
        return self._commonEngine.load(dates, codes)

    def getStockMarketDate(self, code, name=None):
        return self._mongoDbEngine.getStockMarketDate(code, name)

    def loadCode(self, code, dates, indicators=DyStockDataCommon.dayIndicators, latestAdjFactorInDb=True):
        """ 
            以个股（基金）在数据库里的数据加载日线数据。个股对应的指数数据默认载入
            @dates: 类型是list，有如下几种模式：
                        [startDate, endDate]
                        [baseDate, (+/-)n] 负数是向前，正数向后
                        [startDate, baseDate, +n]
                        [-n, baseDate, +n]
                        [-n, startDate, endDate]
            @latestAdjFactorInDb: True - 基于数据库最新复权因子前复权，一般用于选股分析和回归
                                  False - 基于end day的复权因子前复权，一般用于实盘回测
        """
        # 载入股票代码表
        if not self.loadCodeTable([code]):
            self._info.print('载入[{0}]股票代码表失败'.format(code), DyLogData.error)
            return False

        # 载入股票日线数据
        startDay, endDay = self._loadOneCodeDays(code, dates, indicators)
        if startDay is None:
            self._info.print('载入[{0}:{1}]日线数据失败{2}'.format(code, self.stockAllCodesFundsSectors[code], dates), DyLogData.error)
            return False

        # 载入交易日数据
        if not self.loadTradeDays([startDay, endDay]):
            self._info.print('载入交易日数据失败', DyLogData.error)
            return False

        # 载入复权因子
        if not self._loadAdjFactors(endDay, latestAdjFactorInDb):
            self._info.print('载入复权因子失败', DyLogData.error)
            return False

        # 前复权
        self._processAdj()

        return True

    def load(self, dates, indicators=DyStockDataCommon.dayIndicators, latestAdjFactorInDb=True, codes=None):
        """ 
            基于交易日数据，载入股票（基金）日线数据。总是载入指数日线数据。
            @dates: 类型是list，有如下几种模式：
                        [startDate, endDate]
                        [baseDate, (+/-)n] 负数是向前，正数向后
                        [startDate, baseDate, +n]
                        [-n, baseDate, +n]
                        [-n, startDate, endDate]
            @latestAdjFactorInDb: True - 基于数据库最新复权因子前复权，一般用于选股分析和回归
                             False - 基于end day的复权因子前复权，一般用于实盘回测
            @codes: [code], 股票代码，指数数据默认载入。None-载入所有股票（基金）日线数据，[]-只载入指数数据。
        """
        # 载入公共数据
        startDay, endDay = self._loadCommon(dates, codes)
        if startDay is None:
            self._info.print('DyStockDataEngine._loadCommon: 载入数据失败', DyLogData.error)
            return False

        # 载入日线数据
        if not self._loadDays(startDay, endDay, indicators):
            self._info.print('DyStockDataEngine._loadDays: 载入数据失败', DyLogData.error)
            return False

        # 载入复权因子
        if not self._loadAdjFactors(endDay, latestAdjFactorInDb):
            self._info.print('DyStockDataEngine._loadAdjFactors: 载入数据失败', DyLogData.error)
            return False

        # 前复权
        self._processAdj()

        return True

    def getDataFrame(self, code, date=None, n=None):
        df = self._codeDaysDf.get(code)
        if df is None:
            return None

        if date is None:
            return df

        if isinstance(n, int):
            # convert to absloute dates
            endDay = self.tDaysOffset(date, 0)
            startDay = self.tDaysOffset(date, n)

            if n > 0:
                startDay, endDay = endDay, startDay
        else:
            startDay, endDay = self.tDaysOffset(date, 0), n

        # !!!当只有一行数据的时候，会导致环切切不到
        retDf = None
        if df.shape[0] == 1:
            if startDay == endDay and startDay in df.index:
                retDf = df

        if retDf is None:
            retDf = df[startDay:endDay]

        return retDf

    def isExisting(self, code, date):
        if code not in self._codeDaysDf:
            return False

        try:
            self._codeDaysDf[code].ix[date]
        except Exception as ex:
            return False

        return True
