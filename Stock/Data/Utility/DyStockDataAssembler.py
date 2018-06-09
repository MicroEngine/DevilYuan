from datetime import datetime, timedelta

import pandas as pd

from .DyStockDataUtility import *


class DyStockDataAssembler(object):
    """
        股票数据组装，主要是从数据引擎里读出数据，做简单的运算。比如，涨幅之类的等等。
        不像DyStockDataUtility会做统计和技术分析的计算
    """
    def getStockIndexMaxAmplitude(daysEngine, dateCodeList, days, backward=True, progress=None):
        """ 最大振幅，含基准日期

            @dateCodeList: [[baseDate, code]]
            @days: [day]
            @backword: 向后还是向前
            @return: [ [ [day1 stock amplitude, day1 index amplitude],  [day2 stock amplitude, day2 index amplitude], ...] ]
        """
        assert(days)

        days.sort() # for max day, and change the sequence in memory

        dateCodeIncreaseList = []
        if progress: progress.init(len(dateCodeList), 100)
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
            if progress: progress.update()

        return dateCodeIncreaseList

    def getStockIndexIncrease(daysEngine, dateCodeList, days, backward=True, progress=None):
        """ @dateCodeList: [[baseDate, code]]
            @days: [day]
            @backword: 向后还是向前
            @return: [ [ [day1 stock increase, day1 index increase],  [day2 stock increase, day2 index increase], ...] ]
        """
        assert(days)

        days.sort() # for max day, and change the sequence in memory

        dateCodeIncreaseList = []
        if progress: progress.init(len(dateCodeList), 100)
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
            if progress: progress.update()

        return dateCodeIncreaseList

    def flatStockIndexIncrease(data, days, backward=True):
        """
            扁平化涨幅数据好插入到table widget
        """
        colNames = []
        for day in days:
            colNames.append((('' if backward else '前') + '{0}日涨幅(%)').format(day))
            colNames.append((('' if backward else '前') + '{0}日指数涨幅(%)').format(day))

        return colNames, DyStockDataAssembler.__flatColData(data)

    def flatStockIndexMaxAmplitude(data, days, backward=True):
        """
            扁平化振幅数据好插入到table widget
        """
        colNames = []
        for day in days:
            colNames.append((('' if backward else '前') + '{0}日最大振幅(%)').format(day))
            colNames.append((('' if backward else '前') + '{0}日指数最大振幅(%)').format(day))

        return colNames, DyStockDataAssembler.__flatColData(data)

    def getStockIndexMaxMinIncrease(daysEngine, dateCodeList, days, backward=True, progress=None):
        """ @dateCodeList: [[baseDate, code]]
            @days: [day]
            @return: [ [ [day1 stock max increase, day1 stock min increase, day1 index max increase, day1 index min increase] ] ]
        """
        assert(days)

        days.sort() # for max day, and change the sequence in memory

        dateCodeIncreaseList = []
        if progress: progress.init(len(dateCodeList), 100)
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
            if progress: progress.update()

        return dateCodeIncreaseList

    def flatStockIndexMaxMinIncrease(data, days, backward=True):
        """
            扁平化涨幅数据好插入到table widget
        """
        colNames = []
        for day in days:
            colNames.append((('' if backward else '前') + '{0}日最大涨幅(%)').format(day))
            colNames.append((('' if backward else '前') + '{0}日最小涨幅(%)').format(day))
            colNames.append((('' if backward else '前') + '{0}日指数最大涨幅(%)').format(day))
            colNames.append((('' if backward else '前') + '{0}日指数最小涨幅(%)').format(day))

        return colNames, DyStockDataAssembler.__flatColData(data)

    def getStockIndexEr(daysEngine, dateCodeList, days, backward=True, progress=None):
        """ 获取股票和指数的效率系数
            @dateCodeList: [[baseDate, code]]
            @days: [day]
            @backword: 向后还是向前
            @return: [ [ [day1 stock ER, day1 index ER],  [day2 stock ER, day2 index ER], ...] ]
        """
        days.sort() # for max day, and change the sequence in memory

        dateCodeErList = []
        if progress:
            progress.init(len(dateCodeList), 100)

        for date, code in dateCodeList:
            if not daysEngine.loadCode(code, [date, days[-1] if backward else -days[-1] - 1]):
                return None

            # stock and index DF
            stockDf = daysEngine.getDataFrame(code)
            indexDf = daysEngine.getDataFrame(daysEngine.getIndex(code))

            stockCloses =  stockDf['close']
            indexCloses =  indexDf['close']

            # loop to calculate ER each day
            dateCodeEr = []
            for day in days:
                # stock
                if backward:
                    s = stockCloses[:day+1]
                else:
                    s = stockCloses[-day-2:-1]

                stockEr, _ = DyStockDataUtility.getVolatilityEfficiencyRatio(s)

                # index
                s = indexCloses[s.index]

                indexEr, _ = DyStockDataUtility.getVolatilityEfficiencyRatio(s)

                dateCodeEr.append([stockEr, indexEr])

            dateCodeErList.append(dateCodeEr)

            if progress:
                progress.update()

        return dateCodeErList

    def flatStockIndexEr(data, days, backward=True):
        """
            扁平化ER数据好插入到table widget
        """
        colNames = []
        for day in days:
            colNames.append((('' if backward else '前') + '{0}日ER').format(day))
            colNames.append((('' if backward else '前') + '{0}日指数ER').format(day))

        return colNames, DyStockDataAssembler.__flatColData(data)

    def getStockIndexVolatility(daysEngine, dateCodeList, days, backward=True, progress=None):
        """
            获取股票和指数的波动率
            @dateCodeList: [[baseDate, code]]
            @days: [day]
            @backword: 向后还是向前
            @return: [ [ [day1 stock volatility, day1 index volatility],  [day2 stock volatility, day2 index volatility], ...] ]
        """
        days.sort() # for max day, and change the sequence in memory

        dateCodeVolatilityList = []
        if progress:
            progress.init(len(dateCodeList), 100)

        for date, code in dateCodeList:
            if not daysEngine.loadCode(code, [date, days[-1] if backward else -days[-1] - 1]):
                return None

            # stock and index DF
            stockDf = daysEngine.getDataFrame(code)
            indexDf = daysEngine.getDataFrame(daysEngine.getIndex(code))

            stockVolatility = DyStockDataUtility.getVolatility(stockDf)
            indexVolatility = DyStockDataUtility.getVolatility(indexDf)

            # loop to calculate volatility each day
            dateCodeVolatility = []
            for day in days:
                # stock volatility
                if backward:
                    v = stockVolatility[:day]
                else:
                    v = stockVolatility[-day-1:-1]

                # 计算波动率的均值，标准差，偏度和峰度
                stockMean = v.mean()
                stockStd = v.std()
                stockSkew = v.skew()
                stockKurt = v.kurt()

                # index volatility
                v = indexVolatility[v.index]

                # 计算波动率的均值，标准差，偏度和峰度
                indexMean = v.mean()
                indexStd = v.std()
                indexSkew = v.skew()
                indexKurt = v.kurt()

                dateCodeVolatility.append([stockMean, stockStd, stockSkew, stockKurt, indexMean, indexStd, indexSkew, indexKurt])

            dateCodeVolatilityList.append(dateCodeVolatility)

            if progress:
                progress.update()

        return dateCodeVolatilityList

    def flatStockIndexVolatility(data, days, backward=True):
        """
            扁平化波动率数据好插入到table widget
        """
        colNames = []
        for day in days:
            colNames.append((('' if backward else '前') + '{0}日波动率均值(%)').format(day))
            colNames.append((('' if backward else '前') + '{0}日波动率标准差').format(day))
            colNames.append((('' if backward else '前') + '{0}日波动率偏度').format(day))
            colNames.append((('' if backward else '前') + '{0}日波动率峰度').format(day))

            colNames.append((('' if backward else '前') + '{0}日指数波动率均值(%)').format(day))
            colNames.append((('' if backward else '前') + '{0}日指数波动率标准差').format(day))
            colNames.append((('' if backward else '前') + '{0}日指数波动率偏度').format(day))
            colNames.append((('' if backward else '前') + '{0}日指数波动率峰度').format(day))

        return colNames, DyStockDataAssembler.__flatColData(data)

    def getStockIndexDayReturnCorr(daysEngine, dateCodeList, days, backward=True, progress=None):
        """
            获取股票和指数的日收益率相关系数
            采用的是个股相对载入数据方式
            @dateCodeList: [[baseDate, code]]
            @days: [day]
            @backword: 向后还是向前
            @return: [column name], [[day1 Correlation Coefficient, day2 Correlation Coefficient, ...]]
        """
        assert(days)

        days.sort() # for max day, and change the sequence in memory

        # header
        colNames = []
        for day in days:
            colNames.append((('' if backward else '前') + '{0}日DayReturn大盘相关系数').format(day))

        # rows
        corrRows = []
        if progress:
            progress.init(len(dateCodeList), 100)

        for date, code in dateCodeList:
            corrRow = []
            for day in days:
                if not daysEngine.loadCode(code, [date, day if backward else (-day - 1)]):
                    return None, None

                # stock and index DF
                stockDf = daysEngine.getDataFrame(code)
                indexDf = daysEngine.getDataFrame(daysEngine.getIndex(code))

                stockReturns = stockDf['close'].pct_change()
                indexReturns = indexDf['close'].pct_change()

                if not backward: # 剔除当日收益率
                    stockReturns = stockReturns[:-1]

                # 对齐
                indexReturns = indexReturns[stockReturns.index]

                corr = stockReturns.corr(indexReturns)
                corrRow.append(corr)

            corrRows.append(corrRow)

            if progress:
                progress.update()

        return colNames, corrRows

    def getStockEtfMinuteIncrease(dataEngine, dateCodeList, mins, progress=None):
        """ @dateCodeList: [[baseDate, code]]
            @mins: [min]
            @return: [ [ [min1 stock increase, min1 ETF increase],  [min2 stock increase, min2 ETF increase] ], ...] ]
        """
        def _getIncreases(code, date):
            try:
                # preClose
                daysEngine.loadCode(code, [date, -1], latestAdjFactorInDb=False)
                df = daysEngine.getDataFrame(code)
                preClose = df.ix[-2, 'close']

                # ticks of date
                ticksEngine.loadCode(code, date)
                df = ticksEngine.getDataFrame(code)
                prices = df['price']

                prices = [prices[:' '.join([date, x])][-1] for x in newMins]

                return [(x - preClose)/preClose*100 for x in prices]
            except:
                return [None]*len(mins)

        daysEngine = dataEngine.daysEngine
        ticksEngine = dataEngine.ticksEngine
        mins.sort()

        morningStart = datetime(2000, 1, 1, 9, 30, 0)
        newMins = [morningStart + timedelta(minutes=x) for x in mins]
        newMins = [x.strftime('%H:%M:%S') for x in newMins]
        
        if progress is not None:
            progress.init(len(dateCodeList), 100)

        retData = []
        for date, code in dateCodeList:
            stocks = _getIncreases(code, date)
            etfs = _getIncreases(DyStockCommon.getEtf(code), date)

            retData.append([[x, y] for x, y in zip(stocks, etfs)])

            if progress is not None:
                progress.update()

        return retData

    def flatStockEtfMinuteIncrease(data, mins):
        """
            扁平化涨幅数据好插入到table widget
        """
        colNames = []
        for min in mins:
            colNames.append('{0}分涨幅(%)'.format(min))
            colNames.append('{0}分ETF涨幅(%)'.format(min))

        return colNames, DyStockDataAssembler.__flatColData(data)

    def getStockIndexOpenIncrease(daysEngine, dateCodeList, progress=None):
        """ @dateCodeList: [[baseDate, code]]
            @return: [ [ [stock open increase, index open increase] ], ...] ]
        """
        def _getIncrease(code, date):
            try:
                # preClose
                daysEngine.loadCode(code, [date, -1], latestAdjFactorInDb=False)
                df = daysEngine.getDataFrame(code)

                preClose = df.ix[-2, 'close']
                open = df.ix[-1, 'open']
                
                return (open - preClose)/preClose*100
            except:
                return None

        if progress is not None:
            progress.init(len(dateCodeList), 100)

        retData = []
        for date, code in dateCodeList:
            stock = _getIncrease(code, date)
            index = _getIncrease(DyStockCommon.getIndex(code), date)

            retData.append([[stock, index]])

            if progress is not None:
                progress.update()

        return retData

    def flatStockIndexOpenIncrease(data):
        """
            扁平化涨幅数据好插入到table widget
        """
        colNames = ['开盘涨幅(%)', '指数开盘涨幅(%)']

        return colNames, DyStockDataAssembler.__flatColData(data)

    def getStockOpenGap(daysEngine, dateCodeList, days, backward=True, progress=None):
        """
            获取股票的开盘缺口。若T日没有缺口，则是None。
            @dateCodeList: [[baseDate, code]]
            @days: [day]
            @backword: 向后还是向前
            @return: [ [ [day1 stock open gap],  [day2 stock open gap], ...] ]
        """
        days.sort() # for max day, and change the sequence in memory
        
        if progress:
            progress.init(len(dateCodeList), 100)

        rows = []
        for date, code in dateCodeList:
            if not daysEngine.loadCode(code, [date, days[-1] if backward else -days[-1] - 1]):
                return None

            df = daysEngine.getDataFrame(code)

            # loop to calculate open gap each day
            row = []
            for day in days:
                if not backward:
                    day = -day - 1

                try:
                    preHigh, preLow, preClose = df.ix[day - 1, ['high', 'low', 'close']].values.tolist()
                    open = df.ix[day, 'open']

                    if open > preHigh:
                        gap = (open - preHigh)/preClose * 100
                    elif open < preLow:
                        gap = (open - preLow)/preClose * 100
                    else:
                        gap = None
                except:
                    gap = None

                row.append([gap])

            rows.append(row)

            if progress:
                progress.update()

        return rows

    def __flatColData(data):
        """
            扁平化列数据好插入到table widget
        """
        colData = []
        for row in data:
            rowData = []
            for cell in row:
                rowData.extend(cell)

            colData.append(rowData)

        return colData

    def flatStockOpenGap(data, days, backward=True):
        """
            扁平化开盘缺口数据好插入到table widget
        """
        colNames = []
        for day in days:
            colNames.append((('' if backward else '前') + '{0}日开盘缺口').format(day))

        return colNames, DyStockDataAssembler.__flatColData(data)
