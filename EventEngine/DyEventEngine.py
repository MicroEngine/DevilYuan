import threading
import queue

from .DyEvent import *


class DyTimerHand(threading.Thread):
    def __init__(self, queue, eventEngine):
        super().__init__()

        self._intervals = {} # {interval: interval count}
        self._queue = queue
        self._eventEngine = eventEngine

    def run(self):
        while True:
            try:
                event = self._queue.get(block=True, timeout=1)
                interval = event.data

                # register event
                if event.type == DyEventType.register:
                    if interval not in self._intervals:
                        self._intervals[interval] = interval
                else: # unregister event
                    if interval in self._intervals:
                        del self._intervals[interval]
                
            except queue.Empty: # 1s time out
                for interval in self._intervals:
                    count = self._intervals[interval]

                    count -= 1

                    # trigger timer out event
                    if count == 0:
                        self._eventEngine.put(DyEvent(DyEventType.timer + str(interval)))

                        # new start
                        count = interval

                        if DyEventEngine.enableTimerLog:
                            print('Timer_%s'%interval)

                    self._intervals[interval] = count


class DyEventHand(threading.Thread):
    def __init__(self, queue):
        super().__init__()

        self._handlers = {} # {event type:[handlers]}
        self._queue = queue

    def run(self):
        while True:
            event = self._queue.get()

            if event.type == DyEventType.register:
                self._processRegisterEvent(event.data['type'], event.data['handler'])
            elif event.type == DyEventType.unregister:
                self._processUnregisterEvent(event.data['type'], event.data['handler'])
            else:
                self._processOtherEvent(event)

    def _processRegisterEvent(self, type, handler):
        if type not in self._handlers:
            self._handlers[type] = []

        if handler not in self._handlers[type]:
            self._handlers[type].append(handler)

    def _processUnregisterEvent(self, type, handler):
        if type in self._handlers:
            if handler in self._handlers[type]:
                self._handlers[type].remove(handler)

                if not self._handlers[type]:
                    del self._handlers[type]

    def _processOtherEvent(self, event):
        if event.type in self._handlers:
            for handler in self._handlers[event.type]:
                handler(event)


class DyEventEngine(threading.Thread):
    """
        事件引擎类

        非timer事件：
            三元组合（event type，handler，hand）标识一个事件监听。
            重复注册相同的事件监听（event type，handler，hand都相同），只有第一次注册生效。
            支持注销不存在的事件监听。

        timer事件：
            三元组合（handler，hand，timer interval）标识一个timer监听。
            重复注册相同的timer监听（handler，hand，timer interval都相同），只有第一次注册生效。
            也就是说，不同的timer interval，相同的handler和hand，是可以注册成功的。
            支持注销不存在的timer监听。
    """
    enableTimerLog = False


    def __init__(self, handNbr, timer=True):
        super().__init__()

        self._handNbr = handNbr

        # timer
        if timer:
            self._timerHandQueue = queue.Queue()
            self._timerHand = DyTimerHand(self._timerHandQueue, self)
        else:
            self._timerHandQueue = None
            self._timerHand = None

        self._timerMap = {} # {interval:{hand:[handlers]}}

        # hands
        self._hands = []
        self._handQueues = [] # each hand maps to one element in list, [Queue()]

        # main data of event engine
        self._engineQueue = queue.Queue()
        self._eventMap = {} # which hand handles which event, {event type:{hand:[handlers]}}

        self._initHands()

    def _initHands(self):
        for i in range(self._handNbr):
            queue_ = queue.Queue()
            self._handQueues.append(queue_)

            self._hands.append(DyEventHand(queue_))

    def _processUnregister(self, data):
        """ @data: {'type':,'handler':, 'hand':}
        """
        type = data['type']
        handler = data['handler']
        hand = data['hand']

        event = DyEvent(DyEventType.unregister)
        event.data['type'] = type
        event.data['handler'] = handler

        # remove handler from event map
        if type in self._eventMap:
            if hand in self._eventMap[type]:
                if handler in self._eventMap[type][hand]:
                    self._eventMap[type][hand].remove(handler)

                    # unregister from corresponding hand
                    self._handQueues[hand].put(event)

                    if not self._eventMap[type][hand]:
                        del self._eventMap[type][hand]

                if not self._eventMap[type]:
                    del self._eventMap[type]

    def _processRegister(self, data):
        """ @data: {'type':,'handler':, 'hand':}
        """
        type = data['type']
        handler = data['handler']
        hand = data['hand']

        event = DyEvent(DyEventType.register)
        event.data['type'] = type
        event.data['handler'] = handler

        # add to event map
        if type not in self._eventMap:
            self._eventMap[type] = {}

        if hand not in self._eventMap[type]:
            self._eventMap[type][hand] = []

        if handler not in self._eventMap[type][hand]:
            self._eventMap[type][hand].append(handler)

            # register to corresponding hand
            self._handQueues[hand].put(event)

    def _processRegisterTimer(self, data):
        # unpack
        interval = data['interval']
        handler = data['handler']
        hand = data['hand']

        # register timer event to corresponding hand
        self._processRegister(dict(type=DyEventType.timer + str(interval),
                                handler=handler,
                                hand=hand))

        # add to timer map
        if interval not in self._timerMap:
            self._timerMap[interval] = {}

            # register new interval to timer hand
            event = DyEvent(DyEventType.register)
            event.data = interval

            self._timerHandQueue.put(event)

        if hand not in self._timerMap[interval]:
            self._timerMap[interval][hand] = []

        if handler not in self._timerMap[interval][hand]:
            self._timerMap[interval][hand].append(handler)

    def _processUnregisterTimer(self, data):
        # unpack
        interval = data['interval']
        handler = data['handler']
        hand = data['hand']

        # unregister timer event from corresponding hand
        self._processUnregister(dict(type=DyEventType.timer + str(interval),
                                handler=handler,
                                hand=hand))

        # remove handler from timer map
        if interval in self._timerMap:
            if hand in self._timerMap[interval]:
                if handler in self._timerMap[interval][hand]:
                    self._timerMap[interval][hand].remove(handler)

                    if not self._timerMap[interval][hand]: # empty
                        del self._timerMap[interval][hand]

                if not self._timerMap[interval]: # empty
                    del self._timerMap[interval]

                    # no any handler for this timer, so unregister interval from timer hand
                    event = DyEvent(DyEventType.unregister)
                    event.data = interval

                    self._timerHandQueue.put(event)

    def run(self):
        while True:
            event = self._engineQueue.get()

            if event.type == DyEventType.registerTimer:
                self._processRegisterTimer(event.data)

            elif event.type == DyEventType.register:
                self._processRegister(event.data)

            elif event.type == DyEventType.unregisterTimer:
                self._processUnregisterTimer(event.data)

            elif event.type == DyEventType.unregister:
                self._processUnregister(event.data)

            else: # event for applications
                hands = self._eventMap.get(event.type)
                if hands is not None:
                    for hand in hands: # hand which is listening this event
                        self._handQueues[hand].put(event)

    def registerTimer(self, handler, hand=None, interval=1):
        if hand is None:
            hand = self._handNbr - 1

        event = DyEvent(DyEventType.registerTimer)
        event.data = dict(hand=hand, handler=handler, interval=interval)

        self.put(event)

    def register(self, type, handler, hand=None):
        if hand is None:
            hand = self._handNbr - 1

        event = DyEvent(DyEventType.register)
        event.data = dict(type=type, handler=handler, hand=hand)

        self.put(event)

    def unregister(self, type, handler, hand=None):
        if hand is None:
            hand = self._handNbr - 1

        event = DyEvent(DyEventType.unregister)
        event.data = dict(type=type, handler=handler, hand=hand)

        self.put(event)

    def unregisterTimer(self, handler, hand=None, interval=1):
        if hand is None:
            hand = self._handNbr - 1

        event = DyEvent(DyEventType.unregisterTimer)
        event.data = dict(hand=hand, handler=handler, interval=interval)

        self.put(event)

    def put(self, event):
        self._engineQueue.put(event)

    def stop(self):
        pass

    def start(self):
        for hand in self._hands:
            hand.start()

        if self._timerHand:
            self._timerHand.start()

        super().start()


class DyDummyEventEngine:
    def __init__(self):
        pass

    def put(self, event):
        pass
