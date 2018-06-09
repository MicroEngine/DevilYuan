import asyncio
import aiohttp
import re

class DySinaStockQuotation(object):
    """description of class"""

    maxNum = 800
    grep_detail = re.compile(r'(\w+)=([^\s][^,]+?)%s%s' % (r',([\.\d]+)' * 29, r',([-\.\d:]+)' * 2))
    stock_api = 'http://hq.sinajs.cn/?format=text&list='

    def __init__(self):
        self._stockList = [] # include indexes


    def _add2List(self, stockCodes):
        # stored list
        allStocks = []

        for stock in self._stockList:
            allStocks += stock.split(',')

        # combine with new stocks
        allStocks += stockCodes

        # generate new stock list
        self._stockList = []
        for i in range(0, len(allStocks), self.maxNum):
            self._stockList.append(','.join(allStocks[i:i + self.maxNum]))


    def addIndexes(self, indexes):
        indexes = list(
                map(lambda index: ('sh%s' if index.startswith(('0')) else 'sz%s') % index[:-3],
                    indexes))

        self._add2List(indexes)

    def add(self, stockCodes):
        sinaStocks = list(
                map(lambda stockCode: ('sh%s' if stockCode.startswith(('5', '6', '9')) else 'sz%s') % stockCode[:-3],
                    stockCodes))

        self._add2List(sinaStocks)

    def get(self):
        return self._get_stock_data(self._stockList)

    @asyncio.coroutine
    def _get_stocks_by_range(self, params):
        r = yield from aiohttp.get(self.stock_api + params)
        response_text = yield from r.text()
        return response_text

    def _get_stock_data(self, stock_list):
        if not stock_list:
            return {}

        coroutines = []
        for params in stock_list:
            coroutine = self._get_stocks_by_range(params)
            coroutines.append(coroutine)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        res = loop.run_until_complete(asyncio.gather(*coroutines))

        return self._format_response_data(res)

    def _format_response_data(self, rep_data):
        stocks_detail = ''.join(rep_data)
        result = self.grep_detail.finditer(stocks_detail)
        stock_dict = dict()
        for stock_match_object in result:
            stock = stock_match_object.groups()
            stock_dict[stock[0]] = dict(
                    name=stock[1],
                    open=float(stock[2]),
                    pre_close=float(stock[3]), # 昨日收盘价
                    now=float(stock[4]),
                    high=float(stock[5]),
                    low=float(stock[6]),
                    buy=float(stock[7]), # 竞买价，即“买一”报价
                    sell=float(stock[8]), # 竞卖价，即“卖一”报价
                    volume=int(stock[9]), # 成交的股票数，由于股票交易以一百股为基本单位，所以在使用时，通常把该值除以一百
                    amount=float(stock[10]), # 成交金额，单位为“元”，为了一目了然，通常以“万元”为成交金额的单位，所以通常把该值除以一万
                    bid1_volume=int(stock[11]), # “买一”申请股数
                    bid1=float(stock[12]), # “买一”报价
                    bid2_volume=int(stock[13]),
                    bid2=float(stock[14]),
                    bid3_volume=int(stock[15]),
                    bid3=float(stock[16]),
                    bid4_volume=int(stock[17]),
                    bid4=float(stock[18]),
                    bid5_volume=int(stock[19]),
                    bid5=float(stock[20]),
                    ask1_volume=int(stock[21]), # “卖一”申报股数
                    ask1=float(stock[22]), # “卖一”报价
                    ask2_volume=int(stock[23]),
                    ask2=float(stock[24]),
                    ask3_volume=int(stock[25]),
                    ask3=float(stock[26]),
                    ask4_volume=int(stock[27]),
                    ask4=float(stock[28]),
                    ask5_volume=int(stock[29]),
                    ask5=float(stock[30]),
                    date=stock[31],
                    time=stock[32],
            )
        return stock_dict
