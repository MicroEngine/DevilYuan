import math
from collections import OrderedDict
import itertools

import pandas as pd
import talib
import numpy as np

from DyCommon.DyCommon import *
from ...Common.DyStockCommon import *


class DyStockDataUtility(object):
    """ 股票数据工具箱，主要用来计算技术指标和统计相关的数据 """

    def getMinBars(df, m=1):
        """
            合成分钟K线
            @m: 几分钟
        """
        # 合成分钟Bar, 右闭合
        # 缺失的Bar设为NaN
        df = df.resample(str(m) + 'min', closed='right', label='right')[['price', 'volume']].agg(OrderedDict([('price', 'ohlc'), ('volume', 'sum')]))
        df.dropna(inplace=True) # drop缺失的Bars

        return df

    def getMas(df, mas, dropna=True, indicator='close'):
        """
            获取周期内的指标均值
            @mas: [5, 10, 20, 30, 60, ...]
        """
        if df is None:
            return pd.DataFrame([])

        means = []
        for ma in mas:
            mean = df[indicator].rolling(center=False, window=ma).mean() # new method at v0.18.0
            mean.name = 'ma%s'%ma
            means.append(mean)

        df = pd.DataFrame(means).T
        
        return df.dropna() if dropna else df

    def getDealMas(df, mas, dropna=True):
        """
            获取周期内的成交均价
            @mas: [5, 10, 20, 30, 60, ...]
        """
        if df is None:
            return pd.DataFrame([])

        means = []
        for ma in mas:
            amtSum = df['amt'].rolling(center=False, window=ma).sum()
            volSum = df['volume'].rolling(center=False, window=ma).sum()

            mean = amtSum/volSum

            mean.name = 'ma%s'%ma
            means.append(mean)

        df = pd.DataFrame(means).T
        
        return df.dropna() if dropna else df

    def getKamas(df, mas, dropna=True):
        """
            获取周期内的考夫曼均价
            @mas: [5, 10, 20, 30, 60, ...]
        """
        if df is None:
            return pd.DataFrame([])

        means = {}
        names = []
        for ma in mas:
            mean = talib.KAMA(df['close'].values, ma)
            name = 'kama%s'%ma
            
            means[name] = mean
            names.append(name)

        df = pd.DataFrame(means, index=df.index, columns=names)

        return df.dropna() if dropna else df

    def getAtrRatio(df, period=14):
        """
            平均波动率：ATR(14)/MA(14)
        """
        highs = df['high']
        lows = df['low']
        closes = df['close']

        atr = talib.ATR(highs, lows, closes, timeperiod=period)
        ma = talib.MA(closes, timeperiod=period)

        volatility = atr/ma

        s = pd.Series(volatility, index=df.index, name='volatility').dropna()

        return s

    def getVolatilityEfficiencyRatio(series):
        """
            获取波动效率[-1, 1]，正：上涨，负：下跌
            @return: 波动效率，每次波动占比
        """
        # 趋势和总波动
        direction = series[-1] - series[0]

        # 绝对波动
        change = series - series.shift(1)
        volatility = abs(change).sum()

        #　效率系数
        efficiencyRatio = direction/volatility

        # 波动比(每天波动占总体波动多少)
        volatilityRatio = abs(change)/abs(direction)

        return efficiencyRatio, volatilityRatio.dropna()

    def getAreaRatio(df):
        """
            获取DF的面积比(%)
            @return: 面积比
        """
        high = df['high'].max()
        low = df['low'].min()
        totalArea = (high - low)*df.shape[0]

        priceArea = (df['high'] - df['low']).sum()

        return None if totalArea == 0 else  priceArea/totalArea*100

    def getBBands(df, period=10, stdNbr=2):
        try:
            close = df['close']
        except Exception as ex:
            return None

        try:
            upper, middle, lower = talib.BBANDS(
                                close.values, 
                                timeperiod=period,
                                # number of non-biased standard deviations from the mean
                                nbdevup=stdNbr,
                                nbdevdn=stdNbr,
                                # Moving average type: simple moving average here
                                matype=0)
        except Exception as ex:
            return None

        data = dict(upper=upper, middle=middle, lower=lower)
        df = pd.DataFrame(data, index=df.index, columns=['upper', 'middle', 'lower']).dropna()

        return df

    def _cosVector(x, y):
        result1 = 0.0
        result2 = 0.0
        result3 = 0.0

        for i in range(len(x)):
            result1 += x[i]*y[i]   #sum(X*Y)
            result2 += x[i]**2     #sum(X*X)
            result3 += y[i]**2     #sum(Y*Y)

        cos = result1/((result2*result3)**0.5)

        if cos > 1: cos = 1
        if cos < -1: cos = -1

        return cos

    def _rotateAngle(v1, v2):
        """
            二维坐标系的anticlockwise angle.If clockwise, return negative angle.
            
            @v1 or @v2: like (x1, y1) or [x1, y1]
            @return: 从向量v1到向量v2的逆时针夹角
        """
        cos = DyStockDataUtility._cosVector(v1, v2)

        try:
            angle = math.acos(cos)
        except:
            return None

        _, y1 = v1
        _, y2 = v2

        # cross product
        cross = y2 - y1

        # vector v2 is clockwise from vector v1
        # with respect to the origin (0.0)
        if cross < 0:
            angle = -angle

        degree = angle *  180.0 / math.pi

        return degree

    def xAngles(seriesY, orgY=None, newMaxY=None):
        """
            连续两个Y值跟X轴的夹角，@seriesY的index是X轴坐标
            @seriesY：Pandas Series类型, 都是非负值
            @orgY：Y轴原点，Y值基于它做百分比标准化. None：不需要标准化
            @newMaxY: 新Y轴的最大值，标准化后的值需要等比例变换到新Y轴
            @return: Series of angles
        """
        if orgY < 0 or (seriesY < 0).sum() > 0 or seriesY.shape[0] < 2:
            return None

        if orgY is not None:
            seriesY /= orgY
            seriesY = (seriesY - 1)*100

        if newMaxY is not None:
            seriesY = (seriesY/seriesY.max()) * newMaxY

        # 计算Y轴方向上的增量
        seriesY = seriesY - seriesY.shift(1) # Y of vectors
        seriesY = seriesY.dropna()

        data = {}
        for index in seriesY.index:
            angle = DyStockDataUtility._rotateAngle((1, 0), (1, seriesY[index]))

            data[index] = angle

        s = pd.Series(data)
        s.name = 'xAngle'

        return s

    def xAngle(y1, y2, orgY=None, scale=1):
        """
            以@y1为基准标准化，计算向量[(0, @y1), (1, @y2)]跟X轴的夹角。
            X轴方向以一个单位变化。
            通常状况，X轴代表的相等的时间周期，Y轴代表价格。所以这里省略了X轴。

            @orgY：Y轴原点，Y值基于它做百分比标准化. None：不需要标准化
            @scale: 以相对变化率作为新的Y坐标值，即比例尺
                    变化后的@y1 = 0, @y2 = ((@y2-@y1)*100/@y1)*@scale
        """
        assert( y1 > 0 and y2 > 0)

        # 标准化
        if orgY is not None:
            y1 = (y1 - orgY)/orgY*100
            y2 = (y2 - orgY)/orgY*100

        # 比例放大
        y1 *= scale
        y2 *= scale

        # 计算增量
        y2 -= y1

        angle = DyStockDataUtility._rotateAngle((1, 0), (1, y2))

        return angle

    def getJaccardIndex(index, startDate, endDate, param, daysEngine, info, codes=None, load=True):
        """
            @param: {N Days: increase percent in N Days}
            @return: original DF, Jaccard Index DF, code set DF（代码交集）, {code: increase DF}, code table
        """
        def codeSet(data):
            # seperate into code set
            data = set(data.split(','))
            try:
                data.remove('')
            except Exception as ex:
                pass

            return data

        # load
        days = sorted(param)
        if load:
            if not daysEngine.load([-days[-1], startDate, endDate], codes=codes):
                return None, None, None, None, None

        info.print('开始杰卡德指数[{0}]统计...'.format(daysEngine.stockIndexes[index]), DyLogData.ind)

        startDay = daysEngine.tDaysOffset(startDate)
        progress = DyProgress(info)

        codes = daysEngine.getIndexStockCodes(index)

        progress.init(len(codes), 100, 5)

        # get bool increase and scalar increase for each code
        # no need to dropna, it's controlled by algorithm
        scalarIncreaseDfs = {}
        boolIncreaseDfs = {}
        for code, name in codes.items():
            df = daysEngine.getDataFrame(code)
            if df is None:
                progress.update()
                continue

            scalarIncreaseList = []
            boolIncreaseList = []
            close = df['close']
            for day in days:
                shift = close.shift(day)

                # scalar increase
                increase = (close - shift)*100/shift # no need to dropna
                increase.name = str(day) + ',' + str(param[day])
                scalarIncreaseList.append(increase)
                
                # bool increase
                increase = increase >= param[day]

                boolIncreaseList.append(increase)

            # bool increase
            df = pd.concat(boolIncreaseList, axis=1)
            df.replace([True, False], [code + ',', ''], inplace=True)
            
            boolIncreaseDfs[code] = df

            # scalar increase
            df = pd.concat(scalarIncreaseList, axis=1)
            df.replace([True, False], [code + ',', ''], inplace=True)
            
            scalarIncreaseDfs[code] = df

            progress.update()

        # combine into code set
        progress.init(len(boolIncreaseDfs), 100, 5)

        newDf = None
        for code, df in boolIncreaseDfs.items():
            if newDf is None:
                newDf = df
            else:
                newDf = newDf.add(df, fill_value='')

            progress.update()

        if newDf is None:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), scalarIncreaseDfs, daysEngine.stockCodes

        # 补全交易日, 指数不会停牌
        df = daysEngine.getDataFrame(index)
        df = df['close'].copy()
        df = ''
        newDf = newDf.add(df, fill_value='')

        # 使DF的每个元素是一个代码集合
        newDf = newDf.applymap(codeSet)

        # calculate Jaccard index, 从原始数据中统计
        columns = list(newDf.columns)
        newIndex = newDf.index.map(lambda x: x.strftime('%Y-%m-%d')).tolist()
        data = newDf.values.tolist()

        startDayPos = newDf.index.get_loc(startDay)

        newData = {} # 杰卡德指数
        newCodeSetData = {} # 代码交集
        for pos, (index_, data_) in enumerate(zip(newIndex[startDayPos:], data[startDayPos:]), startDayPos):
            # calculate Jaccard index for each combination
            jaccardIndexes = {}
            jaccardIndexesCodeSet = {}
            combinations = list(itertools.combinations(range(len(columns)), 2))
            for a, b in combinations:
                # get A set
                assert(days[a] < days[b])
                aSetPos = pos - (days[b] - days[a]) # date sequence like 0, A Days, B Days
                aSet = data[aSetPos][a]

                # B set is always data of current date
                intersection = aSet & data_[b]

                try:
                    #jaccardIndex = len(intersection)/len(aSet | data_[b])
                    jaccardIndex = len(intersection)/len(aSet) # !!!only A set, not union of A set and B set, different with Jaccard Index defination
                except Exception as ex:
                    jaccardIndex = 0 # !!!Null Sets, different with Jaccard Index defination

                key = 'J({0};{1})'.format(columns[a], columns[b])
                jaccardIndexes[key] = jaccardIndex
                jaccardIndexesCodeSet[key] = intersection

            # finish Jaccard index for one day
            newData[index_] = jaccardIndexes
            newCodeSetData[index_] = jaccardIndexesCodeSet

        info.print('杰卡德指数[{0}]统计完成'.format(daysEngine.stockIndexes[index]), DyLogData.ind)

        return newDf, pd.DataFrame(newData).T, pd.DataFrame(newCodeSetData).T, scalarIncreaseDfs, daysEngine.stockCodes

    def edExtremaPIPs(df, w=4, peakIndicator='high', bottomIndicator='low'):
        """
            以滑动窗口为周期获取欧氏距离的极值PIPs
            这里的滑动窗口是相对@rwExtremas而言
        """
        windowSize = 2*w + 1

        pipsPct = windowSize*100/df.shape[0]

        peaks = DyStockDataUtility.edPIPs(df, pipsPct, peakIndicator, True)
        bottoms = DyStockDataUtility.edPIPs(df, pipsPct, bottomIndicator, True)

        extremas = pd.concat([peaks, bottoms]).sort_index()

        return extremas, peaks, bottoms

    def edPIPs(df, pipsPct, indicator='close', excludeHeadTail=False):
        """
            获取指定列的欧氏距离的PIPs（perceptually important points）
            @pipsPct: PIP点的百分占比，不包含头尾两个PIPs，因为初始就有头尾两个PIPs
            @excludeHeadTail: 返回的PIPs不含有默认头尾两个PIPs
            @return: PIPs的Series
        """
        assert(df.shape[0] > 2)

        # 原始值
        series = df[indicator]
        x = np.arange(series.shape[0])
        y = series.values
        size = x.shape[0]
        nbrPIPs = round(size*pipsPct/100)

        # 初始化相邻PIPs矩阵, 已经计算出来的PIP用nan标识
        # row0: 左PIPs， row1: 右PIPs
        xAdjacents = np.array([[x[0]]*size, [x[-1]]*size], dtype=np.float64)
        xAdjacents[0][0] = np.nan; xAdjacents[0][-1] = np.nan
        xAdjacents[1][0] = np.nan; xAdjacents[1][-1] = np.nan

        yAdjacents = np.array([[y[0]]*size, [y[-1]]*size])
        yAdjacents[0][0] = np.nan; yAdjacents[0][-1] = np.nan
        yAdjacents[1][0] = np.nan; yAdjacents[1][-1] = np.nan

        # PIPs的索引
        indexPIPs = [0, size-1]

        # 计算PIPs
        for _ in range(nbrPIPs):
            # 计算中间点跟相邻两个PIPs之间的欧式距离
            ed = np.sqrt((x - xAdjacents[0])**2 + (y - yAdjacents[0])**2) + np.sqrt((x - xAdjacents[1])**2 + (y - yAdjacents[1])**2)

            # 最大距离的index
            try:
                edMax = np.nanargmax(ed)
            except ValueError as ex: # All-NaN slice encountered
                break

            # 标识PIP
            xAdjacents[0][edMax] = np.nan; xAdjacents[1][edMax] = np.nan
            yAdjacents[0][edMax] = np.nan; yAdjacents[1][edMax] = np.nan

            indexPIPs.append(edMax)
            indexPIPs.sort()
            edMaxIndex = indexPIPs.index(edMax)

            # 重新计算相邻PIPs矩阵
            xAdjacents[0][edMax + 1:indexPIPs[edMaxIndex+1]] = edMax # 左PIP向右广播到NaN
            xAdjacents[1][indexPIPs[edMaxIndex-1] + 1:edMax] = edMax # 右PIP向左广播到NaN
            yAdjacents[0][edMax + 1:indexPIPs[edMaxIndex+1]] = y[edMax]
            yAdjacents[1][indexPIPs[edMaxIndex-1] + 1:edMax] = y[edMax]

        # 去除头尾
        if excludeHeadTail:
            indexPIPs = indexPIPs[1:-1]

        return series[indexPIPs]

    def rwExtremas(df, w=4, peakIndicator='high', bottomIndicator='low'):
        """
            获取滑动窗口的极值
            Get peak or bottom extrema in a window of size 2w+1 centered on this observation
            @return: extremas, peaks, bottoms, type is Series
        """
        def _extrema(rwArray):
            # 极大值
            extrema = _peak(rwArray)

            # 极小值
            if np.isnan(extrema):
                extrema = _bottom(rwArray)

            return extrema

        def _peak(rwArray):
            center = rwArray[w]

            # 极大值
            if center >= rwArray[:w].max() and center >= rwArray[w+1:].max():
                return True

            return np.nan

        def _bottom(rwArray):
            center = rwArray[w]

            # 极小值
            if center <= rwArray[:w].min() and center <= rwArray[w+1:].min():
                return False

            return np.nan

        if peakIndicator == bottomIndicator:
            series = df[peakIndicator]
        
            extremas = series.rolling(2*w + 1, center=True).apply(_extrema)

            peaks = series[extremas==True]
            bottoms = series[extremas==False]
            extremas = series[extremas.notnull()]

        else:
            peakSeries = df[peakIndicator]
            bottomSeries = df[bottomIndicator]
        
            peaks = peakSeries.rolling(2*w + 1, center=True).apply(_peak)
            bottoms = bottomSeries.rolling(2*w + 1, center=True).apply(_bottom)

            peaks = peakSeries[peaks.notnull()]
            bottoms = bottomSeries[bottoms.notnull()]
            
            extremas = pd.concat([peaks, bottoms])
            extremas.sort_index(inplace=True)

        # rename
        extremas.name = 'extrema'
        peaks.name = 'peak'
        bottoms.name = 'bottom'

        return extremas, peaks, bottoms

    def swings(df, w=4):
        """
            获取DF的波段值
            @w: 滑动窗口大小
            @return: extremas, peaks, bottoms, type is Series
        """
        # 获取滚动窗口极值
        extremas, peaks, bottoms = DyStockDataUtility.rwExtremas(df, w=w)

        # 去除相邻值相同的点
        extremas = extremas.loc[extremas.shift(1) != extremas]

        # 获取有效极值点
        peaks, bottoms = [], [] # 极值索引list
        extremaList = extremas.values.tolist()
        for i in range(1, len(extremaList) - 1):
            if extremaList[i] >= extremaList[i-1] and extremaList[i] >= extremaList[i+1]:
                peaks.append(i)
            elif extremaList[i] <= extremaList[i-1] and extremaList[i] <= extremaList[i+1]:
                bottoms.append(i)

        # 处理两头
        if peaks and bottoms:
            # 头
            if peaks[0] < bottoms[0]:
                bottoms.insert(0, 0)
            else:
                peaks.insert(0, 0)

            #　尾
            if peaks[-1] < bottoms[-1]:
                peaks.append(len(extremaList) - 1)
            else:
                bottoms.append(len(extremaList) - 1)

        elif peaks:
            bottoms.insert(0, 0)
            bottoms.append(len(extremaList) - 1)

        elif bottoms:
            peaks.insert(0, 0)
            peaks.append(len(extremaList) - 1)
        else:
            return pd.Series(), pd.Series(), pd.Series()

        extremaList = sorted(peaks + bottoms)

        return extremas[extremaList], extremas[peaks], extremas[bottoms]

    def dealsHSARs(df, volatility=2, hsarsVolatility=5):
        """
            根据分笔成交计算支撑和阻力价格，支撑和阻力价格取最大成交量区间的均值
            @df: ticksDF
            @volatility: 价格波动率(%)，把@df里的价格按波动率分成若干个区间
            @hsarsVolatility：每@volatility个波动一个支撑或者阻力价格区间
        """
        def _group(x):
            # 最大值归为@granularity-1
            return min(int((x - priceMin)/priceStep), granularity-1)

        def _calc(df):
            df = df.reset_index()

            volumeSum = df['volume'].sum()

            # 均价
            price = (df['price']*df['volume']).sum()/volumeSum

            return pd.DataFrame({'price': price, 'volume': volumeSum}, index=[0])

        prices = df['price']

        # 价差
        priceMin = prices.min()
        priceMax = prices.max()
        priceDiff = priceMax - priceMin
        pricePct = priceDiff*100/priceMin
        granularity = math.ceil(pricePct/volatility)
        priceStep = priceDiff/granularity
        hsarsNbr = int(granularity/hsarsVolatility)
        hsarsNbr = min(6, hsarsNbr) # 最多6个

        # 按价格区间计算成交均价及总成交量
        priceDf = df.set_index('price')
        prices = priceDf.groupby(_group).apply(_calc)

        # 按成交量排序并
        prices = prices.sort_values('volume', ascending=False)

        return prices['price'][:hsarsNbr].values.tolist()

    def _rwExtremaHs(prices, volatility, mean=True):
        """
            按滑动窗口的极值，计算水平线
            @prices: 极大值或者极小值
            @return: [[price, count]]
        """
        def _group(x):
            # 最大值归为@granularity-1
            return min(int((x - priceMin)/priceStep), granularity-1)

        def _calc(df):
            if df.index.size > 0:
                count = df.index.size

                if mean: # 均价
                    sumExtremas = sum(df.index.values.tolist())
                    price = sumExtremas/count
                else:
                    if prices.name == 'bottom':
                        price = df.index.values.min()
                    else:
                        price = df.index.values.max()
            else:
                price = np.nan
                count = np.nan

            return pd.DataFrame({'price': price, 'count': count}, index=[0])

        # 价差
        priceMin = prices.min()
        priceMax = prices.max()
        priceDiff = priceMax - priceMin
        pricePct = priceDiff*100/priceMin
        granularity = math.ceil(pricePct/volatility)
        priceStep = priceDiff/granularity

        # 按价格区间计算极值均价
        priceDf = prices.reset_index().set_index(prices.name)
        prices = priceDf.groupby(_group).apply(_calc)
        prices.dropna(inplace=True)

        # resort columns
        prices = prices.reindex(columns=['price', 'count'])

        return prices.values.tolist()

    def rwExtremaHSARs(df, w=4, volatility=5):
        """
            根据滑动窗口极值计算支撑和阻力价格，支撑和阻力价格取区间极值的均值
            @df: DF, e.g. ticksDF, daysDF, minsDF
            @volatility: 价格波动率(%)，把@df里的价格按波动率分成若干个区间
            @return: HSARs like [[price, count]]
        """
        def _group(x):
            # 最大值归为@granularity-1
            try:
                return min(int((x - priceMin)/priceStep), granularity-1)
            except Exception:
                return granularity-1

        def _calc(df):
            if df.index.size > 0:
                sumExtremas = sum(df.index.values.tolist())
                count = df.index.size

                # 均价
                price = sumExtremas/count
            else:
                price = np.nan
                count = np.nan

            return pd.DataFrame({'price': price, 'count': count}, index=[0])

        extremas, peaks, bottoms = DyStockDataUtility.rwExtremas(df, w)

        prices = extremas

        # 价差
        priceMin = prices.min()
        priceMax = prices.max()
        priceDiff = priceMax - priceMin
        pricePct = priceDiff*100/priceMin

        try:
            granularity = math.ceil(pricePct/volatility)
        except Exception:
            granularity = 2

        priceStep = priceDiff/granularity

        # 按价格区间计算极值均价
        priceDf = extremas.reset_index().set_index('extrema')
        prices = priceDf.groupby(_group).apply(_calc)
        prices.dropna(inplace=True)

        # resort columns
        prices = prices.reindex(columns=['price', 'count'])

        return prices.values.tolist()

    def rwPeakBottomHSARs(df, w=4, volatility=5, mean=True):
        """
            根据滑动窗口最小极值和最大极值计算支撑和阻力价格
            @df: DF, e.g. ticksDF, daysDF, minsDF
            @volatility: 价格波动率(%)，把@df里的价格按波动率分成若干个区间
            @mean: 取极值的平均值还是极值的最大或最小值，peak是最大值，bottom是最小值
            @return: (HSs, HRs), HSs and HRs like [[price, count]]
        """
        extremas, peaks, bottoms = DyStockDataUtility.rwExtremas(df, w)

        hss = DyStockDataUtility._rwExtremaHs(bottoms, volatility, mean)
        hrs = DyStockDataUtility._rwExtremaHs(peaks, volatility, mean)

        return hss, hrs

    def trendLine(df):
        """
            获取DF的趋势线
            判定原则基于《专业投机原理》
            若周期内最高价和最低价相邻，则没有趋势线，也是说返回None, None
            @return: series, bool. series - 2 points with Series type, point is like (time, high/low). bool - 上升趋势还是下降趋势
        """
        highs = df['high'].values
        lows = df['low'].values

        highestX = np.nanargmax(highs); highestY = highs[highestX]
        lowestX = np.nanargmin(lows); lowestY = lows[lowestX]

        if highestX < lowestX: # 下降趋势
            # 下降趋势线判别公式：
            #   (x2-x1)(y-y1) - (y2-y1)(x-x1) > 0 右侧
            #   (x2-x1)(y-y1) - (y2-y1)(x-x1) < 0 左侧

            highsY = highs[highestX + 1:lowestX]
            highsX = np.array(range(highestX + 1, lowestX))

            # 从最低点开始寻找某一高点，使之与最高点连成趋势线
            for i in range(lowestX - 1, highestX, -1): # Loop X axis
                result = (i - highestX)*(highsY - highestY) - (highs[i] - highestY)*(highsX - highestX)
                if (result > 0).sum() == 0:
                    return df['high'][[highestX, i]], False

        else: # 上升趋势
            # 上升趋势线判别公式：
            #   (x2-x1)(y-y1) - (y2-y1)(x-x1) < 0 右侧
            #   (x2-x1)(y-y1) - (y2-y1)(x-x1) > 0 左侧

            lowsY = lows[lowestX + 1:highestX]
            lowsX = np.array(range(lowestX + 1, highestX))

            # 从最低点开始寻找某一高点，使之与最高点连成趋势线
            for i in range(highestX - 1, lowestX, -1): # Loop X axis
                result = (i - lowestX)*(lowsY - lowestY) - (lows[i] - lowestY)*(lowsX - lowestX)
                if (result < 0).sum() == 0:
                    return df['low'][[lowestX, i]], True

        return None, None

    def getAtrExtreme(df, atrPeriod=14, emaPeriod=30, stdPeriod=30, atrExtremeFastPeriod=3, dropna=True):
        """
            获取TTI ATR Exterme通道, which is based on 《Volatility-Based Technical Analysis》
            TTI is 'Trading The Invisible'

            @atrPeriod: ATR N日平均
            @emaPeriod: 移动指数均线周期
            @stdPeriod: ATR Extermes的标准差周期
            @atrExtremeFastPeriod: ATR Extermes快速简单均线周期

            @return: DF
        """
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values

        # talib 的源码，它的 ATR 不是 N 日简单平均，而是类似 EMA 的方法计算的指数平均
        atr = talib.ATR(highs, lows, closes, timeperiod=atrPeriod)

        emaDf = df.ewm(span=emaPeriod).mean()

        atrExtremes = np.where(closes > emaDf['close'].values,
                               ((highs - emaDf['high'].values)/closes * 100) * (atr/closes * 100),
                               ((lows - emaDf['low'].values)/closes * 100) * (atr/closes * 100)
                               )

        atrExtremeSeries = pd.Series(atrExtremes)

        emaAtrExtremes = atrExtremeSeries.ewm(span=emaPeriod).mean().values
        stdAtrExtremes = atrExtremeSeries.rolling(center=False, window=stdPeriod).std().values
        maAtrExtremes = atrExtremeSeries.rolling(center=False, window=atrExtremeFastPeriod).mean().values

        atrExtremeDf = pd.DataFrame(data={'ema': emaAtrExtremes, 'std': stdAtrExtremes, 'ma': maAtrExtremes},
                                    index=df.index
                                    )

        return atrExtremeDf.dropna() if dropna else atrExtremeDf

    def countConsecutiveLine(df, bar='day', greenLine=True):
        """
            统计连续阴线或者阳线(含十字星), 至少2个。由于算法原因，忽略K线的第1根
            @df: 个股（基金）或者指数的Bar DF(OHLC)
            @bar: 日K线(day)还是分钟K线(min)
            @greenLine: True-阴线，False-阳线
            @return: counted DF
        """
        def _count(df):
            # 忽略一根K线，至少连续两根K线
            if df.shape[0] == 1:
                return None

            if greenLine: # 是否是连续阴线
                if df.ix[-1, 'close'] >= df.ix[-1, 'open']:
                    return None

            else: # 是否是连续阳线
                if df.ix[-1, 'close'] <= df.ix[-1, 'open']:
                    return None

            # 是否包含第一根K线
            if np.isnan(df.ix[0, 'preClose']): # 包含第一根K线
                if df.shape[0] == 2:
                    return None

                preClose = df.ix[1, 'preClose']
                consecutiveLineNbr = df.shape[0] - 1

            else:
                preClose = df.ix[0, 'preClose']
                consecutiveLineNbr = df.shape[0]

            data = {'开始时间': [df.index[0].strftime("%Y-%m-%d") if bar == 'day' else df.index[0].strftime("%Y-%m-%d %H:%M:%S")],
                    '结束时间': [df.index[-1].strftime("%Y-%m-%d") if bar == 'day' else df.index[-1].strftime("%Y-%m-%d %H:%M:%S")],
                    '连续阴线数' if greenLine else '连续阳线数': [consecutiveLineNbr],
                    '跌幅(%)' if greenLine else '涨幅(%)': [(df.ix[-1, 'close'] - preClose)*100/preClose],
                    '上缺口数': df['upGap'].sum(),
                    '下缺口数': df['downGap'].sum(),
                    '上缺口幅度(%)': df[df['upGap']]['upGapInc'].sum() if df['upGap'].sum() > 0 else None,
                    '下缺口幅度(%)': df[df['downGap']]['downGapInc'].sum() if df['downGap'].sum() > 0 else None
                    }

            return pd.DataFrame(data=data, columns=columns)

        columns = ['开始时间', '结束时间',
                   '连续阴线数' if greenLine else '连续阳线数',
                   '跌幅(%)' if greenLine else '涨幅(%)',
                   '上缺口数', '下缺口数', '上缺口幅度(%)', '下缺口幅度(%)']

        # concat previous close for calculating total drop down
        preCloses = df['close'].shift(1)
        preCloses.name = 'preClose'

        # 计算上缺口
        upGaps = df['low'] > df['high'].shift(1)
        upGaps.name = 'upGap'

        upGapsIncrease = (df['low'] - df['high'].shift(1))/preCloses*100
        upGapsIncrease = upGapsIncrease[upGaps]
        upGapsIncrease.name = 'upGapInc'

        # 计算下缺口
        downGaps = df['high'] < df['low'].shift(1)
        downGaps.name = 'downGap'

        downGapsIncrease = (df['high'] - df['low'].shift(1))/preCloses*100
        downGapsIncrease = downGapsIncrease[downGaps]
        downGapsIncrease.name = 'downGapInc'

        df = pd.concat([df, preCloses, upGaps, downGaps, upGapsIncrease, downGapsIncrease], axis=1)

        lineSeries = df['close'] <= df['open'] if greenLine else df['close'] >= df['open']

        lineDf = df.groupby((lineSeries != lineSeries.shift(1)).cumsum()).apply(_count)
        
        # !!!必须要先转成时间类型才能被用作索引
        lineDf = lineDf.set_index(pd.to_datetime(lineDf['结束时间']))

        # add after days increase
        afterIncreases = []
        for day in [1, 2, 3, 4, 5, 10, 20, 30, 60]:
            afterCloses = df['close'].shift(-day)

            afterIncrease = (afterCloses[lineDf.index] - df['close'][lineDf.index])*100/df['close'][lineDf.index]
            afterIncrease.name = '{0}{1}涨幅(%)'.format(day, '日' if bar == 'day' else '分')

            afterIncreases.append(afterIncrease)

        # concat after days increase
        lineDf = pd.concat([lineDf] + afterIncreases, axis=1)
        lineDf = lineDf.reindex(columns=columns + [s.name for s in afterIncreases]) # sort by columns

        return lineDf

    def getIntraDayBars(df, bar='1min'):
        """
            根据tick DF合成日内K线
        """
        # 合成Bar, 右闭合
        # 缺失的Bar设为NaN
        barDf = df.resample(bar, closed='right', label='right')[['price', 'volume']].agg(OrderedDict([('price', 'ohlc'), ('volume', 'sum')]))
        barDf.dropna(inplace=True) # drop缺失的Bars

        # remove multi-index of columns
        barDf = pd.concat([barDf['price'], barDf['volume']], axis=1)
        barDf = barDf[barDf['volume'] > 0] # 剔除无交易的Bar

        return barDf

    def countLimitUp(dfs, info):
        """
            统计每日封板数据
            @dfs: {code: DF}
            @return: DF - 未封板数, 封板数, 封板率(%), 封板数占总比(%)
        """
        info.print('开始统计封板数据...', DyLogData.ind)

        progress = DyProgress(info)
        progress.init(len(dfs), 100, 10)

        limitUpStats, nokLimitUpStats, totalCodeNbr = pd.Series(), pd.Series(), pd.Series()
        for _, df in dfs.items():
            # 非停牌或者非上市股票计数
            totalCodeNbr = totalCodeNbr.add(df['volume'] > 0, fill_value=0)

            # 封板
            closeChange = df['close'].pct_change()
            closeChange = closeChange[df['high'] != df['low']]
            boolCloseChange = closeChange > DyStockCommon.limitUpPct/100

            limitUpStats = limitUpStats.add(boolCloseChange, fill_value=0)

            # 未封板
            shiftClose = df['close'].shift(1)
            highChange = (df['high'] - shiftClose)/shiftClose
            highChange = highChange[df['high'] != df['low']]
            boolHighChange = highChange > DyStockCommon.limitUpPct/100
            boolHighChange = boolHighChange & -boolCloseChange

            nokLimitUpStats = nokLimitUpStats.add(boolHighChange, fill_value=0)

            progress.update()

        info.print('完成统计封板数据', DyLogData.ind)

        # sum for removing zero division exception
        limitUpSum = limitUpStats + nokLimitUpStats
        boolLimitSum = limitUpSum > 0

        # remove 0
        limitUpSum = limitUpSum[boolLimitSum]
        limitUpStats = limitUpStats[boolLimitSum]
        nokLimitUpStats = nokLimitUpStats[boolLimitSum]
        totalCodeNbr = totalCodeNbr[boolLimitSum]

        # limit-up ratio
        limitUpRatio = limitUpStats/limitUpSum*100

        # limit-up over total stocks
        limitUpTotalRatio = limitUpStats/totalCodeNbr*100

        # rename
        nokLimitUpStats.name = '未封板数'
        limitUpStats.name = '封板数'
        limitUpRatio.name = '封板率(%)'
        limitUpTotalRatio.name = '封板数占总比(%)'

        return pd.concat([nokLimitUpStats, limitUpStats, limitUpRatio, limitUpTotalRatio], axis=1)

    def getVolatility(df):
        """
            获取波动率
            @return: volatility Series
        """
        preCloses = df['close'].shift(1)

        highVolatility = (df['high'] - preCloses)/preCloses
        lowVolatility = (df['low'] - preCloses)/preCloses
        highLowVolatility = highVolatility - lowVolatility

        # 类似于True Range，但这里是比率
        trueVolatility = pd.concat([highVolatility, lowVolatility, highLowVolatility], axis=1)
        trueVolatility = trueVolatility.abs()
        trueVolatility = trueVolatility.max(axis=1)
        trueVolatility *= 100

        return trueVolatility.dropna()

    def getChipDistByDays(df, ohlcRatio=40, gridNbr=60):
        """
            根据日线，计算筹码分布
            @df: 日线DF
            @ohlcRatio: %, OHLC占比成交量的百分比
            @gridNbr: 其他价格的网格数
            @return: Series, index is price, value is volume(股数)
        """
        dfs = []

        # 按OHLC，四个价格均分成交量的ratio%
        ratio = ohlcRatio/100
        volumes = df['volume']*(ratio/4)
        for col in ['open', 'high', 'low', 'close']:
            df_ = pd.concat([df[col].rename('price'), volumes], axis=1)
            dfs.append(df_)

        # 剩余的按网格，每网格均分成交量的(1-ratio)%
        gridSeries = (df['high'] - df['low'])/gridNbr
        volumes = df['volume']*((1 - ratio)/(gridNbr - 1))
        for i in range(1, gridNbr):
            s = df['low'] + gridSeries*i
            s.name = 'price'

            df_ = pd.concat([s, volumes], axis=1)
            dfs.append(df_)

        # concat all
        df = pd.concat(dfs, axis=0)

        s = df['volume'].groupby(df['price']).sum()

        s.sort_index(inplace=True)

        return s

    def getChipDistByTicks(df):
        """
            根据Ticks，计算筹码分布
            @df: Ticks DF
            @return: Series, index is price, value is volume(股数)
        """
        s = df['volume'].groupby(df['price']).sum()
        s *= 100

        s.sort_index(inplace=True)

        return s

    def isMasLong(maDf, diffLong=True):
        """
            均线是否连续多头排列
            @maDf: DF of MAs with sorted columns
            @diffLong: bool, True - 短线均线之差大于等于长线均线之差，比如(ma10 - ma20) >= (ma20 - ma30)，False - 不检查这一项
        """
        maColumns = maDf.columns

        # 均线多头
        longs = None
        diffList = []
        for i in range(len(maColumns) - 1):
            diff = maDf[maColumns[i]] - maDf[maColumns[i+1]]

            # 多头排列
            bool = diff < 0
            if longs is None:
                longs = bool
            else:
                longs &= bool

            if longs.sum() > 0:
                return False

            diffList.append(diff)

        # 均线差值多头
        longs = None
        if diffLong:
            for i in range(len(diffList) - 1):
                bool = diffList[i+1] > diffList[i]

                # 差值多头排列
                if longs is None:
                    longs = bool
                else:
                    longs &= bool

                if longs.sum() > 0:
                    return False

        return True

    def getMasLong(maDf, diffLong=True):
        """
            获取均线连续多头排列天数
            @maDf: DF of MAs with sorted columns
            @diffLong: bool, True - 短线均线之差大于等于长线均线之差，比如(ma10 - ma20) >= (ma20 - ma30)，False - 不检查这一项
            @return: 从最近交易日算起的连续天数
        """
        maColumns = maDf.columns

        # 均线多头
        longs = None
        diffList = []
        for i in range(len(maColumns) - 1):
            diff = maDf[maColumns[i]] - maDf[maColumns[i+1]]

            # 多头排列
            bool = diff >= 0
            if longs is None:
                longs = bool
            else:
                longs &= bool

            diffList.append(diff)

        # 均线差值多头
        if diffLong:
            for i in range(len(diffList) - 1):
                bool = diffList[i] >= diffList[i+1]

                # 差值多头排列
                if longs is None:
                    longs = bool
                else:
                    longs &= bool

        # 找出连续多头天数
        start = longs.iloc[::-1].idxmin()
        longs = longs[start:]

        nbr = len(longs) - 1
        if nbr == 0: # check if all of these are MA long or no any MA long
            if longs[-1]:
                nbr = len(maDf)

        return nbr

