from EventEngine.DyEvent import *


class DyStockStrategyState:
    running = 'sRunning'
    monitoring = 'sMonitoring'

    backTesting = 'sBackTesting'

    def __init__(self, *states):
        self._state = None

        self.add(*states)

    @property
    def state(self):
        if self._state is None:
            return '空'

        state = self._state.replace(self.running, '运行')
        state = state.replace(self.monitoring, '监控')
        state = state.replace(self.backTesting, '回测')

        return state

    def add(self, *states):
        if self._state:
            self._state +=  ('+' + '+'.join(states))
        else:
            if states:
                self._state = '+'.join(states)

    def isState(self, state):
        if self._state is None:
            if state is None:
                return True
            else:
                return False

        if state in self._state:
            return True

        return False

    def remove(self, *states):
        if not self._state: return

        curStates = self._state.split('+')

        for state in states:
            if state in curStates:
                curStates.remove(state)

        curStates = '+'.join(curStates)

        if not curStates:
            curStates = None

        self._state = curStates

    def checkState(self, state, strategyCls, eventEngine):
        if self.isState(state):
            return

        self.add(state)

        if self._state == state:
            event = DyEvent(DyEventType.startStockCtaStrategy)

            event.data['class'] = strategyCls
            event.data['state'] = DyStockStrategyState(self._state)
        else:
            event = DyEvent(DyEventType.changeStockCtaStrategyState)

            event.data['class'] = strategyCls
            event.data['state'] = DyStockStrategyState(*self._state.split('+'))

        eventEngine.put(event)

    def uncheckState(self, state, strategyCls, eventEngine):
        if not self.isState(state):
            return

        self.remove(state)

        if not self._state:
            event = DyEvent(DyEventType.stopStockCtaStrategy)

            event.data['class'] = strategyCls
        else:
            event = DyEvent(DyEventType.changeStockCtaStrategyState)

            event.data['class'] = strategyCls
            event.data['state'] = DyStockStrategyState(self._state)

        eventEngine.put(event)

    def checkAll(self, strategyCls, eventEngine):
        """ check '运行' 和 '监控' """

        if self.isState(DyStockStrategyState.running) and self.isState(DyStockStrategyState.monitoring):
            return

        if self._state is None:
            event = DyEvent(DyEventType.startStockCtaStrategy)

            event.data['class'] = strategyCls
            event.data['state'] = DyStockStrategyState(DyStockStrategyState.running, DyStockStrategyState.monitoring)

            self.add(DyStockStrategyState.running, DyStockStrategyState.monitoring)

        else:
            if self.isState(DyStockStrategyState.running):
                self.add(DyStockStrategyState.monitoring)
            else:
                self.add(DyStockStrategyState.running)

            event = DyEvent(DyEventType.changeStockCtaStrategyState)

            event.data['class'] = strategyCls
            event.data['state'] = DyStockStrategyState(DyStockStrategyState.monitoring, DyStockStrategyState.running)

        eventEngine.put(event)

    def uncheckAll(self, strategyCls, eventEngine):
        if self._state is None:
            return

        self._state = None

        event = DyEvent(DyEventType.stopStockCtaStrategy)
        event.data['class'] = strategyCls

        eventEngine.put(event)


