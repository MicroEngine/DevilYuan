import operator

from ..DyStockSelectStrategyTemplate import *
from ....Data.Utility.DyStockDataUtility import *


class DySS_MasAttack(DyStockSelectStrategyTemplate):
    name = 'DySS_MasAttack'
    chName = '均线上攻'

    autoFillDays = True
    optimizeAutoFillDays = True

    colNames = ['代码', '名称', '均线上攻总角度', '均线上攻角度']

    param = OrderedDict\
                ([
                    ('基准日期', datetime.today().strftime("%Y-%m-%d")),
                    ('向前N日周期', 3),
                    ('几日均线上攻', '5,10,20,30'),
                    ('角度关系', '5>10')
                ])

    paramToolTip = {'角度关系': '格式: 均线1角度>均线2角度,均线2角度>=均线3角度,...'}


    def __init__(self, param, info):
        super().__init__(param, info)

        # unpack parameters
        self._baseDate              = param['基准日期']
        self._forwardNTDays         = param['向前N日周期'] # @self._baseDate is included
        self._attackMas             = [int(x) for x in param['几日均线上攻'].split(',')]; self._attackMas.sort()

        self._anglesRelationship    = []
        anglesRelationshipList = param['角度关系'].split(',')
        for angles in anglesRelationshipList:
            sign = '>'
            angle1, angle2 = angles.split('>')
            if '=' in angle2:
                angle2 = angle2[1:]
                sign += '='

            self._anglesRelationship.append([int(angle1), int(angle2), sign])

        # all MAs
        self._mas = list(set(self._attackMas + [5, 10, 20, 30, 60]))
        self._mas.sort()

    def onDaysLoad(self):
        return self._baseDate, -(self._forwardNTDays + self._mas[-1]) + 2

    def onInit(self, dataEngine, errorDataEngine):
        self._daysEngine = dataEngine.daysEngine

        self._stockAllCodes = self._daysEngine.stockAllCodes
        
        self._startDay = self._daysEngine.tDaysOffset(self._baseDate, -self._forwardNTDays + 1)
        self._endDay = self._daysEngine.tDaysOffset(self._baseDate)

    def onStockDays(self, code, df):
        oriDf = df

        maDf = DyStockDataUtility.getMas(df, self._mas)
        df = df.ix[maDf.index]

        # 剔除周期内停牌的股票
        if df.shape[0] != self._forwardNTDays:
            return

        close = df.ix[-1, 'close']
        ma5 = maDf.ix[-1, 'ma5']
        if close < ma5: return

        # 当日均线上攻
        angleChange = False # 至少一条均线的角度有下穿变为上穿
        angles = []
        angleDict = {}
        for ma in self._attackMas:
            y0 = maDf.ix[-3, 'ma%s'%ma]
            y1 = maDf.ix[-2, 'ma%s'%ma]
            y2 = maDf.ix[-1, 'ma%s'%ma]

            angle = DyStockDataUtility.xAngle(y1, y2)
            if angle <= 0: return

            angles.append(angle)
            angleDict[ma] = angle

            angle = DyStockDataUtility.xAngle(y0, y1)
            if angle <= 0:
                angleChange = True

        if not angleChange: return

        # 角度关系
        for angle1, angle2, sign in self._anglesRelationship:
            if not eval('angleDict[angle1]' + sign + 'angleDict[angle2]'):
                return

        if angleDict[5] < 10: return

        """
        
        highest = oriDf['high'].max()
        lowest = oriDf['low'].min()

        if close > (highest + lowest)/2: return
        """

        """
        # 当日收盘围绕60日均线
        close = df.ix[-1, 'close']
        ma60 = maDf.ix[-1, 'ma60']

        if close > ma60:
            if (close - ma60)*100/ma60 > 10:
                return

        
        ma5 = maDf.ix[-1, 'ma5']
        ma10 = maDf.ix[-1, 'ma10']
        ma20 = maDf.ix[-1, 'ma20']
        ma30 = maDf.ix[-1, 'ma30']

        if not ma5 > ma10 > ma20: return
        """

        """
        if ma5 - ma10 < ma20 - ma30: return
        """

        # 设置结果
        pair = [code, self._stockAllCodes[code], int(sum(angles)), ','.join([str(int(x)) for x in angles])]
        self._result.append(pair)
        self._result.sort(key=operator.itemgetter(2), reverse=True)
