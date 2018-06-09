import json

from PyQt5.QtWidgets import QDialog, QLabel, QCheckBox, QTextEdit, QPushButton, QGridLayout

from DyCommon.DyCommon import DyCommon
from Stock.Common.DyStockCommon import DyStockCommon
from .DyStockConfig import DyStockConfig


class DyStockHistDaysDataSourceConfigDlg(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self._read()
        self._initUi()
        
    def _initUi(self):
        self.setWindowTitle('配置-股票历史日线数据源')
 
        # 控件
        label = QLabel('请选择股票历史日线数据源')

        self._windCheckBox = QCheckBox('Wind')
        self._tuShareCheckBox = QCheckBox('TuShare')

        description = """只选一个：更新交易日数据，股票代码表和股票历史日线数据到对应的数据库

选两个：更新交易日数据，股票代码表和股票历史日线数据到默认的数据库，即Wind对应的数据库，并同时做两个源的数据验证

若不选择：默认是Wind
        """
        textEdit = QTextEdit()
        textEdit.setPlainText(description)
        textEdit.setReadOnly(True)

        cancelPushButton = QPushButton('Cancel')
        okPushButton = QPushButton('OK')
        cancelPushButton.clicked.connect(self._cancel)
        okPushButton.clicked.connect(self._ok)

        # 布局
        grid = QGridLayout()
        grid.setSpacing(10)
 
        grid.addWidget(label, 0, 0)
        grid.addWidget(self._windCheckBox, 1, 0)
        grid.addWidget(self._tuShareCheckBox, 2, 0)
        grid.addWidget(textEdit, 3, 0)

        grid.addWidget(okPushButton, 0, 1)
        grid.addWidget(cancelPushButton, 1, 1)
 
        self.setLayout(grid)

        # set data to UI
        if self._data.get('Wind'):
            self._windCheckBox.setChecked(True)

        if self._data.get('TuShare'):
            self._tuShareCheckBox.setChecked(True)

    def _read(self):
        file = DyStockConfig.getStockHistDaysDataSourceFileName()

        # open
        try:
            with open(file) as f:
                self._data = json.load(f)
        except:
            self._data = DyStockConfig.getDefaultHistDaysDataSource()

    def _ok(self):
        # get data from UI
        data = {'Wind': False, 'TuShare': False}
        if self._windCheckBox.isChecked():
            data['Wind'] = True

        if self._tuShareCheckBox.isChecked():
            data['TuShare'] = True

        # set default data source
        if not DyStockCommon.defaultHistDaysDataSource:
            data['Wind'] = True

        # config to variables
        DyStockConfig.configStockHistDaysDataSource(data)

        # save config
        file = DyStockConfig.getStockHistDaysDataSourceFileName()
        with open(file, 'w') as f:
            f.write(json.dumps(data, indent=4))

        self.accept()

    def _cancel(self):
        self.reject()