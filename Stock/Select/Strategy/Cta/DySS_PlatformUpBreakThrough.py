import operator

from DyCommon.DyCommon import *
from ..DyStockSelectStrategyTemplate import *
from ....Data.Utility.DyStockDataUtility import *


class DySS_PlatformUpBreakThrough(DyStockSelectStrategyTemplate):
    name = 'DySS_PlatformUpBreakThrough'
    chName = '平台向上突破'

    colNames = ['代码', '名称', '粘合比例(%)', '当日涨幅(%)']

    param = OrderedDict\
                ([
                    ('基准日期', datetime.today().strftime("%Y-%m-%d")),
                    ('向前N日周期', 30),
                    ('几日均线粘合', "5,10,20,30"),
                    ('突破几日均线', 60),
                    ('粘合比例不低于(%)', 50), # 指定日期内符合粘合度的天数比例
                    ('均线极差均值比不高于(%)', 2) # 均线极差的绝对值跟平均值的比例
                ])

    paramToolTip = {'突破几日均线': '0:不突破'}

    def __init__(self, param, info):
        super().__init__(param, info)

        # unpack parameters
        self._baseDate              = param['基准日期']
        self._forwardNTDays         = param['向前N日周期'] # @self._baseDate is not included
        self._bondMas               = [int(x) for x in param['几日均线粘合'].split(',')]; self._bondMas.sort()
        self._upBreakThroughMa      = param['突破几日均线']
        self._bondRatio             = param['粘合比例不低于(%)']
        self._maStdMeanRatio        = param['均线极差均值比不高于(%)']

    def onDaysLoad(self):
        return self._baseDate, -max(self._forwardNTDays + self._bondMas[-1], self._upBreakThroughMa + 1) + 1

    def onInit(self, dataEngine, errorDataEngine):
        self._daysEngine = dataEngine.daysEngine

        self._stockAllCodes = self._daysEngine.stockAllCodes
        
        self._bondMasColumns = ['ma%s'%x for x in self._bondMas]
        self._upBreakThroughMaName = 'ma%s'%self._upBreakThroughMa

        self._mas = (self._bondMas + [self._upBreakThroughMa]) if self._upBreakThroughMa not in self._bondMas else self._bondMas

        self._baseDay = self._daysEngine.tDaysOffset(self._baseDate)
        self._bondStartDay = self._daysEngine.tDaysOffset(self._baseDate, -self._forwardNTDays)
        self._bondEndDay = self._daysEngine.tDaysOffset(self._baseDate, -1)

    def onStockDays(self, code, df):
        # 计算均线
        maDf = DyStockDataUtility.getMas(df, self._mas, False)
        
        # 均线粘合
        masBond, bondRatio = self._isMasBond(maDf)
        if not masBond: return

        # 突破
        if not self._isBreakThrough(df, maDf): return

        # 设置结果
        pair = [code, self._stockAllCodes[code], bondRatio, self._getBaseDayIncrease(df)]
        self._result.append(pair)
        self._result.sort(key=operator.itemgetter(3), reverse=True)

    def _getBaseDayIncrease(self, df):
        preClose = df.ix[self._bondEndDay, 'close']
        close = df.ix[self._baseDay, 'close']

        return (close - preClose)*100 / preClose

    def _isBreakThrough(self, df, maDf):

        preClose = df.ix[self._bondEndDay, 'close']
        close = df.ix[self._baseDay, 'close']
        open = df.ix[self._baseDay, 'open']
        high = df.ix[self._baseDay, 'high']

        # 不突破
        if self._upBreakThroughMa == 0:
            mean = maDf.ix[self._baseDay].mean()
            if abs(close - mean)/mean < 0.05:
                return True

            return False

        # 当日是阳线
        if close < open: return False

        # 剔除十字星
        if (close - open) == 0: return False

        # 剔除长上影线
        if ( high - close) / (close - open) > 0.8: return False

        # 前一天的收盘价在突破均线之下 and 当日收盘价在突破均线之上 and 当日收盘价是指定日期内的最高价
        if preClose < maDf.ix[self._bondEndDay, self._upBreakThroughMaName] and \
            close > maDf.ix[self._baseDay, self._upBreakThroughMaName] and \
            close > df.ix[self._bondStartDay:self._bondEndDay, 'high'].max():
            return True

        return False

    def _isMasBond(self, maDf):
        # 数据对齐
        maDf = maDf.ix[self._bondStartDay:self._bondEndDay, self._bondMasColumns]

        # 均线的每日均值
        masMean = maDf.mean(axis = 1)

        # broadcast at axis 1 by numpy
        masMean = masMean.values.reshape((masMean.shape[0], 1))

        # 每日的均线均值离差绝对值比
        masDiff = abs(maDf.values - masMean)*100/masMean

        masDiffMean = (masDiff.max(axis = 1) + masDiff.min(axis = 1))/2

        # 不高于均线极差均值比的交易日数
        bondTDaysNbr = (masDiffMean <= self._maStdMeanRatio).sum()

        bondRatio = bondTDaysNbr*100 / maDf.shape[0]

        return (True, bondRatio) if bondRatio >= self._bondRatio else (False, None)
