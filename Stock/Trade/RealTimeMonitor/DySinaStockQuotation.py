import asyncio
import aiohttp
import re

class DySinaStockQuotation(object):
    """description of class"""

    maxNum = 800
    grep_detail = re.compile(r'(\d+)=([^\s][^,]+?)%s%s' % (r',([\.\d]+)' * 29, r',([-\.\d:]+)' * 2))
    stock_api = 'http://hq.sinajs.cn/?format=text&list='

    def __init__(self):
        self._stockList = []

    def add(self, stockCodes):
        sinaStocks = list(
                map(lambda stockCode: ('sh%s' if stockCode.startswith(('5', '6', '9')) else 'sz%s') % stockCode[:-3],
                    stockCodes))

        for i in range(0, len(stockCodes), self.maxNum):
            self._stockList.append(','.join(sinaStocks[i:i + self.maxNum]))

    def get(self):
        return self._get_stock_data(self._stockList)

    @asyncio.coroutine
    def _get_stocks_by_range(self, params):
        r = yield from aiohttp.get(self.stock_api + params)
        response_text = yield from r.text()
        return response_text

    def _get_stock_data(self, stock_list):
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
                    close=float(stock[3]),
                    now=float(stock[4]),
                    high=float(stock[5]),
                    low=float(stock[6]),
                    buy=float(stock[7]),
                    sell=float(stock[8]),
                    turnover=int(stock[9]),
                    volume=float(stock[10]),
                    bid1_volume=int(stock[11]),
                    bid1=float(stock[12]),
                    bid2_volume=int(stock[13]),
                    bid2=float(stock[14]),
                    bid3_volume=int(stock[15]),
                    bid3=float(stock[16]),
                    bid4_volume=int(stock[17]),
                    bid4=float(stock[18]),
                    bid5_volume=int(stock[19]),
                    bid5=float(stock[20]),
                    ask1_volume=int(stock[21]),
                    ask1=float(stock[22]),
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
