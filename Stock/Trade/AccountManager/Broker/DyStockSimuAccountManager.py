from .DyStockGtjaAccountManager import *


class DyStockSimuAccountManager(DyStockGtjaAccountManager):
    """
        模拟券商账户管理，参照的是国泰君安
    """
    broker = 'simu'
    brokerName = '模拟'


    def __init__(self, eventEngine, info):
        super().__init__(eventEngine, info)

    def _matchDyEntrustByBrokerDeal(self, dyEntrust, dealType, dealedVolume, brokerEntrustId=None):
        """
            根据券商的成交单匹配DevilYuan系统的委托单
            子类可以重载此函数
        """
        return DyStockAccountManager._matchDyEntrustByBrokerDeal(self, dyEntrust, dealType, dealedVolume, brokerEntrustId)


class DyStockSimuAccountManager1(DyStockSimuAccountManager):
    """
        模拟券商账户管理，参照的是国泰君安
    """
    broker = 'simu1'
    brokerName = '模拟1'


    def __init__(self, eventEngine, info):
        super().__init__(eventEngine, info)


class DyStockSimuAccountManager2(DyStockSimuAccountManager):
    """
        模拟券商账户管理，参照的是国泰君安
    """
    broker = 'simu2'
    brokerName = '模拟2'


    def __init__(self, eventEngine, info):
        super().__init__(eventEngine, info)


class DyStockSimuAccountManager3(DyStockSimuAccountManager):
    """
        模拟券商账户管理，参照的是国泰君安
    """
    broker = 'simu3'
    brokerName = '模拟3'


    def __init__(self, eventEngine, info):
        super().__init__(eventEngine, info)


class DyStockSimuAccountManager4(DyStockSimuAccountManager):
    """
        模拟券商账户管理，参照的是国泰君安
    """
    broker = 'simu4'
    brokerName = '模拟4'


    def __init__(self, eventEngine, info):
        super().__init__(eventEngine, info)


class DyStockSimuAccountManager5(DyStockSimuAccountManager):
    """
        模拟券商账户管理，参照的是国泰君安
    """
    broker = 'simu5'
    brokerName = '模拟5'


    def __init__(self, eventEngine, info):
        super().__init__(eventEngine, info)


class DyStockSimuAccountManager6(DyStockSimuAccountManager):
    """
        模拟券商账户管理，参照的是国泰君安
    """
    broker = 'simu6'
    brokerName = '模拟6'


    def __init__(self, eventEngine, info):
        super().__init__(eventEngine, info)

class DyStockSimuAccountManager7(DyStockSimuAccountManager):
    """
        模拟券商账户管理，参照的是国泰君安
    """
    broker = 'simu7'
    brokerName = '模拟7'


    def __init__(self, eventEngine, info):
        super().__init__(eventEngine, info)

class DyStockSimuAccountManager8(DyStockSimuAccountManager):
    """
        模拟券商账户管理，参照的是国泰君安
    """
    broker = 'simu8'
    brokerName = '模拟8'


    def __init__(self, eventEngine, info):
        super().__init__(eventEngine, info)

class DyStockSimuAccountManager9(DyStockSimuAccountManager):
    """
        模拟券商账户管理，参照的是国泰君安
    """
    broker = 'simu9'
    brokerName = '模拟9'


    def __init__(self, eventEngine, info):
        super().__init__(eventEngine, info)

