from DyCommon.Ui.DyTreeWidget import *
from EventEngine.DyEvent import *
from ...DyStockStrategyBase import *

# CTA
from ...Strategy.Cta.DyST_AbnormalVolatility import DyST_AbnormalVolatility
from ...Strategy.Cta.DyST_IntraDayT import DyST_IntraDayT
from ...Strategy.Cta.DyST_MaWalk import DyST_MaWalk
from ...Strategy.Cta.DyST_BankIntraDaySpread import DyST_BankIntraDaySpread


class DyStockTradeStrategyWidget(DyTreeWidget):

    strategyFields = \
        [
            ['CTA',
                [DyST_AbnormalVolatility],
                [DyST_IntraDayT],
                [DyST_MaWalk],
                [DyST_BankIntraDaySpread],
            ],
        ]


    def __init__(self, eventEngine):
        self._strategies = {} # {strategy chName: strategy class}
        newFields = self._transform(self.__class__.strategyFields)
        
        super().__init__(newFields)
        self.collapse('废弃')

        self._eventEngine = eventEngine

    def on_itemClicked(self, item, column):
        super(DyStockTradeStrategyWidget, self).on_itemClicked(item, column)

        if item.checkState(0) == Qt.Checked:
            pass

    def on_itemChanged(self, item, column):

        text = item.text(0)

        if item.checkState(0) == Qt.Checked:

            if text in self._strategies:
                strategyState, strategyCls = self._strategies[text]
                strategyState.checkAll(strategyCls, self._eventEngine)

            elif text == '运行' or text == '监控':
                strategyState, strategyCls = self._strategies[item.parent().text(0)]

                state = self._getStateByText(text)
                strategyState.checkState(state, strategyCls, self._eventEngine)
        else:

            if text in self._strategies:
                strategyState, strategyCls = self._strategies[text]
                strategyState.uncheckAll(strategyCls, self._eventEngine)

            elif text == '运行' or text == '监控':
                strategyState, strategyCls = self._strategies[item.parent().text(0)]

                state = self._getStateByText(text)
                strategyState.uncheckState(state, strategyCls, self._eventEngine)

        super().on_itemChanged(item, column)

    def _getStateByText(self, text):
        if text == '运行':
            return DyStockStrategyState.running

        return DyStockStrategyState.monitoring

    def _transform(self, fields):
        newFields = []
        for field in fields:
            if isinstance(field, list):
                newFields.append(self._transform(field))
            else:
                if hasattr(field,  'chName'):
                    newFields.append(field.chName)
                    newFields.append(['运行'])
                    newFields.append(['监控'])

                    self._strategies[field.chName] = [DyStockStrategyState(), field]
                else:
                    newFields.append(field)

        return newFields
