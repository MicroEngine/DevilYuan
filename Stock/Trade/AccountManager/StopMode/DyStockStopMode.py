class DyStockStopMode(object):
    
    def __init__(self, accountManager):
        self._accountManager = accountManager

    def onOpen(self, date):
        return True

    def onTicks(self, ticks):
        pass

    def onBars(self, bars):
        pass

    def setAccountManager(self, accountManager):
        self._accountManager = accountManager
