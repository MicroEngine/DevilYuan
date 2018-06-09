from DyEventType import *
from DyEventEngine import *
from DyCtaStockBase import *

from DySinaQuotation import *


class PyRealTimeStockMarketMonitor(object):
    """ Real time monitor stock market """

    def __init__(self, eventEngine):
        self._eventEngine = eventEngine

        self._monitoredStocks = []

        self._sinaQuotation = DySinaQuotation()

    def _stockMarketMonitorHandler(self, event):

        newCodes = []
        for code in event.data['data']:
            if code not in self._monitoredStocks:
                self._monitoredStocks.append(code)
                newCodes.append(code)

        if newCodes:
            self._sinaQuotation.add(newCodes)

    def _timerHandler(self, event):
        sinaStockTickData = self._sinaQuotation.get()

        ctaTickDatas = self._convert(sinaStockTickData)

        self._putTickEvent(ctaTickDatas)

    def _convert(self, sinaStockTickData):
        """ convert sina tick stock data to DyCtaStockTickData """

        ctaTickDatas = {} # {code:cta tick data}
        for code, data in sinaStockTickData.items():
            ctaTickData = DyCtaStockTickData()

            ctaTickData.convertFromSina(code, data)

            ctaTickDatas[ctaTickData.code] = ctaTickData

    def _registerEvent(self):
        self._eventEngine.register(DyEventType.stockMarketMonitor, self._stockMarketMonitorHandler, DyEventHandType.sinaStockQuotation)
        self._eventEngine.register(DyEventType.timer, self._timerHandler, DyEventHandType.sinaStockQuotation)

    def _putTickEvent(self, ctaTickDatas):
        event = DyEvent(DyEvent.stockTick)
        event.data['data'] = ctaTickDatas

        self._eventEngine.put(event)