import pandas as pd
import numpy as np
from matplotlib.gridspec import GridSpec
from matplotlib.ticker import FuncFormatter, FixedLocator

from DyCommon.DyCommon import *
from DyCommon.Ui.DyTableWidget import *
from EventEngine.DyEvent import *


class DyStockBackTestingStrategyResultStatsWidget(DyTableWidget):

    header = ['日期', '初始资金', '总市值', '持仓市值', '资金',
              '盈亏(%)', '年化盈亏(%)', '最大回撤(%)', '最大亏损(%)', '最大盈利(%)',
              '胜率(%)', '盈亏比(%/金额)', '夏普比率']

    def __init__(self, dataEngine):
        super().__init__(None, True, False)

        self._dataEngine = dataEngine
        self._daysEngine = self._dataEngine.daysEngine

        self.setColNames(self.header)
        self.setAutoForegroundCol('盈亏(%)')

        self._curPnlRatio = 0
        self._maxDrop = 0
        self._maxLoss = 0
        self._maxProfit = 0

        self._ackData = [] # save all ack data
        self._closePnl = {} # 收盘后的盈亏(%)统计，为了画图，obsolete
        self._closePosRatio = {} # 收盘后持仓比列(%)统计，为了画图，obsolete
        self._closeData = {} # 收盘后[盈亏(%), 持仓资金比列(%), 持仓股票数]统计，为了画图
        self._hits = [0, 0] # 命中次数，[盈利次数, 亏损次数]，为了计算胜率
        self._dealPnlRatioSums = [0, 0] # 每笔交易的总盈利百分比，[总盈利, 总亏损]，为了计算盈亏比
        self._dealPnlSums = [0, 0] # 每笔交易的总盈利金额，[总盈利, 总亏损]，为了计算盈亏比

        self.itemDoubleClicked.connect(self._itemDoubleClicked)

    def update(self, ackData):
        # save
        self._ackData.append(ackData)

        initCash = ackData.initCash
        curCash = ackData.curCash 

        # 持仓市值
        posValue = 0
        for _, pos in ackData.curPos.items():
            posValue += pos.price * pos.totalVolume

        # 账户市值
        totalValue = posValue + curCash

        self._curPnlRatio = (totalValue - initCash)/initCash * 100

        self._maxProfit = max(self._maxProfit, self._curPnlRatio)
        self._maxLoss = min(self._maxLoss, self._curPnlRatio)

        curDrop = (self._maxProfit - self._curPnlRatio)/(100 + self._maxProfit) * 100
        self._maxDrop = max(self._maxDrop, curDrop)

        # 胜率 & 盈利和
        for deal in ackData.deals:
            if deal.pnlRatio is None:
                continue

            if deal.pnlRatio > 0:
                self._hits[0] += 1
                self._dealPnlRatioSums[0] += deal.pnlRatio
                self._dealPnlSums[0] += deal.pnl
            else:
                self._hits[1] += 1
                self._dealPnlRatioSums[1] += deal.pnlRatio
                self._dealPnlSums[1] += deal.pnl

        totalHits = sum(self._hits)
        hitRate = self._hits[0]*100/totalHits if totalHits > 0 else 'N/A'

        # close Ack data
        if ackData.isClose:
            # 相比初始资金的每日盈亏(%)
            self._closePnl[ackData.datetime.strftime("%Y-%m-%d")] = [self._curPnlRatio]
            self._closePosRatio[ackData.datetime.strftime("%Y-%m-%d")] = [posValue/totalValue*100]
            self._closeData[ackData.datetime.strftime("%Y-%m-%d")] = [self._curPnlRatio, posValue/totalValue*100, len(ackData.curPos)]

        # 年化夏普比率
        sharpe = self._annualisedSharpe()

        # 年化盈亏(%)
        annualisedPnlRatio = self._curPnlRatio/len(self._closePnl) * 252 if self._closePnl else 'N/A'

        # 盈亏比，根据每笔交易计算盈亏比
        profitLossRatio = self._calcProfitLossRatio()

        # UI
        self[0] = [ackData.day, initCash, totalValue, posValue, curCash,
                   self._curPnlRatio, annualisedPnlRatio, self._maxDrop, self._maxLoss, self._maxProfit,
                   hitRate, profitLossRatio, sharpe]

    def _calcProfitLossRatio(self):
        """
            根据每笔交易计算盈亏比
        """
        ratio = 'N/A'
        
        if self._hits[0] > 0 and self._hits[1] > 0 and self._dealPnlRatioSums[1] != 0:
            pnlRatio = (self._dealPnlSums[0]/self._hits[0]) / abs(self._dealPnlSums[1]/self._hits[1])
            pctRatio = (self._dealPnlRatioSums[0]/self._hits[0]) / abs(self._dealPnlRatioSums[1]/self._hits[1])

            ratio = '{:.2f}/{:.2f}'.format(pctRatio, pnlRatio)

        return ratio

    def _annualisedSharpe(self):
        # pnl ratio of strategy DF
        df = pd.DataFrame(self._closePnl).T

        df += 100

        dailyReturns = df[0].pct_change()
        dailyReturns -= 0.025/252 # 年化货币基金收益2.5%

        std = dailyReturns.std()
        sharpe = np.sqrt(252) * dailyReturns.mean() / std if std > 0 else np.nan

        if np.isnan(sharpe) or np.isinf(sharpe):
            sharpe = 'N/A'

        return sharpe

    def _plotStats(self, df, strategyName):
        """
            绘制账户盈亏统计图
        """
        def _dateFormatter(x, pos):
            if not (0 <= int(x) < df.shape[0]):
                return None

            return df.index[int(x)].strftime("%y-%m-%d")

        # create grid spec
        gs = GridSpec(4, 1)
        gs.update(hspace=0)

        # subplot for PnL
        axPnl = plt.subplot(gs[:-1, :])
        axPnl.grid(True)
        axPnl.set_title('{}: 盈亏(%)'.format(strategyName))

        # set x ticks
        x = [x for x in range(df.shape[0])]
        xspace = max((len(x)+9)//10, 1)
        axPnl.xaxis.set_major_locator(FixedLocator(x[:-xspace-1: xspace] + x[-1:]))
        axPnl.xaxis.set_major_formatter(FuncFormatter(_dateFormatter))

        # plot pnl
        for name in df.columns:
            if name not in ['持仓资金(%)', '持仓股票数']:
                axPnl.plot(x, df[name].values, label=name)

        axPnl.legend(loc='upper left', frameon=False)

        # subplot for position
        axPos = plt.subplot(gs[-1, :], sharex=axPnl)
        axPos.grid(True)
        axPos.bar(x, df['持仓资金(%)'].values, label='持仓资金(%)')
        axPos.plot(x, df['持仓资金(%)'].values.cumsum()/np.array(list(range(1, df.shape[0] + 1))), label='平均持仓资金(%)', color='g')
        axPos.plot(x, df['持仓股票数'].values, label='持仓股票数', color='r')

        axPos.legend(loc='upper left', frameon=False)
        
    def _itemDoubleClicked(self, item):
        # close data of strategy DF
        df = pd.DataFrame(self._closeData).T

        strategyName = self._ackData[0].strategyCls.chName
        df.rename(columns={0: strategyName, 1: '持仓资金(%)', 2: '持仓股票数'}, inplace=True)

        # for load index Days data
        dates = [df.index[0], df.index[-1]]

        # change index to datetime for concating alignment
        df.index  =  pd.to_datetime(df.index + ' 00:00:00', format='%Y-%m-%d %H:%M:%S')

        # 载入指数日线数据
        if not self._daysEngine.load(dates, codes=[]):
            return

        # 计算周期内指数涨幅
        for index, name in self._daysEngine.stockIndexes.items():
            indexDf = self._daysEngine.getDataFrame(index)
            if indexDf is None:
                continue

            indexClose = ((indexDf['close'].pct_change() + 1).fillna(1).cumprod() - 1)*100
        
            # concate index DF and strategy DF
            df = pd.concat([df, indexClose], axis=1)
            df.rename(columns={'close': name}, inplace = True)

        # plot
        DyMatplotlib.newFig()

        self._plotStats(df, strategyName)

        # layout
        f = plt.gcf()
        plt.setp([a.get_xticklabels() for a in f.axes[:-1]], visible=False)
        f.show()

    @property
    def ackData(self):
        return self._ackData

    @property
    def curPnlRatio(self):
        return self._curPnlRatio

    def overview(self):
        """
            统计总览
        """
        columns = self.header[self.header.index('资金') + 1:]
        return columns, self.getColumnsData(columns)