from DyCommon.DyCommon import *
from ....Common.DyStockCommon import *


class DyStockDataSectorCodeTable(object):
    """
        按日期的板块成份股票代码表
        除了数据更新到数据库外，板块的成份股代码表最终还是要通过DyStockDataCodeTable载入
    """


    def __init__(self, mongoDbEngine, gateway, info):
        self._mongoDbEngine = mongoDbEngine
        self._gateway = gateway
        self._info = info

        self._sectorStockCodeTable = {} # {sector index: {code: name}}

    def _init(self, sectorCode):
        self._sectorStockCodeTable[sectorCode] = {}

    def getSectorStockCodes(self, sectorCode):
        return self._sectorStockCodeTable[sectorCode]

    def load(self, sectorCode, date, codes=None):
        """
            @codes: None, load all stock codes of sector
                    [], not load any code
                    [code], load specified [code] in sector
        """
        self._info.print('开始载入[{0}]股票代码表[{1}]...'.format(DyStockCommon.sectors[sectorCode], date))

        # 初始化板块相关的数据
        self._init(sectorCode)

        data = self._mongoDbEngine.getSectorStockCodes(date, sectorCode, codes)
        if data is None:
            return False

        codeTable = self._sectorStockCodeTable[sectorCode]
        for doc in data:
            codeTable[doc['code']] = doc['name']

        self._info.print('[{0}]股票代码表载入完成'.format(DyStockCommon.sectors[sectorCode]))
        return True

    def _update2Db(self, sectorCode, date, codes):

        # convert to MongoDB format
        codesForDb = [{'code': code, 'name': name} for code, name in codes.items()]

        # update into DB
        return self._mongoDbEngine.updateSectorStockCodes(sectorCode, date, codesForDb)

    def _set(self, sectorCode, codesDict):
        """
            set codes gotten from Gateway to DB
            @codesDict: {date: {code: name}}
        """
        codesInDb = self._sectorStockCodeTable[sectorCode]
        for date, codes in codesDict.items():
            for code in codes:
                if code not in codesInDb:
                    self._info.print('[{0}]股票代码表[{1}]变化'.format(DyStockCommon.sectors[sectorCode], date), DyLogData.ind1)

                    # update to DB
                    if not self._update2Db(sectorCode, date, codes):
                        return False

                    # new codes in DB
                    codesInDb = codes

                    break

        return True

    def update(self, sectorCode, startDate, endDate):
        self._info.print('开始更新[{0}]股票代码表[{1}, {2}]...'.format(DyStockCommon.sectors[sectorCode], startDate, endDate))

        # first, load from DB without caring about return value.
        self.load(sectorCode, startDate)

        # always getting from Gateway
        codesDict = self._gateway.getSectorStockCodes(sectorCode, startDate, endDate)
        if codesDict is None:
            return False

        # set codes gotten from Gateway to DB
        return self._set(sectorCode, codesDict)

    def updateAll(self, startDate, endDate):
        """
            update code table of all sectors
        """
        for sectorCode in DyStockCommon.sectors:
            self.update(sectorCode, startDate, endDate)
    