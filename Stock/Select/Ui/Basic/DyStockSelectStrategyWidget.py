from PyQt5.QtWidgets import QAbstractItemView

from DyCommon.Ui.DyTreeWidget import *
from EventEngine.DyEvent import *

# CTA
from ...Strategy.Cta.DySS_BBands import *
from ...Strategy.Cta.DySS_MacdBottomDeviation import *
from ...Strategy.Cta.DySS_RisingEve import *
from ...Strategy.Cta.DySS_PlatformUpBreakThrough import *
from ...Strategy.Cta.DySS_Stagflation import *
from ...Strategy.Cta.DySS_StrongBack import *
from ...Strategy.Cta.DySS_OverSold import *
from ...Strategy.Cta.DySS_LimitUpRise import *
from ...Strategy.Cta.DySS_NeedleBottom import *
from ...Strategy.Cta.DySS_MasLong import *
from ...Strategy.Cta.DySS_MasAttack import *
from ...Strategy.Cta.DySS_Rebound import *
from ...Strategy.Cta.DySS_MaWalk import *
from ...Strategy.Cta.DySS_HighTurn import *
from ...Strategy.Cta.DySS_InsideRedLine import *
from ...Strategy.Cta.DySS_SwingTrough import DySS_SwingTrough

# Stats
from ...Strategy.Stats.DySS_Correlation import *
from ...Strategy.Stats.DySS_LimitUp import *
from ...Strategy.Stats.DySS_UpDownList import *
from ...Strategy.Stats.DySS_AbnormalVolatility import *
from ...Strategy.Stats.DySS_LimitUpAnalysis import *
from ...Strategy.Stats.DySS_LimitUpPredict import *
from ...Strategy.Stats.DySS_Pairs import *
from ...Strategy.Stats.DySS_ChipDist import DySS_ChipDist

# Fundamental
from ...Strategy.Fundamental.DySS_High2SendStocks import *
from ...Strategy.Fundamental.DySS_GrowingStocks import *

# Other
from ...Strategy.Other.DySS_ETF import *


class DyStockSelectStrategyWidget(DyTreeWidget):

    strategyFields = \
        [
            ['CTA',
                [DySS_MacdBottomDeviation],
                [DySS_NeedleBottom],
                [DySS_BBands],
                [DySS_RisingEve],
                [DySS_PlatformUpBreakThrough],
                [DySS_Stagflation],
                [DySS_StrongBack],
                [DySS_OverSold],
                [DySS_LimitUpRise],
                [DySS_MasLong],
                [DySS_MasAttack],
                [DySS_Rebound],
                [DySS_MaWalk],
                [DySS_HighTurn],
                [DySS_InsideRedLine],
                [DySS_SwingTrough],
            ],
            ['统计分析',
                [DySS_Correlation],
                [DySS_LimitUp],
                [DySS_UpDownList],
                [DySS_AbnormalVolatility],
                [DySS_LimitUpAnalysis],
                [DySS_LimitUpPredict],
                [DySS_Pairs],
                [DySS_ChipDist],
            ],
            ['基本面',
                [DySS_High2SendStocks],
                [DySS_GrowingStocks],
            ],
            ['其他',
                [DySS_ETF],
            ]
        ]

    def __init__(self, paramWidget=None):
        self._strategies = {} # {strategy chName: strategy class}
        newFields = self._transform(self.__class__.strategyFields)
        super().__init__(newFields)

        # 设置相互引用
        self._paramWidget = paramWidget
        if paramWidget is not None:
            self._paramWidget.setStrategyWidget(self)

        self._relatedActions = None

        self._curStrategyCls = None
        self._curLeafItem = None

    def _setParamWidget(self, text):
        if self._paramWidget is None: return

        if text in self._strategies:
            strategyName = text
            parameters = self._strategies[strategyName].param
            toolTips = self._strategies[strategyName].paramToolTip if hasattr(self._strategies[strategyName], 'paramToolTip') else None

            self._paramWidget.set(strategyName, parameters, toolTips)

    def on_currentItemChanged(self, current, previous):
        self._setParamWidget(current.text(0))

    def on_itemClicked(self, item, column):
        self._setParamWidget(item.text(0))

    def on_itemChanged(self, item, column):

        # 选中新的策略
        if item.checkState(0) == Qt.Checked and item.text(0) in self._strategies:
            
            # 先清除当前已经选择的策略item的界面显示
            if self._curLeafItem:

                self.blockSignals(True)
                self._curLeafItem.setCheckState(0, Qt.Unchecked)
                self.blockSignals(False)

                super().on_itemChanged(self._curLeafItem, column)

            # 设置新的策略
            self._curLeafItem = item
            self._curStrategyCls = self._strategies[item.text(0)]

            self._setRelatedActionsEnabled(True)

        else:
            self.blockSignals(True)
            item.setCheckState(0, Qt.Unchecked)
            self.blockSignals(False)

            if item.text(0) in self._strategies:
                self._curLeafItem = None
                self._curStrategyCls = None

                self._setRelatedActionsEnabled(False)
                
        super().on_itemChanged(item, column)

    @property
    def curStrategyCls(self):
        return self._curStrategyCls

    def getStrategy(self):
        if self._paramWidget is None: return self._curStrategyCls, {}

        if self._curStrategyCls is None:
            return None, None

        return self._curStrategyCls, self._paramWidget.get(self._curLeafItem.text(0))

    def _saveParam(self, strategyChName, param):
        orderedParam = self._strategies[strategyChName].param

        for key, value in param.items():
            orderedParam[key] = value

    def uncheckStrategy(self, strategyChName, param):
        # save parameters
        self._saveParam(strategyChName, param)

        # uncheck if it is checked
        strategyCls = self._strategies[strategyChName]
        if strategyCls == self._curStrategyCls:
            self.blockSignals(True)
            self._curLeafItem.setCheckState(0, Qt.Unchecked)
            self.blockSignals(False)

            self.on_itemChanged(self._curLeafItem, 0)

    def setRelatedActions(self, actions):
        self._relatedActions = actions

    def _setRelatedActionsEnabled(self, enabled=True):
        if self._relatedActions is None: return

        for action in self._relatedActions:
            action.setEnabled(enabled)

    def _transform(self, fields):
        newFields = []
        for field in fields:
            if isinstance(field, list):
                newFields.append(self._transform(field))
            else:
                if hasattr(field,  'chName'):
                    newFields.append(field.chName)
                    self._strategies[field.chName] = field
                else:
                    newFields.append(field)

        return newFields
