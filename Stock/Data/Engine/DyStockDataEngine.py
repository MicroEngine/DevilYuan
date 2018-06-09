from EventEngine.DyEvent import *
from ..DyStockDataCommon import *
from .DyStockMongoDbEngine import *
from ..Gateway.DyStockDataGateway import *
from .DyStockDataTicksEngine import *
from .DyStockDataDaysEngine import *
from .DyStockDataStrategyDataPrepareEngine import *


class DyStockDataEngine(object):

    class State:
        sWaitingDays = 'sWaitingDays'
        sWaitingTicks = 'sWaitingTicks'

    def __init__(self, eventEngine, info, registerEvent=True):
        self._eventEngine = eventEngine
        self._info = info

        self._mongoDbEngine = DyStockMongoDbEngine(self._info)
        self._gateway = DyStockDataGateway(self._eventEngine, self._info, registerEvent)

        self._daysEngine = DyStockDataDaysEngine(self._eventEngine, self._mongoDbEngine, self._gateway, self._info, registerEvent)
        self._ticksEngine = DyStockDataTicksEngine(self._eventEngine, self._daysEngine, self._mongoDbEngine, self._gateway, self._info, registerEvent)

        self._strategyDataPrepareEngine = DyStockDataStrategyDataPrepareEngine(self._eventEngine, self, self._info, registerEvent)

        self._isStopped = False
        self._updateDates = None
        self._oneKeyUpdateState = None

        if registerEvent:
            self._registerEvent()

    @property
    def daysEngine(self):
        return self._daysEngine

    @property
    def ticksEngine(self):
        return self._ticksEngine

    @property
    def eventEngine(self):
        return self._eventEngine

    @property
    def info(self):
        return self._info

    def _registerEvent(self):
        self._eventEngine.register(DyEventType.stockOneKeyUpdate, self._stockOneKeyUpdateHandler)
        self._eventEngine.register(DyEventType.stopStockOneKeyUpdateReq, self._stopStockOneKeyUpdateReqHandler)
        self._eventEngine.register(DyEventType.stockDaysCommonUpdateFinish, self._stockDaysCommonUpdateFinishHandler)

        self._eventEngine.register(DyEventType.stopAck, self._stopAckHandler)
        self._eventEngine.register(DyEventType.finish, self._finishHandler)
        self._eventEngine.register(DyEventType.fail, self._failHandler)

    def _stockOneKeyUpdateHandler(self, event):
        if self._oneKeyUpdateState is None:

            # 自动更新日线数据
            event = DyEvent(DyEventType.updateStockHistDays)
            event.data = None

            self._eventEngine.put(event)

            self._isStopped = False
            self._updateDates = None
            self._oneKeyUpdateState = DyStockDataEngine.State.sWaitingDays

    def _stopStockOneKeyUpdateReqHandler(self, event):
        self._isStopped = True

        if self._oneKeyUpdateState == DyStockDataEngine.State.sWaitingDays:
            self._eventEngine.put(DyEvent(DyEventType.stopUpdateStockHistDaysReq))

        elif self._oneKeyUpdateState == DyStockDataEngine.State.sWaitingTicks:
            self._eventEngine.put(DyEvent(DyEventType.stopUpdateStockHistTicksReq))
            
    def _stockDaysCommonUpdateFinishHandler(self, event):
        if self._oneKeyUpdateState == DyStockDataEngine.State.sWaitingDays:
            self._updateDates = event.data

    def _finishHandler(self, event):
        if self._oneKeyUpdateState == DyStockDataEngine.State.sWaitingDays:
            if self._isStopped:
                self._eventEngine.put(DyEvent(DyEventType.stopAck)) # for UI
                self._oneKeyUpdateState = None

            else:
                if self._updateDates is not None:
                    event = DyEvent(DyEventType.updateStockHistTicks)
                    event.data = self._updateDates

                    self._eventEngine.put(event)

                    self._oneKeyUpdateState = DyStockDataEngine.State.sWaitingTicks
                else:
                    # UI is waiting for 2 actions, when no need to update ticks, it means ticks updating is finished also.
                    self._eventEngine.put(DyEvent(DyEventType.finish))

                    self._oneKeyUpdateState = None

        elif self._oneKeyUpdateState == DyStockDataEngine.State.sWaitingTicks:
            self._oneKeyUpdateState = None

    def _failHandler(self, event):
        if self._oneKeyUpdateState == DyStockDataEngine.State.sWaitingDays:
            self._eventEngine.put(DyEvent(DyEventType.fail)) # for UI

            self._oneKeyUpdateState = None

        elif self._oneKeyUpdateState == DyStockDataEngine.State.sWaitingTicks:
            self._oneKeyUpdateState = None

    def _stopAckHandler(self, event):
        if self._oneKeyUpdateState == DyStockDataEngine.State.sWaitingDays:
            self._eventEngine.put(DyEvent(DyEventType.stopAck)) # for UI

            self._oneKeyUpdateState = None

        elif self._oneKeyUpdateState == DyStockDataEngine.State.sWaitingTicks:
            self._oneKeyUpdateState = None
