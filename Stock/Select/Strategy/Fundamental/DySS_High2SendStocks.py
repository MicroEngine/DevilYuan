from datetime import datetime
import re
import requests
from bs4 import BeautifulSoup
import pandas as pd

from ....Data.Engine.DyStockDataEngine import *
from ..DyStockSelectStrategyTemplate import *
from ....Data.Utility.DyStockDataSpider import *


class DySS_High2SendStocks(DyStockSelectStrategyTemplate):
    """
        高送转主要因子：
            每股公积金： >= 5
            每股未分配利润： >= 1
            总股本(亿)： <= 2
            股本因子： 1
            机构持仓比例低
            高成长性： 营业收入和净利润增长，首先看营业收入（可以列为可选，但还是比较重要的）
            最近解禁日期： 配合出货（可选因子）
            每股净资产：>=5（可选因子）

        高转送炒作时间:
            5月左右炒中报
            10~11月左右炒年报，有些高增长的可能9月底炒作。9月可以结合大盘开始布局
    """
    name = 'DySS_High2SendStocks'
    chName = '高送转'

    colNames = ['代码', '名称', '排名', '得分', '现价', '每股净资产(元)', '每股公积金(元)', '每股未分配利润(元)',
                '流通A股(亿)', '总股本(亿)', '流通市值(亿元)', '总市值(亿元)',
                '最近解禁日期', '解禁股占总股本比例(%)',
                '股本因子', '最近送转日期', '机构持股占流通股比例(%)',
                '净利润YoY(%)', '营业收入YoY(%)', '每股收益(元)', '每股现金流(元)',
                '上市日期'
                ]

    param = OrderedDict\
                ([
                    ('基准日期', datetime.today().strftime("%Y-%m-%d")),
                    ('选几只股票', 0)
                ])

    paramToolTip = {'选几只股票': '0：所有股票'}

    fullyPushDays = True # 全推所有股票的日线数据

    # 策略参数
    dividendPlanGrepDetail = re.compile('(\d+)股?(?:送({0})股?)?(?:转增?({0})股?)?'.format('\d+(?:\.\d+)?'))

    def __init__(self, param, info):
        super().__init__(param, info)

        # unpack parameters
        self._baseDate              = param['基准日期']
        self._selectStockNbr        = param['选几只股票']

        self.__data = {}

    def onDaysLoad(self):
        return self._baseDate, 0

    def onInit(self, dataEngine, errorDataEngine):
        self._stockAllCodes = dataEngine.daysEngine.stockAllCodes

        errorInfo = DyErrorInfo(dataEngine.eventEngine)
        errorDataEngine = DyStockDataEngine(dataEngine.eventEngine, errorInfo, registerEvent=False)
        self._errorDaysEngine = errorDataEngine.daysEngine
        
    def _getShareFactor(self, dividendPlan):
        """
            根据同花顺的'分红方案说明'计算股本因子

            匹配的文本格式:
                dividendPlan = '10送5股转25股派1.25元(含税)'
                dividendPlan = '10送5股派1.25元(含税)'
                dividendPlan = '10转25股派1.25元(含税)'
                dividendPlan = '10股转10.090840股派0.504542元(含税)'
                dividendPlan = '10转增2股派2.5元(含税)'
        """
        match = self.dividendPlanGrepDetail.match(dividendPlan)
        if match:
            groups = match.groups()

            base = int(groups[0])
            sum = 0
            for group in groups[1:]:
                try:
                    group = float(group)
                    sum += group
                except Exception as ex:
                    pass

            shareFactor = (sum + base)/base
        else:
            shareFactor = 1

        return shareFactor

    def _getIndicators(self, code):
        """
            @return: ['每股净资产(元)', '每股公积金(元)', '每股未分配利润(元)', '流通A股(亿)', '总股本(亿)',
                      '最近解禁日期', '解禁股占总股本比例(%), '股本因子', '最近送转日期',
                      '净利润YoY(%)', '营业收入YoY(%)', '每股收益(元)', '每股现金流(元)'
                     ]
        """
        mainLink = 'http://basic.10jqka.com.cn/16/{0}/'.format(code[:-3])
        r = requests.get(mainLink)
        soup = BeautifulSoup(r.text, 'lxml')

        tag = soup.find('h2', text='财务指标')
        tag = tag.parent.parent
        tag = tag.find('tbody')
        tag = tag.find('tr')
        tags = tag.find_all('td')
        nextTrTag = tag.next_sibling.next_sibling # 由于业绩快报原因，可能每股公积金和每股未分配利润还没出来，则用前期的。
        nextTdTags = nextTrTag.find_all('td')

        for i, tag in enumerate(tags):
            if i == 2: # 每股净资产(Net asset value per share)
                navps = DyCommon.toFloat(tag.string)

            elif i == 3: # 每股公积金(Provident fund per share)
                pfps = DyCommon.toFloat(tag.string, None)
                if pfps is None:
                    pfps = DyCommon.toFloat(nextTdTags[3].string)

            elif i == 4: # 每股未分配利润(Undistributed profit per share)
                udpps = DyCommon.toFloat(tag.string, None)
                if udpps is None:
                    udpps = DyCommon.toFloat(nextTdTags[4].string)

        tag = soup.find('span', text='流通A股：')
        tag = tag.next_sibling
        floatingShares = float(tag.text[:-2]) # 流通A股(亿)

        tag = soup.find('span', text='总股本：')
        tag = tag.next_sibling.next_sibling
        totalShares = float(tag.text[:-2]) # 总股本(亿)

        # get 股本结构 page
        tag = soup.find('a', text='股本结构')
        link = mainLink + tag.attrs['href'][2:]
        r = requests.get(link)
        soup = BeautifulSoup(r.text, 'lxml')

        latestReleaseDate = None
        latestBanSharesPct = None
        tag = soup.find('h2', text='解禁时间表')
        if tag is not None:
            tag = tag.parent.parent.find('tbody')
            tags = tag.find_all('tr')

            todayDate = datetime.now().strftime("%Y-%m-%d")
            for tag in tags:
                # 解禁日期
                tag_ = tag.find('th')
                releaseDate = str(tag_.string)

                if releaseDate > todayDate:
                    if latestReleaseDate is None:
                        latestReleaseDate = releaseDate
                    else:
                        if releaseDate < latestReleaseDate:
                            latestReleaseDate = releaseDate

                if latestReleaseDate == releaseDate:
                    # 解禁股占总股本比例(%)
                    tags_ = tag.find_all('td')
                    latestBanSharesPct = float(tags_[-3].string[:-1])
        
        # get 分红融资 page
        tag = soup.find('a', text='分红融资')
        link = mainLink + tag.attrs['href'][2:]
        r = requests.get(link)
        soup = BeautifulSoup(r.text, 'lxml')

        # 历史送转记录
        shareFactor = 1 # 股本因子
        latestSendSharesDate = None

        tag = soup.find('th', text='分红方案说明')
        if tag is not None: # 新股有可能还没有过分红
            tag = tag.parent.parent.parent.find('tbody')
            tags = tag.find_all('tr')
            
            for tag in tags:
                tags_ = tag.find_all('td')
                dividendPlan = tags_[4].string # 每次的'分红方案说明'
                newShareFactor = self._getShareFactor(dividendPlan)
                shareFactor *= newShareFactor

                # 获取最近的送转日期
                if newShareFactor > 1 and latestSendSharesDate is None:
                    latestSendSharesDate = str(tags_[3].string) # 送转实施日期

        # 最近机构持股占流通股比例(%)
        fundPositionsRatio, fundNbr = DyStockDataSpider.getLatestFundPositionsRatio(code)

        # 财务报表里的指标
        otherIndicators = DyStockDataSpider.getLatestFinanceReport(code, ['净利润YoY(%)', '营业收入YoY(%)', '每股收益(元)', '每股现金流(元)'])

        return [navps, pfps, udpps, floatingShares, totalShares, latestReleaseDate, latestBanSharesPct, shareFactor, latestSendSharesDate, fundPositionsRatio] + otherIndicators

    def onStockDays(self, code, df):
        try:
            values = self._getIndicators(code)
        except Exception as ex:
            self._info.print('从同花顺爬取[{0}: {1}]数据错误[{2}]'.format(code, self._stockAllCodes[code], self._baseDate), DyLogData.warning)
            return

        # get ['现价'] and ['流通市值(亿元)', '总市值(亿元)']
        if df is None or df.empty:
            if not self._errorDaysEngine.loadCode(code, [self._baseDate, 0]):
                self._info.print('载入[{0}: {1}]日线数据错误[{2}]'.format(code, self._stockAllCodes[code], self._baseDate), DyLogData.warning)
                return

            df = self._errorDaysEngine.getDataFrame(code)

        pos = self.colNames.index('流通市值(亿元)') - self.colNames.index('每股净资产(元)')
        close = df.ix[-1, 'close']
        marketValues = [values[pos - 2]*close, values[pos - 1]*close]

        # get 股票上市日期
        marketDate = self._errorDaysEngine.getStockMarketDate(code, name=self._stockAllCodes[code])
        if marketDate is None:
            self._info.print('获取[{0}: {1}]上市日期错误'.format(code, self._stockAllCodes[code]), DyLogData.warning)
            return

        # combine, note that value positons should be aligned with @colNames
        self.__data[code] = [self._stockAllCodes[code]] + [close] + values[:pos] + marketValues + values[pos:] + [marketDate]

    def onDone(self):
        df = pd.DataFrame(self.__data).T
        start = self.colNames.index('每股净资产(元)')
        df.rename(columns={i: x for i, x in enumerate(['名称', '现价'] + self.colNames[start:])}, inplace=True)

        # add scores, default
        colNames = ['每股净资产(元)', '每股公积金(元)', '每股未分配利润(元)',
                    '总股本(亿)', '流通A股(亿)',
                    '现价',
                    '最近解禁日期', '解禁股占总股本比例(%)',
                    '股本因子',
                    '最近送转日期',
                    '机构持股占流通股比例(%)',
                    '营业收入YoY(%)'
                   ]

        df = self.__class__._addScores(df, colNames)

        # set result
        if self._selectStockNbr > 0:
            df = df.ix[:self._selectStockNbr]

        df.reset_index(inplace=True)

        self._result = df.values.tolist()

    def _addScores(df, colNames):
        """
            @df: index is code, and no ['排名', '得分'] columns
            @colNames: [colName], in which column is taken for calculating scores
        """
        columns = list(df.columns)
        newColumns = columns[:1] + ['排名', '得分'] + columns[1:]

        seriesList = []

        # rank for each indicator, think rank as score that the high score is the better is
        if '每股净资产(元)' in colNames:
            series = df['每股净资产(元)'].rank()
            seriesList.append(series)

        if '每股公积金(元)' in colNames:
            series = df['每股公积金(元)'].rank()
            seriesList.append(series)

        if '每股未分配利润(元)' in colNames:
            series = df['每股未分配利润(元)'].rank()
            seriesList.append(series)

        if '总股本(亿)' in colNames:
            series = df['总股本(亿)'].rank(ascending=False)
            seriesList.append(series)

        if '流通A股(亿)' in colNames:
            series = df['流通A股(亿)'].rank(ascending=False)
            seriesList.append(series)

        if '现价' in colNames:
            series = df['现价'].rank(ascending=False)
            seriesList.append(series)

        if '最近解禁日期' in colNames:
            series = df['最近解禁日期'].fillna('3000-01-01').rank(ascending=False)
            seriesList.append(series)

        if '解禁股占总股本比例(%)' in colNames:
            series = df['解禁股占总股本比例(%)'].fillna(0).rank()
            seriesList.append(series)

        if '股本因子' in colNames:
            series = df['股本因子'].rank(ascending=False)
            seriesList.append(series)

        if '最近送转日期' in colNames:
            # '最近送转日期', 若没有送转，则用上市日期替代
            series1 = df['最近送转日期']
            series2 = df['上市日期'][series1.isnull()]
            series1 = series1[series1.notnull()]
            series = pd.concat([series1, series2])

            series = series.rank(ascending=False)
            seriesList.append(series)

        if '机构持股占流通股比例(%)' in colNames:
            series = df['机构持股占流通股比例(%)'].rank(ascending=False)
            seriesList.append(series)

        if '营业收入YoY(%)' in colNames:
            series = df['营业收入YoY(%)'].rank()
            seriesList.append(series)

        if '净利润YoY(%)' in colNames:
            series = df['净利润YoY(%)'].rank()
            seriesList.append(series)

        if '每股收益(元)' in colNames:
            series = df['每股收益(元)'].rank()
            seriesList.append(series)

        if '每股现金流(元)' in colNames:
            series = df['每股现金流(元)'].rank()
            seriesList.append(series)

        # concat to rank DF
        rankDf = pd.concat(seriesList, axis=1)

        # total rank
        scoreSeries = rankDf.sum(axis=1)*100/(len(seriesList) * rankDf.shape[0])
        scoreSeries.sort_values(ascending=False, inplace=True)
        scoreSeries.name = '得分'

        rankSeries = scoreSeries.rank(ascending=False)
        rankSeries.name = '排名'

        df = pd.concat([df, scoreSeries, rankSeries], axis=1)
        df = df.reindex(columns=newColumns)

        df = df.ix[scoreSeries.index]

        return df

    def refactory(df, params):
        """
            @return: new rows list
        """
        # clean
        df.set_index('代码', inplace=True)
        del df['排名']
        del df['得分']

        # parse @params
        colNames = []
        for key, value in params.items():
            if value == 1:
                colNames.append(key)

        # add scores
        df = DySS_High2SendStocks._addScores(df, colNames)

        df.reset_index(inplace=True)
        return df.values.tolist()

    def getRefactoryParams():
        pos = DySS_High2SendStocks.colNames.index('得分') + 1

        colNames = ['每股净资产(元)', '每股公积金(元)', '每股未分配利润(元)',
                    '总股本(亿)',
                    '股本因子']

        return ['列名', '值(0:不使用,1:使用)'], [[x, 1] if x in colNames else [x, 0] for x in DySS_High2SendStocks.colNames[pos:]]