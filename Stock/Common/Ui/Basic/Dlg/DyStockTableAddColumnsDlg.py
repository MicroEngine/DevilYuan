from PyQt5.QtWidgets import QDialog, QGridLayout, QLabel, QLineEdit, QPushButton, QApplication, QRadioButton, QButtonGroup


class DyStockTableAddColumnsDlg(QDialog):

    def __init__(self, data, title, parent=None, backward=True):
        super().__init__(parent)

        self._data = data

        self._initUi(title, backward)

    def _initUi(self, title, backward):
        self.setWindowTitle('添加{0}列'.format(title))
 
        # 控件
        increaseColumnsLable = QLabel('基准日期几日{0}'.format(title))
        self._increaseColumnsLineEdit = QLineEdit(','.join([str(x) for x in self._data['days']]) if self._data else '2,3,4,5,10' )

        # 前 & 后
        forwardRadioButton = QRadioButton('向前')
        backwardRadioButton = QRadioButton('向后');
        if backward:
            backwardRadioButton.setChecked(True)
        else:
            forwardRadioButton.setChecked(True)

        # 添加到QButtonGroup
        self._wardButtonGroup = QButtonGroup()
        self._wardButtonGroup.addButton(forwardRadioButton, 1); 
        self._wardButtonGroup.addButton(backwardRadioButton, 2)

        cancelPushButton = QPushButton('Cancel')
        okPushButton = QPushButton('OK')
        cancelPushButton.clicked.connect(self._cancel)
        okPushButton.clicked.connect(self._ok)

        # 布局
        grid = QGridLayout()
        grid.setSpacing(10)
 
        grid.addWidget(increaseColumnsLable, 0, 0, 1, 2)
        grid.addWidget(self._increaseColumnsLineEdit, 1, 0, 1, 2)

        grid.addWidget(forwardRadioButton, 2, 0)
        grid.addWidget(backwardRadioButton, 2, 1)

        grid.addWidget(okPushButton, 3, 1)
        grid.addWidget(cancelPushButton, 3, 0)
 
 
        self.setLayout(grid)
        self.setMinimumWidth(QApplication.desktop().size().width()//5)

    def _ok(self):
        checkedButton = self._wardButtonGroup.checkedButton()
        text = checkedButton.text()
        self._data['backward'] = True if text == '向后' else False

        self._data['days'] = [int(x) for x in self._increaseColumnsLineEdit.text().split(',')]

        self.accept()

    def _cancel(self):
        self.reject()
