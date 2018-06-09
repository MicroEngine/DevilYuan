import operator

from ..DyStockSelectStrategyTemplate import *
from ....Data.Utility.DyStockDataUtility import *


class DySS_MasLong(DyStockSelectStrategyTemplate):
    name = 'DySS_MasLong'
    chName = '均线多头'

    autoFillDays = True
    optimizeAutoFillDays = True

    colNames = ['代码', '名称', '均线多头日数', '均线多头涨幅(%)', '均线多头ER']

    param = OrderedDict\
                ([
                    ('基准日期', datetime.today().strftime("%Y-%m-%d")),
                    ('向前N日周期', 60),
                    ('几日均线多头排列', '10,20,30'),
                    ('均线差值多头排列', 1),
                    ('均线连续多头日数[x,y]', '10,inf'),
                    ('均线多头ER>=', 0.3),
                ])


    def __init__(self, param, info):
        super().__init__(param, info)

        # unpack parameters
        self._baseDate              = param['基准日期']
        self._forwardNTDays         = param['向前N日周期'] # @self._baseDate is included
        self._longMas               = [int(x) for x in param['几日均线多头排列'].split(',')]; self._longMas.sort()
        self._longMaDiff            = False if param['均线差值多头排列'] == 0 else True
        self._longMasDays           = [float(x) for x in param['均线连续多头日数[x,y]'].split(',')]
        self._longMasEr             = param['均线多头ER>=']

        self._mas = list(set(self._longMas + [5, 10]))
        self._mas.sort()

    def onDaysLoad(self):
        self._loadedDaysNbr = (self._forwardNTDays + self._mas[-1]) - 1

        return self._baseDate, -(self._loadedDaysNbr - 1)

    def onInit(self, dataEngine, errorDataEngine):
        self._daysEngine = dataEngine.daysEngine

        self._stockAllCodes = self._daysEngine.stockAllCodes

    def _checkMasLong(self, maDf):
        """
            check if Mas is long
            @maDf: DF of MAs
        """
        maColumns = ['ma%s'%x for x in self._longMas]
        maDf = maDf[maColumns]

        nbr = DyStockDataUtility.getMasLong(maDf, self._longMaDiff)
        if self._longMasDays[0] <= nbr <= self._longMasDays[1]:
            return True, nbr

        return False, nbr

    def onStockDays(self, code, df):
        if df.shape[0] != self._loadedDaysNbr:
            return

        maDf = DyStockDataUtility.getMas(df, self._mas)

        ret, longDayNbr = self._checkMasLong(maDf)
        if not ret:
            return

        # get DF of long with one ahead
        longDf = df[-longDayNbr - 1:]
        
        longIncrease = (longDf.ix[-1, 'close'] - longDf.ix[0, 'close'])/longDf.ix[0, 'close']*100
        
        er, _ = DyStockDataUtility.getVolatilityEfficiencyRatio(longDf['close'])
        if er < self._longMasEr:
            return

        # 设置结果
        pair = [code, self._stockAllCodes[code], longDayNbr, longIncrease, er]
        self._result.append(pair)
