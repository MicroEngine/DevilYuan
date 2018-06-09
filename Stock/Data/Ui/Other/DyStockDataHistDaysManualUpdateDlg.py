from datetime import *

from PyQt5.QtWidgets import QDialog, QGridLayout, QLabel, QLineEdit, QPushButton, QCheckBox, QGroupBox

from ...DyStockDataCommon import * 


class DyStockDataHistDaysManualUpdateDlg(QDialog):

    def __init__(self, data, parent=None):
        super().__init__(parent)

        self._data = data

        self._initUi()

    def _createIndicatorGroupBox(self):
        indicatorGroupBox = QGroupBox('指标')

        grid = QGridLayout()
        grid.setSpacing(10)

        rowNbr = 4
        self._indicatorCheckBoxList = []
        for i, indicator in enumerate(DyStockDataCommon.dayIndicators):
            checkBox = QCheckBox(indicator)
            checkBox.setChecked(True)

            grid.addWidget(checkBox, i//rowNbr, i%rowNbr)

            self._indicatorCheckBoxList.append(checkBox)

        indicatorGroupBox.setLayout(grid)

        return indicatorGroupBox

    def _initUi(self):
        self.setWindowTitle('股票历史日线手动更新')
 
        # 控件
        codeLable = QLabel("股票代码(如果'指数'没有勾上，空代表所有代码), e.g. 600016,510300,002213,...")
        self._codeLineEdit = QLineEdit()
        codes = self._data.get('codes')
        if codes:
            self._codeLineEdit.setText(','.join(codes))

        startDateLable = QLabel('开始日期')
        self._startDateLineEdit = QLineEdit(datetime.now().strftime("%Y-%m-%d"))

        endDateLable = QLabel('结束日期')
        self._endDateLineEdit = QLineEdit(datetime.now().strftime("%Y-%m-%d"))

        self._forcedCheckBox = QCheckBox('强制')
        self._indexCheckBox = QCheckBox('指数') # 更新指数的日线数据

        self._indicatorGroupBox = self._createIndicatorGroupBox()

        cancelPushButton = QPushButton('Cancel')
        okPushButton = QPushButton('OK')
        cancelPushButton.clicked.connect(self._cancel)
        okPushButton.clicked.connect(self._ok)

        # 布局
        grid = QGridLayout()
        grid.setSpacing(10)
 
        grid.addWidget(startDateLable, 0, 0)
        grid.addWidget(self._startDateLineEdit, 1, 0)

        grid.addWidget(endDateLable, 0, 1)
        grid.addWidget(self._endDateLineEdit, 1, 1)
 
        grid.addWidget(codeLable, 2, 0, 1, 2)
        grid.addWidget(self._codeLineEdit, 3, 0, 1, 2)

        grid.addWidget(self._forcedCheckBox, 4, 0)
        grid.addWidget(self._indexCheckBox, 4, 1)
        
        grid.addWidget(self._indicatorGroupBox, 5, 0, 1, 2)

        grid.addWidget(okPushButton, 6, 1)
        grid.addWidget(cancelPushButton, 6, 0)
 
        self.setLayout(grid)

    def _ok(self):
        self._data['startDate'] = self._startDateLineEdit.text()
        self._data['endDate'] = self._endDateLineEdit.text()

        codes = self._codeLineEdit.text()
        self._data['codes'] = codes.split(',') if codes else None

        self._data['forced'] = self._forcedCheckBox.isChecked()
        self._data['index'] = self._indexCheckBox.isChecked()

        indicators = []
        for checkBox in self._indicatorCheckBoxList:
            if checkBox.isChecked():
                indicators.append(checkBox.text())

        self._data['indicators'] = indicators

        self.accept()

    def _cancel(self):
        self.reject()
