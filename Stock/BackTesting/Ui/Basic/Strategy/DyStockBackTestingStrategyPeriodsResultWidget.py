from PyQt5.QtWidgets import QTabWidget

from EventEngine.DyEvent import *
from .DyStockBackTestingStrategyPeriodResultWidget import *


class DyStockBackTestingStrategyPeriodsResultWidget(QTabWidget):
    """ 策略一个参数组合的多周期回测窗口 """

    def __init__(self, strategyCls, paramGroupNo, param, eventEngine, dataEngine, dataViewer):
        super().__init__()

        self._strategyCls = strategyCls
        self._paramGroupNo = paramGroupNo
        self._param = param
        self._eventEngine = eventEngine
        self._dataEngine = dataEngine
        self._dataViewer = dataViewer

        # 每个回测策略会被分成几个时间周期并行运行，每个周期的回归结果会生成一个周期窗口
        self._strategyPeriodWidgets = {}

    def _getTabPos(self, period):
        periodStartDates = [period[0]]

        for periodKey in self._strategyPeriodWidgets:
            periodStartDates.append(periodKey[1: 1+len('2016-01-01')])

        periodStartDates.sort()

        return periodStartDates.index(period[0])

    def update(self, ackData):
        """ 更新策略一个回测周期的回测结果 """
        # unpack
        period = ackData.period

        tabName = '[' + ','.join(period) + ']'
        self._strategyPeriodWidgets[tabName].update(ackData)

    def removeAll(self):
        count = self.count()

        for _ in range(count):
            self.removeTab(0)

        self._strategyPeriodWidgets = {}

    def mergePeriod(self, name):
        pass

    def newPeriod(self, event):
        # unpack
        period = event.data['period']

        # tab window title
        tabName = '[' + ','.join(period) + ']'

        assert(tabName not in self._strategyPeriodWidgets)

        widget = DyStockBackTestingStrategyPeriodResultWidget(self._strategyCls, self._paramGroupNo, period, self._eventEngine, self._dataEngine, self._dataViewer)
            
        tabPos = self._getTabPos(period)
        self.insertTab(tabPos, widget, tabName)

        # save
        self._strategyPeriodWidgets[tabName] = widget

    def getCurPnlRatio(self):

        curPnlRatio = 1
        for _, widget in self._strategyPeriodWidgets.items():
            curPnlRatio *= (1 + widget.getCurPnlRatio()/100)

        return (curPnlRatio - 1)*100

    def overview(self):
        columns = ['盈亏(%)', '年化盈亏(%)', '最大回撤(%)', '最大亏损(%)', '最大盈利(%)', '胜率(%)', '夏普比率']

        pnlRatio = 1; pnlRatioPos = columns.index('盈亏(%)')
        annualPnlRatio = 1; annualPnlRatioPos = columns.index('年化盈亏(%)')
        maxDrop = None; maxDropPos = columns.index('最大回撤(%)')
        maxLoss = None; maxLossPos = columns.index('最大亏损(%)')
        maxProfit = None; maxProfitPos = columns.index('最大盈利(%)')
        hitRate = 0; hitRatePos = columns.index('胜率(%)'); hitRateCount = 0
        sharpe = 0; sharpePos = columns.index('夏普比率'); sharpeCount = 0

        for _, widget in self._strategyPeriodWidgets.items():
            columns_, data = widget.overview()
            assert columns == columns_

            data = data[0]

            pnlRatio *= (1 + data[pnlRatioPos]/100)
            annualPnlRatio *= (1 + data[annualPnlRatioPos]/100)

            maxDrop = data[maxDropPos] if maxDrop is None else max(maxDrop, data[maxDropPos])
            maxLoss = data[maxLossPos] if maxLoss is None else max(maxLoss, data[maxLossPos])
            maxProfit = data[maxProfitPos] if maxProfit is None else max(maxProfit, data[maxProfitPos])
            
            if isinstance(data[hitRatePos], float):
                hitRate += data[hitRatePos]
                hitRateCount += 1

            if isinstance(data[sharpePos], float):
                sharpe += data[sharpePos]
                sharpeCount += 1

        # adjust
        pnlRatio = (pnlRatio - 1)*100
        annualPnlRatio = (annualPnlRatio - 1)*100
        hitRate = hitRate/hitRateCount if hitRateCount > 0 else 'N/A'
        sharpe = sharpe/sharpeCount if sharpeCount > 0 else 'N/A'

        return columns, [pnlRatio, annualPnlRatio, maxDrop, maxLoss, maxProfit, hitRate, sharpe]

