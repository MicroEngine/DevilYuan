from ..DyStockAccountManager import *
from ....Common.DyStockCommon import *


class DyStockGtjaAccountManager(DyStockAccountManager):
    """
        国泰君安Web管理类
        由于Web接口不同数据之间的异步性，推送券商原始数据时，一定要保证顺序。
            委托->成交->资金->持仓
    """
    broker = 'gtja'
    brokerName = '国泰君安'

    headerNameMap = {'capital': {'availCash': '可用余额'},
                     'position': {'code': '证券代码',
                                  'name': '证券名称',
                                  'totalVolume': '实际数量',
                                  'availVolume': '可用数量',
                                  'price': '最新价格',
                                  'cost': '成本价(元)'
                                  },
                     'curEntrust': {'code': '证券代码',
                                    'price': '委托价格',
                                    'totalVolume': '委托数量',
                                    'dealedVolume': '成交数量',
                                    'type': '类型',
                                    'status': '委托状态',
                                    'entrustId': '委托序号'
                                    },
                     'curDeal': {'code': '证券代码',
                                 'price': '成交价',
                                 'datetime': '成交时间',
                                 'dealedVolume': '成交数',
                                 'type': '交易类型',
                                 'dealId': '合同号'
                                 }
                     }


    def __init__(self, eventEngine, info):
        super().__init__(eventEngine, info)

    def _matchDyEntrustByBrokerDeal(self, dyEntrust, dealType, dealedVolume, brokerEntrustId=None):
        """
            根据券商的成交单匹配DevilYuan系统的委托单
            子类可以重载此函数
        """
        # 由于券商的当日委托推送和当日成交推送是异步的，所以要考虑这之间可能有新的委托
        # 这里不考虑废单撤单状态，整个时序保证了不可能
        # !!!如果有跟策略股票和类型相同的手工委托单（通过其他系统的委托），则可能出现会错误地认为是由策略发出的。
        if dyEntrust.status != DyStockEntrust.Status.allDealed and dyEntrust.status != DyStockEntrust.Status.partDealed:
            return False

        #!!! 国泰君安的当日成交单的'交易类型'是'普通成交'和'撤单成交'
        # 所以这里就没法匹配type
        if dealType != '普通成交':
            return False

        # 在获取当日成交的时候，同一个委托又有了新的成交。
        # 由于推送的委托是上一次的，并且是贪婪式匹配，如果同一时刻两个策略发出相同的委托，则可能匹配错。
        # 但由于策略生成新委托时，若同一类型的委托还没有完成，账户管理类则拒绝策略的新委托。
        # 这个保证了匹配错误不会发生。
        if dyEntrust.matchedDealedVolume + dealedVolume > dyEntrust.dealedVolume:
            return False

        return True