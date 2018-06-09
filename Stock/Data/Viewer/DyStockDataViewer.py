from collections import OrderedDict
import numpy as np

# !!!for ignore matplotlib.finance warnings
import warnings
import matplotlib.cbook
warnings.filterwarnings("ignore", category=matplotlib.cbook.mplDeprecation)

import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
try:
    from matplotlib.finance import candlestick2_ohlc, volume_overlay
except ImportError:
    from mpl_finance import candlestick2_ohlc, volume_overlay
from matplotlib.ticker import FuncFormatter, FixedLocator

from PyQt5.QtWidgets import QMessageBox

from EventEngine.DyEvent import *
from ..Utility.DyStockDataUtility import *
from DyCommon.DyCommon import *
from ...Common.DyStockCommon import *
from ..Utility.DyStockDataML import *


class DyStockDataViewer(object):
    """
        股票数据的视图展示，主要是计算股票数据生成matplotlib视图
        若要生成跟股票代码相关的表格窗口，则需要使用DyStockDataWindow类(友元类)，这样可以防止import递归。
    """

    def __init__(self, dataEngine, info=None):
        self._dataEngine = dataEngine
        self._info = info

        self._progress = DyProgress(self._info)

        self._testedStocks = None
        self._windows = [] # only for showing windows

        # for easy access
        self._daysEngine = self._dataEngine.daysEngine
        self._ticksEngine = self._dataEngine._ticksEngine
        self._eventEngine = self._dataEngine.eventEngine

    @property
    def dataEngine(self):
        return self._dataEngine

    @property
    def eventEngine(self):
        return self._eventEngine

    def setTestedStocks(self, codes):
        self._testedStocks = codes

    def _plotNetCapitalFlow(self, df, ax, code):
        try:
            mf = df['mf_amt'].values

            close = df['close'].values.copy()
            open = df['open'].values.copy()

            close[mf>0] = 1; open[mf>0] = 0
            close[mf<=0] = 0; open[mf<=0] = 1

            volume_overlay(ax, open, close, abs(mf)/10**7, colorup='r', colordown='g', width=.5, alpha=1)

        except KeyError:
            # !!!刚上市新股的前几个交易日，有时万得没有资金净流入和成交量净流入的日线数据
            #self._info.print('[{0}: {1}]没有日线[资金净流入]数据'.format(code, self._daysEngine.stockAllCodesFunds[code]), DyLogData.warning)
            pass

    def _getTDays(self, code, dates):
        """ @return: base tDay, start tDay, end tDay """
        baseDay = self._daysEngine.codeTDayOffset(code, dates[1], 0)

        # get start date and end date for @nDays
        startDate = self._daysEngine.codeTDayOffset(code, baseDay, dates[0], strict=False)
        endDate = self._daysEngine.codeTDayOffset(code, baseDay, dates[2], strict=False)

        return baseDay, startDate, endDate

    def plotCandleStick(self, code, dates, maIndicator='close'):
        """
            @dates: [-n, baseDate, n]
        """
        # fowarding 59 days for calculating MAs
        dates[0] -= 59

        # load stock days data
        if not self._daysEngine.loadCode(code, dates):
            return

        DyMatplotlib.newFig()

        # get date range
        dates[0] += 59 # restore date range
        baseDay, startDay, endDay = self._getTDays(code, dates)

        # plot stock
        periods = self._plotCandleStick(code, startDate=startDay, endDate=endDay, baseDate=baseDay, left=0.05, right=0.95, top=0.95, bottom=0.5, maIndicator=maIndicator)

        # plot index
        indexCode = self._daysEngine.getIndex(code)
        self._daysEngine.loadCode(indexCode, [-59, startDay, endDay])
        self._plotCandleStick(indexCode, periods=periods, baseDate=baseDay, netCapitalFlow=False, left=0.05, right=0.95, top=0.45, bottom=0.05, maIndicator=maIndicator)

        # layout
        f = plt.gcf()
        plt.setp([a.get_xticklabels() for a in f.axes[:-1]], visible=False)
        f.show()

    def _plotCandleStick(self, code, startDate=None, endDate=None, periods=None, baseDate=None, netCapitalFlow=True, left=None, right=None, top=None, bottom=None, maIndicator='close'):
        """
            股票日线K线图
            成交量单位是万手
            资金流向单位是千万元
            @periods: 周期索引，主要用来对齐不同子图的时间坐标
        """
        def _dateFormatter(x, pos):
            if not (0 <= int(x) < df.shape[0]):
                return None

            return df.index[int(x)].strftime("%y-%m-%d")

        # get DataFrame
        df = self._daysEngine.getDataFrame(code)
        if df is None:
            return None

        maDf = DyStockDataUtility.getMas(df, [5,10,20,30,60], False, maIndicator)

        if periods is None:
            if startDate is not None and endDate is not None:
                df = df.ix[startDate:endDate]
                maDf = maDf.ix[startDate:endDate]

            periods = df.index

        else:
            # 数据对齐
            df = df.ix[periods]
            maDf = maDf.ix[periods]

        if df.shape[0] == 0 or maDf.shape[0] == 0:
            return periods

        highest = df['high'].max()
        lowest = df['low'].min()

        # create grid spec
        gs = GridSpec(4, 1)
        gs.update(left=left, right=right, top=top, bottom=bottom, hspace=0)

        # subplot for price candle stick
        axPrice = plt.subplot(gs[:-1, :])
        axPrice.set_title('{0}({1}),均线指标:{2},交易日数:{3},振幅:{4}%'.format(self._daysEngine.stockAllCodesFunds[code],
                                                                            code,
                                                                            DyStockCommon.indicatorNameTable[maIndicator],
                                                                            periods.shape[0],
                                                                            '%.2f'%((highest - lowest)*100/lowest)
                                                                            ))
        axPrice.grid(True)

        # set x ticks
        x = [x for x in range(df.shape[0])]
        xspace = max((len(x)+9)//10, 1)
        axPrice.xaxis.set_major_locator(FixedLocator(x[:-xspace-1: xspace] + x[-1:]))
        axPrice.xaxis.set_major_formatter(FuncFormatter(_dateFormatter))

        # plot K-chart
        lineCollection, barCollection = candlestick2_ohlc(axPrice, df['open'].values, df['high'].values, df['low'].values, df['close'].values, width=.9, colorup='r', colordown='g', alpha=1)
        barCollection.set_edgecolor('face') # 边框同色
        lineCollection.set_color(barCollection.get_facecolor())

        # plot MAs
        for ma in maDf.columns:
            axPrice.plot(x, maDf[ma].values, label=ma)

        # plot volume
        axVolume = plt.subplot(gs[-1, :], sharex=axPrice)
        axVolume.grid(True)
        barCollection = volume_overlay(axVolume, df['open'].values, df['close'].values, df['volume'].values/10**6, colorup='r', colordown='g', width=.9, alpha=1)
        barCollection.set_edgecolor('face') # 边框同色

        # plot net capital flow
        if netCapitalFlow:
            self._plotNetCapitalFlow(df, axVolume, code)

        # 标记基准日期
        if baseDate is not None:
            baseTDay = self._daysEngine.tDaysOffset(baseDate)

            try:
                x = df.index.get_loc(baseTDay)
                y = df.ix[baseTDay, 'high']

                yLimitBottom, yLimitTop = axPrice.get_ylim()
                textYOffset = (yLimitTop - yLimitBottom)*0.1

                axPrice.annotate(baseTDay, xy=(x, y), xycoords='data',
                                xytext=(x, y + textYOffset), textcoords='data',
                                arrowprops=dict(facecolor='black', shrink=0.05),
                                horizontalalignment='right', verticalalignment='bottom',
                                )
            except Exception as ex:
                pass

        axPrice.legend(loc='upper left', frameon=False)

        return periods

    def _plotTimeShareChart(self, code, date, left=None, right=None, top=None, bottom=None):
        def _timeFormatter(x, pos):
            if not (0 <= int(x) < df.shape[0]):
                return None

            return df.index[int(x)].strftime("%H:%M:%S")

        """ 数据载入 """
        # 为了获取前日收盘价，向前一日获取股票日线数据，前复权方式基于当日
        if not self._daysEngine.loadCode(code, [date, -1], latestAdjFactorInDb=False):
            return

        try:
            # get previous close
            df = self._daysEngine.getDataFrame(code)
            preTDay = self._daysEngine.codeTDayOffset(code, date, -1)
            preClose = df.ix[preTDay, 'close']

            # 获取当日数据
            date = self._daysEngine.codeTDayOffset(code, date, 0)
            high = df.ix[date, 'high']
            low = df.ix[date, 'low']
            close = df.ix[date, 'close']
            turn = df.ix[date, 'turn']
        except:
            return

        try:
            mfAmt = df.ix[date, 'mf_amt']
        except:
            mfAmt = None

        # load ticks
        if not self._ticksEngine.loadCode(code, date):
            return

        # 分笔数据
        df = self._ticksEngine.getDataFrame(code)

        """ 分时图 """
        # create grid spec
        gs = GridSpec(4, 1)
        gs.update(left=left, right=right, top=top, bottom=bottom, hspace=0.15)

        # subplot for price time share
        axPrice = plt.subplot(gs[:-1, :])
        axPrice.grid(True)
        
        increaseStr = '%.2f' % ((close - preClose)*100/preClose)
        turnStr = '%.2f' % turn
        color = 'k' if close == preClose else 'r' if close > preClose else 'g'
        axPrice.set_title('{0}({1})@{2},涨幅:{3}%,换手:{4}%'.format(self._daysEngine.stockAllCodesFunds[code], code, date, increaseStr, turnStr), color=color)

        # set x ticks
        x = [x for x in range(df.shape[0])]
        xspace = max((len(x)+9)//10, 1)
        axPrice.xaxis.set_major_locator(FixedLocator(x[:-xspace-1: xspace] + x[-1:]))
        axPrice.xaxis.set_major_formatter(FuncFormatter(_timeFormatter))

        # set y limit
        maxYLimit = max(abs(high - preClose), abs(low - preClose))
        axPrice.set_ylim(preClose - maxYLimit*1.01, preClose + maxYLimit*1.01) # 乘以1.01，这样涨停线可以画出来

        # plot price time share
        axPrice.plot(x, df['price'].values)

        # 画一条昨日收盘价的水平直线
        axPrice.axhline(preClose, color='k', alpha=.5)

        # Y轴的右侧标记涨幅区间
        increaseText = '%.2f'%(maxYLimit*100/preClose) + '%'
        axPrice.text(1, 1, increaseText, color='r', transform=axPrice.transAxes)
        axPrice.text(1, 0, '-' + increaseText, color='g', transform=axPrice.transAxes)

        # ----- 标记净资金流 -----

        # 新浪
        type = df['type'].values
        amount = df['amount'].values

        moneyFlow = amount[type == '买盘'].sum() - amount[type == '卖盘'].sum()
        c = 'k' if moneyFlow == 0 else 'r' if moneyFlow > 0 else 'g'
        moneyFlow = '新浪:净流入{0}(万元)'.format(moneyFlow//10000)

        axPrice.text(0.5, 0.9, moneyFlow, color=c, transform=axPrice.transAxes)

        # 万得
        if mfAmt is not None:
            moneyFlow = int(mfAmt)
            c = 'k' if moneyFlow == 0 else 'r' if moneyFlow > 0 else 'g'
            moneyFlow = '万得:净流入{0}(万元)'.format(moneyFlow//10000)

            axPrice.text(0.5, 0.8, moneyFlow, color=c, transform=axPrice.transAxes)

        """ 成交量 """
        # plot volume
        axVolume = plt.subplot(gs[-1, :], sharex=axPrice)
        axVolume.grid(True)

        x = np.array(x)
        y = df['volume'].values
        type = df['type'].values

        for t, c in {'买盘':'r', '卖盘':'g', '中性盘':'b'}.items():
            bool = (type == t)
            newX = x[bool]
            newY = y[bool]
            axVolume.bar(newX, newY, linewidth=0, color=c)

        # 标记换手超过万分之五的大单
        volumeSeries = df['volume']
        volumeSum = volumeSeries.sum()
        volumeSeries = volumeSeries * ((turn*100)/volumeSum)

        bigVolumeSeries = volumeSeries[volumeSeries >= 5]

        for i in range(bigVolumeSeries.shape[0]):
            index = bigVolumeSeries.index[i]
            newX = volumeSeries.index.get_loc(index)
            newVolumeY = df.ix[index, 'volume']
            newPriceY = df.ix[index, 'price']

            type = df.ix[index, 'type']
            c = 'ro' if type == '买盘' else 'go' if type == '卖盘' else 'bo'

            axPrice.plot(newX, newPriceY, c)
            axVolume.plot(newX, newVolumeY, c)

        # 标记成交量万分之坐标
        _, top = axVolume.get_ylim()
        top = top * ((turn*100)/volumeSum)
        top = '%.2f万分之'%top
        axVolume.text(1, 1, top, color='r', transform=axVolume.transAxes)

    def plotTimeShareChart(self, code, date, n):

        date = self._daysEngine.codeTDayOffset(code, date, n)
        if date is None: return

        DyMatplotlib.newFig()

        # plot stock time share chart
        self._plotTimeShareChart(code, date, left=0.05, right=0.95, top=0.95, bottom=0.05)

        # plot index time share chart
        #self._plotTimeShareChart(self._daysEngine.getIndex(code), date, left=0.05, right=0.95, top=0.45, bottom=0.05)

        # layout
        f = plt.gcf()
        plt.setp([a.get_xticklabels() for a in f.axes[::2]], visible=False)
        f.show()

    def plotScatterChart(self, target, code, baseDate, n):

        codes = [code]

        if target != '指数':
            self._daysEngine.loadCodeTable()

            targetCode = self._daysEngine.getCode(target)
            codes.append(targetCode)
        else:
            targetCode = self._daysEngine.getIndex(code)

        # load
        if not self._daysEngine.load([baseDate, n], codes=codes):
            return

        try:
            # concat to one DF
            targetDf = self._daysEngine.getDataFrame(targetCode)
            df = self._daysEngine.getDataFrame(code)

            targetName = self._daysEngine.stockAllCodesFunds[targetCode]
            name = self._daysEngine.stockAllCodesFunds[code]
            df = pd.DataFrame({targetName: targetDf['close'], name: df['close']})

            startDay = df.index[0].strftime("%Y-%m-%d")
            endDay = df.index[-1].strftime("%Y-%m-%d")
            
            DyMatplotlib.newFig()

            df.plot.scatter(x=targetName, y=name)
            
            f = plt.gcf()
            f.axes[0].set_title('收盘价散列图[{0}, {1}]'.format(startDay, endDay))

            f.show()
        except Exception as ex:
            pass

    def plotSpreadChart(self, target, code, baseDate, n):
        def _dateFormatter(x, pos):
            if not (0 <= int(x) < spreads.shape[0]):
                return None

            return spreads.index[int(x)].strftime("%y-%m-%d")

        codes = [code]

        if target != '指数':
            self._daysEngine.loadCodeTable()

            targetCode = self._daysEngine.getCode(target)
            codes.append(targetCode)
        else:
            targetCode = self._daysEngine.getIndex(code)

        # load
        if not self._daysEngine.load([baseDate, n], codes=codes):
            return

        try:
            # concat to one DF
            targetDf = self._daysEngine.getDataFrame(targetCode)
            df = self._daysEngine.getDataFrame(code)

            targetName = self._daysEngine.stockAllCodesFunds[targetCode]
            name = self._daysEngine.stockAllCodesFunds[code]
            df = pd.DataFrame({targetName: targetDf['close'], name: df['close']})
            df = df.dropna()

            # calculate spread
            # 标准化
            targetCloses = df[targetName]
            targetCloses = np.log(targetCloses)
            targetCloses -= targetCloses[0]
            targetCloses *= 100

            closes = df[name]
            closes = np.log(closes)
            closes -= closes[0]
            closes *= 100

            # spread
            spreads = targetCloses - closes

            # 平稳性检验
            pvalue = DyStockDataML.adfTest(spreads)

            startDay = df.index[0].strftime("%Y-%m-%d")
            endDay = df.index[-1].strftime("%Y-%m-%d")
            
            # plot
            DyMatplotlib.newFig()

            ax = plt.subplot()
            ax.grid(True)

            # set x ticks
            x = [x for x in range(spreads.shape[0])]
            xspace = max((len(x)+9)//10, 1)
            ax.xaxis.set_major_locator(FixedLocator(x[:-xspace-1: xspace] + x[-1:]))
            ax.xaxis.set_major_formatter(FuncFormatter(_dateFormatter))

            ax.bar(x, spreads.values, label='价差')
            ax.plot(x, targetCloses.values, label=targetName, color='r')
            ax.plot(x, closes.values, label=name, color='g')

            ax.legend(loc='upper left', frameon=False)
            ax.set_ylabel('幅度(%)')
            ax.set_title('[{0}-{1}]收盘价差图[{2}, {3}], p值(‰): {4}'.format(targetName, name, startDay, endDay, round(pvalue*1000, 5)))
            
            f = plt.gcf()
            f.show()
        except Exception as ex:
            pass
        
    def plotDealsDist(self, code, baseDate, n):
        # 载入tick数据
        if not self._ticksEngine.loadCodeN(code, [baseDate, n]):
            return

        ticksDf = self._ticksEngine.getDataFrame(code, adj=True)

        # 交易日数据
        days = self._ticksEngine.getDays(code)

        # 日线数据
        daysDf = self._ticksEngine.getDaysDataFrame(code)

        # group
        prices = ticksDf['volume'].groupby([ticksDf['type'], ticksDf['price']]).sum()

        try:
            DyMatplotlib.newFig()

            ax = plt.subplot()
            ax.grid(True)

            # plot by stacked way
            # 买盘
            if '买盘' in prices:
                ax.bar(prices['买盘'].index.values, prices['买盘'].values, width=.01, color='r')
            
            # 卖盘
            if '买盘' in prices and '卖盘' in prices:
                bottom = prices['买盘'][prices['卖盘'].index].values
            else:
                bottom = None

            if '卖盘' in prices:
                ax.bar(prices['卖盘'].index.values, prices['卖盘'].values, bottom=bottom, width=.01, color='g')

            # 中性盘
            if '买盘' in prices and '卖盘' in prices and '中性盘' in prices:
                bottom = prices['买盘'][prices['中性盘'].index].values + prices['卖盘'][prices['中性盘'].index].values
            elif '买盘' in prices and '中性盘' in prices:
                bottom = prices['买盘'][prices['中性盘'].index].values
            elif '卖盘' in prices and '中性盘' in prices:
                bottom = prices['卖盘'][prices['中性盘'].index].values
            else:
                bottom = None

            if '中性盘' in prices:
                ax.bar(prices['中性盘'].index.values, prices['中性盘'].values, bottom=bottom, width=.01, color='b')

            # 标记买卖盘量比
            ratio = prices['卖盘'].sum()/prices['买盘'].sum()
            ratio = '买卖盘量比1:%.2f'%ratio

            ax.text(0, 0.97, ratio, color='r', transform=ax.transAxes)

            # 标记买卖盘资金比
            amount = ticksDf['amount'].groupby(ticksDf['type']).sum()

            ratio = amount['卖盘'].sum()/amount['买盘'].sum()
            ratio = '买卖盘资金比1:%.2f'%ratio

            ax.text(0, 0.94, ratio, color='r', transform=ax.transAxes)

            # 标记均价
            priceMean = daysDf['amt'].sum()/daysDf['volume'].sum()
            priceMean = '成交均价%.2f'%priceMean

            ax.text(0, 0.91, priceMean, color='r', transform=ax.transAxes)

            # other
            ax.set_title('{0}({1})成交分布[{2},{3}], {4}个交易日'.format(self._daysEngine.stockAllCodesFunds[code], code, days[0], days[-1], len(days)))
            ax.set_ylabel('成交量(手)')
            ax.set_xlabel('成交价格(元)')

            f = plt.gcf()
            f.show()

        except Exception as ex:
            pass

    def _plotRegionalLocals(self, ax, index, regionalLocals, color='k'):
        """
            在现有坐标系里绘制特征点
            @ax：现有坐标
            @index：当前坐标对应的时间索引
            @regionalLocals：特征点Series
        """
        # get x-coordinates
        x = []
        for i in regionalLocals.index:
            try:
                x_ = index.get_loc(i)
            except Exception as ex:
                x_ = None

            x.append(x_)

        ax.plot(x, regionalLocals.values, color + 'o--')

    def _plotDealsHSARs(self, ax, hsars):
        """
            在现有坐标系里绘制成本HSARs
            @ax：现有坐标
            @hsars：HSARs list
        """
        hsars = hsars[::-1]
        for i, y in enumerate(hsars):
            ax.axhline(y, color='y', linestyle='--', linewidth=i+1)

    def _plotExtremaHSARs(self, ax, hsars):
        """
            在现有坐标系里绘制极值HSARs
            @ax：现有坐标
            @hsars：HSARs list
        """
        for y, i in hsars:
            ax.axhline(y, color='y', linestyle='--', linewidth=i)

    def _plotTAHSARs(self, ax, code, startDay, endDay, index=False):
        """
            @index: 指数还是股票，指数没有成本压力阻力支撑
        """
        # plot deals HSARs of stock
        if DyStockCommon.hsarMode == '成本':
            if not index:
                self._ticksEngine.loadCodeN(code, [startDay, endDay])
                df = self._ticksEngine.getDataFrame(code, adj=True)
                hsars = DyStockDataUtility.dealsHSARs(df, volatility=2, hsarsVolatility=3)
                self._plotDealsHSARs(ax, hsars)

        else:
            df = self._daysEngine.getDataFrame(code, startDay, endDay)
            if DyStockCommon.hsarMode == '极值平均': # 把极大值和极小值作为整体看
                hsars = DyStockDataUtility.rwExtremaHSARs(df, w=DyStockCommon.rollingWindowW)
            else:
                hss, hrs = DyStockDataUtility.rwPeakBottomHSARs(df, w=DyStockCommon.rollingWindowW, mean=False)
                hsars = hss + hrs

            self._plotExtremaHSARs(ax, hsars)

    def _plotTrendLine(self, df, ax, xIndex):
        """
            绘制@df的趋势线
            @ax: matplotlib subplot axis
            @xIndex: 子图的x坐标值，X轴位时间
        """
        for i in DyStockCommon.trendLinePeriods:
            if i > df.shape[0]:
                break

            twoPoints, _ = DyStockDataUtility.trendLine(df[-i:])
            if twoPoints is None: continue # 无趋势线

            # get x-coordinates
            x = []
            for i in twoPoints.index:
                try:
                    x_ = xIndex.get_loc(i)
                except Exception as ex:
                    x_ = None

                x.append(x_)

            # 绘制趋势线的两点线段
            ax.plot(x, twoPoints.values, '*-', color='#FF6100', linewidth=1.5, markerfacecolor='#FF6100', markersize=12)
        
            # 趋势延长线
            try:
                y = twoPoints.values
                xExtendPoint = xIndex.get_loc(df.index[-1])
                yExtendPoint = (y[1] - y[0])/(x[1] - x[0]) * (xExtendPoint - x[1]) + y[1]

                ax.plot([x[1], xExtendPoint], [y[1], yExtendPoint], '-', color='#FF6100', linewidth=1.5)
            except Exception as ex:
                pass

    def _plotTrendChannel(self, df, ax, xIndex):
        """
            绘制@df的趋势通道
            @ax: matplotlib subplot axis
            @xIndex: 子图的x坐标值，X轴位时间
        """
        def _plotLine(twoPoints):
            # get x-coordinates
            x = []
            for i in twoPoints.index:
                try:
                    x_ = xIndex.get_loc(i)
                except Exception as ex:
                    x_ = None

                x.append(x_)

            # 绘制趋势线的两点线段
            ax.plot(x, twoPoints.values, '-', color='#FF6100', linewidth=2)
        
            # 趋势延长线
            try:
                y = twoPoints.values
                xExtendPoint = xIndex.get_loc(df.index[-1])
                yExtendPoint = (y[1] - y[0])/(x[1] - x[0]) * (xExtendPoint - x[1]) + y[1]

                ax.plot([x[1], xExtendPoint], [y[1], yExtendPoint], '-', color='#FF6100', linewidth=2)
            except:
                pass

        # get trend channel
        up, down = DyStockDataML.trendChannel(df, DyStockCommon.rollingWindowW)
        if up is None: # 无趋势通道
            return

        # plot trend channel
        _plotLine(up)
        _plotLine(down)

    def plotHSARs(self, code, dates, maIndicator='close'):
        """
            绘制股票的水平支撑和阻力图表，含《专业投机原理》里的趋势线
        """
        # fowarding 59 days for calculating MAs
        dates[0] -= 59

        """ stock """
        # load stock days data
        if not self._daysEngine.loadCode(code, dates):
            return

        DyMatplotlib.newFig()
        f = plt.gcf()

        # get trade day range
        dates[0] += 59 # restore date range
        baseDay, startDay, endDay = self._getTDays(code, dates)

        # plot stock
        periods = self._plotCandleStick(code, startDate=startDay, endDate=endDay, baseDate=baseDay, left=0.05, right=0.95, top=0.95, bottom=0.5, maIndicator=maIndicator)

        # plot regional locals of stock
        df = self._daysEngine.getDataFrame(code, startDay, endDay)
        
        # 滑动窗口极值
        regionalLocals, peaks, bottoms = DyStockDataUtility.rwExtremas(df, w=DyStockCommon.rollingWindowW)
        self._plotRegionalLocals(f.axes[0], df.index, regionalLocals)

        # 欧氏距离极值PIPs
        #regionalLocals, peaks, bottoms = DyStockDataUtility.edExtremaPIPs(df)
        #self._plotRegionalLocals(f.axes[0], df.index, regionalLocals, color='m')

        # plot HSARs of stock
        self._plotTAHSARs(f.axes[0], code, startDay, baseDay)

        # 趋势线
        self._plotTrendLine(df[startDay:baseDay], f.axes[0], df.index)

        """ index """
        # plot index
        indexCode = self._daysEngine.getIndex(code)
        self._daysEngine.loadCode(indexCode, [-59, startDay, endDay])
        self._plotCandleStick(indexCode, periods=periods, baseDate=baseDay, netCapitalFlow=False, left=0.05, right=0.95, top=0.45, bottom=0.05, maIndicator=maIndicator)

        # plot regional locals of index
        df = self._daysEngine.getDataFrame(indexCode, startDay, endDay)

        # 滑动窗口极值
        regionalLocals, peaks, bottoms = DyStockDataUtility.rwExtremas(df, w=DyStockCommon.rollingWindowW)
        self._plotRegionalLocals(f.axes[2], df.ix[periods].index, regionalLocals)

        # 欧氏距离极值PIPs
        #regionalLocals, peaks, bottoms = DyStockDataUtility.edExtremaPIPs(df)
        #self._plotRegionalLocals(f.axes[2], df.ix[periods].index, regionalLocals, color='m')

        # plot HSARs of index
        self._plotTAHSARs(f.axes[2], indexCode, startDay, baseDay, index=True)

        # 趋势线
        self._plotTrendLine(df[startDay:baseDay], f.axes[2], df.ix[periods].index)

        # layout
        plt.setp([a.get_xticklabels() for a in f.axes[:-1]], visible=False)
        f.show()

    def plotVolatilityDist(self, code, baseDate, forwardNTDays):
        """
            波动率分布图
            基准日数据不在直方图里
            计算基准日z-score
        """
        # ---------- stock ----------
        if not self._daysEngine.loadCode(code, [baseDate, -forwardNTDays-1]):
            return

        stockName = self._daysEngine.stockAllCodesFunds[code]
        stockDf = self._daysEngine.getDataFrame(code)

        newBaseDate = stockDf.index[-1].strftime("%Y-%m-%d")

        stockHighAbsoluteVolatility = (stockDf['high'] - stockDf['close'].shift(1))/stockDf['close'].shift(1)
        stockLowAbsoluteVolatility = (stockDf['low'] - stockDf['close'].shift(1))/stockDf['close'].shift(1)
        stockHighLowAbsoluteVolatility = stockHighAbsoluteVolatility - stockLowAbsoluteVolatility

        # 类似于True Range，但这里是比率
        stockTrueAbsoluteVolatility = pd.concat([stockHighAbsoluteVolatility, stockLowAbsoluteVolatility, stockHighLowAbsoluteVolatility], axis=1)
        stockTrueAbsoluteVolatility = stockTrueAbsoluteVolatility.abs()
        stockTrueAbsoluteVolatility = stockTrueAbsoluteVolatility.max(axis=1)

        # ---------- index ----------
        indexCode = self._daysEngine.getIndex(code)
        self._daysEngine.loadCode(indexCode, [stockDf.index[0].strftime("%Y-%m-%d"), stockDf.index[-1].strftime("%Y-%m-%d")])

        indexName = self._daysEngine.stockAllCodesFunds[indexCode]
        indexDf = self._daysEngine.getDataFrame(indexCode)

        indexHighAbsoluteVolatility = (indexDf['high'] - indexDf['close'].shift(1))/indexDf['close'].shift(1)
        indexLowAbsoluteVolatility = (indexDf['low'] - indexDf['close'].shift(1))/indexDf['close'].shift(1)
        indexHighLowAbsoluteVolatility = indexHighAbsoluteVolatility - indexLowAbsoluteVolatility

        # 类似于True Range，但这里是比率
        indexTrueAbsoluteVolatility = pd.concat([indexHighAbsoluteVolatility, indexLowAbsoluteVolatility, indexHighLowAbsoluteVolatility], axis=1)
        indexTrueAbsoluteVolatility = indexTrueAbsoluteVolatility.abs()
        indexTrueAbsoluteVolatility = indexTrueAbsoluteVolatility.max(axis=1)

        # select according to stock DF index
        indexHighAbsoluteVolatility = indexHighAbsoluteVolatility.ix[stockDf.index]
        indexLowAbsoluteVolatility = indexLowAbsoluteVolatility.ix[stockDf.index]
        indexTrueAbsoluteVolatility = indexTrueAbsoluteVolatility.ix[stockDf.index]

        # stock self volatility
        stockHighSelfVolatility = stockHighAbsoluteVolatility - indexHighAbsoluteVolatility
        stockLowSelfVolatility = stockLowAbsoluteVolatility - indexLowAbsoluteVolatility
        stockTrueSelfVolatility = stockTrueAbsoluteVolatility - indexTrueAbsoluteVolatility

        # 命名并concat
        stockHighAbsoluteVolatility.name = '最高绝对波动[{0}]'.format(stockName)
        stockLowAbsoluteVolatility.name = '最低绝对波动[{0}]'.format(stockName)
        stockTrueAbsoluteVolatility.name = '真实绝对波动[{0}]'.format(stockName)

        stockHighSelfVolatility.name = '最高自身波动[{0}]'.format(stockName)
        stockLowSelfVolatility.name = '最低自身波动[{0}]'.format(stockName)
        stockTrueSelfVolatility.name = '真实自身波动[{0}]'.format(stockName)

        indexHighAbsoluteVolatility.name = '最高绝对波动[{0}]'.format(indexName)
        indexLowAbsoluteVolatility.name = '最低绝对波动[{0}]'.format(indexName)
        indexTrueAbsoluteVolatility.name = '真实绝对波动[{0}]'.format(indexName)

        df = pd.concat([stockHighAbsoluteVolatility,
                        stockLowAbsoluteVolatility,
                        stockTrueAbsoluteVolatility,

                        stockHighSelfVolatility,
                        stockLowSelfVolatility,
                        stockTrueSelfVolatility,

                        indexHighAbsoluteVolatility,
                        indexLowAbsoluteVolatility,
                        indexTrueAbsoluteVolatility
                        ], axis=1)

        df *= 100 # %

        # exclude @baseDate
        oldDf = df.ix[:-1]

        # 计算基准日期的对应的z-score
        stds = oldDf.std()
        means = oldDf.mean()

        zscores = (df.ix[-1].values - means.values)/stds.values

        oldDf = oldDf.rename(columns={c: (c + ',z-score:%.2f'%z) for c, z in zip(df.columns, zscores)})

        # plot
        DyMatplotlib.newFig()
        oldDf.hist(color='r', alpha=0.5, bins=100)
        plt.gcf().suptitle('波动分布(%) - 基准日期[{0}],向前{1}个交易日'.format(newBaseDate, forwardNTDays), fontsize=20, color='b')
        plt.gcf().show()

    def plotAtrExtreme(self, code, dates, maIndicator='close'):
        """
            绘制股票的ATR Extreme图表
        """
        # fowarding 59 days for calculating MAs
        dates[0] -= 59

        # load stock days data
        if not self._daysEngine.loadCode(code, dates):
            return

        DyMatplotlib.newFig()
        f = plt.gcf()

        # get trade day range
        dates[0] += 59 # restore date range
        baseDay, startDay, endDay = self._getTDays(code, dates)

        # plot K Chart
        timeIndex = self._plotCandleStick(code, startDate=startDay, endDate=endDay, baseDate=baseDay, left=0.05, right=0.95, top=0.95, bottom=0.5, maIndicator=maIndicator)

        # plot ATR Extreme通道图
        self._plotAtrExtreme(code, timeIndex=timeIndex, left=0.05, right=0.95, top=0.45, bottom=0.05)

        # layout
        plt.setp([a.get_xticklabels() for a in f.axes[:-1]], visible=False)
        f.show()

    def _plotAtrExtreme(self, code, timeIndex=None, left=None, right=None, top=None, bottom=None):
        """
            绘制个股的TTI ATR Exterme通道, which is based on 《Volatility-Based Technical Analysis》
            @timeIndex: 时间索引，主要用来对齐不同子图的时间坐标
        """
        def _dateFormatter(x, pos):
            if not (0 <= int(x) < df.shape[0]):
                return None

            return df.index[int(x)].strftime("%y-%m-%d")

        # create grid spec
        gs = GridSpec(1, 1)
        gs.update(left=left, right=right, top=top, bottom=bottom)

        ax = plt.subplot(gs[:, :])
        ax.set_title('ATR Extreme')
        ax.grid(True)

        # calculate ATR Extreme
        atrExtremeFastPeriod = 3
        emaPeriod = 20
        stdPeriod = 20

        df = self._daysEngine.getDataFrame(code)
        df = DyStockDataUtility.getAtrExtreme(df, emaPeriod=emaPeriod, stdPeriod=stdPeriod, atrExtremeFastPeriod=atrExtremeFastPeriod, dropna=False)

        # slice periods of DF
        if timeIndex is None:
            timeIndex = df.index

        df = df.ix[timeIndex]

        # set x ticks
        x = [x for x in range(df.shape[0])]
        xspace = max((len(x)+9)//10, 1)
        ax.xaxis.set_major_locator(FixedLocator(x[:-xspace-1: xspace] + x[-1:]))
        ax.xaxis.set_major_formatter(FuncFormatter(_dateFormatter))

        # plot ATR简单快速均线
        ax.plot(x, df['ma'].values, label='ma_%s'%atrExtremeFastPeriod)

        # plot ATR慢速指数移动均线
        ax.plot(x, df['ema'].values, label='ema_%s'%emaPeriod)

        # plot ATR布林带
        ax.plot(x, df['ema'].values + df['std'].values, '--', label='上轨')
        ax.plot(x, df['ema'].values - df['std'].values, '--', label='下轨')

        ax.axhline(0, color='k')
        ax.legend(loc='upper left', frameon=False)

        return timeIndex

    def _plotIntraDayCandleStick(self,
                                 code, name,
                                 df,
                                 startDay=None, endDay=None,
                                 refIndex=None,
                                 bar='1min',
                                 left=None, right=None, top=None, bottom=None,
                                 maIndicator='close'
                                 ):
        """
            股票日内K线图
            成交量单位是手
            @refIndex: 参照的周期索引，主要用来对齐不同子图的时间坐标
        """
        def _timeFormatter(x, pos):
            if not 0 <= int(x) < df.shape[0]:
                return None

            if 'min' in bar:
                return df.index[int(x)].strftime('%Y-%m-%d %H:%M')
            else:
                return df.index[int(x)].strftime('%Y-%m-%d %H:%M:%S')

        # get MA DataFrame
        maDf = DyStockDataUtility.getMas(df, [5, 10, 20, 30, 60], dropna=False, indicator=maIndicator)

        # data wrangle
        if refIndex is None:
            if startDay and endDay:
                df = df.ix[startDay:endDay]
                maDf = maDf.ix[startDay:endDay]

            refIndex = df.index

        else: # 数据对齐
            df = df.ix[refIndex]
            maDf = maDf.ix[refIndex]

        if df.shape[0] == 0 or maDf.shape[0] == 0:
            return refIndex

        highest = df['high'].max()
        lowest = df['low'].min()

        # create grid spec
        gs = GridSpec(4, 1)
        gs.update(left=left, right=right, top=top, bottom=bottom, hspace=0)

        # subplot for price candle stick
        axPrice = plt.subplot(gs[:-1, :])
        axPrice.grid(True)
        axPrice.set_title('{0}({1}),均线指标:{2},交易日:[{3}~{4}],振幅:{5}%,{6}'.format(name, code,
                                                                            DyStockCommon.indicatorNameTable[maIndicator],
                                                                            startDay, endDay,
                                                                            '%.2f'%((highest - lowest)*100/lowest),
                                                                            bar
                                                                            ))

        # set x ticks
        x = [x for x in range(df.shape[0])]
        xspace = max((len(x)+9)//10, 1)
        axPrice.xaxis.set_major_locator(FixedLocator(x[:-xspace-1: xspace] + x[-1:]))
        axPrice.xaxis.set_major_formatter(FuncFormatter(_timeFormatter))

        # plot K-chart
        lineCollection, barCollection = candlestick2_ohlc(axPrice, df['open'].values, df['high'].values, df['low'].values, df['close'].values, width=.9, colorup='r', colordown='g', alpha=1)
        barCollection.set_edgecolor('face') # 边框同色
        lineCollection.set_color(barCollection.get_facecolor())

        # plot MAs
        for ma in maDf.columns:
            axPrice.plot(x, maDf[ma].values, label=ma)

        # plot volume
        axVolume = plt.subplot(gs[-1, :], sharex=axPrice)
        axVolume.grid(True)
        barCollection = volume_overlay(axVolume, df['open'].values, df['close'].values, df['volume'].values/10**2, colorup='r', colordown='g', width=.9, alpha=1)
        barCollection.set_edgecolor('face') # 边框同色

        axPrice.legend(loc='upper left', frameon=False)

        return refIndex

    def plotIntraDayCandleStick(self, code, dates, bar='1min', maIndicator='close'):
        """
            日内K线图
            @dates: [-n, baseDate, n]
        """
        # get actual days
        if not self._daysEngine.loadCode(code, dates):
            return

        dayDf = self._daysEngine.getDataFrame(code)
        days = [date.strftime("%Y-%m-%d") for date in dayDf.index]

        # name
        name = self._daysEngine.stockAllCodesFunds[code]

        # load ticks
        dates[0] -= 1 # 为了计算均线
        if not self._ticksEngine.loadCodeN(code, dates):
            return

        # tick DF
        tickDf = self._ticksEngine.getDataFrame(code, adj=True, continuous=True)

        # 合成Bar, 右闭合
        # 缺失的Bar设为NaN
        barDf = tickDf.resample(bar, closed='right', label='right')[['price', 'volume']].agg(OrderedDict([('price', 'ohlc'), ('volume', 'sum')]))
        barDf.dropna(inplace=True) # drop缺失的Bars

        # remove multi-index of columns
        barDf = pd.concat([barDf['price'], barDf['volume']], axis=1)

        DyMatplotlib.newFig()

        # plot
        self._plotIntraDayCandleStick(code, name,
                                      barDf,
                                      days[0], days[-1],
                                      bar=bar,
                                      left=0.05, right=0.95, top=0.95, bottom=0.5,
                                      maIndicator=maIndicator
                                      )

        # layout
        f = plt.gcf()
        plt.setp([a.get_xticklabels() for a in f.axes[:-1]], visible=False)
        f.show()
                      
    def _plotVolatilityChart(self,
                             df,
                             startDay=None, endDay=None,
                             refIndex=None,
                             volatilityVolumePeriod=20,
                             left=None, right=None, top=None, bottom=None
                             ):
        """
            股票波动率图（Bar图）
            @refIndex: 参照的周期索引，主要用来对齐不同子图的时间坐标
        """
        def _dateFormatter(x, pos):
            if not (0 <= int(x) < df.shape[0]):
                return None

            return df.index[int(x)].strftime("%y-%m-%d")

        # data wrangle
        if refIndex is None:
            if startDay and endDay:
                df = df.ix[startDay:endDay]

            refIndex = df.index

        else: # 数据对齐
            df = df.ix[refIndex]

        if df.shape[0] == 0:
            return refIndex

        # 波动率
        highAbsoluteVolatility = (df['high'] - df['close'].shift(1))/df['close'].shift(1)
        lowAbsoluteVolatility = (df['low'] - df['close'].shift(1))/df['close'].shift(1)
        highLowAbsoluteVolatility = highAbsoluteVolatility - lowAbsoluteVolatility

        # 类似于True Range，但这里是比率
        trueAbsoluteVolatility = pd.concat([highAbsoluteVolatility, lowAbsoluteVolatility, highLowAbsoluteVolatility], axis=1)
        trueAbsoluteVolatility = trueAbsoluteVolatility.abs()
        trueAbsoluteVolatility = trueAbsoluteVolatility.max(axis=1)
        trueAbsoluteVolatility *= 100

        # create grid spec
        gs = GridSpec(4, 1)
        gs.update(left=left, right=right, top=top, bottom=bottom, hspace=0)

        # subplot for volatility
        ax = plt.subplot(gs[:, :])
        ax.grid(True)
        ax.set_title('波动率')

        # set x ticks
        x = [x for x in range(df.shape[0])]
        xspace = max((len(x)+9)//10, 1)
        ax.xaxis.set_major_locator(FixedLocator(x[:-xspace-1: xspace] + x[-1:]))
        ax.xaxis.set_major_formatter(FuncFormatter(_dateFormatter))

        # plot volatility
        ax.bar(x, trueAbsoluteVolatility.values, width=.9, color='b', label='波动率(%)')

        # plot combined volatility
        volumeRatios = df['volume']/df['volume'].shift(1)
        combinedVolatility = trueAbsoluteVolatility*np.sqrt(volumeRatios)
        ax.plot(x, combinedVolatility.values, color='r', label='波动率*√量比(%)')

        yMax = combinedVolatility.max()
        for i in range(1, int(yMax)):
            ax.axhline(i, color='y', linewidth=.2)

        # plot bband of combined volatility
        try:
            upper, middle, lower = talib.BBANDS(
                                    combinedVolatility.values, 
                                    timeperiod=volatilityVolumePeriod,
                                    # number of non-biased standard deviations from the mean
                                    nbdevup=1,
                                    nbdevdn=1,
                                    # Moving average type: simple moving average here
                                    matype=0)

            ax.plot(x, middle, color='k', label='波动率*√量比{}日均值(%)'.format(volatilityVolumePeriod))

            std = upper - middle
            for i in range(1, 4):
                ax.plot(x, middle + i*std, '--')
        except:
            pass

        ax.legend(loc='upper left', frameon=False)

        return refIndex

    def plotVolatilityChart(self, code, dates, volatilityVolumePeriod=20, maIndicator='close'):
        """
            波动率图
            @dates: [-n, baseDate, n]
            @volatilityVolumePeriod: 波动率量比的均值周期，用来画布林通道用
        """
        # fowarding 59 days for calculating MAs
        dates[0] -= 59

        # load stock days data
        if not self._daysEngine.loadCode(code, dates):
            return

        df = self._daysEngine.getDataFrame(code)

        DyMatplotlib.newFig()

        # get date range
        dates[0] += 59 # restore date range
        baseDay, startDay, endDay = self._getTDays(code, dates)

        # plot stock
        periods = self._plotCandleStick(code, startDate=startDay, endDate=endDay, baseDate=baseDay, left=0.05, right=0.95, top=0.95, bottom=0.5, maIndicator=maIndicator)

        # plot volatility chart
        self._plotVolatilityChart(df, refIndex=periods, volatilityVolumePeriod=volatilityVolumePeriod, left=0.05, right=0.95, top=0.45, bottom=0.05)

        # layout
        f = plt.gcf()
        plt.setp([a.get_xticklabels() for a in f.axes[:-1]], visible=False)
        f.show()

    def plotSwingChart(self, code, dates, maIndicator='close'):
        """
            绘制股票的波段图
            @dates: [-n, baseDate, n]
        """
        # fowarding 59 days for calculating MAs
        dates[0] -= 59

        """ stock """
        # load stock days data
        if not self._daysEngine.loadCode(code, dates):
            return

        DyMatplotlib.newFig()
        f = plt.gcf()

        # get trade day range
        dates[0] += 59 # restore date range
        baseDay, startDay, endDay = self._getTDays(code, dates)

        #df = self._daysEngine.getDataFrame(code, startDay, endDay)
        #DyStockDataML.predictReboundVol(df)

        # plot stock
        periods = self._plotCandleStick(code, startDate=startDay, endDate=endDay, baseDate=baseDay, left=0.05, right=0.95, top=0.95, bottom=0.5, maIndicator=maIndicator)

        # plot swing
        df = self._daysEngine.getDataFrame(code, startDay, endDay)
        regionalLocals, peaks, bottoms = DyStockDataUtility.swings(df, w=DyStockCommon.rollingWindowW)
        self._plotRegionalLocals(f.axes[0], df.index, regionalLocals)

        """ index """
        # plot index
        indexCode = self._daysEngine.getIndex(code)
        self._daysEngine.loadCode(indexCode, [-59, startDay, endDay])
        self._plotCandleStick(indexCode, periods=periods, baseDate=baseDay, netCapitalFlow=False, left=0.05, right=0.95, top=0.45, bottom=0.05, maIndicator=maIndicator)

        # plot swing
        df = self._daysEngine.getDataFrame(indexCode, startDay, endDay)
        regionalLocals, peaks, bottoms = DyStockDataUtility.swings(df, w=DyStockCommon.rollingWindowW)
        self._plotRegionalLocals(f.axes[2], df.ix[periods].index, regionalLocals)

        # layout
        plt.setp([a.get_xticklabels() for a in f.axes[:-1]], visible=False)
        f.show()

    def plotTrendChannelChart(self, code, dates, maIndicator='close'):
        """
            绘制股票的趋势通道图
            @dates: [-n, baseDate, n]
        """
        # fowarding 59 days for calculating MAs
        dates[0] -= 59

        """ stock """
        # load stock days data
        if not self._daysEngine.loadCode(code, dates):
            return

        DyMatplotlib.newFig()
        f = plt.gcf()

        # get trade day range
        dates[0] += 59 # restore date range
        baseDay, startDay, endDay = self._getTDays(code, dates)

        # plot stock K chart
        periods = self._plotCandleStick(code, startDate=startDay, endDate=endDay, baseDate=baseDay, left=0.05, right=0.95, top=0.95, bottom=0.5, maIndicator=maIndicator)

        df = self._daysEngine.getDataFrame(code, startDay, endDay)

        # plot trend channel
        self._plotTrendChannel(df[startDay:baseDay], f.axes[0], df.index)

        # plot swing
        regionalLocals, peaks, bottoms = DyStockDataUtility.swings(df, w=DyStockCommon.rollingWindowW)
        self._plotRegionalLocals(f.axes[0], df.index, regionalLocals)

        """ index """
        # plot index K chart
        indexCode = self._daysEngine.getIndex(code)
        self._daysEngine.loadCode(indexCode, [-59, startDay, endDay])
        self._plotCandleStick(indexCode, periods=periods, baseDate=baseDay, netCapitalFlow=False, left=0.05, right=0.95, top=0.45, bottom=0.05, maIndicator=maIndicator)

        df = self._daysEngine.getDataFrame(indexCode, startDay, endDay)

        # plot trend channel
        self._plotTrendChannel(df[startDay:baseDay], f.axes[2], df.ix[periods].index)

        # plot swing
        regionalLocals, peaks, bottoms = DyStockDataUtility.swings(df, w=DyStockCommon.rollingWindowW)
        self._plotRegionalLocals(f.axes[2], df.ix[periods].index, regionalLocals)

        # layout
        plt.setp([a.get_xticklabels() for a in f.axes[:-1]], visible=False)
        f.show()

    def plotBuySellDayCandleStick(self, code, buySellDates, maIndicator='close'):
        """
            绘制有买卖标记的股票日K线
        """
        if not buySellDates:
            return

        # calculate date range
        dates = sorted(buySellDates)
        tDaysCount = self._daysEngine.tDaysCountInDb(dates[0], dates[-1])

        dates = [-DyStockCommon.dayKChartPeriodNbr, dates[0], tDaysCount + DyStockCommon.dayKChartPeriodNbr]

        # fowarding 59 days for calculating MAs
        dates[0] -= 59
        
        # load stock days data
        if not self._daysEngine.loadCode(code, dates):
            return

        DyMatplotlib.newFig()

        # get date range
        dates[0] += 59 # restore date range
        baseDay, startDay, endDay = self._getTDays(code, dates)

        # plot stock
        periods = self._plotBuySellDayCandleStick(code, buySellDates,
                                                  startDate=startDay, endDate=endDay,
                                                  left=0.05, right=0.95, top=0.95, bottom=0.5,
                                                  maIndicator=maIndicator)

        # plot index
        indexCode = self._daysEngine.getIndex(code)
        self._plotBuySellDayCandleStick(indexCode, buySellDates,
                                        periods=periods,
                                        left=0.05, right=0.95, top=0.45, bottom=0.05,
                                        maIndicator=maIndicator)

        # layout
        f = plt.gcf()
        plt.setp([a.get_xticklabels() for a in f.axes[:-1]], visible=False)
        f.show()

    def _plotBuySellDayCandleStick(self, code, buySellDates,
                                   startDate=None, endDate=None,
                                   periods=None,
                                   left=None, right=None, top=None, bottom=None,
                                   maIndicator='close'):
        """
            股票有买卖记号的日线K线图
            成交量单位是万手
            @buySellDates: {date: '买入', date: '卖出'}
            @periods: 周期索引，主要用来对齐不同子图的时间坐标
            @return: periods or None
        """
        def _dateFormatter(x, pos):
            if not (0 <= int(x) < df.shape[0]):
                return None

            return df.index[int(x)].strftime("%y-%m-%d")

        # get DataFrame
        df = self._daysEngine.getDataFrame(code)
        if df is None:
            return None

        maDf = DyStockDataUtility.getMas(df, [5, 10, 20, 30, 60], False, maIndicator)

        if periods is None:
            if startDate is not None and endDate is not None:
                df = df.ix[startDate:endDate]
                maDf = maDf.ix[startDate:endDate]

            periods = df.index
        else:
            # 数据对齐
            df = df.ix[periods]
            maDf = maDf.ix[periods]

        if df.shape[0] == 0 or maDf.shape[0] == 0:
            return periods

        highest = df['high'].max()
        lowest = df['low'].min()

        # create grid spec
        gs = GridSpec(4, 1)
        gs.update(left=left, right=right, top=top, bottom=bottom, hspace=0)

        # subplot for price candle stick
        axPrice = plt.subplot(gs[:-1, :])
        axPrice.set_title('{0}({1}),均线指标:{2},交易日数:{3},振幅:{4}%'.format(self._daysEngine.stockAllCodesFunds[code],
                                                                            code,
                                                                            DyStockCommon.indicatorNameTable[maIndicator],
                                                                            periods.shape[0],
                                                                            '%.2f'%((highest - lowest)*100/lowest)
                                                                            ))
        axPrice.grid(True)

        # set x ticks
        x = [x for x in range(df.shape[0])]
        xspace = max((len(x)+9)//10, 1)
        axPrice.xaxis.set_major_locator(FixedLocator(x[:-xspace-1: xspace] + x[-1:]))
        axPrice.xaxis.set_major_formatter(FuncFormatter(_dateFormatter))

        # plot K-chart
        lineCollection, barCollection = candlestick2_ohlc(axPrice, df['open'].values, df['high'].values, df['low'].values, df['close'].values, width=.9, colorup='r', colordown='g', alpha=1)
        barCollection.set_edgecolor('face') # 边框同色
        lineCollection.set_color(barCollection.get_facecolor())

        # plot MAs
        for ma in maDf.columns:
            axPrice.plot(x, maDf[ma].values, label=ma)

        # plot volume
        axVolume = plt.subplot(gs[-1, :], sharex=axPrice)
        axVolume.grid(True)
        barCollection = volume_overlay(axVolume, df['open'].values, df['close'].values, df['volume'].values/10**6, colorup='r', colordown='g', width=.9, alpha=1)
        barCollection.set_edgecolor('face') # 边框同色

        # 标记买卖日期
        for date, type in buySellDates.items():
            try:
                x = df.index.get_loc(date)

                yLimitBottom, yLimitTop = axPrice.get_ylim()
                dateYOffset = (yLimitTop - yLimitBottom)*0.08

                if type == '卖出':
                    y = df.ix[date, 'high']
                    symbol = 'S'
                    color = 'g'
                    verticalalignment = 'bottom'
                else:
                    y = df.ix[date, 'low']
                    symbol = 'B'
                    color = 'r'
                    verticalalignment = 'top'

                    dateYOffset = -dateYOffset

                axPrice.text(x, y, symbol,
                             color='k',
                             verticalalignment=verticalalignment,
                             horizontalalignment='center')
                axPrice.text(x, y + dateYOffset, date[2:], horizontalalignment='center')
            except:
                pass

        axPrice.legend(loc='upper left', frameon=False)

        return periods


    ############################################################################################################################
    ############################################################################################################################
    ############################################################################################################################
    # -------------------------------------------------- Test --------------------------------------------------
    # -------------------------------------------------- Test --------------------------------------------------
    # -------------------------------------------------- Test --------------------------------------------------
    ############################################################################################################################
    ############################################################################################################################
    ############################################################################################################################
    def plotReqTest(self):
        self._plotReqHSARs()
        #self._plotReqRWExtremas()

    def plotAckTest(self, event):
        #self._plotAckRWExtremas(event)
        self._plotAckHSARs(event)

    def _plotReqRWExtremas(self):
        self._daysEngine.load(['2016-01-10', '2016-10-21'], codes=['002551.SZ'])
        df = self._daysEngine.getDataFrame('002551.SZ')

        regionalLocals, peaks, bottoms = DyStockDataUtility.rwExtremas(df)

        #regionalLocals = DyStockDataUtility.edPIPs(df, 20)

        # put event to UI
        event = DyEvent(DyEventType.plotAck)
        event.data['plot'] = self.plotAckTest
        event.data['code'] = '002551.SZ'
        event.data['df'] = df
        event.data['regionalLocals'] = regionalLocals

        self._eventEngine.put(event)

    def _plotAckRWExtremas(self, event):
        code = event.data['code']
        df = event.data['df']
        regionalLocals = event.data['regionalLocals']

        DyMatplotlib.newFig()
        f = plt.gcf()

        index = df.index
        startDay = index[0].strftime('%Y-%m-%d')
        endDay = index[-1].strftime('%Y-%m-%d')

        # plot stock
        periods = self._plotCandleStick(code, startDate=startDay, endDate=endDay, baseDate=endDay, left=0.05, right=0.95, top=0.95, bottom=0.5, maIndicator='close')

        self._plotRegionalLocals(f.axes[0], index, regionalLocals)

        plt.setp([a.get_xticklabels() for a in f.axes[:-1]], visible=False)
        f.show()

    def _plotReqHSARs(self):
        code = '002551.SZ'
        self._ticksEngine.loadCodeN('002551.SZ', ['2016-01-10', '2016-10-21'])
        df = self._ticksEngine.getDataFrame('002551.SZ', adj=True)
        daysDf = self._ticksEngine.getDaysDataFrame(code)

        hsars = DyStockDataUtility.dealsHSARs(df)

        # put event to UI
        event = DyEvent(DyEventType.plotAck)
        event.data['plot'] = self.plotAckTest
        event.data['code'] = '002551.SZ'
        event.data['df'] = daysDf
        event.data['hsars'] = hsars

        self._eventEngine.put(event)

    def _plotAckHSARs(self, event):
        code = event.data['code']
        df = event.data['df']
        hsars = event.data['hsars']

        DyMatplotlib.newFig()
        f = plt.gcf()

        index = df.index
        startDay = index[0].strftime('%Y-%m-%d')
        endDay = index[-1].strftime('%Y-%m-%d')

        # plot stock
        periods = self._plotCandleStick(code, startDate=startDay, endDate=endDay, baseDate=endDay, left=0.05, right=0.95, top=0.95, bottom=0.5, maIndicator='close')

        self._plotHSARs(f.axes[0], hsars)

        plt.setp([a.get_xticklabels() for a in f.axes[:-1]], visible=False)
        f.show()

    def plotReqSvm(self):
        from sklearn import svm

        # get Index MAs statistic
        stats = DyStockDataUtility.getIndexMaStats('2015-07-01', '2015-12-31', self._daysEngine, self._info, '000001.SH', self._testedStocks)
        if stats is None: return

        masStatsDf = stats['000001.SH'].ix[:, ['ma5', 'ma60']]

        self._daysEngine.load(['2015-07-01', '2015-12-31', 5], codes=[])

        df = self._daysEngine.getDataFrame('000001.SH')
        shift = df['close'].shift(-5)
        increase = (shift - df['close'])*100/df['close']
        increase = increase.dropna()
        increase = increase.astype(int)

        clf = svm.SVC()

        self._info.print('开始SVM拟合...')

        clf.fit(masStatsDf.values, increase.values)

        self._info.print('SVM拟合结束')


        # get Index MAs statistic
        stats = DyStockDataUtility.getIndexMaStats('2016-01-01', '2016-07-01', self._daysEngine, self._info, '000001.SH', self._testedStocks)
        if stats is None: return

        masStatsDf = stats['000001.SH'].ix[:, ['ma5', 'ma60']]

        self._daysEngine.load(['2016-01-01', '2016-07-01', 5], codes=[])

        df = self._daysEngine.getDataFrame('000001.SH')
        shift = df['close'].shift(-5)
        increase = (shift - df['close'])*100/df['close']
        increase = increase.dropna()


        self._info.print('开始SVM预测...')

        predictIncrease = clf.predict(masStatsDf.values)

        self._info.print('SVM预测结束')

        # put event to UI
        event = DyEvent(DyEventType.plotAck)
        event.data['plot'] = self.plotAckSvm
        event.data['increase'] = increase
        event.data['predictIncrease'] = predictIncrease

        self._eventEngine.put(event)

    def plotReqOls(self):
        import statsmodels.api as sm
        import statsmodels.formula.api as smf

        # get Index MAs statistic
        stats = DyStockDataUtility.getIndexMaStats('2015-07-01', '2015-12-31', self._daysEngine, self._info, '000001.SH', self._testedStocks)
        if stats is None: return

        masStatsDf = stats['000001.SH']

        self._daysEngine.load(['2015-07-01', '2015-12-31', 5], codes=[])

        df = self._daysEngine.getDataFrame('000001.SH')
        shift = df['close'].shift(-5)
        increase = (shift - df['close'])*100/df['close']
        increase = increase.dropna()
        increase.name = 'increase'

        newDf = pd.concat([increase, masStatsDf], axis=1)

        self._info.print('开始OLS拟合...')

        #model = smf.ols('increase ~ ma5 + ma10 + ma20 + ma30 + ma60', data=newDf)
        model = smf.ols('increase ~ ma5', data=newDf)
        model.fit()

        self._info.print('OLS拟合结束')


        # get Index MAs statistic
        stats = DyStockDataUtility.getIndexMaStats('2016-01-01', '2016-07-01', self._daysEngine, self._info, '000001.SH', self._testedStocks)
        if stats is None: return

        masStatsDf = stats['000001.SH']

        self._daysEngine.load(['2016-01-01', '2016-07-01', 5], codes=[])

        df = self._daysEngine.getDataFrame('000001.SH')
        shift = df['close'].shift(-5)
        increase = (shift - df['close'])*100/df['close']
        increase = increase.dropna()

        self._info.print('开始OLS预测...')

        predictIncrease = model.predict(masStatsDf)

        self._info.print('OLS预测结束')

        # put event to UI
        event = DyEvent(DyEventType.plotAck)
        event.data['plot'] = self.plotAckSvm
        event.data['increase'] = increase
        event.data['predictIncrease'] = predictIncrease

        self._eventEngine.put(event)

    def plotAckSvm(self, event):

        # unpack
        increase = event.data['increase']
        predictIncrease = event.data['predictIncrease']

        plt.plot(increase.values, color='r')
        plt.plot(predictIncrease, color='b')

        plt.show()

    def plotReqMasXAngels(self):
        self._daysEngine.load([-59, '2016-01-01', '2016-08-19'], codes=[])
        df = self._daysEngine.getDataFrame('000001.SH')

        masDf = DyStockDataUtility.getMas(df, [5,10,20,30,60])

        self._daysEngine.load(['2016-01-01', '2016-08-19'], codes=[])

        df = self._daysEngine.getDataFrame('000001.SH')

        orgY = df['low'].min()

        masXAngels = []

        for col in masDf.columns:
            xAngels = DyStockDataUtility.xAngles(masDf[col], orgY, masDf.shape[0]//2)

            masXAngels.append(xAngels)

        df = pd.concat(masXAngels, axis=1)

        # put event to UI
        event = DyEvent(DyEventType.plotAck)
        event.data['plot'] = self.plotAckMasXAngels
        event.data['df'] = df

        self._eventEngine.put(event)

    def plotAckMasXAngels(self, event):
        # unpack
        df = event.data['df']

        # change index to string
        df.index = df.index.map(lambda x: x.strftime('%Y-%m-%d'))

        # change index to column
        df.reset_index(inplace=True)
        df.rename(columns={'index':'日期'}, inplace=True)

        self.window = DyStatsDataFrameTableWidget(df)

        for row in range(self.window.rowCount()):
            color = True
            for col in range(self.window.columnCount()):
                if col == 0: continue

                if self.window[row, col] < 0:
                    color = False
                    break

            if color:
                self.window.setRowForeground(row, Qt.red)

        self.window.show()

    def plotReqKama(self):
        # put event to UI
        event = DyEvent(DyEventType.plotAck)
        event.data['plot'] = self.plotAckKama

        self._eventEngine.put(event)

    def plotAckKama(self, event):
        code, startDate, endDate = '002551.SZ', '2015-07-01', '2016-03-01'

        # load
        if not self._daysEngine.load([-200, startDate, endDate], codes=[code]):
            return

        DyMatplotlib.newFig()

        # plot basic stock K-Chart
        periods = self._plotCandleStick(code, startDate=startDate, endDate=endDate, netCapitalFlow=True, left=0.05, right=0.95, top=0.95, bottom=0.5)
        
        # plot customized stock K-Chart
        self._plotKamaCandleStick(code, periods=periods, left=0.05, right=0.95, top=0.45, bottom=0.05)

        # layout
        f = plt.gcf()
        plt.setp([a.get_xticklabels() for a in f.axes[:-1]], visible=False)
        f.show()

    def _plotKamaCandleStick(self, code, periods, left=None, right=None, top=None, bottom=None):
        def _dateFormatter(x, pos):
            if not (0 <= int(x) < df.shape[0]):
                return None

            return df.index[int(x)].strftime("%y-%m-%d")

        # get DataFrame
        df = self._daysEngine.getDataFrame(code)
        #maDf = DyStockDataUtility.getKamas(df, [5, 10], False)
        maDf = DyStockDataUtility.getDealMas(df, [5, 10, 20, 30, 60], False)

        # 数据对齐
        df = df.ix[periods]
        maDf = maDf.ix[periods]

        if df.shape[0] == 0 or maDf.shape[0] == 0:
            return

        # create grid spec
        gs = GridSpec(4, 1)
        gs.update(left=left, right=right, top=top, bottom=bottom, hspace=0)

        # subplot for price candle stick
        axPrice = plt.subplot(gs[:-1, :])
        axPrice.set_title('{0}({1}),考夫曼指标'.format(self._daysEngine.stockAllCodesFunds[code], code))
        axPrice.grid(True)

        # set x ticks
        x = [x for x in range(df.shape[0])]
        xspace = max((len(x)+9)//10, 1)
        axPrice.xaxis.set_major_locator(FixedLocator(x[:-xspace-1: xspace] + x[-1:]))
        axPrice.xaxis.set_major_formatter(FuncFormatter(_dateFormatter))

        # plot K-chart
        candlestick2_ohlc(axPrice, df['open'].values, df['high'].values, df['low'].values, df['close'].values, width=.9, colorup='r', colordown='g', alpha =1)

        # plot MAs
        for ma in maDf.columns:
            axPrice.plot(x, maDf[ma].values, label=ma)

        # plot volume
        axVolume = plt.subplot(gs[-1, :], sharex=axPrice)
        axVolume.grid(True)
        volume_overlay(axVolume, df['open'].values, df['close'].values, df['volume'].values/10**6, colorup='r', colordown='g', width=.9, alpha=1)

        axPrice.legend(loc='upper left', frameon=False)
