import operator
from datetime import datetime
import requests

from ..DyStockSelectStrategyTemplate import *
from DyCommon.DyCommon import *


class DySS_GrowingStocks(DyStockSelectStrategyTemplate):
    name = 'DySS_GrowingStocks'
    chName = '成长股'

    colNames = ['代码', '名称', '得分', '3Y平均营业总收入YoY(%)', '3Y平均净利润YoY(%)', 'PE', 'PEG', '3Y平均每股现金收益差', '相对指数强度(%)']

    param = OrderedDict\
                ([
                    ('基准日期', datetime.today().strftime("%Y-%m-%d")),
                    ('向前N日周期', 30),
                    ('得分至少', 80)
                ])

    paramToolTip = {'向前N日周期': '周期内相对指数强度'}

    def __init__(self, param, info):
        super().__init__(param, info)

        # unpack parameters
        self._baseDate              = param['基准日期']
        self._forwardNTDays         = param['向前N日周期'] # @self._baseDate is included
        self._score                 = param['得分至少']

    def onDaysLoad(self):
        return self._baseDate, -self._forwardNTDays + 1

    def onInit(self, dataEngine, errorDataEngine):
        self._daysEngine = dataEngine.daysEngine

        self._stockAllCodes = self._daysEngine.stockAllCodes

    def _toFloat(self, value):
        try:
            value = float(value)
        except Exception as ex:
            value = 0

        return value

    def _getIndicators(self, code):
        """
            @return: 近三年营业总收入同比增长率, 近三年净利润同比增长率, 最新年化每股收益, 近三年平均每股现金收益差
        """
        mainLink = 'http://basic.10jqka.com.cn/{0}/flash/main.txt'.format(code[:-3])
        r = requests.get(mainLink)

        table = dict(json.loads(r.text))

        # get'营业总收入同比增长率'position
        pos = None
        for i, e in enumerate(table['title']):
            if isinstance(e, list):
                if e[0] == '营业总收入同比增长率':
                    pos = i
                    break

        # 最近12个季度的'营业总收入同比增长率'
        rates1 = table['report'][pos][:12]

        # get'净利润同比增长率'position
        pos = None
        for i, e in enumerate(table['title']):
            if isinstance(e, list):
                if e[0] == '净利润同比增长率':
                    pos = i
                    break

        # 最近12个季度的'净利润同比增长率'
        rates2 = table['report'][pos][:12]

        # 年度每股收益
        date = table['report'][0][0]
        dates = date.split('-')
        factor = 12/int(dates[1])
        
        # get'基本每股收益'position
        pos = None
        for i, e in enumerate(table['title']):
            if isinstance(e, list):
                if e[0] == '基本每股收益':
                    pos = i
                    break

        # '基本每股收益'
        earningPerShares = table['report'][pos][:12]
        earningPerShares = [self._toFloat(x) for x in earningPerShares]
        earningPerShare = earningPerShares[0] * factor

        # get'每股经营现金流'position
        pos = None
        for i, e in enumerate(table['title']):
            if isinstance(e, list):
                if e[0] == '每股经营现金流':
                    pos = i
                    break

        # '每股经营现金流'
        cashPerShares = table['report'][pos][:12]
        cashPerShares = [self._toFloat(x) for x in cashPerShares]

        cashEarningDiffPerShares = list(map(lambda x, y: x - y, cashPerShares, earningPerShares))
        aveCashEarningDiffPerShare = sum(cashEarningDiffPerShares)/len(cashEarningDiffPerShares)

        return [self._toFloat(x) for x in rates1], [self._toFloat(x) for x in rates2], earningPerShare, aveCashEarningDiffPerShare

    def _getScore(self, rates):
        """ 100分制
            @return: 得分，平均每季度增长率
        """
        # (0, 10]: 1, (10, 20]: 2, (20, 30]: 3, (30, ): 4
        scores = []
        for rate in rates:
            score = 0
            if 0 < rate <= 10: score = 1
            elif 10 < rate <= 20: score = 2
            elif 20 < rate <= 30: score = 3
            elif rate > 30: score = 4

            scores.append(score)

        return sum(scores)*100/(4*len(scores)), sum(rates)/len(rates)

    def _getScores(self, code):
        """ 100分制
            @return: 总得分，平均每季度营业总收入同比增长率，平均每季度净利润同比增长率
        """
        rates1, rates2, earningPerShare, aveCashEarningDiffPerShare = self._getIndicators(code)

        score1, aveRate1 = self._getScore(rates1)
        score2, aveRate2 = self._getScore(rates2)

        return (score1 + score2)/2, aveRate1, aveRate2, earningPerShare, aveCashEarningDiffPerShare

    def onStockDays(self, code, df):
        try:
            score, aveRate1, aveRate2, earningPerShare, aveCashEarningDiffPerShare = self._getScores(code)
        except Exception as ex:
            self._info("从同花顺读取{0}: {1}'财务概况'异常".format(code, self._stockAllCodes[code]), DyLogData.warning)
            return

        if score < self._score: return

        # PE & PEG
        pe = None
        peg = None
        if not df.empty:
            try:
                pe = df.ix[-1, 'close']/earningPerShare
                peg = pe/aveRate2
            except Exception as ex:
                pass

        # 相对指数强度
        strong = None

        indexDf = self._daysEngine.getDataFrame(self._daysEngine.getIndex(code))
        indexCloses = indexDf['close']
        indexRatio = indexCloses[-1]/indexCloses[0]

        if not df.empty:
            closes = df['close']
            stockRatio = closes[-1]/closes[0]

            strong = (stockRatio - indexRatio)*100/indexRatio

        # 设置结果
        pair = [code, self._stockAllCodes[code], score, aveRate1, aveRate2, pe, peg, aveCashEarningDiffPerShare, strong]
        self._result.append(pair)
        self._result.sort(key=operator.itemgetter(2), reverse=True)
