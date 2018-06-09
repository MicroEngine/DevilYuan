from .DyStockDataCodeTable import *
from .DyStockDataTradeDayTable import *
from .DyStockDataSectorCodeTable import *


class DyStockDataCommonEngine(object):
    """ 代码表和交易日数据引擎 """

    def __init__(self, mongoDbEngine, gateway, info):
        self._mongoDbEngine = mongoDbEngine
        self._gateway = gateway
        self._info = info

        self._codeTable = DyStockDataCodeTable(self._mongoDbEngine, self._gateway, self._info)
        self._tradeDayTable = DyStockDataTradeDayTable(self._mongoDbEngine, self._gateway, self._info)

        self._sectorCodeTable = DyStockDataSectorCodeTable(self._mongoDbEngine, self._gateway, self._info)

    def updateCodes(self):
        return self._codeTable.update()

    def updateTradeDays(self, startDate, endDate):
        return self._tradeDayTable.update(startDate, endDate)

    def updateSectorCodes(self, sectorCode, startDate, endDate):
        return self._sectorCodeTable.update(sectorCode, startDate, endDate)

    def updateAllSectorCodes(self, startDate, endDate):
        return self._sectorCodeTable.updateAll(startDate, endDate)

    def getTradeDays(self, startDate, endDate):
        return self._tradeDayTable.get(startDate, endDate)

    def getLatestDateInDb(self):
        return self._tradeDayTable.getLatestDateInDb()

    def getLatestTradeDayInDb(self):
        return self._tradeDayTable.getLatestTradeDayInDb()

    def getIndex(self, code):
        return self._codeTable.getIndex(code)

    def getCode(self, name):
        return self._codeTable.getCode(name)

    def getIndexStockCodes(self, index=None):
        return self._codeTable.getIndexStockCodes(index)

    def getIndexSectorStockCodes(self, index=None):
        if index in DyStockCommon.sectors:
            return self._sectorCodeTable.getSectorStockCodes(index)
            
        return self._codeTable.getIndexStockCodes(index)

    @property
    def shIndex(self):
        return self._codeTable.shIndex

    @property
    def szIndex(self):
        return self._codeTable.szIndex

    @property
    def cybIndex(self):
        return self._codeTable.cybIndex

    @property
    def zxbIndex(self):
        return self._codeTable.zxbIndex

    @property
    def etf50(self):
        return self._codeTable.etf50

    @property
    def etf300(self):
        return self._codeTable.etf300

    @property
    def etf500(self):
        return self._codeTable.etf500

    @property
    def stockFunds(self):
        return self._codeTable.stockFunds

    @property
    def stockSectors(self):
        return self._codeTable.stockSectors

    @property
    def stockCodesFunds(self):
        return self._codeTable.stockCodesFunds

    @property
    def stockAllCodesFunds(self):
        return self._codeTable.stockAllCodesFunds

    @property
    def stockAllCodesFundsSectors(self):
        return self._codeTable.stockAllCodesFundsSectors

    @property
    def stockAllCodes(self):
        return self._codeTable.stockAllCodes

    @property
    def stockCodes(self):
        return self._codeTable.stockCodes

    @property
    def stockIndexes(self):
        return self._codeTable.stockIndexes

    @property
    def stockIndexesSectors(self):
        return self._codeTable.stockIndexesSectors

    def tDaysOffset(self, base, n):
        return self._tradeDayTable.tDaysOffset(base, n)

    def tDaysOffsetInDb(self, base, n=0):
        return self._tradeDayTable.tDaysOffsetInDb(base, n)

    def tDays(self, start, end):
        return self._tradeDayTable.get(start, end)

    def tDaysCountInDb(self, start, end):
        return self._tradeDayTable.tDaysCountInDb(start, end)
     
    def tLatestDay(self):
        return self._tradeDayTable.tLatestDay()

    def tOldestDay(self):
        return self._tradeDayTable.tOldestDay()

    def isInTradeDayTable(self, startDate, endDate):
        return self._tradeDayTable.isIn(startDate, endDate)

    def load(self, dates, codes=None):
        if not self._codeTable.load(codes):
            return False

        return self._tradeDayTable.load(dates)

    def loadCodeTable(self, codes=None):
        return self._codeTable.load(codes)

    def loadTradeDays(self, dates):
        return self._tradeDayTable.load(dates)

    def loadSectorCodeTable(self, sectorCode, date, codes=None):
        return self._sectorCodeTable.load(sectorCode, date, codes)

    def getSectorCodes(self, sectorCode):
        return self._sectorCodeTable.getSectorStockCodes(sectorCode)