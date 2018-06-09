from .DyStockDataViewer import *

from .JaccardIndex.DyStockDataJaccardIndexMainWindow import *
from .IndexConsecutiveDayLineStats.DyStockDataIndexConsecutiveDayLineStatsTabWidget import *
from .LimitUpStats.DyStockDataLimitUpStatsMainWindow import *
from .FocusAnalysis.DyStockDataFocusAnalysisMainWindow import *
from ..Utility.Other.DyStockDataFocusAnalysisUtility import *


class DyStockDataWindow(object):
    """ 股票数据自定义窗口生成展示，非matplotlib窗口 """

    def __init__(self, dataEngine, info=None):
        self._dataEngine = dataEngine
        self._info = info

        self._progress = DyProgress(self._info)
        self._dataViewer = DyStockDataViewer(dataEngine, info)

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

    @property
    def dataViewer(self):
        return self._dataViewer

    def setTestedStocks(self, codes):
        self._testedStocks = codes

    def plotReqMaStats(self, startDate, endDate, index, mas, vmas):
        # close
        stats = DyStockDataUtility.getIndexMaStats(startDate, endDate, self._daysEngine, self._info, index, self._testedStocks, floatMarketValue=False)
        if stats is None: return

        # 收盘价均线离差比
        diffStats = DyStockDataUtility.getIndexDiffMaStats(startDate, endDate, self._daysEngine, self._info, index, self._testedStocks, load=False)
        if diffStats is None: return

        # volume
        volStats = DyStockDataUtility.getIndexVolumeMaStats(startDate, endDate, self._daysEngine, self._info, index, self._testedStocks, False)
        if volStats is None: return

        # concat
        for index_ in stats:
            stats[index_] = pd.concat([stats[index_], diffStats[index_], volStats[index_]], axis=1)

        # put event to UI
        event = DyEvent(DyEventType.plotAck)
        event.data['plot'] = self.plotAckMaStats
        event.data['stats'] = stats
        event.data['index'] = index
        event.data['mas'] = mas
        event.data['vmas'] = vmas

        self._eventEngine.put(event)

    def plotAckMaStats(self, event):
        # unpack
        stats = event.data['stats']
        index = event.data['index']
        mas = event.data.get('mas')
        vmas = event.data.get('vmas')

        if index is None:
            self._plotIndexesMaStats(stats, mas, vmas)

        else:
            self._showIndexMaKChartWindow(index, stats[index])

    def _plotIndexMaStats(self, index, df, indicators, left=None, right=None, top=None, bottom=None):
        def _dateFormatter(x, pos):
            if not (0 <= int(x) < df.shape[0]):
                return None

            return df.index[int(x)].strftime("%y-%m-%d")

        # create grid spec
        gs = GridSpec(1, 1)
        gs.update(left=left, right=right, top=top, bottom=bottom)

        # subplot for index MA stats
        ax = plt.subplot(gs[:, :])
        ax.set_title('{0}({1})'.format(DyStockCommon.getIndexesSectors()[index], index))
        ax.grid(True)

        # set x ticks
        x = [x for x in range(df.shape[0])]
        xspace = max((len(x)+9)//10, 1)
        ax.xaxis.set_major_locator(FixedLocator(x[:-xspace-1: xspace] + x[-1:]))
        ax.xaxis.set_major_formatter(FuncFormatter(_dateFormatter))

        # construct show indicators from DF
        mas = []
        for ind, values in indicators.items():
            mas += [ind + str(key) for key, _ in values.items()]

        # plot
        for ma in df.columns:
            if ma in mas:
                ax.plot(x, df[ma].values, label=ma)

        # construct indciator MAs
        for ind, values in indicators.items():
            for key, value in values.items():
                if not value: continue

                indDf = DyStockDataUtility.getMas(df, value, dropna=False, indicator=ind + str(key))
                for ma in indDf.columns:
                    ax.plot(x, indDf[ma].values, label=ind + str(key) + '_' + ma[2:])

        ax.legend(loc='upper left', frameon=False)

    def _plotIndexesMaStats(self, stats, mas, vmas):

        indicators = {'ma': {x: [] for x in mas},
                      'vma': {x: [] for x in vmas}
                      }

        DyMatplotlib.newFig()

        nbr = len(stats)
        hspace = 0.1/(nbr - 1)
        height = 0.9/nbr

        for i, index in enumerate(stats):
            self._plotIndexMaStats(index, stats[index], indicators, left=0.05, right=0.95, top=0.98 - i*height - hspace, bottom=0.98 - (i+1)*height)

        # layout
        f = plt.gcf()
        plt.setp([a.get_xticklabels() for a in f.axes[:-1]], visible=False)
        f.show()

    def _showIndexMaKChartWindow(self, index, df):
        """
            显示均线统计窗口
        """
        window = DyStockDataIndexMaStatsMainWindow(self, index, DyStockCommon.getIndexesSectors()[index], df)
        window.show()
        self._windows.append(window)

    def plotIndexMaKChartStats(self, index, df, indicators):
        """
            画指数均线统计K线图
            @index: 指数代码
            @df: 指数均线统计数据DF
            @indicators: 图示哪些指标
                         {'ma': {5: [5, 10]},
                          'vma': {5: [5, 10]},
                          'dma': {5: [5, 10]}
                         }
        """
        # ----- 均线K线统计图 -----
        startDay = df.index[0].strftime("%Y-%m-%d")
        endDay = df.index[-1].strftime("%Y-%m-%d")

        # fowarding 59 days for calculating MAs
        dates = [-119, startDay, endDay]

        # load
        if not self._daysEngine.load(dates, codes=[index]):
            return

        DyMatplotlib.newFig()

        self._dataViewer._plotCandleStick(index, startDate=startDay, endDate=endDay, netCapitalFlow=False, left=0.05, right=0.95, top=0.95, bottom=0.5)

        self._plotIndexMaStats(index, df, indicators, left=0.05, right=0.95, top=0.45, bottom=0.05)

        # layout
        f = plt.gcf()
        plt.setp([a.get_xticklabels() for a in f.axes[:-1]], visible=False)
        f.show()

    def plotReqJaccardIndex(self, startDate, endDate, param):
        """
            统计指数板块的杰卡德指数的请求, 主要是计算UI所需要的数据
        """
        load = True
        orgDfs, jaccardDfs, codeSetDfs, codeIncreaseDfDicts = {}, {}, {}, {}
        for index in DyStockCommon.indexes:
            orgDf, jaccardDf, codeSetDf, codeIncreaseDfDict, codeTable = DyStockDataUtility.getJaccardIndex(index, startDate, endDate, param, self._daysEngine, self._info, self._testedStocks, load)
            if jaccardDf is None: return

            load = False
            orgDfs[index] = orgDf
            jaccardDfs[index] = jaccardDf
            codeSetDfs[index] = codeSetDf
            codeIncreaseDfDicts[index] = codeIncreaseDfDict

        # put event to UI
        event = DyEvent(DyEventType.plotAck)
        event.data['plot'] = self.plotAckJaccardIndex
        event.data['orgDfs'] = orgDfs
        event.data['jaccardDfs'] = jaccardDfs
        event.data['codeSetDfs'] = codeSetDfs
        event.data['codeIncreaseDfDicts'] = codeIncreaseDfDicts
        event.data['codeTable'] = codeTable

        self._eventEngine.put(event)

    def plotAckJaccardIndex(self, event):
        """
        统计指数板块的杰卡德指数的Ack, 主要是UI操作
        """
        # unpack
        orgDfs = event.data['orgDfs']
        jaccardDfs = event.data['jaccardDfs']
        codeSetDfs = event.data['codeSetDfs']
        codeIncreaseDfDicts = event.data['codeIncreaseDfDicts']
        codeTable = event.data['codeTable']

        # new DyStockDataViewer instance so that plot can run parallelly
        errorInfo = DyErrorInfo(self._eventEngine)
        dataEngine = DyStockDataEngine(self._eventEngine, errorInfo, False)
        dataViewer = DyStockDataViewer(dataEngine, errorInfo)

        window = DyStockDataJaccardIndexMainWindow(orgDfs, jaccardDfs, codeSetDfs, codeIncreaseDfDicts, codeTable, dataViewer)
        window.show()
        self._windows.append(window)

    def _plotJaccardIndex(self, df, columns, left=None, right=None, top=None, bottom=None):
        """
            生成杰卡德指数曲线图
        """
        def _dateFormatter(x, pos):
            if not (0 <= int(x) < df.shape[0]):
                return None

            return df.index[int(x)]

        # create grid spec
        gs = GridSpec(1, 1)
        gs.update(left=left, right=right, top=top, bottom=bottom)

        ax = plt.subplot(gs[:, :])
        ax.set_title('杰卡德指数')
        ax.grid(True)

        # set x ticks
        x = [x for x in range(df.shape[0])]
        xspace = max((len(x)+9)//10, 1)
        ax.xaxis.set_major_locator(FixedLocator(x[:-xspace-1: xspace] + x[-1:]))
        ax.xaxis.set_major_formatter(FuncFormatter(_dateFormatter))

        # plot
        for column in columns:
            ax.plot(x, df[column].values, label=column)

        ax.axhline(0.5, color='k')
        ax.legend(loc='upper left', frameon=False)

    def plotJaccardIndex(self, index, jaccardIndexDf, columns):
        """
            @columns: 哪些杰卡德指数可视化
            生成指数K线图和杰卡德指数曲线图
        """
        if jaccardIndexDf is None or jaccardIndexDf.empty:
            return

        startDate = jaccardIndexDf.index[0]
        endDate = jaccardIndexDf.index[-1]

        # load
        if not self._daysEngine.load([-59, startDate, endDate], codes=[]):
            return

        DyMatplotlib.newFig()

        # plot index K-chart
        periods = self._dataViewer._plotCandleStick(index, startDate=startDate, endDate=endDate, netCapitalFlow=False, left=0.05, right=0.95, top=0.95, bottom=0.4)
        
        # plot Jaccard Index
        self._plotJaccardIndex(jaccardIndexDf, columns, left=0.05, right=0.95, top=0.35, bottom=0.05)

        # layout
        f = plt.gcf()
        plt.setp([a.get_xticklabels() for a in f.axes[:-1]], visible=False)
        f.show()

    def plotReqIndexConsecutiveDayLineStats(self, startDate, endDate, greenLine=True):
        # load
        if not self._daysEngine.load([startDate, endDate], codes=[]):
            return

        # count index DF
        indexCountedDfs = {}
        for index in self._daysEngine.stockIndexes:
            df = self._daysEngine.getDataFrame(index)

            indexCountedDfs[index] = DyStockDataUtility.countConsecutiveLine(df, greenLine=greenLine)

        # put event to UI
        event = DyEvent(DyEventType.plotAck)
        event.data['plot'] = self.plotAckIndexConsecutiveDayLineStats
        event.data['startDate'] = startDate
        event.data['endDate'] = endDate
        event.data['indexCountedDfs'] = indexCountedDfs
        event.data['greenLine'] = greenLine

        self._eventEngine.put(event)

    def plotAckIndexConsecutiveDayLineStats(self, event):
        # unpack
        startDate = event.data['startDate']
        endDate = event.data['endDate']
        indexCountedDfs = event.data['indexCountedDfs']
        greenLine = event.data['greenLine']

        window = DyStockDataIndexConsecutiveDayLineStatsTabWidget(self, startDate, endDate, indexCountedDfs, greenLine)
        window.showMaximized()

        self._windows.append(window)

    def _plotBBandsStats(self, code, periods=None, bBandPeriods=[10, 20], left=None, right=None, top=None, bottom=None):
        def _dateFormatter(x, pos):
            if not (0 <= int(x) < df.shape[0]):
                return None

            return df.index[int(x)].strftime("%y-%m-%d")

        # create grid spec
        gs = GridSpec(1, 1)
        gs.update(left=left, right=right, top=top, bottom=bottom)

        ax = plt.subplot(gs[:, :])
        ax.set_title('标准差均值比(%)')
        ax.grid(True)

        for i, bBandPeriod in enumerate(bBandPeriods):
            # get bbands
            df = self._daysEngine.getDataFrame(code)
            dfBBands = DyStockDataUtility.getBBands(df, period=bBandPeriod, stdNbr=1)
            df = pd.concat([df, dfBBands], axis=1)

            # slice periods of DF
            if periods is None:
                periods = df.index

            df = df.ix[periods]

            # 计算标准差均值比
            dfRatio = (df['lower'] - df['middle'])*100/df['middle']
            df = pd.concat([dfRatio[df['close'] < df['middle']], dfRatio[df['close'] >= df['middle']]*-1])
            df.sort_index(inplace=True) # Series做concat，不会做索引排序

            # set x ticks
            if i == 0:
                x = [x for x in range(df.shape[0])]
                xspace = max((len(x)+9)//10, 1)
                ax.xaxis.set_major_locator(FixedLocator(x[:-xspace-1: xspace] + x[-1:]))
                ax.xaxis.set_major_formatter(FuncFormatter(_dateFormatter))

            # plot
            ax.plot(x, df.values, label='N' + str(bBandPeriod))

        ax.axhline(0, color='k')
        ax.legend(loc='upper left', frameon=False)

        return periods

    def plotAckBBandsStats(self, event):
        # unpack
        code = event.data['code']
        startDate = event.data['startDate']
        endDate = event.data['endDate']
        bBand1Period = event.data['bBand1Period']
        bBand2Period = event.data['bBand2Period']

        DyMatplotlib.newFig()

        # net capital flow if stock
        netCapitalFlow = False if code in self._daysEngine.stockIndexes else True

        # plot K-chart
        periods = self._dataViewer._plotCandleStick(code, startDate=startDate, endDate=endDate, netCapitalFlow=netCapitalFlow, left=0.05, right=0.95, top=0.95, bottom=0.4)
        
        # plot bbands
        self._plotBBandsStats(code, periods, [bBand1Period, bBand2Period], left=0.05, right=0.95, top=0.35, bottom=0.05)

        # layout
        f = plt.gcf()
        plt.setp([a.get_xticklabels() for a in f.axes[:-1]], visible=False)
        f.show()

    def plotReqBBandsStats(self, code, startDate, endDate,  bBand1Period=10, bBand2Period=20):
        # fowarding 59 days for calculating MAs
        dates = [-59, startDate, endDate]

        # load
        if not self._daysEngine.load(dates, codes=[code]):
            return

        # put event to UI
        event = DyEvent(DyEventType.plotAck)
        event.data['plot'] = self.plotAckBBandsStats
        event.data['code'] = code
        event.data['startDate'] = startDate
        event.data['endDate'] = endDate
        event.data['bBand1Period'] = bBand1Period
        event.data['bBand2Period'] = bBand2Period

        self._eventEngine.put(event)

    def plotReqLimitUpStats(self, startDate, endDate):
        # load
        if not self._daysEngine.load([startDate, endDate]):
            return

        # count DF
        dfs = {}
        for code in self._daysEngine.stockCodes:
            df = self._daysEngine.getDataFrame(code)
            if df is None: continue

            dfs[code] = df

        df = DyStockDataUtility.countLimitUp(dfs, self._info)

        # put event to UI
        event = DyEvent(DyEventType.plotAck)
        event.data['plot'] = self.plotAckLimitUpStats
        event.data['startDate'] = startDate
        event.data['endDate'] = endDate
        event.data['df'] = df

        self._eventEngine.put(event)

    def plotAckLimitUpStats(self, event):
        # unpack
        startDate = event.data['startDate']
        endDate = event.data['endDate']
        df = event.data['df']

        window = DyStockDataLimitUpStatsMainWindow(self, df)
        window.showMaximized()

        self._windows.append(window)

    def plotLimitUpStats(self, index, df):
        """
            画封板率统计图
            @index: 指数代码
            @df: 封板率统计数据DF
        """
        startDay = df.index[0].strftime("%Y-%m-%d")
        endDay = df.index[-1].strftime("%Y-%m-%d")

        # fowarding 59 days for calculating MAs
        dates = [-59, startDay, endDay]

        # load
        if not self._daysEngine.load(dates, codes=[]):
            return

        DyMatplotlib.newFig()

        self._dataViewer._plotCandleStick(index, startDate=startDay, endDate=endDay, netCapitalFlow=False, left=0.05, right=0.95, top=0.95, bottom=0.5)

        self._plotLimitUpStats(df, left=0.05, right=0.95, top=0.45, bottom=0.05)

        # layout
        f = plt.gcf()
        plt.setp([a.get_xticklabels() for a in f.axes[:-1]], visible=False)
        f.show()

    def _plotLimitUpStats(self, df, left=None, right=None, top=None, bottom=None):
        def _dateFormatter(x, pos):
            if not (0 <= int(x) < df.shape[0]):
                return None

            return df.index[int(x)].strftime("%y-%m-%d")

        # create grid spec
        gs = GridSpec(4, 1)
        gs.update(left=left, right=right, top=top, bottom=bottom, hspace=0)

        # subplot for limit-up numbers
        ax = plt.subplot(gs[:2, :])
        ax.set_title('封板统计, 封板率均值:{0}%'.format(round(df['封板率(%)'].mean(), 2)))
        ax.grid(True)

        # set x ticks
        x = [x for x in range(df.shape[0])]
        xspace = max((len(x)+9)//10, 1)
        ax.xaxis.set_major_locator(FixedLocator(x[:-xspace-1: xspace] + x[-1:]))
        ax.xaxis.set_major_formatter(FuncFormatter(_dateFormatter))

        # plot
        ax.bar(x, df['未封板数'].values, color='g', width=.9, label='未封板数')
        ax.bar(x, df['封板数'].values, color='r', bottom=df['未封板数'].values, width=.9, label='封板数')

        ax.legend(loc='upper left', frameon=False)

        # subplot for limit-up percentage
        ax = plt.subplot(gs[2:3, :], sharex=ax)
        ax.grid(True)

        ax.plot(x, df['封板率(%)'].values, label='封板率(%)')

        ax.legend(loc='upper left', frameon=False)

        # subplot for limit-up percentage
        ax = plt.subplot(gs[-1, :], sharex=ax)
        ax.grid(True)

        ax.plot(x, df['封板数占总比(%)'].values, label='封板数占总比(%)')
        ax.axhline(1, color='y', linewidth=.2)
        ax.axhline(0.5, color='y', linewidth=.2)

        ax.legend(loc='upper left', frameon=False)

    def plotReqFocusAnalysis(self, startDate, endDate):
        # load
        #if not self._daysEngine.load([startDate, endDate], codes=['601668.SH']):
        if not self._daysEngine.load([startDate, endDate]):
            return

        # stock DFs
        dfs = {}
        for code in self._daysEngine.stockCodes:
            df = self._daysEngine.getDataFrame(code)
            if df is None: continue

            dfs[code] = df

        # index DF
        indexDf = self._daysEngine.getDataFrame(DyStockCommon.szIndex)

        # analysis
        focusStrengthDf, focusInfoPoolDict = DyStockDataFocusAnalysisUtility.analysis(dfs, indexDf.index, self._daysEngine.stockCodes, self._eventEngine, self._info)

        # put event to UI
        event = DyEvent(DyEventType.plotAck)
        event.data['plot'] = self.plotAckFocusAnalysis
        event.data['startDate'] = startDate
        event.data['endDate'] = endDate
        event.data['focusStrengthDf'] = focusStrengthDf
        event.data['focusInfoPoolDict'] = focusInfoPoolDict

        self._eventEngine.put(event)

    def plotAckFocusAnalysis(self, event):
        # unpack
        startDate = event.data['startDate']
        endDate = event.data['endDate']
        focusStrengthDf = event.data['focusStrengthDf']
        focusInfoPoolDict = event.data['focusInfoPoolDict']

        window = DyStockDataFocusAnalysisMainWindow(self, focusStrengthDf, focusInfoPoolDict)
        window.showMaximized()

        self._windows.append(window)

    def plotFocusStrength(self, index, df):
        """
            画热点强度图
            @index: 指数代码
            @df: focus strength DF
        """
        startDay = df.index[0].strftime("%Y-%m-%d")
        endDay = df.index[-1].strftime("%Y-%m-%d")

        # fowarding 59 days for calculating MAs
        dates = [-59, startDay, endDay]

        # load
        if not self._daysEngine.load(dates, codes=[]):
            return

        DyMatplotlib.newFig()

        self._dataViewer._plotCandleStick(index, startDate=startDay, endDate=endDay, netCapitalFlow=False, left=0.05, right=0.95, top=0.95, bottom=0.5)

        self._plotFocusStrength(df, left=0.05, right=0.95, top=0.45, bottom=0.05)

        # layout
        f = plt.gcf()
        plt.setp([a.get_xticklabels() for a in f.axes[:-1]], visible=False)
        f.show()

    def _plotFocusStrength(self, df, left=None, right=None, top=None, bottom=None):
        def _dateFormatter(x, pos):
            if not (0 <= int(x) < df.shape[0]):
                return None

            return df.index[int(x)].strftime("%y-%m-%d")

        # create grid spec
        gs = GridSpec(1, 1)
        gs.update(left=left, right=right, top=top, bottom=bottom, hspace=0)

        # subplot for focus strength
        ax = plt.subplot(gs[:, :])
        ax.set_title('热点强度')
        ax.grid(True)

        # set x ticks
        x = [x for x in range(df.shape[0])]
        xspace = max((len(x)+9)//10, 1)
        ax.xaxis.set_major_locator(FixedLocator(x[:-xspace-1: xspace] + x[-1:]))
        ax.xaxis.set_major_formatter(FuncFormatter(_dateFormatter))

        # scatter
        totalNbr = df.shape[0]
        columns = list(df.columns)[:20] # only select top20
        for name in columns:
            ratio = round(df[name].notnull().sum()/totalNbr*100, 2) # 出现次数占比总交易日数
            ax.scatter(x, df[name].values, label='{0}({1}%)'.format(name, ratio), edgecolors='none')
        
        ax.legend(loc='lower left', frameon=False)

    def plotReqHighLowDist(self, startDate, endDate, size=1):
        """
            请求绘制全市场股票的日内最高和最低价的时间分布
            @size: 按多少分钟绘制分布
        """
        def _time2Number(time):
            return time.hour*60*60 + time.minute*60 + time.second

        # load
        #if not self._daysEngine.loadCommon([startDate, endDate], codes=['000001.SZ']):
        if not self._daysEngine.loadCommon([startDate, endDate]):
            return

        dates = self._daysEngine.tDays(startDate, endDate)
        codes = self._daysEngine.stockCodes
        self._progress.init(len(dates)*len(codes))

        highs, lows = [], []
        for date in dates:
            for code in codes:
                if not self._ticksEngine.loadCode(code, date):
                    self._progress.update()
                    continue

                df = self._ticksEngine.getDataFrame(code)
                prices = df['price']

                highs.append(_time2Number(prices.argmax()))
                lows.append(_time2Number(prices.argmin()))

                self._progress.update()

        # put event to UI
        event = DyEvent(DyEventType.plotAck)
        event.data['plot'] = self.plotAckHighLowDist
        event.data['startDate'] = startDate
        event.data['endDate'] = endDate
        event.data['size'] = size
        event.data['highs'] = highs
        event.data['lows'] = lows

        self._eventEngine.put(event)

    def plotAckHighLowDist(self, event):
        # unpack
        startDate = event.data['startDate']
        endDate = event.data['endDate']
        size = event.data['size']
        highs = event.data['highs']
        lows = event.data['lows']

        def _plot(data, type):
            def _getTime(seconds):
                h = seconds // 3600
                m = (seconds % 3600 ) // 60
                s = (seconds % 3600 ) % 60

                return h, m, s

            def _dateFormatter(x, pos):
                h, m, s = _getTime(int(x))

                time = '{0}:{1}:{2}'.format(h if h > 9 else ('0' + str(h)), m if m > 9 else ('0' + str(m)), s if s > 9 else ('0' + str(s)))

                return time

            DyMatplotlib.newFig()

            plt.hist(data, bins=6*60//size)

            f = plt.gcf()
            ax = f.axes[0]

            # set x ticks
            ax.xaxis.set_major_formatter(FuncFormatter(_dateFormatter))
            ax.set_title('日内{}分布[{} ~ {}]'.format(type, startDate, endDate))
            f.autofmt_xdate()
            
            plt.show()

        _plot(highs, '最高价')
        _plot(lows, '最低价')