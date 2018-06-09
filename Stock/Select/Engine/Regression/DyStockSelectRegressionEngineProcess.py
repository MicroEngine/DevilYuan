import queue

from DyCommon.DyCommon import *
from EventEngine.DyEvent import *
from EventEngine.DyEventEngine import *
from ..DyStockSelectSelectEngine import *
from ....Common.DyStockCommon import DyStockCommon


def dyStockSelectRegressionEngineProcess(outQueue, inQueue, tradeDays, strategy, codes, histDaysDataSource):
    strategyCls = strategy['class']
    parameters = strategy['param']

    DyStockCommon.defaultHistDaysDataSource = histDaysDataSource

    dummyEventEngine = DyDummyEventEngine()
    queueInfo = DyQueueInfo(outQueue)

    selectEngine = DyStockSelectSelectEngine(dummyEventEngine, queueInfo, False)
    selectEngine.setTestedStocks(codes)

    for day in tradeDays:
        try:
            event = inQueue.get_nowait()
        except queue.Empty:
            pass

        parameters['基准日期'] = day

        if selectEngine.runStrategy(strategyCls, parameters):
            event = DyEvent(DyEventType.stockSelectStrategyRegressionAck)
            event.data['class'] = strategyCls
            event.data['period'] = [tradeDays[0], tradeDays[-1]]
            event.data['day'] = day
            event.data['result'] = selectEngine.result

            outQueue.put(event)
        else:
            queueInfo.print('回归选股策略失败:{0}, 周期[{1}, {2}], 基准日期{3}'.format(strategyCls.chName, tradeDays[0], tradeDays[-1], day), DyLogData.error)

