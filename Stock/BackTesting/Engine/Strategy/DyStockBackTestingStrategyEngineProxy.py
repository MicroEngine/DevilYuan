import multiprocessing
import threading
import queue

from .DyStockBackTestingStrategyEngineProcess import *


class DyStockBackTestingStrategyEngineProxy(threading.Thread):
    """ 以进程方式启动一个周期的策略回测 """

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

    def startBackTesting(self, reqData):
        childQueue = self._ctx.Queue()
        self._childQueues.append(childQueue)

        p = self._ctx.Process(target=dyStockBackTestingStrategyEngineProcess, args=(self._queue, childQueue, reqData))
        p.start()

        self._processes.append(p)


class DyStockBackTestingStrategyEngineProxyThread(threading.Thread):
    """ 以线程方式启动一个周期的策略回测, 主要做调试用 """

    def __init__(self, eventEngine):
        super().__init__()

        self._eventEngine = eventEngine

        self._queue = queue.Queue() # queue to receive event from child threads

        self._threads = []
        self._childQueues = []

        self.start()

    def run(self):
        while True:
            event = self._queue.get()

            self._eventEngine.put(event)

    def startBackTesting(self, reqData):
        childQueue = queue.Queue()
        self._childQueues.append(childQueue)

        t = threading.Thread(target=dyStockBackTestingStrategyEngineProcess, args=(self._queue, childQueue, reqData))
        t.start()

        self._threads.append(t)
