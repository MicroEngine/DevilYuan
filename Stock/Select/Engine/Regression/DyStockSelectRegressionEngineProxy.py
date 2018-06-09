import multiprocessing
import threading

from .DyStockSelectRegressionEngineProcess import *
from ....Common.DyStockCommon import DyStockCommon


class DyStockSelectRegressionEngineProxy(threading.Thread):
    threadMode = False # only for debug without care about errors


    def __init__(self, eventEngine):
        super().__init__()

        self._eventEngine = eventEngine

        self._ctx = multiprocessing.get_context('spawn')
        self._queue = self._ctx.Queue() # queue to receive event from child processes

        self._processes = []
        self._childQueues = []

        self.start()

    def run(self):
        while True:
            event = self._queue.get()

            self._eventEngine.put(event)

    def startRegression(self, tradeDays, strategy, codes = None):
        """
            @strategy: {'class':strategyCls, 'param': strategy paramters}
        """
        _childQueue = self._ctx.Queue()
        self._childQueues.append(_childQueue)

        if self.threadMode:
            p = threading.Thread(target=dyStockSelectRegressionEngineProcess, args=(self._queue, _childQueue, tradeDays, strategy, codes, DyStockCommon.defaultHistDaysDataSource))
        else:
            p = self._ctx.Process(target=dyStockSelectRegressionEngineProcess, args=(self._queue, _childQueue, tradeDays, strategy, codes, DyStockCommon.defaultHistDaysDataSource))

        p.start()

        self._processes.append(p)
