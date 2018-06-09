import struct
from datetime import *


class DyStockSelectEventHandType:
    engine = 0
    viewer = 1
    other = 2

    nbr = 3


class DyStockSelectCommon:
    # 打开选股引擎的异常捕捉
    enableSelectEngineException = False

    def getStockIndexMaxAmplitude(daysEngine, dateCodeList, days, backward=True):
        """ 最大振幅，含基准日期

            @dateCodeList: [[baseDate, code]]
            @days: [day]
            @backword: 向后还是向前
            @return: [ [ [day1 stock amplitude, day1 index amplitude],  [day2 stock amplitude, day2 index amplitude], ...] ]
        """
        assert(days)

        days.sort() # for max day, and change the sequence in memory

        dateCodeIncreaseList = []
        for date, code in dateCodeList:
            if not daysEngine.load([date, days[-1] if backward else -days[-1]], codes=[code]):
                return None

            # stock and index DF
            stockDf = daysEngine.getDataFrame(code)
            indexDf = daysEngine.getDataFrame(daysEngine.getIndex(code))

            # close of base date
            baseDay = daysEngine.tDaysOffset(date)

            # 股票@baseDay停牌或者整个区间停牌
            stockBaseDayClose = None if stockDf is None else stockDf.ix[0, 'close'] if backward else stockDf.ix[-1, 'close']
            indexBaseDayClose = indexDf.ix[baseDay, 'close']

            # loop to calculate amplitude each day
            dateCodeIncrease = []
            for day in days:
                tDay = daysEngine.tDaysOffset(baseDay, day if backward else -day)

                # stock and index amplitude
                try:
                    idxmax, idxmin = (stockDf.ix[baseDay:tDay, 'high'].idxmax(), stockDf.ix[baseDay:tDay, 'low'].idxmin()) if backward else (stockDf.ix[tDay:baseDay, 'high'].idxmax(), stockDf.ix[tDay:baseDay, 'low'].idxmin())
                    high, low = stockDf.ix[idxmax, 'high'], stockDf.ix[idxmin, 'low']
                    start, end = (low, high) if idxmax >= idxmin else (high, low)

                    stockIncrease = (end - start)*100/start
                except Exception as ex:
                    stockIncrease = ''

                try:
                    idxmax, idxmin = (indexDf.ix[baseDay:tDay, 'high'].idxmax(), indexDf.ix[baseDay:tDay, 'low'].idxmin()) if backward else (indexDf.ix[tDay:baseDay, 'high'].idxmax(), indexDf.ix[tDay:baseDay, 'low'].idxmin())
                    high, low = indexDf.ix[idxmax, 'high'], indexDf.ix[idxmin, 'low']
                    start, end = (low, high) if idxmax >= idxmin else (high, low)

                    indexIncrease = (end - start)*100/start
                except Exception as ex:
                    indexIncrease = ''

                dateCodeIncrease.append([stockIncrease, indexIncrease])

            dateCodeIncreaseList.append(dateCodeIncrease)

        return dateCodeIncreaseList

    def getStockIndexIncrease(daysEngine, dateCodeList, days, backward=True):
        """ @dateCodeList: [[baseDate, code]]
            @days: [day]
            @backword: 向后还是向前
            @return: [ [ [day1 stock increase, day1 index increase],  [day2 stock increase, day2 index increase], ...] ]
        """
        assert(days)

        days.sort() # for max day, and change the sequence in memory

        dateCodeIncreaseList = []
        for date, code in dateCodeList:
            if not daysEngine.load([date, days[-1] if backward else -days[-1]], codes=[code]):
                return None

            # stock and index DF
            stockDf = daysEngine.getDataFrame(code)
            indexDf = daysEngine.getDataFrame(daysEngine.getIndex(code))

            # close of base date
            baseDay = daysEngine.tDaysOffset(date)

            stockBaseDayClose = None if stockDf is None else stockDf.ix[0, 'close'] if backward else stockDf.ix[-1, 'close']
            indexBaseDayClose = indexDf.ix[baseDay, 'close']

            # loop to calculate increase each day
            dateCodeIncrease = []
            for day in days:
                tDay = daysEngine.tDaysOffset(baseDay, day if backward else -day)

                # stock and index increase
                try:
                    # 考虑正好@tDay停牌，则取@tDay ~ @baseDay的涨幅
                    startClose, endClose = (stockBaseDayClose, stockDf.ix[baseDay:tDay, 'close'].ix[-1, 'close']) if backward else (stockDf.ix[tDay:baseDay, 'close'].ix[0, 'close'], stockBaseDayClose)
                    stockIncrease = (endClose - startClose)*100/startClose
                except Exception as ex:
                    stockIncrease = ''

                try:
                    startClose, endClose = (indexBaseDayClose, indexDf.ix[tDay, 'close']) if backward else (indexDf.ix[tDay, 'close'], indexBaseDayClose)
                    indexIncrease = (endClose - startClose)*100/startClose
                except Exception as ex:
                    indexIncrease = ''

                dateCodeIncrease.append([stockIncrease, indexIncrease])

            dateCodeIncreaseList.append(dateCodeIncrease)

        return dateCodeIncreaseList

    def flatStockIndexIncrease(dateCodeIncreaseList, days, backward=True):
        """
            扁平化涨幅数据好插入到table widget
        """
        colNames = []
        for day in days:
            colNames.append((('' if backward else '前') + '{0}日涨幅(%)').format(day))
            colNames.append((('' if backward else '前') + '{0}日指数涨幅(%)').format(day))

        colData = []
        for dateCodeIncrease in dateCodeIncreaseList:
            rowData = []
            for dayDateCodeIncrease in dateCodeIncrease:
                rowData.extend(dayDateCodeIncrease)

            colData.append(rowData)

        return colNames, colData

    def flatStockIndexMaxAmplitude(dateCodeIncreaseList, days, backward=True):
        """
            扁平化振幅数据好插入到table widget
        """
        colNames = []
        for day in days:
            colNames.append((('' if backward else '前') + '{0}日最大振幅(%)').format(day))
            colNames.append((('' if backward else '前') + '{0}日指数最大振幅(%)').format(day))

        colData = []
        for dateCodeIncrease in dateCodeIncreaseList:
            rowData = []
            for dayDateCodeIncrease in dateCodeIncrease:
                rowData.extend(dayDateCodeIncrease)

            colData.append(rowData)

        return colNames, colData

    def export2Jqka(path, stocks):
        if not stocks: return

        now = datetime.now().strftime("%Y_%m_%d %H-%M-%S")

        file = path + "\\" + now + ".sel"
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

    def getStockIndexMaxMinIncrease(daysEngine, dateCodeList, days, backward=True):
        """ @dateCodeList: [[baseDate, code]]
            @days: [day]
            @return: [ [ [day1 stock max increase, day1 stock min increase, day1 index max increase, day1 index min increase] ] ]
        """
        assert(days)

        days.sort() # for max day, and change the sequence in memory

        dateCodeIncreaseList = []
        for date, code in dateCodeList:
            if not daysEngine.load([date, days[-1] if backward else -days[-1]], codes=[code]):
                return None

            # stock and index DF
            stockDf = daysEngine.getDataFrame(code)
            indexDf = daysEngine.getDataFrame(daysEngine.getIndex(code))

            # close of base date
            baseDay = daysEngine.tDaysOffset(date)

            stockBaseDayClose = None if stockDf is None else stockDf.ix[0, 'close'] if backward else stockDf.ix[-1, 'close']
            indexBaseDayClose = indexDf.ix[baseDay, 'close']

            # loop to calculate increase each day
            dateCodeIncrease = []
            for day in days:
                tDay = daysEngine.tDaysOffset(baseDay, day if backward else -day)
                nextDay = daysEngine.tDaysOffset(baseDay if backward else tDay, 1)

                # stock max&min increase
                try:
                    start, end = (stockBaseDayClose, stockDf.ix[nextDay:tDay, 'high'].max()) if backward else (stockDf.ix[tDay, 'close'], stockDf.ix[nextDay:baseDay, 'high'].max())
                    stockMaxIncrease = (end - start)*100/start
                except Exception as ex:
                    stockMaxIncrease = ''

                try:
                    start, end = (stockBaseDayClose, stockDf.ix[nextDay:tDay, 'low'].min()) if backward else (stockDf.ix[tDay, 'close'], stockDf.ix[nextDay:baseDay, 'low'].min())
                    stockMinIncrease = (end - start)*100/start
                except Exception as ex:
                    stockMinIncrease = ''

                # index max&min increase
                try:
                    start, end = (indexBaseDayClose, indexDf.ix[nextDay:tDay, 'high'].max()) if backward else (indexDf.ix[tDay, 'close'], indexDf.ix[nextDay:baseDay, 'high'].max())
                    indexMaxIncrease = (end - start)*100/start
                except Exception as ex:
                    indexMaxIncrease = ''

                try:
                    start, end = (indexBaseDayClose, indexDf.ix[nextDay:tDay, 'low'].min()) if backward else (indexDf.ix[tDay, 'close'], indexDf.ix[nextDay:baseDay, 'low'].min())
                    indexMinIncrease = (end - start)*100/start
                except Exception as ex:
                    indexMinIncrease = ''

                dateCodeIncrease.append([stockMaxIncrease, stockMinIncrease, indexMaxIncrease, indexMinIncrease])

            dateCodeIncreaseList.append(dateCodeIncrease)

        return dateCodeIncreaseList

    def flatStockIndexMaxMinIncrease(dateCodeIncreaseList, days, backward=True):
        """
            扁平化涨幅数据好插入到table widget
        """
        colNames = []
        for day in days:
            colNames.append((('' if backward else '前') + '{0}日最大涨幅(%)').format(day))
            colNames.append((('' if backward else '前') + '{0}日最小涨幅(%)').format(day))
            colNames.append((('' if backward else '前') + '{0}日指数最大涨幅(%)').format(day))
            colNames.append((('' if backward else '前') + '{0}日指数最小涨幅(%)').format(day))

        colData = []
        for dateCodeIncrease in dateCodeIncreaseList:
            rowData = []
            for dayDateCodeIncrease in dateCodeIncrease:
                rowData.extend(dayDateCodeIncrease)

            colData.append(rowData)

        return colNames, colData

