from PyQt5.QtWidgets import QDialog, QGridLayout, QLabel, QTextEdit, QPushButton, QApplication, QCheckBox

from DyCommon.Ui.DyTableWidget import *


class DyStockTableColumnOperateDlg(QDialog):
    """
        列运算对话框
    """

    def __init__(self, data, colNames, parent=None):
        super().__init__(parent)

        self._data = data

        self._initUi(colNames)

    def _initUi(self, colNames):
        self.setWindowTitle('列运算')
 
        # 控件
        table = DyTableWidget(parent=None, readOnly=True, index=False, floatCut=True, autoScroll=False)
        table.setColNames(['列名', '表达式'])
        rows = [[name, 'x[{0}]'.format(i)] for i, name in enumerate(colNames)]
        table.fastAppendRows(rows)

        descriptionLabel = QLabel('列运算表达式(Pandas语法)')
        self._expressionTextEdit = QTextEdit()

        cancelPushButton = QPushButton('Cancel')
        okPushButton = QPushButton('OK')
        cancelPushButton.clicked.connect(self._cancel)
        okPushButton.clicked.connect(self._ok)

        # 布局
        grid = QGridLayout()
        grid.setSpacing(10)
 
        grid.addWidget(table, 0, 0, 22, 1)

        grid.addWidget(descriptionLabel, 0, 1)

        grid.addWidget(self._expressionTextEdit, 1, 1, 20, 20)
 
        grid.addWidget(okPushButton, 0, 21)
        grid.addWidget(cancelPushButton, 1, 21)
 
 
        self.setLayout(grid)
        self.resize(QApplication.desktop().size().width()//2, QApplication.desktop().size().height()//4*3)

    def _ok(self):
        expression = self._expressionTextEdit.toPlainText().replace('\n', ' ')

        self._data['exp'] = expression

        self.accept()

    def _cancel(self):
        self.reject()
