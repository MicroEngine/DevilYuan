from DyCommon.Ui.DyTableWidget import *

from EventEngine.DyEvent import *


class DyStockBackTestingStrategyResultPositionWidget(DyTableWidget):

    header = ['代码','名称','可用数量/总数量','成本价/现价','盈亏(%)','最大盈/亏(%)','持有期','除权除息']

    def __init__(self, dataViewer):
        super().__init__(None, True, False)

        self._dataViewer = dataViewer
        
        self.setColNames(self.header)
        self.setAutoForegroundCol('盈亏(%)')

    def update(self, pos):
        # remove non-existing codes
        rows = self.getAll()

        for row in rows:
            if row[0] not in pos:
                self.removeRow(row[0])

        # update new positions
        for code, pos_ in pos.items():
            self[code] = [pos_.code, pos_.name,
                          '%.2f/%.2f'%(pos_.availVolume, pos_.totalVolume),
                          '%.3f/%.3f'%(pos_.cost, pos_.price),
                          pos_.pnlRatio,
                          '%.2f/%.2f'%(pos_.maxPnlRatio, pos_.minPnlRatio),
                          pos_.holdingPeriod,
                          '是' if pos_.xrd else '否'
                          ]
