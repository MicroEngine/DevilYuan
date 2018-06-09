import numpy as np

from EventEngine.DyEvent import *
from ..DyStockDataCommon import *
from .DyStockMongoDbEngine import *
from ..Gateway.DyStockDataGateway import *
from .Common.DyStockDataCommonEngine import *
from DyCommon.DyCommon import *


class DyStockDataTicksEngine(object):
    """
        从新浪获取股票（基金）的分笔数据
        新浪没有指数分笔数据
        !!!由于新浪会有无效历史分笔数据，所以分笔数据的更新依赖日线数据更新。也就是说要先更新日线数据，然后再更新分笔数据。
    """

    batchSize = 10
    #shiftWindowSize = DyStockDataEventHandType.stockHistTicksHandNbr
    shiftWindowSize = 1

    def __init__(self, eventEngine, daysEngine, mongoDbEngine, gateway, info, registerEvent=True):
        self._eventEngine = eventEngine
        self._daysEngine = daysEngine
        self._mongoDbEngine = mongoDbEngine
        self._gateway = gateway
        self._info = info

        self._progress = DyProgress(self._info)

        self._isStopped = False

        self._codeTicksDf = {} # 股票的分笔DataFrame, {code: ticks DF}
        self._codeTicksAdj = {} # 股票的分笔DataFrame是否已经前复权过
        self._codeDaysDf = {} # 股票的分笔对应的日线数据, {code: day DF}

        # counts for Ui show
        self._inserted2DbCount = 0 # increased count
        self._noDataCount = 0 # increased count

        # sending window related, which is used for controlling sending ticks' request to Gateway
        self._windowSize = 0
        self._totalWindowData = [] # [(code,date)]
        self._windowCursor = 0

        if registerEvent:
            self._registerEvent()

    def _initWindow(self, codes):
        self._windowSize = 0
        self._windowCursor = 0

        # init
        self._totalWindowData = codes

        self._increaseWindowSize(self.batchSize)

    def _increaseWindowSize(self, size=1):
        windowData = self._totalWindowData[self._windowCursor : self._windowCursor + size]

        self._windowSize += len(windowData)
        self._windowCursor += len(windowData)
        
        # send to Gateway by round robin
        for i, (code, date) in enumerate(windowData, 1):
            self._sendTicksReq(code, date, self._windowCursor - i)

    def _updateWindow(self):
        assert(self._windowSize > 0)

        # decrease
        self._windowSize -= 1

        # hook stop event
        if self._isStopped:
            if self._windowSize == 0: # send stopAck event
                self._printCounts()

                self._eventEngine.put(DyEvent(DyEventType.stopAck))

            return

        # Note: To get good Gateway throughput, size can be more than 1. factor * @stockHistTicksHandNbr is a good choice.
        # Note: Don't forget intial number of requests already sent to Gateway.
        self._increaseWindowSize(self.shiftWindowSize)

    def autoUpdateTickData(self):
        pass

    def _initProgress(self, totalReqNbr):
        self._info.print('总共{0}笔Ticks数据需要更新...'.format(totalReqNbr))

        self._progress.init(totalReqNbr)

        # if no any tickes to be gotten, send finish event to Ui
        if self._progress.totalReqCount == 0:
            self._printCounts()
            
            # put finish event
            self._eventEngine.put(DyEvent(DyEventType.finish))

    def _printCounts(self):
        self._info.print('{0}笔Ticks插入到数据库'.format(self._inserted2DbCount))
        self._info.print('由于股票停牌或者没有上市, {0}笔Ticks没有数据'.format(self._noDataCount))

    def _updateProgress(self):
        
        self._progress.update()

        if self._progress.totalReqCount == 0: # if 0, always set 100% without considering total request nbr
            if not self._isStopped: # Note: if stopped, finish event no need to be sent.
                self._printCounts()

                # put finish event
                self._eventEngine.put(DyEvent(DyEventType.finish))

    def _insert2Db(self, code, date, data):
        if self._mongoDbEngine.insertTicks(code, date, data): # insert into DB successfully
            # count firstly
            self._inserted2DbCount += 1

            self._updateProgress()
            self._updateWindow()

        else: # failed into DB

            # send to Gateway to get ticks again, 2016/7/1
            #self._sendTicksReq(code, date, self._progress.totalReqCount) # just use @self._progress.totalReqCount as request count

            # simualte Ack event and push back to insert into DB again
            event = DyEvent(DyEventType.stockHistTicksAck)
            event.data = DyStockHistTicksAckData(code, date, data)

            self._eventEngine.put(event)

    def _getTicksNotInDb(self, startDate, endDate, codes):
        """
            过期函数，被@_getTicksByDays替换。
            意味着，更新分笔数据，先要更新日线数据，否则分笔数据将不会更新。
        """
        # load code table and trade days table
        commonEngine = DyStockDataCommonEngine(self._mongoDbEngine, self._gateway, self._info)
        if not commonEngine.load([startDate, endDate]):
            return None

        stockCodes = commonEngine.stockCodesFunds if codes is None else codes
        tdays = commonEngine.getTradeDays(startDate, endDate)
        
        # get dates of code not in DB
        self._info.print('开始从数据库获取[{0}, {1}]没有Ticks数据的信息...'.format(startDate, endDate))

        self._progress.init(len(stockCodes), 100)

        codes = []
        for code in stockCodes: # Note: Sina doesn't provide indexes history ticks
            for date in tdays:
                if not self._mongoDbEngine.isTicksExisting(code, date):
                    codes.append((code, date))

            self._progress.update()

        return codes

    def _loadCommon(self, startDate, endDate, codes=None):
        commonEngine = DyStockDataCommonEngine(self._mongoDbEngine, self._gateway, self._info)
        if not commonEngine.load([startDate, endDate], codes=codes):
            return None, None

        stockCodes = commonEngine.stockCodesFunds # Note: Sina doesn't provide indexes history ticks, so we don't return index
        tdays = commonEngine.getTradeDays(startDate, endDate)

        return stockCodes, tdays

    def _getTicksByDays(self, startDate, endDate, codes=None):
        """ 根据日线数据获取数据库里不存在的分笔数据 """

        # load code table and trade days table to check if there're trade days between [startDate, endDate]
        stockCodes, tdays = self._loadCommon(startDate, endDate)
        if tdays is None: return None

        # 载入日线数据
        if tdays:
            if not self._daysEngine.load([startDate, endDate], codes=codes):
                return None
        
        # get dates of code in days database but not in DB
        self._info.print('开始根据日线数据获取[{0}, {1}]没有Ticks数据的信息...'.format(startDate, endDate))

        self._progress.init(len(stockCodes), 100)

        codes = []
        for code in stockCodes: # Note: Sina doesn't provide indexes history ticks
            for date in tdays:
                if self._daysEngine.isExisting(code, date) and (not self._mongoDbEngine.isTicksExisting(code, date)):
                    codes.append((code, date))

            self._progress.update()

        return codes

    def _deleteInvalidTicksByDays(self, startDate, endDate):
        """ 根据日线数据删除数据库里不应该存在的分笔数据
            新浪有时会含有不存在的分笔数据
        """
        # load code table and trade days table to check if there're trade days between [startDate, endDate]
        stockCodes, tdays = self._loadCommon(startDate, endDate)
        if tdays is None: return False

        # 载入日线数据
        if tdays:
            if not self._daysEngine.load([startDate, endDate]):
                return False

        # 获取所有日期
        dates = DyTime.getDates(startDate, endDate, strFormat=True)
        
        self._info.print('开始根据日线数据删除[{0}, {1}]不应该存在的Ticks数据...'.format(startDate, endDate))

        self._progress.init(len(stockCodes), 100)

        codes = []
        deleteCount = 0
        for code in stockCodes: # Note: Sina doesn't provide indexes history ticks
            for date in dates:
                if (not self._daysEngine.isExisting(code, date)) and self._mongoDbEngine.isTicksExisting(code, date):
                    self._mongoDbEngine._deleteTicks(code, date)
                    deleteCount += 1

            self._progress.update()

        self._info.print('总共删除{0}个无效Ticks数据'.format(deleteCount), DyLogData.ind)

        return True

    def _getTicks(self, codes):
        """ request Gateway to get ticks
            @codes: [(code, date)]
        """
        # reset stop flag firstly
        self._isStopped = False

        # reset counts frislty
        self._inserted2DbCount = 0
        self._noDataCount = 0

        # init progress
        self._initProgress(len(codes))

        # init sending window
        self._initWindow(codes)

    def _updateTicks(self, startDate, endDate, codes):
        """ only update ticks in days database but not in DB.
            That means you should update days data firslty, and then update ticks data.
            Otherwise, nothing will be updated for ticks data.
        """
        # 2016.10.30, replace @_getTicksNotInDb
        codes = self._getTicksByDays(startDate, endDate, codes)
        if codes is None:
            self._eventEngine.put(DyEvent(DyEventType.fail))
            return

        # start getting ticks from Gateway
        self._getTicks(codes)

    def _verifyTicks(self, startDate, endDate, verifyMissing=True, verifyInvalid=True):
        """ verify ticks according to Days data """
        # 先校验无效历史分笔数据
        if verifyInvalid:
            self._info.print('开始校验无效历史分笔数据...', DyLogData.ind)

            if not self._deleteInvalidTicksByDays(startDate, endDate):
                self._eventEngine.put(DyEvent(DyEventType.fail))
                return

            self._info.print('校验无效历史分笔数据完成', DyLogData.ind)

        # 然后校验缺失历史分笔数据
        if verifyMissing:
            self._info.print('开始校验缺失历史分笔数据...', DyLogData.ind)

            codes = self._getTicksByDays(startDate, endDate)
            if codes is None:
                self._eventEngine.put(DyEvent(DyEventType.fail))
                return
        
            # start getting ticks from Gateway
            self._getTicks(codes)
        else:
            self._eventEngine.put(DyEvent(DyEventType.finish))

    def _sendTicksReq(self, code, date, reqCount):
        reqHand = reqCount % DyStockDataEventHandType.stockHistTicksHandNbr

        event = DyEvent(DyEventType.stockHistTicksReq + str(reqHand))
        event.data = DyStockHistTicksReqData(code, date)

        self._eventEngine.put(event)

    def _stockHistTicksAckHandler(self, event):
        """ handle ticks received from Gateway
            2 cases successful:
                a. 股票当日没有数据, 可能原因是停牌或者还没有上市（股票代码不存在)
                b. 成功插入数据库
        """
        # unpack
        code = event.data.code
        date = event.data.date
        data = event.data.data

        # hook stop event
        if self._isStopped:
            self._updateWindow() # drain out already sent @stockHistTicksReq events
            return

        if data is None: # set failed to Gateway again
            self._sendTicksReq(code, date, self._progress.totalReqCount) # just use @self._progress.totalReqCount as request count

        elif data == DyStockHistTicksAckData.noData: # 股票当日没有数据, think it as success
            if DyStockDataCommon.logDetailsEnabled:
                self._info.print('{0}:{1}没有[{2}]Ticks数据'.format(code, self._daysEngine.stockCodesFunds.get(code), date), DyLogData.warning)

            # count firstly
            self._noDataCount += 1

            self._updateProgress()
            self._updateWindow()

        else: # get ticks successfully, and then insert into DB
            self._insert2Db(code, date, data)

    def _updateStockHistTicksHandler(self, event):
        codes = event.data['codes'] if 'codes' in event.data else None

        self._updateTicks(event.data['startDate'], event.data['endDate'], codes)

    def _verifyStockHistTicksHandler(self, event):
        self._verifyTicks(event.data['startDate'], event.data['endDate'], event.data['verifyMissing'], event.data['verifyInvalid'])

    def _stopReqHandler(self, event):
        self._isStopped = True

    def _registerEvent(self):
        self._eventEngine.register(DyEventType.updateStockHistTicks, self._updateStockHistTicksHandler, DyStockDataEventHandType.ticksEngine)
        self._eventEngine.register(DyEventType.stockHistTicksAck, self._stockHistTicksAckHandler, DyStockDataEventHandType.ticksEngine)
        self._eventEngine.register(DyEventType.stopUpdateStockHistTicksReq, self._stopReqHandler, DyStockDataEventHandType.ticksEngine)
        self._eventEngine.register(DyEventType.verifyStockHistTicks, self._verifyStockHistTicksHandler, DyStockDataEventHandType.ticksEngine)
        self._eventEngine.register(DyEventType.stopVerifyStockHistTicksReq, self._stopReqHandler, DyStockDataEventHandType.ticksEngine)

    # -------------------- 公共接口 --------------------
    def loadCode(self, code, date):
        # init
        self._codeTicksDf = {}
        self._codeTicksAdj = {}
        self._codeDaysDf = {}

        df = self._mongoDbEngine.getTicks(code, date, date)
        if df is None:
            return False
        
        self._codeTicksDf[code] = df

        return True

    def getDataFrame(self, code, adj=False, continuous=True):
        """
            获取股票载入进来的分笔DF
            @adj：是否基于最新的复权因子前复权
            @continuous: 返回值是连续模式，非连续模式是字典模式{day: ticksDF}
        """
        if code not in self._codeTicksDf:
            return None

        df = self._codeTicksDf[code]

        if adj and not self._codeTicksAdj.get(code, False): # 前复权 and 还没有前复权过

            self._codeTicksAdj[code] = True

            # get latest adjFactor
            latestAdjFactor = self._mongoDbEngine.getAdjFactor(code, datetime.now().strftime("%Y-%m-%d"))

            if code in self._codeDaysDf: # 历史复权因子已经载入, 也就是通过@loadCodeN载入Tick数据
                adjFactor = self._codeDaysDf[code]['adjfactor']

                adjFactorIndex = [date.strftime("%Y-%m-%d") for date in adjFactor.index]
                adjFactors = adjFactor.values.tolist()
                
                # 复权因子扩散到对应的每个Tick
                adjFactor = []
                for date, factor in zip(adjFactorIndex, adjFactors):
                    size = df[date:date].shape[0]
                    adjFactor.extend(size * [factor])

                    if size == 0:
                        self._info.print('{0}Tick数据[{1}]缺失'.format(self._daysEngine.stockAllCodesFunds[code], date), DyLogData.warning)

                adjFactor = np.array(adjFactor)
                adjFactor = adjFactor.reshape((adjFactor.shape[0], 1))

            else: # get this day adjFactor
                adjFactor = self._mongoDbEngine.getAdjFactor(code, df.index[0].strftime("%Y-%m-%d"))

            df[['price']] = df[['price']]*(adjFactor / latestAdjFactor)
            df[['volume']] = df[['volume']]*(latestAdjFactor / adjFactor)

        # process return format
        if not continuous:
            dfDict = {}
            if code in self._codeDaysDf: # 历史复权因子已经载入, 也就是通过@loadCodeN载入Tick数据
                for date in [date.strftime("%Y-%m-%d") for date in self._codeDaysDf[code].index]:
                    df_ = df[date:date]
                    if df_.shape[0] > 0:
                        dfDict[date] = df_
            else:
                dfDict[df.index[0].strftime("%Y-%m-%d")] = df

            df = dfDict

        return df

    def loadCodeN(self, code, dates):
        """
            载入指定股票的一段连续日期的Ticks

            @dates: 类型是list，有如下几种模式：
                        [startDate, endDate]
                        [baseDate, (+/-)n] 负数是向前，正数向后
                        [startDate, baseDate, +n]
                        [-n, baseDate, +n]
                        [-n, startDate, endDate]
        """
        # init
        self._codeTicksDf = {}
        self._codeTicksAdj = {}
        self._codeDaysDf = {}

        # 载入日线数据
        if not self._daysEngine.loadCode(code, dates):
            return False

        daysDf = self._daysEngine.getDataFrame(code)

        # 载入Tick数据
        startDay = daysDf.index[0].strftime("%Y-%m-%d")
        endDay = daysDf.index[-1].strftime("%Y-%m-%d")

        ticksDf = self._mongoDbEngine.getTicks(code, startDay, endDay)
        if ticksDf is None: return False

        # 保存Tick数据
        self._codeTicksDf[code] = ticksDf

        # 保存对应的日线数据
        self._codeDaysDf[code] = daysDf

        return True

    def getDays(self, code):
        """
            得到股票载入ticks数据对应的交易日
            只在调用@loadCodeN后有效
        """
        if code not in self._codeDaysDf: return None

        return [date.strftime("%Y-%m-%d") for date in self._codeDaysDf[code].index]

    def getDaysDataFrame(self, code):
        """
            得到股票载入ticks数据对应的日线数据
            只在调用@loadCodeN后有效
        """
        return self._codeDaysDf[code] if code in self._codeDaysDf else None

    def getCodeName(self, code):
        """
            得到股票名称
            只在调用@loadCodeN后有效
        """
        if code not in self._codeDaysDf: return None

        return self._daysEngine.stockAllCodesFunds[code]
