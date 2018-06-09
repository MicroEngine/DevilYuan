import os
import json

from DyCommon.DyCommon import DyCommon
from Stock.Common.DyStockCommon import DyStockCommon
from ..Data.Engine.DyStockMongoDbEngine import DyStockMongoDbEngine
from ..Trade.WeChat.DyStockTradeWxEngine import DyStockTradeWxEngine
from ..Trade.Broker.YhNew.YhTrader import YhTrader


class DyStockConfig(object):
    """
        Read configs from files and then set to corresponding variables
    """

    defaultMongoDb = {"Connection": {"Host": "localhost", "Port": 27017},
                      "CommonDays": {
                          "Wind": {
                              "stockCommonDb": 'stockCommonDb',
                              'tradeDayTableName': "tradeDayTable",
                              'codeTableName': "codeTable",
                              'stockDaysDb': 'stockDaysDb'
                              },
                          "TuShare": {
                              "stockCommonDb": 'stockCommonDbTuShare',
                              'tradeDayTableName': "tradeDayTableTuShare",
                              'codeTableName': "codeTableTuShare",
                              'stockDaysDb': 'stockDaysDbTuShare'
                              }
                          },
                      "Ticks": {"db": 'stockTicksDb'}
                      }

    defaultWxScKey = {"WxScKey": ""}

    defaultAccount = {"Ths": {"Account": "", "Password": "", "Exe": r"C:\Program Files\同花顺\xiadan.exe"},
                      "Yh": {"Account": "", "Password": "", "Exe": r"C:\Program Files\中国银河证券双子星3.2\Binarystar.exe"},
                      }


    def getDefaultHistDaysDataSource():
        if DyStockCommon.WindPyInstalled:
            return {"Wind": True, "TuShare": False}

        return {"Wind": False, "TuShare": True}

    def _configStockHistDaysDataSource():
        path = DyCommon.createPath('Stock/User/Config/Common')
        file = os.path.join(path, 'DyStockHistDaysDataSource.json')

        # open
        try:
            with open(file) as f:
                data = json.load(f)
        except:
            data = DyStockConfig.getDefaultHistDaysDataSource()

        DyStockConfig.configStockHistDaysDataSource(data)

    def configStockHistDaysDataSource(data):
        DyStockCommon.defaultHistDaysDataSource = []
        if data.get('Wind'):
            DyStockCommon.defaultHistDaysDataSource.append('Wind')

        if data.get('TuShare'):
            DyStockCommon.defaultHistDaysDataSource.append('TuShare')

    def getStockHistDaysDataSourceFileName():
        path = DyCommon.createPath('Stock/User/Config/Common')
        file = os.path.join(path, 'DyStockHistDaysDataSource.json')

        return file

    def _configStockMongoDb():
        path = DyCommon.createPath('Stock/User/Config/Common')
        file = os.path.join(path, 'DyStockMongoDb.json')

        # open
        try:
            with open(file) as f:
                data = json.load(f)
        except:
            data = DyStockConfig.defaultMongoDb

        DyStockConfig.configStockMongoDb(data)

    def configStockMongoDb(data):
        DyStockMongoDbEngine.host = data['Connection']['Host']
        DyStockMongoDbEngine.port = data['Connection']['Port']

        # Wind
        DyStockMongoDbEngine.stockCommonDb = data["CommonDays"]["Wind"]['stockCommonDb']
        DyStockMongoDbEngine.tradeDayTableName = data["CommonDays"]["Wind"]['tradeDayTableName']
        DyStockMongoDbEngine.codeTableName = data["CommonDays"]["Wind"]['codeTableName']

        DyStockMongoDbEngine.stockDaysDb = data["CommonDays"]["Wind"]['stockDaysDb']

        # TuShare
        DyStockMongoDbEngine.stockCommonDbTuShare = data["CommonDays"]["TuShare"]['stockCommonDb']
        DyStockMongoDbEngine.tradeDayTableNameTuShare = data["CommonDays"]["TuShare"]['tradeDayTableName']
        DyStockMongoDbEngine.codeTableNameTuShare = data["CommonDays"]["TuShare"]['codeTableName']

        DyStockMongoDbEngine.stockDaysDbTuShare = data["CommonDays"]["TuShare"]['stockDaysDb']

        # ticks
        DyStockMongoDbEngine.stockTicksDb = data["Ticks"]["db"]

    def getStockMongoDbFileName():
        path = DyCommon.createPath('Stock/User/Config/Common')
        file = os.path.join(path, 'DyStockMongoDb.json')

        return file

    def _configStockWxScKey():
        file = DyStockConfig.getStockWxScKeyFileName()

        # open
        try:
            with open(file) as f:
                data = json.load(f)
        except:
            data = DyStockConfig.defaultWxScKey

        DyStockConfig.configStockWxScKey(data)

    def configStockWxScKey(data):
        DyStockTradeWxEngine.scKey = data["WxScKey"]

    def getStockWxScKeyFileName():
        path = DyCommon.createPath('Stock/User/Config/Trade')
        file = os.path.join(path, 'DyStockWxScKey.json')

        return file

    def _configStockAccount():
        file = DyStockConfig.getStockAccountFileName()

        # open
        try:
            with open(file) as f:
                data = json.load(f)
        except:
            data = DyStockConfig.defaultAccount

        DyStockConfig.configStockAccount(data)

    def configStockAccount(data):
        YhTrader.account = data["Yh"]["Account"]
        YhTrader.password = data["Yh"]["Password"]
        YhTrader.exePath = data["Yh"]["Exe"]

    def getStockAccountFileName():
        path = DyCommon.createPath('Stock/User/Config/Trade')
        file = os.path.join(path, 'DyStockAccount.json')

        return file

    def config():
        DyStockConfig._configStockHistDaysDataSource()
        DyStockConfig._configStockMongoDb()
        DyStockConfig._configStockWxScKey()
        DyStockConfig._configStockAccount()