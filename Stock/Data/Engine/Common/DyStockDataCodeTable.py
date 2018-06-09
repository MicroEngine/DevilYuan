import operator
import os
import copy

from DyCommon.DyCommon import *
from ....Common.DyStockCommon import *


class DyStockDataCodeTable:
    """
        股票代码表
        大盘指数，个股，基金（ETF），板块是独立的概念。
        除了大盘指数是默认载入，其他的必须显示载入。
    """
    

    def __init__(self, mongoDbEngine, gateway, info):
        self._mongoDbEngine = mongoDbEngine
        self._gateway = gateway
        self._info = info

        self._init()

    def _init(self):

        self._stockCodesTable = {}
        self._fundCodesTable = {} # 基金代码表需要用户显示载入，不像指数总是载入
        self._sectorCodesTable = {} # 板块代码表需要用户显示载入，不像指数总是载入

        # added at 2016.2.19 for tracking codes/names changes
        # only for updating CodeName table
        self.NewName_CodeNameDict = {}
        self.NewCode_CodeNameDict = {}
        self.Same_CodeNameDict = {}

    @property
    def shIndex(self):
        return DyStockCommon.shIndex

    @property
    def szIndex(self):
        return DyStockCommon.szIndex

    @property
    def cybIndex(self):
        return DyStockCommon.cybIndex

    @property
    def zxbIndex(self):
        return DyStockCommon.zxbIndex

    @property
    def etf50(self):
        return DyStockCommon.etf50

    @property
    def etf300(self):
        return DyStockCommon.etf300

    @property
    def etf500(self):
        return DyStockCommon.etf500

    @property
    def stockCodes(self):
        return self._stockCodesTable

    @property
    def stockIndexes(self):
        return DyStockCommon.indexes

    @property
    def stockFunds(self):
        return self._fundCodesTable

    @property
    def stockSectors(self):
        return self._sectorCodesTable

    @property
    def stockCodesFunds(self):
        return dict(self.stockCodes, **self.stockFunds)

    @property
    def stockAllCodesFunds(self):
        return dict(self.stockAllCodes, **self.stockFunds)

    @property
    def stockAllCodes(self):
        """
            个股和大盘指数，不含基金（ETF）
        """
        return dict(self.stockCodes, **DyStockCommon.indexes)

    @property
    def stockAllCodesFundsSectors(self):
        """
            大盘指数，个股，基金，板块指数
        """
        return dict(self.stockAllCodesFunds, **self.stockSectors)

    @property
    def stockIndexesSectors(self):
        return dict(self.stockSectors, **DyStockCommon.indexes)

    def getIndexStockCodes(self, index=None):
        if index is None:
            return self.stockCodes

        codes = {}
        for code, name in self._stockCodesTable.items():
            if index == self.getIndex(code):
                codes[code] = name

        return codes

    def _getCodeByName(self, name):
        for code, name_ in self.stockAllCodesFunds.items():
            if name_ == name:
                return code

        return None

    def getCode(self, name):
        try:
            int(name[0])

            if len(name) == 6:
                return name + '.SH' if name[0] in ['6', '5'] else name + '.SZ'
            else:
                return name.upper() # Dy format

        except Exception as ex:
            # chinese
            return self._getCodeByName(name)

        return None

    def getIndex(self, code):
        if code[-2:] == 'SH': return self.shIndex

        if code[:3] == '002': return self.zxbIndex
        if code[:3] == '300': return self.cybIndex
            
        if code[-2:] == 'SZ': return self.szIndex

        assert(0)
        return None

    def _setStockCodes(self, code, name):
        if code in self._stockCodesTable:
            if name == self._stockCodesTable[code]:
                self.Same_CodeNameDict[code] = name
            else:
                self.NewName_CodeNameDict[code] = self._stockCodesTable[code] + '->' + name
                self._stockCodesTable[code] = name
        else:
            self.NewCode_CodeNameDict[code] = name
            self._stockCodesTable[code] = name

    def _getAndSyncStockCodes(self):
        """ @return: {new code:name}, {code:old name->new name}, {exit code:name} """

        if len(self.Same_CodeNameDict) == len(self._stockCodesTable):
            return None, None, None

        if ( len(self.Same_CodeNameDict) + len(self.NewName_CodeNameDict) + len(self.NewCode_CodeNameDict) ) == len(self._stockCodesTable):
            return self.NewCode_CodeNameDict, self.NewName_CodeNameDict, None

        # 退市
        exit = {}
        for code in self._stockCodesTable:
            if code in self.Same_CodeNameDict: continue
            if code in self.NewName_CodeNameDict: continue
            if code in self.NewCode_CodeNameDict: continue

            exit[code] = self._stockCodesTable[code]

        assert(exit)

        # delete exit code from table
        for code in exit: del self._stockCodesTable[code]

        return self.NewCode_CodeNameDict, self.NewName_CodeNameDict, exit

    def _removeIndexes(self, codes):
        if codes:
            for index in self.stockIndexes:
                try:
                    codes.remove(index)
                except Exception as ex:
                    pass

    def _removeSectors(self, codes):
        if codes is None:
            self._sectorCodesTable = {}
        elif codes:
            for sector in DyStockCommon.sectors:
                try:
                    codes.remove(sector)

                    # user wants to load sector code, so add it
                    self._sectorCodesTable[sector] = DyStockCommon.sectors[sector]
                except Exception as ex:
                    pass

    def _removeFunds(self, codes):
        if codes is None:
            self._fundCodesTable = copy.copy(DyStockCommon.funds)
        elif codes:
            for fund in DyStockCommon.funds:
                try:
                    codes.remove(fund)

                    # user wants to load fund code, so add it
                    self._fundCodesTable[fund] = DyStockCommon.funds[fund]
                except Exception as ex:
                    pass

    def load(self, codes=None):
        """
            indexes are always loaded by default
            @codes: None, load all stock codes, including indexes, funds, excluding sectors
                    [], not load any code(including funds), but only indexes
                    [code], load specified [code] with indexes
        """
        self._info.print('开始载入股票代码表...')

        # 初始化
        self._init()

        # copy so that not changing original @codes
        # 不改变传入参数的内容
        codes = copy.copy(codes)

        # 大盘指数不需要载入
        self._removeIndexes(codes)

        # 板块代码不需要从数据库载入
        self._removeSectors(codes)

        # 基金不需要从数据库载入
        self._removeFunds(codes)

        data = self._mongoDbEngine.getStockCodes(codes)
        if data is None:
            self._info.print('股票代码表载入失败', DyLogData.error)
            return False

        for doc in data:
            self._stockCodesTable[doc['code']] = doc['name']

        self._info.print('股票代码表载入完成')
        return True

    def _update2Db(self, codes):

        # convert to MongoDB format
        codesForDb = [{'code':code, 'name':name} for code, name in codes.items()]

        # update into DB
        return self._mongoDbEngine.updateStockCodes(codesForDb)

    def _set(self, codes):
        """
            set codes gotten from Gateway to DB
        """
        # set into object variables
        for code, name in codes.items():
            self._setStockCodes(code, name)

        # get changes and sync
        newCode, newName, exit = self._getAndSyncStockCodes()

        if newCode or newName:
            newNameTemp = {code: name[name.rfind('->') + 2:] for code, name in newName.items()}

            if not self._update2Db(dict(newCode, **newNameTemp)):
                return False

        # print updated result
        self._print(newCode, newName, exit)

        return True

    def update(self):
        self._info.print('开始更新股票代码表...')

        # first, load from DB
        self.load()

        # always getting from Gateway
        codes = self._gateway.getStockCodes()
        if codes is None: return False

        # set codes gotten from Gateway to DB
        return self._set(codes)

    def _print(self, newCode, newName, exit):
        if not (newCode or newName or exit):
            self._info.print("股票相同")

        if newCode:
            info = newCode
            info = str(info).split(',')
            infLen = len(info) 
            if infLen > 5:
                info = ','.join(info[:5]) + ",...[total {0}]".format(infLen)
            else:
                info = ','.join(info)

            self._info.print("新加股票" + info)

        if newName:
            info = newName
            info = str(info).split(',')
            infLen = len(info) 
            if infLen > 5:
                info = ','.join(info[:5]) + ",...[total {0}]".format(infLen)
            else:
                info = ','.join(info)

            self._info.print("换名股票" + info)

        if exit:
            info = exit
            info = str(info).split(',')
            infLen = len(info) 
            if infLen > 5:
                info = ','.join(info[:5]) + ",...[total {0}]".format(infLen)
            else:
                info = ','.join(info)

            self._info.print("退市股票" + info)
