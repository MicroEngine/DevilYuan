from datetime import *

from PyQt5.QtWidgets import QDialog, QGridLayout, QLabel, QLineEdit, QPushButton, QApplication, QMessageBox

from DyCommon.Ui.DyTreeWidget import *
from ....Trade.Ui.Basic.DyStockTradeStrategyWidget import * 


class DyStockDataStrategyDataPrepareDlg(QDialog):
    """ 为交易策略提供准备数据, 所以策略配置也是从交易策略窗口读取
    """

    def __init__(self, data, parent=None):
        super().__init__(parent)

        self._data = data

        self._initUi()

    def _parseFields(self, fields):
        if isinstance(fields, list):
            newFields = []

            for field in fields:
                ret = self._parseFields(field)

                if not ((not ret) or ret == '运行' or ret == '监控'): # filter
                    newFields.append(ret)

            return newFields
        else:
            return fields

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

    def _getFields(self):
        fields = self._parseFields(DyStockTradeStrategyWidget.strategyFields)

        return self._transform(fields)

    def _initUi(self):
        self.setWindowTitle('生成策略准备数据')
 
        # 控件
        dateLable = QLabel('日期')
        self._dateLineEdit = QLineEdit(datetime.now().strftime("%Y-%m-%d"))

        cancelPushButton = QPushButton('Cancel')
        okPushButton = QPushButton('OK')
        cancelPushButton.clicked.connect(self._cancel)
        okPushButton.clicked.connect(self._ok)

        self._strategies = {}
        self._strategyWidget = DyTreeWidget(self._getFields())

        # 布局
        grid = QGridLayout()
        grid.setSpacing(10)
 
        grid.addWidget(self._strategyWidget, 0, 0, 20, 10)
 
        grid.addWidget(dateLable, 0, 10, 1, 2)
        grid.addWidget(self._dateLineEdit, 1, 10, 1, 2)

        grid.addWidget(okPushButton, 2, 11)
        grid.addWidget(cancelPushButton, 2, 10)
 
        self.setLayout(grid)
        self.resize(QApplication.desktop().size().width()//3, QApplication.desktop().size().height()//2)

    def _ok(self):
        # get selected strategy classes
        clsNames = self._strategyWidget.getCheckedTexts()

        if not clsNames:
           QMessageBox.warning(self, '错误', '没有选择策略!')
           return

        self._data['classes'] = [self._strategies[cls] for cls in clsNames]
        self._data['date'] = self._dateLineEdit.text()

        self.accept()

    def _cancel(self):
        self.reject()
