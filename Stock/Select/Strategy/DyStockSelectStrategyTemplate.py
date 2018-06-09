import os
from datetime import datetime
import operator
import json
import numpy as np
from collections import OrderedDict


class DyStockSelectStrategyTemplate(object):
    """ 所有选股策略的父类。
        对每个选出的股票，添加额外的数据列
    """
    #----- 由子类重新赋值 -----
    name = 'DyStockSelectStrategyTemplate'
    chName = '选股策略模板'
    colNames = None
    param = None

    # 不管个股所对应的日线数据DF有没有，全推所有股票的日线数据。比如高送转策略，需要遍历所有股票的代码但不管所对应的周期有没有日线数据
    # 默认只推个股有所对应的日线数据
    fullyPushDays = False

    # 相对载入数据时，由于股票停牌，统一时间切片时导致个股日线数据未载满。
    # 策略载入的基准日期的数据要在统一时间切片里，要不补全没有意义，因为有可能补全一个直到当日还长时间停牌的个股。
    # @True：引擎会补齐日线数据
    autoFillDays = False

    # 只在@autoFillDays is True时有效
    # 只向策略推送@baseDate不停牌的股票日线数据，若@baseDate是非交易日，则是向前离它最近的交易日
    optimizeAutoFillDays = False

    continuousTicks = False # Ticks数据是不是以连续模式推入策略，非连续模式为{date: ticksDF of date}

    #----- 基类私有变量, 几日是跟@__nDays相对应 -----
    __baseColNames = ['当日价格', '当日涨幅(%)', '当日指数涨幅(%)', '1日涨幅(%)', '1日指数涨幅(%)', '流通市值(亿)']
    __nDays = 1


    def __init__(self, param, info):
        self._info = info

        self._result = [] # 选股结果，由子类赋值

        # 实盘相关数据
        self._forTrade = True if 'forTrade' in param else False # 实盘选股，由策略处理实盘选股的区别。非回测时，默认生成JSON
        self._forTradeNoJson = True if 'forTradeNoJson' in param else False # 默认生成JSON file，回测时使用，由回测引擎处理。回测时无需生成JSON
        self._resultForTrade = {'stocks':{}} # 实盘选股结果，由子类赋值

        # 基准日期，模板类基于它算出 N trade days后的个股涨幅，以及对应的指数涨幅
        self.__baseDate = None # 私有变量

    #---------- 类方法 ----------
    def getAutoColName():
        return DyStockSelectStrategyTemplate.__baseColNames[1]

    #---------- 只被引擎调用 ----------
    def onPostDaysLoad(self, startDate, baseDate, n=0):
        """ 设置基准日期，并返回载入数据的日期，由引擎调用 """
        self.__baseDate = baseDate

        # 计算当日涨幅需要前一日的数据
        if isinstance(startDate, int) and startDate == 0:
            startDate = -1

        return [startDate, baseDate, max(self.__nDays, n)]

    def onDoneForEngine(self, dataEngine, errorDataEngine):
        """ 返回策略的选股结果，由引擎调用 """
        self._result.insert(0, self.colNames.copy())

        self.__adjust(dataEngine.daysEngine, errorDataEngine.daysEngine)

        return self._result

    def toTrade(self):
        """ 生成策略实盘选股结果到JSON文件，由引擎调用 """
        if self._forTrade and not self._forTradeNoJson:
            self.__toJson()

        return self._resultForTrade

    @property
    def baseDate(self):
        return self.__baseDate

    def getResultCodes(self):
        """
            选股引擎执行完日线选股后，调用此接口获取日线选股的股票代码来进行Tick选股。
            子类可以改写
        """
        return [x[0] for x in self._result]

    #---------- 子类改写 ----------
    def onCodes(self):
        """ 返回策略需要载入的股票代码，指数默认载入。返回None，全部载入。"""
        return None

    def onDaysLoad(self):
        """
            返回策略需要载入日线数据的日期范围
            返回None, None则说明不做日线数据载入。
        """
        return None, None

    def onTicksLoad(self):
        """
            返回策略需要载入分笔数据的日期范围
            返回None, None则说明不做Tick数据载入。
        """
        return None, None

    def onInit(self, dataEngine, errorDataEngine):
        """
            策略初始化，执行完onDaysLoad和onTicksLoad后执行
            @dataEngine：策略由此获取相关载入的信息，比如代码表等等。策略角度，这个是只读数据引擎。模板类也会使用它。
            @errorDataEngine：策略运行时，如果需要载入数据，则需要用此数据引擎，防止@dataEngine被污染。
        """
        pass

    # 日线级别
    def onIndexDays(self, code, df):
        """ 指数日线数据 """
        pass

    def onStockDays(self, code, df):
        """ 个股日线数据 """
        pass

    # Tick级别
    def onStockTicks(self, code, dfs):
        """ 个股分笔数据
            如果先日线选过股后，则载入入选个股的Ticks数据
            @dfs: 2 formats --
                a. 连续模式 ticksDf
                b. 非连续模式 {date: ticksDf}
        """
        pass

    def onDone(self):
        """ 所有数据都推送完毕 """
        pass

    #---------- 子类调用 ----------
    def removeFromResult(self, code):
        pos = None
        for i, group in enumerate(self._result):
            if group[0] == code:
                pos = i
                break

        if pos is not None:
            del self._result[pos]

    def getFromResult(self, code):
        """
            从@self._result得到指定code的一行
        """
        for group in self._result:
            if group[0] == code:
                return group

        return None

    #---------- 私有方法 ----------
    def __adjust(self, daysEngine, errorDaysEngine):
        for i, stock in enumerate(self._result):
            if i == 0: # header
                stock.extend(self.__baseColNames)
                continue

            # 当日价格
            price = self.__stockCurPrice(stock[0], daysEngine)
            stock.append(price)

            #----- 当日涨幅 -----
            # 个股
            increase = self.__stockCurIncrease(stock[0], daysEngine, errorDaysEngine)
            stock.append('') if increase is None else stock.append(increase)
                
            # 指数
            increase = self.__indexCurIncrease(daysEngine.getIndex(stock[0]), daysEngine)
            stock.append('') if increase is None else stock.append(increase)

            #----- @nDays涨幅 -----
            # 个股
            increase = self.__stockIncrease(stock[0], daysEngine)
            stock.append('') if increase is None else stock.append(increase)
                
            # 指数
            increase = self.__indexIncrease(daysEngine.getIndex(stock[0]), daysEngine)
            stock.append('') if increase is None else stock.append(increase)

            # 流通市值
            floatMarketValue = self.__floatMarketValue(stock[0], daysEngine)
            stock.append('') if floatMarketValue is None else stock.append(floatMarketValue)

    def __getTDays(self, daysEngine):
        """ @return: base tDay, start tDay, end tDay in @nDays """
        baseDay = daysEngine.tDaysOffset(self.__baseDate, 0)

        # get start date and end date for @nDays
        startDate = daysEngine.tDaysOffset(baseDay, 1)
        endDate = daysEngine.tDaysOffset(baseDay, self.__nDays)
        if endDate is None:
            endDate = daysEngine.tLatestDay()

        if startDate is None or endDate is None:
            return None, None, None

        return baseDay, startDate, endDate

    def __maxIncrease(self, code, daysEngine):
        """ @return: nDays内最大涨幅 """

        baseTDay, startTDay, endTDay = self.__getTDays(daysEngine)

        try:
            data = daysEngine.getDataFrame(code)

            # get close at @baseDay
            close = data.ix[baseTDay]['close']

            # get max price in @nDays
            highest = data.ix[startTDay:endTDay]['high'].max()

            increase = (highest - close)*100/close
        except Exception as ex:
            increase = np.nan

        return None if np.isnan(increase) else increase

    def __floatMarketValue(self, code, daysEngine):
        baseDay = daysEngine.tDaysOffset(self.__baseDate, 0)

        data = daysEngine.getDataFrame(code)

        try:
            pos = data.index.get_loc(baseDay)
        except Exception as ex:
            pos = -1

        try:
            # get turn at @baseDay
            turn = data.ix[pos, 'turn']

            # get amount in @baseDay
            amount = data.ix[pos, 'amt']

            marketValue = (amount*100/turn)/10**8
        except Exception as ex:
            marketValue = np.nan

        return None if np.isnan(marketValue) else marketValue

    def __stockMeanIncrease(self, code, daysEngine):
        baseTDay, startTDay, endTDay = self.__getTDays(daysEngine)

        try:
            df = daysEngine.getDataFrame(code)

            # get close at @baseTDay
            close = df.ix[baseTDay, 'close']

            # get mean price in @nDays
            volume = df['volume'][startTDay:endTDay].sum()
            amt = df['amt'][startTDay:endTDay].sum()

            mean = amt/volume

            increase = (mean - close)*100/close
        except Exception as ex:
            increase = np.nan

        return None if np.isnan(increase) else increase

    def __indexMeanIncrease(self, code, daysEngine):
        baseTDay, startTDay, endTDay = self.__getTDays(daysEngine)

        try:
            df = daysEngine.getDataFrame(code)

            # get close at @baseTDay
            close = df.ix[baseTDay, 'close']

            # get mean index in @nDays
            mean = df[['open', 'high', 'low', 'close']][startTDay:endTDay].mean().mean()

            increase = (mean - close)*100/close
        except Exception as ex:
            increase = np.nan

        return None if np.isnan(increase) else increase

    def __toJson(self):
        return

        # file name like '.\Config\Strategy\策略中文名\date.json'

        path = os.getcwd()

        path += '\\Config'
        if not os.path.exists(path):
            os.mkdir(path)

        path = path + '\\Strategy'
        if not os.path.exists(path):
            os.mkdir(path)

        path = path + '\\' + self.chName
        if not os.path.exists(path):
            os.mkdir(path)

        date = self._resultForTrade['date']
        fileName = path + '\\' + date + '.json'
        with open(fileName, 'w') as f:
            f.write(json.dumps(self._resultForTrade, indent=4))

    def __stockCurIncrease(self, code, daysEngine, errorDaysEngine):
        """ 股票当日涨幅 """

        baseDay = daysEngine.tDaysOffset(self.__baseDate, 0)

        try:
            df = daysEngine.getDataFrame(code)
            if df.shape[0] == 1:
                errorDaysEngine.loadCode(code, [baseDay, -1])
                df = errorDaysEngine.getDataFrame(code)

            # get close at @baseTDay
            close = df.ix[baseDay, 'close']

            # previous close
            baseDayPos = df.index.get_loc(baseDay)
            preClose = df.ix[baseDayPos - 1, 'close']

            increase = (close - preClose)*100/preClose

        except Exception as ex:
            increase = np.nan

        return None if np.isnan(increase) else increase

    def __stockCurPrice(self, code, daysEngine):
        """ 股票当日价格 """

        baseDay = daysEngine.tDaysOffset(self.__baseDate, 0)

        try:
            df = daysEngine.getDataFrame(code)

            # get close at @baseDay
            price = df.ix[baseDay, 'close']

        except Exception as ex:
            # 股票@baseDay停牌，获取向前最靠近@baseDay交易日的收盘价
            # !!!当日涨幅不做类似处理，这样根据当日涨幅就知道当日有没有停牌
            try:
                df = df[df.index[0]:baseDay]
                price = df.ix[-1, 'close']
            except Exception as ex:
                price = np.nan

        return None if np.isnan(price) else price

    def __indexCurIncrease(self, code, daysEngine):
        """ 指数当日涨幅 """

        baseDay = daysEngine.tDaysOffset(self.__baseDate, 0)

        try:
            df = daysEngine.getDataFrame(code)

            # get close at @baseTDay
            close = df.ix[baseDay, 'close']

            # previous close
            preDay = daysEngine.tDaysOffset(baseDay, -1)
            preClose = df.ix[preDay, 'close']

            increase = (close - preClose)*100/preClose
        except Exception as ex:
            increase = np.nan

        return None if np.isnan(increase) else increase

    def __stockIncrease(self, code, daysEngine):
        """ 股票@__nDays涨幅
            若股票@__nDays内停牌，则可能会导致数据缺失
        """
        baseTDay, startTDay, endTDay = self.__getTDays(daysEngine)

        try:
            df = daysEngine.getDataFrame(code)

            # get close at @baseTDay
            close = df.ix[baseTDay, 'close']

            # get close after @nDays
            nDaysClose = df.ix[endTDay, 'close']

            increase = (nDaysClose - close)*100/close
        except Exception as ex:
            increase = np.nan

        return None if np.isnan(increase) else increase

    def __indexIncrease(self, code, daysEngine):
        """ 指数@__nDays涨幅 """

        baseTDay, startTDay, endTDay = self.__getTDays(daysEngine)

        try:
            df = daysEngine.getDataFrame(code)

            # get close at @baseTDay
            close = df.ix[baseTDay, 'close']

            # get close after @nDays
            nDaysClose = df.ix[endTDay, 'close']

            increase = (nDaysClose - close)*100/close
        except Exception as ex:
            increase = np.nan

        return None if np.isnan(increase) else increase
