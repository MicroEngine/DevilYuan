class PyRealTimeStockFilter(object):
    """description of class"""

    def __init__(self):
        self._filters = {} # {strategy name:{monitored stock1:None, monitored stock2:None, ...}}

    def addFilter(self, strategyName, monitoredStocks):
        pass

    def filter(self, strategyName, stocks):
        pass


