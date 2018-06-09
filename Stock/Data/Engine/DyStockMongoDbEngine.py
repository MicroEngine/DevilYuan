import pymongo
import pandas as pd
from time import sleep

from DyCommon.DyCommon import *
from ...Common.DyStockCommon import *


class DyStockMongoDbEngine(object):
    host = 'localhost'
    port = 27017

    stockTicksDb = 'stockTicksDb' # 股票分笔数据

    # default DB for Wind Data Source
    stockCommonDb = 'stockCommonDb'
    tradeDayTableName = "tradeDayTable"
    codeTableName = "codeTable"

    stockDaysDb = 'stockDaysDb' # 股票日线行情数据

    # DB for TuShare Data Source
    stockCommonDbTuShare = 'stockCommonDbTuShare'
    tradeDayTableNameTuShare = "tradeDayTableTuShare"
    codeTableNameTuShare = "codeTableTuShare"

    stockDaysDbTuShare = 'stockDaysDbTuShare' # 股票日线行情数据
    

    # 板块股票代码表，一个日期对应一张表
    sectorCodeDbMap = {DyStockCommon.sz50Index: 'sz50CodeTableDb',
                       DyStockCommon.hs300Index: 'hs300CodeTableDb',
                       DyStockCommon.zz500Index: 'zz500CodeTableDb'
                       }

    
    def __init__(self, info):
        self._info = info

        self._client = pymongo.MongoClient(self.host, self.port)

    def _getTradeDayTableCollection(self):
        if 'Wind' in DyStockCommon.defaultHistDaysDataSource:
            collection = self._client[self.stockCommonDb][self.tradeDayTableName]
        else:
            collection = self._client[self.stockCommonDbTuShare][self.tradeDayTableNameTuShare]

        return collection

    def _getCodeTableCollection(self):
        if 'Wind' in DyStockCommon.defaultHistDaysDataSource:
            collection = self._client[self.stockCommonDb][self.codeTableName]
        else:
            collection = self._client[self.stockCommonDbTuShare][self.codeTableNameTuShare]

        return collection

    def _getStockDaysDb(self):
        if 'Wind' in DyStockCommon.defaultHistDaysDataSource:
            db = self._client[self.stockDaysDb]
        else:
            db = self._client[self.stockDaysDbTuShare]

        return db

    def _deleteTicks(self, code, date):
        collection = self._client[self.stockTicksDb][code]

        dateStart = datetime.strptime(date, '%Y-%m-%d')
        dateEnd = datetime.strptime(date + ' 23:00:00', '%Y-%m-%d %H:%M:%S')

        flt = {'datetime':{'$gt':dateStart,
                        '$lt':dateEnd}}

        try:
            collection.delete_many(flt)
        except Exception as ex:
            self._info.print("删除Tick数据[{0},{1}]引发MongoDB异常:{2}".format(code, date, str(ex) + ', ' + str(ex.details)), DyLogData.error)

            return False

        return True

    def _findTicks(self, code, startDate, endDate):
        collection = self._client[self.stockTicksDb][code]

        dateStart = datetime.strptime(startDate, '%Y-%m-%d')
        dateEnd = datetime.strptime(endDate + ' 23:00:00', '%Y-%m-%d %H:%M:%S')

        flt = {'datetime':{'$gt':dateStart,
                        '$lt':dateEnd}}

        try:
            cursor = collection.find(flt)
        except Exception as ex:
            self._info.print("MongoDB Exception({0}): find ticks for {1} at {2}".format(str(ex) + ', ' + str(ex.details), code, date),
                             DyLogData.error)
            return None

        return cursor

    def _findTradeDays(self, startDate=None, endDate=None):
        collection = self._getTradeDayTableCollection()

        if startDate is None:
            flt = None
        else:
            dateStart = datetime.strptime(startDate, '%Y-%m-%d')
            dateEnd = datetime.strptime(endDate + ' 23:00:00', '%Y-%m-%d %H:%M:%S')

            flt = {'datetime':{'$gte':dateStart,
                               '$lt':dateEnd}}

        try:
            cursor = collection.find(flt)
        except Exception as ex:
            self._info.print("MongoDB Exception({0}): find TradeDays[{1}, {2}]".format(str(ex) + ', ' + str(ex.details), startDate, endDate),
                             DyLogData.error)
            return None

        return cursor
        
    def _getTradeDaysByRelativeNegative(self, baseDate, n):
        
        baseDateSave = baseDate
        nSave = n

        # always get 0 offset trade day
        baseDate = self._getTradeDaysByRelativeZero(baseDate)
        if baseDate is None: return None

        # find forward n trade days
        collection = self._getTradeDayTableCollection()

        flt = {'datetime':{'$lt':baseDate[0]['datetime']}}

        try:
            cursor = collection.find(flt).sort('datetime', pymongo.DESCENDING)
        except Exception as ex:
            self._info.print("MongoDB Exception({0}): @_getTradeDaysByRelativeNegative({1}, {2})".format(str(ex) + ', ' + str(ex.details), baseDateSave, nSave),
                             DyLogData.error)
            return None

        dates = [baseDate[0]]
        for d in cursor:
            if d['tradeDay']:
                dates.append(d)

                n += 1
                if n == 0:
                    return dates

        self._info.print("数据库里没有{0}向前{1}个交易日的日期数据".format(baseDateSave, abs(nSave)),
                             DyLogData.error)
        return None

    def _getTradeDaysByRelativeZero(self, baseDate):
        """ 基准日期向前找到第一个交易日 """

        baseDateSave = baseDate

        collection = self._getTradeDayTableCollection()

        baseDate = datetime.strptime(baseDate, '%Y-%m-%d')
        flt = {'datetime':{'$lte':baseDate}}

        try:
            cursor = collection.find(flt).sort('datetime', pymongo.DESCENDING)
        except Exception as ex:
            self._info.print("MongoDB Exception({0}): @_getTradeDaysByRelativeZero({1})".format(str(ex) + ', ' + str(ex.details), baseDateSave),
                             DyLogData.error)
            return None

        for d in cursor:
            if d['tradeDay']:
                return [d]

        return None

    def _getTradeDaysByRelativePositive(self, baseDate, n):

        baseDateSave = baseDate
        nSave = n

        # always get 0 offset trade day
        baseDate = self._getTradeDaysByRelativeZero(baseDate)
        if baseDate is None: return None

        # find backward n trade days
        collection = self._getTradeDayTableCollection()

        flt = {'datetime': {'$gt': baseDate[0]['datetime']}}

        try:
            cursor = collection.find(flt).sort('datetime', pymongo.ASCENDING)
        except Exception as ex:
            self._info.print("MongoDB Exception({0}): @_getTradeDaysByRelativePositive({1}, {2})".format(str(ex) + ', ' + str(ex.details), baseDateSave, nSave),
                             DyLogData.error)
            return None

        dates = [baseDate[0]]
        for d in cursor:
            if d['tradeDay']:
                dates.append(d)

                n -= 1
                if n == 0:
                    return dates

        # 如果数据库里的最新日期不是今日，提醒更新数据, 并返回None
        date = self.getDaysLatestDate()
        if date is not None:
            now = datetime.now()
            if now > datetime(now.year, now.month, now.day, 18, 0, 0) and DyTime.dateCmp(date['datetime'], now) != 0:
                self._info.print("数据库里的最新日期不是今日, 请更新历史日线数据", DyLogData.error)

                return None

        return dates

    def _findOneCodeDays(self, code, startDate, endDate, name=None):
        collection = self._getStockDaysDb()[code]

        dateStart = datetime.strptime(startDate, '%Y-%m-%d')
        dateEnd = datetime.strptime(endDate + ' 23:00:00', '%Y-%m-%d %H:%M:%S')

        flt = {'datetime':{'$gte':dateStart,
                           '$lt':dateEnd}}

        try:
            cursor = collection.find(flt)
        except Exception as ex:
            self._info.print("MongoDB Exception({0}): 查找{1}:{2}, [{3}, {4}]日线数据".format(str(ex) + ', ' + str(ex.details),
                                                                                        code, name,
                                                                                        startDate, endDate),
                             DyLogData.error)
            return None

        return cursor

    def _getCodeDay(self, code, baseDate, name=None):
        """ 得到个股的当日交易日, 向前贪婪 """
        collection = self._getStockDaysDb()[code]

        date = datetime.strptime(baseDate + ' 23:00:00', '%Y-%m-%d %H:%M:%S')
        flt = {'datetime': {'$lt': date}}

        sortMode = pymongo.DESCENDING

        try:
            cursor = collection.find(flt).sort('datetime', sortMode).limit(1)
        except Exception as ex:
            self._info.print("MongoDB Exception({0}): @_findOneCodeDaysByZeroRelative{1}:{2}, [{3}, {4}]日线数据".format(str(ex) + ', ' + str(ex.details),
                                                                                                                    code, name,
                                                                                                                    baseDate, n),
                             DyLogData.error)
            return None

        for d in cursor:
            return d['datetime'].strftime('%Y-%m-%d')
        
        return None 

    def _findOneCodeDaysByRelative(self, code, baseDate, n=0, name=None):
        """
            包含当日，也就是说offset 0总是被包含的
        """
        # 获取当日日期
        baseDay = self._getCodeDay(code, baseDate, name)
        if baseDay is None: return None

        collection = self._getStockDaysDb()[code]

        if n <= 0:
            date = datetime.strptime(baseDay + ' 23:00:00', '%Y-%m-%d %H:%M:%S')
            flt = {'datetime':{'$lt':date}}

            sortMode = pymongo.DESCENDING
        else:
            date = datetime.strptime(baseDay, '%Y-%m-%d')
            flt = {'datetime':{'$gte':date}} # ignore baseDate, no matter its in DB or not

            sortMode = pymongo.ASCENDING

        # 向前贪婪
        n = abs(n) + 1

        try:
            cursor = collection.find(flt).sort('datetime', sortMode).limit(n)
        except Exception as ex:
            self._info.print("MongoDB Exception({0}): @_findOneCodeDaysByRelative{1}:{2}, [{3}, {4}]日线数据".format(str(ex) + ', ' + str(ex.details),
                                                                                                                    code, name,
                                                                                                                    baseDate, n),
                             DyLogData.error)
            return None

        # We don't check any thing about if we actually get n days data.
        # The reason is that we don't know future, as well as 何时股票上市
        
        return cursor 

    def _getOneCodeDaysByCursor(self, cursor, indicators):
        try:
            columns = indicators + ['datetime']
            if 'adjfactor' not in columns:
                columns.append('adjfactor')

            df = pd.DataFrame(list(cursor), columns=columns)
            df = df.dropna(axis=1, how='all') # 去除全为NaN的列，比如指数数据，没有'mf_vol'
            df = df.set_index('datetime')

        except Exception as ex:
            return None

        return None if df.empty else df

    def _getOneCodeDaysUnified2(self, code, startDate, endDate, indicators, name=None):
        if isinstance(endDate, int):
            df = self._getOneCodeDaysByRelative(code, indicators, startDate, endDate, name)
        else:
            df = self.getOneCodeDays(code, startDate, endDate, indicators, name)

        return df

    def _getOneCodeDaysUnified3(self, code, startDate, endDate, n, indicators, name=None):
        # 分部分载入
        # front part
        startDateNew, endDateNew = startDate, endDate
        if isinstance(startDate, int):
            startDateNew, endDateNew = endDateNew, startDateNew

        frontDf = self._getOneCodeDaysUnified2(code, startDateNew, endDateNew, indicators, name)
        if frontDf is None: return None

        # back part
        backDf = self._getOneCodeDaysUnified2(code, endDate, n, indicators, name)
        if backDf is None: return None

        # concat front DF and back DF
        df = pd.concat([frontDf, backDf])

        # drop duplicated
        df = df[~df.index.duplicated()]

        return df

    def _getOneCodeDaysByRelative(self, code, indicators, baseDate, n=0, name=None):

        cursor = self._findOneCodeDaysByRelative(code, baseDate, n, name)
        if cursor is None: return None

        return self._getOneCodeDaysByCursor(cursor, indicators)


    # -------------------- 公共接口 --------------------
    def updateDays(self, code, data):
        """ @data: [{row0}, {row1}] """
        collection = self._getStockDaysDb()[code]

        # create index
        try:
            collection.index_information()
        except Exception as ex: # collection or database not existing
            collection.create_index([('datetime', pymongo.ASCENDING)], unique=True)

        # update to DB
        try:
            for doc in data:
                flt = {'datetime': doc['datetime']}
                collection.update_one(flt, {'$set':doc}, upsert=True)
        except Exception as ex:
            self._info.print("更新{0}日线数据到MongoDB异常:{1}".format(code, str(ex) + ', ' + str(ex.details)), DyLogData.error)
            return False

        return True

    def updateTradeDays(self, dates):
        collection = self._getTradeDayTableCollection()

        # create index
        try:
            collection.index_information()
        except Exception as ex: # collection or database not existing
            collection.create_index([('datetime', pymongo.ASCENDING)], unique=True)

        # update into DB
        try:
            for date in dates:
                flt = {'datetime': date['datetime']}
                collection.update_one(flt, {'$set':{'tradeDay': date['tradeDay']}}, upsert=True)

        except Exception as ex:
            self._info.print("更新交易日数据到MongoDB异常:{0}".format(str(ex) + ', ' + str(ex.details)), DyLogData.error)
            return False

        return True

    def updateStockCodes(self, codes):
        collection = self._getCodeTableCollection()

        # create index
        try:
            collection.index_information()
        except Exception as ex: # collection or database not existing
            collection.create_index([('code', pymongo.ASCENDING)], unique=True)

        # update into DB
        try:
            for code in codes:
                flt = {'code': code['code']}
                collection.update_one(flt, {'$set':{'name': code['name']}}, upsert=True)

        except Exception as ex:
            self._info.print("更新股票代码数据到MongoDB异常:{0}".format(str(ex) + ', ' + str(ex.details)), DyLogData.error)
            return False

        return True

    def getOneCodeDays(self, code, startDate, endDate, indicators, name=None):
        """
            通过绝对日期获取个股日线数据
        """
        cursor = self._findOneCodeDays(code, startDate, endDate, name)
        if cursor is None: return None

        return self._getOneCodeDaysByCursor(cursor, indicators)

    def getDays(self, codes, startDate, endDate, indicators):
        """ @codes: [code] or {code:name}
            @return: {code:DF}
        """
        isDict = True if isinstance(codes, dict) else False

        codesDf = {}
        for code in codes:

            name = codes[code] if isDict else None
            df = self.getOneCodeDays(code, startDate, endDate, indicators, name)

            if df:
                codesDf[code] = df

        return codesDf if codesDf else None

    def getAdjFactor(self, code, date, name=None):
        collection = self._getStockDaysDb()[code]

        dateEnd = datetime.strptime(date + ' 23:00:00', '%Y-%m-%d %H:%M:%S')

        flt = {'datetime':{'$lt':dateEnd}}

        try:
            cursor = collection.find(flt).sort('datetime', pymongo.DESCENDING).limit(1)
        except Exception as ex:
            self._info.print("MongoDB 异常({0}): 获取{1}:{2}, {3}复权因子".format(str(ex) + ', ' + str(ex.details),
                                                                                code, name,
                                                                                date),
                             DyLogData.error)
            return None

        # get adjust factor
        for d in cursor:
            return d['adjfactor']

        return None

    def getDaysLatestDate(self):
        """ 获取数据库里交易日数据的最新日期，不是交易日 """

        while True:
            try:
                cursor = self._findTradeDays()
                if cursor is None: return None

                cursor = cursor.sort('datetime', pymongo.DESCENDING).limit(1)

                for d in cursor:
                    return d

                return None

            except Exception as ex:
                self._info.print("MongoDB 异常({0}): 获取最新日期".format(str(ex) + ', ' + str(ex.details)),
                                 DyLogData.error)

                if '无法连接' in str(ex):
                    self._info.print('MongoDB正在启动, 等待60s后重试...')
                                
                    sleep(60)
                    continue

                return None

    def getDaysLatestTradeDay(self):
        """ 获取数据库里交易日数据的最新交易日 """
        cursor = self._findTradeDays()
        if cursor is None: return None

        cursor = cursor.sort('datetime', pymongo.DESCENDING)

        for d in cursor:
            if d['tradeDay']:
                return d

        return None

    def getOneCodeDaysUnified(self, code, dates, indicators, name=None):
        """
            获取个股日线数据的统一接口
        """
        if len(dates) == 2:
            df = self._getOneCodeDaysUnified2(code, dates[0], dates[1], indicators, name)
        else:
            df = self._getOneCodeDaysUnified3(code, dates[0], dates[1], dates[2], indicators, name)
        
        if df is not None:
            df = df.sort_index()

        return df

    def codeTDayOffset(self, code, baseDate, n=0, strict=True):
        """
            获取基于个股偏移的交易日
        """
        cursor = self._findOneCodeDaysByRelative(code, baseDate, n)
        if cursor is None: return None

        df = self._getOneCodeDaysByCursor(cursor, [])
        if df is None: return None

        # 保留查找的次序，也就是说n<=0是降序，反之是升序

        if strict:
            if df.shape[0] != abs(n) + 1:
                return None

        return None if df.empty else df.index[-1].strftime("%Y-%m-%d")

    def getTicks(self, code, startDate, endDate):
        cursor = self._findTicks(code, startDate, endDate)
        if cursor is None: return None

        try:
            # !!!实盘回测引擎将会使用列的次序，所以不要更改
            df = pd.DataFrame(list(cursor), columns=['datetime', 'price', 'volume', 'amount', 'type'])
            df.set_index('datetime', inplace=True)

        except Exception as ex:
            return None

        return None if df.empty else df

    def insertTicks(self, code, date, data):

        collection = self._client[self.stockTicksDb][code]

        # create index
        try:
            collection.index_information()
        except Exception as ex: # collection or database not existing
            collection.create_index([('datetime', pymongo.ASCENDING)], unique=True)

        # insert ticks into DB
        try:
            collection.insert_many(data)
        except Exception as ex:
            self._info.print("插入Tick数据[{0},{1}]到MongoDB异常:{2}".format(code, date, str(ex) + ', ' + str(ex.details)), DyLogData.error)

            # delete documents due to duplicate key error
            if 'duplicate key error' in str(ex.details):
                # Usually it's not happened for new ticks inserting. If happened, it means some wrong at data getting and cleaning from Gateway.
                self._info.print("删除MongoDB里的重复Tick数据[{0},{1}]".format(code, date), DyLogData.warning)

                self._deleteTicks(code, date)

            return False

        return True

    def isTicksExisting(self, code, date):
        cursor = self._findTicks(code, date, date)
        if cursor is None: return False

        if cursor.count() == 0:
            return False

        return True

    def getNotExistingDates(self, code, dates, indicators):
        """ @dates: sorted [date]
            @indicators: [indicator]

            @return: {indicator:[date]}
        """
        if (not dates) or (not indicators):
            return None

        collection = self._getStockDaysDb()[code]

        dateStart = datetime.strptime(dates[0], '%Y-%m-%d')
        dateEnd = datetime.strptime(dates[-1] + ' 23:00:00', '%Y-%m-%d %H:%M:%S')

        flt = {'datetime':{'$gte':dateStart,
                           '$lt':dateEnd}}

        try:
            cursor = collection.find(flt)
        except Exception as ex:
            self._info.print("MongoDB Exception({0}): find existing dates[{1}, {2}] for {3}".format(str(ex) + ', ' + str(ex.details), dates[0], dates[-1], code),
                             DyLogData.error)
            return None

        # assume all not in DB
        data = {x : dates.copy() for x in indicators}
        
        for d in cursor:
            date = datetime.strftime(d['datetime'], '%Y-%m-%d')

            for indicator in d:
                if indicator in data:
                    if date in data[indicator]:
                        # remove existing date
                        data[indicator].remove(date)

                        if not data[indicator]:
                            del data[indicator]
        
        return data if data else None

    def isTradeDaysExisting(self, startDate, endDate):
        cursor = self._findTradeDays(startDate, endDate)
        if cursor is None: return False

        # all dates can be found in DB
        if len(DyTime.getDates(startDate, endDate)) == cursor.count():
            return True

        return False

    def getTradeDaysByRelative(self, baseDate, n):
        """ 从数据库获取相对日期的交易日数据
            @n: 向前或者向后多少个交易日
            @return: [doc of trade day]
        """
        if n > 0:
            tradeDays = self._getTradeDaysByRelativePositive(baseDate, n)
        elif n < 0:
            tradeDays = self._getTradeDaysByRelativeNegative(baseDate, n)
        else:
            tradeDays = self._getTradeDaysByRelativeZero(baseDate)

        if tradeDays is None: return None

        return tradeDays

    def getTradeDaysByAbsolute(self, startDate=None, endDate=None):
        """ 从数据库获取指定日期区间的交易日数据 """
        cursor = self._findTradeDays(startDate, endDate)
        if cursor is None:
            return None

        if startDate is not None:
            # some of dates can not be found in DB
            if len(DyTime.getDates(startDate, endDate)) != cursor.count():
                self._info.print("有些交易日[{0}, {1}]没有在数据库".format(startDate, endDate), DyLogData.error)
                return None

        tradeDays = []
        for d in cursor:
            if d['tradeDay']:
                tradeDays.append(d)

        return tradeDays

    def getStockCodes(self, codes=None):
        # 不载入任何股票
        if codes == []:
            return []

        collection = self._getCodeTableCollection()

        if codes is None:
            flt = None
        else:
            flt = {'code': {'$in': codes}}

        try:
            cursor = collection.find(flt)
        except Exception as ex:
            self._info.print("MongoDB Exception({0}): 查询股票名称表".format(str(ex) + ', ' + str(ex.details)),
                             DyLogData.error)
            return None

        data = []
        for d in cursor:
            data.append(d)

        return data if data else None

    def getStockMarketDate(self, code, name=None):
        """
            获取个股上市日期
            由于数据库的数据限制，有可能是个股数据在数据库里的最早信息
        """
        collection = self._getStockDaysDb()[code]

        flt = {'datetime': {'$lt':datetime.now()}}

        try:
            cursor = collection.find(flt).sort('datetime', pymongo.ASCENDING).limit(1)
        except Exception as ex:
            self._info.print("MongoDB Exception({0}): @getStockMarketDate{1}:{2}, 日线数据".format(str(ex) + ', ' + str(ex.details),
                                                                                                    code, name),
                             DyLogData.error)
            return None

        for d in cursor:
            return d['datetime'].strftime('%Y-%m-%d')
        
        return None

    def getSectorStockCodes(self, date, sectorCode, codes=None):
        # 不载入任何股票
        if codes == []:
            return []

        # find corresponding code table collection of specified date
        collectionNames = self._client[self.sectorCodeDbMap[sectorCode]].collection_names(include_system_collections=False)
        if not collectionNames:
            return []

        collectionNames = sorted(collectionNames)
        for i, date_ in enumerate(collectionNames):
            if date_ > date:
                break
        else:
            i += 1

        collection = collectionNames = self._client[self.sectorCodeDbMap[sectorCode]][collectionNames[i-1]]

        # get code table
        if codes is None:
            flt = None
        else:
            flt = {'code': {'$in': codes}}

        try:
            cursor = collection.find(flt)
        except Exception as ex:
            self._info.print("MongoDB Exception({0}): 查询[{1}]股票名称表".format(str(ex) + ', ' + str(ex.details), DyStockCommon.sectors[sectorCode]),
                             DyLogData.error)
            return None

        data = []
        for d in cursor:
            data.append(d)

        return data if data else None

    def updateSectorStockCodes(self, sectorCode, date, codes):
        collection = self._client[self.sectorCodeDbMap[sectorCode]][date]

        # create index
        try:
            collection.index_information()
        except Exception as ex: # collection or database not existing
            collection.create_index([('code', pymongo.ASCENDING)], unique=True)

        # update into DB
        try:
            for code in codes:
                flt = {'code': code['code']}
                collection.update_one(flt, {'$set': {'name': code['name']}}, upsert=True)

        except Exception as ex:
            self._info.print("更新[{0}]股票代码数据[{1}]到MongoDB异常:{2}".format(DyStockCommon.sectors[sectorCode], date, str(ex) + ', ' + str(ex.details)), DyLogData.error)
            return False

        return True
