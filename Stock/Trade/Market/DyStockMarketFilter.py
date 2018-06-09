class DyStockMarketFilter(object):

    def __init__(self, monitoredStocks=None):
        self._filter = None if monitoredStocks is None else set(monitoredStocks) # [code]

    def addFilter(self, monitoredStocks):
        if self._filter is None:
            self._filter = set(monitoredStocks)
        else:
            self._filter |= set(monitoredStocks)

    def filter(self, data):
        """ 过滤市场发过来的股票tick数据或者bar数据
            @data: {code:DyStockCtaTickData} or {code:DyStockCtaBarData}
            @return: {code:DyStockCtaTickData} or {code:DyStockCtaBarData}
        """
        if self._filter is None:
            return data

        newData = {}
        for code in self._filter:
            data_ = data.get(code)
            if data_ is not None:
                newData[code] = data_

        return newData

    def removeFilter(self, stocks):
        if self._filter is not None:
            self._filter -= set(stocks)

    @property
    def codes(self):
        return self._filter

