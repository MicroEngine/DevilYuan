from .DyStockSelectRegressionEngineProxy import *
from ....Data.Engine.Common.DyStockDataCommonEngine import *
from ....Data.Engine.DyStockMongoDbEngine import *
from DyCommon.DyCommon import *


class DyStockSelectRegressionEngine(object):

    periodNbr = 4 # 一个周期一个进程
    
    def __init__(self, eventEngine, info):
        self._eventEngine = eventEngine
        self._info = info

        self._progress = DyProgress(self._info)

        self._proxy = DyStockSelectRegressionEngineProxy(self._eventEngine)
        self._testedStocks = None

        self._registerEvent()

    def _stockSelectTestedCodesHandler(self, event):
        self._testedStocks = event.data

    def _regression(self, startDate, endDate, strategyCls, parameters):

        self._progress.reset()

        # load code table and trade days table
        commonEngine = DyStockDataCommonEngine(DyStockMongoDbEngine(self._info), None, self._info)
        if not commonEngine.load([startDate, endDate]):
            return False

        self._info.print("开始回归策略: {0}[{1}, {2}]...".format(strategyCls.chName, startDate, endDate), DyLogData.ind)

        strategy = {'class':strategyCls, 'param':parameters}
        tradeDays = commonEngine.getTradeDays(startDate, endDate)

        # init progress
        self._progress.init(len(tradeDays))

        stepSize = (len(tradeDays) + self.periodNbr - 1)//self.periodNbr
        if stepSize == 0: return False

        # start processes
        for i in range(0, len(tradeDays), stepSize):
            self._proxy.startRegression(tradeDays[i:i + stepSize], strategy, self._testedStocks)

        return True

    def _stockSelectStrategyRegressionReqHandler(self, event):
        # unpack
        strategyCls = event.data['class']
        parameters = event.data['param']
        startDate = event.data['startDate']
        endDate = event.data['endDate']

        # regression
        if not self._regression(startDate, endDate, strategyCls, parameters):
            self._eventEngine.put(DyEvent(DyEventType.fail))
    
    def _stockSelectStrategyRegressionAckHandler(self, event):
        self._progress.update()

        if self._progress.totalReqCount == 0:
            self._eventEngine.put(DyEvent(DyEventType.finish))

    def _registerEvent(self):
        self._eventEngine.register(DyEventType.stockSelectStrategyRegressionReq, self._stockSelectStrategyRegressionReqHandler, DyStockSelectEventHandType.engine)
        self._eventEngine.register(DyEventType.stockSelectStrategyRegressionAck, self._stockSelectStrategyRegressionAckHandler, DyStockSelectEventHandType.engine)
        self._eventEngine.register(DyEventType.stockSelectTestedCodes, self._stockSelectTestedCodesHandler, DyStockSelectEventHandType.engine)


