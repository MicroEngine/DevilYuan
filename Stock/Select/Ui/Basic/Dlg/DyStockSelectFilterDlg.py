from PyQt5.QtWidgets import QDialog, QGridLayout, QLabel, QTextEdit, QPushButton, QApplication, QCheckBox

from DyCommon.Ui.DyTableWidget import *


class DyStockSelectFilterDlg(QDialog):

    def __init__(self, data, colNames, parent=None):
        super().__init__(parent)

        self._data = data

        self._initUi(colNames)

    def _initUi(self, colNames):
        self.setWindowTitle('过滤')
 
        # 控件
        table = DyTableWidget(parant=None, readOnly=True, index=False, floatCut=True, autoScroll=False)
        table.setColNames(['列名', '表达式'])
        rows = [[name, 'x[{0}]'.format(i)] for i, name in enumerate(colNames)]
        table.fastAppendRows(rows)

        descriptionLabel = QLabel('过滤表达式(Python语法)')
        self._filterTextEdit = QTextEdit()
        self._newWindowCheckBox = QCheckBox('新窗口')
        self._newWindowCheckBox.setChecked(True)
        self._highlightCheckBox = QCheckBox('原窗口高亮')
        self._highlightCheckBox.setChecked(True)

        cancelPushButton = QPushButton('Cancel')
        okPushButton = QPushButton('OK')
        cancelPushButton.clicked.connect(self._cancel)
        okPushButton.clicked.connect(self._ok)

        # 布局
        grid = QGridLayout()
        grid.setSpacing(10)
 
        grid.addWidget(table, 0, 0, 22, 1)
        grid.addWidget(self._newWindowCheckBox, 0, 1)
        grid.addWidget(self._highlightCheckBox, 0, 2)

        grid.addWidget(descriptionLabel, 1, 1)

        grid.addWidget(self._filterTextEdit, 2, 1, 20, 20)
 
        grid.addWidget(okPushButton, 0, 21)
        grid.addWidget(cancelPushButton, 1, 21)
 
 
        self.setLayout(grid)
        self.resize(QApplication.desktop().size().width()//2, QApplication.desktop().size().height()//4*3)

    def _ok(self):
        filter = self._filterTextEdit.toPlainText().replace('\n', ' ')

        self._data['filter'] = filter
        self._data['newWindow'] = self._newWindowCheckBox.isChecked()
        self._data['highlight'] = self._highlightCheckBox.isChecked()

        self.accept()

    def _cancel(self):
        self.reject()
