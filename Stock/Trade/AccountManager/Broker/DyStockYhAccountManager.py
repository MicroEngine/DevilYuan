from ..DyStockAccountManager import *
from ....Common.DyStockCommon import *


class DyStockYhAccountManager(DyStockAccountManager):
    """
        银河证券UI管理类
        由于UI接口不同数据之间的异步性，推送券商原始数据时，一定要保证顺序。
            委托->成交->资金->持仓
    """
    broker = 'yh'
    brokerName = '银河证券'

    headerNameMap = {'capital': {'availCash': '可用金额'},
                     'position': {'code': '证券代码',
                                  'name': '证券名称',
                                  'totalVolume': '当前持仓',
                                  'availVolume': '可用余额',
                                  'price': '参考市价',
                                  'cost': '参考成本价'
                                  },
                     'curEntrust': {'code': '证券代码',
                                    'price': '委托价格',
                                    'totalVolume': '委托数量',
                                    'dealedVolume': '成交数量',
                                    'type': '操作',
                                    'status': '备注',
                                    'entrustId': '合同编号'
                                    },
                     'curDeal': {'code': '证券代码',
                                 'price': '成交均价',
                                 'datetime': '成交时间',
                                 'dealedVolume': '成交数量',
                                 'type': '操作',
                                 'dealId': '成交编号',
                                 'entrustId': '合同编号',
                                 }
                     }


    def __init__(self, eventEngine, info):
        super().__init__(eventEngine, info)

