from EventEngine.DyEvent import *
from ...Data.Viewer.DyStockDataViewer import *
from ...Data.Viewer.DyStockDataWindow import *
from ...Data.Engine.DyStockDataEngine import *
from ..DyStockSelectCommon import *


class DyStockSelectViewerEngine(object):
    
    def __init__(self, eventEngine, info):
        self._eventEngine = eventEngine
        self._info = info

        self._testedStocks = None

        self._initDataViewer()

        self._registerEvent()

    def _initDataViewer(self):
        self._dataEngine = DyStockDataEngine(self._eventEngine, self._info, False)
        self._dataViewer = DyStockDataViewer(self._dataEngine, self._info)
        self._dataWindow = DyStockDataWindow(self._dataEngine, self._info)

        # 省去非错误log的输出
        errorInfo = DyErrorInfo(self._eventEngine)
        self._errorDataEngine = DyStockDataEngine(self._eventEngine, errorInfo, False)

    def _registerEvent(self):
        self._eventEngine.register(DyEventType.plotReq, self._plotReqHandler, DyStockSelectEventHandType.viewer)
        self._eventEngine.register(DyEventType.stockSelectTestedCodes, self._stockSelectTestedCodesHandler, DyStockSelectEventHandType.viewer)

    def _stockSelectTestedCodesHandler(self, event):
        self._testedStocks = event.data

        self._dataViewer.setTestedStocks(self._testedStocks)
        self._dataWindow.setTestedStocks(self._testedStocks)

    def _plotReqHandler(self, event):
        type = event.data['type']

        if type == 'bBandsStats': # 布林统计
            self._dataWindow.plotReqBBandsStats(event.data['code'],
                                             event.data['startDate'],
                                             event.data['endDate'],
                                             event.data['bBands1Period'],
                                             event.data['bBands2Period']
                                             )

        elif type == 'jaccardIndex': # 杰卡德指数
            self._dataWindow.plotReqJaccardIndex(event.data['startDate'],
                                             event.data['endDate'],
                                             event.data['param']
                                             )

        elif type == 'indexConsecutiveDayLineStats': # 指数连续日阴线统计
            self._dataWindow.plotReqIndexConsecutiveDayLineStats(event.data['startDate'],
                                             event.data['endDate'],
                                             event.data['greenLine']
                                             )

        elif type == 'limitUpStats': # 封板率统计
            self._dataWindow.plotReqLimitUpStats(event.data['startDate'],
                                             event.data['endDate']
                                             )

        elif type == 'focusAnalysis': # 热点分析
            self._dataWindow.plotReqFocusAnalysis(event.data['startDate'],
                                             event.data['endDate']
                                             )

        elif type == 'highLowDist': # 最高和最低价分布
            self._dataWindow.plotReqHighLowDist(event.data['startDate'],
                                             event.data['endDate'],
                                             size=1
                                             )

        elif type == 'test':
            self._dataViewer.plotReqTest()

