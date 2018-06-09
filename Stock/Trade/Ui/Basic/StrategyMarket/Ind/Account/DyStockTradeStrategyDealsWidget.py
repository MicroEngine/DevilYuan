from DyCommon.Ui.DyTableWidget import *


class DyStockTradeStrategyDealsWidget(DyTableWidget):
    """ 策略成交窗口，不是当日成交是策略启动后的成交 """

    header = ['DY成交号', '券商成交号', '成交时间', '代码', '名称', '类型', '成交价(元)', '成交数量(股)', '成交额(元)']

    def __init__(self):
        super().__init__(readOnly=True, index=True, floatRound=3)

        self.setColNames(self.header)

    def update(self, deals):
        """
            @deals: [DyStockDeal]
        """
        rowKeys = []
        for deal in deals:
            rowNbr = self.appendRow([deal.dyDealId, deal.brokerDealId,
                                  deal.datetime, # 成交时间，来自券商的格式，这边不做处理
                                  deal.code, deal.name,
                                  deal.type,
                                  deal.price, deal.volume,
                                  deal.price*deal.volume
                                  ])

            rowKeys.append(rowNbr)

        self.setItemsForeground(rowKeys, (('买入', Qt.red), ('卖出', Qt.darkGreen)))