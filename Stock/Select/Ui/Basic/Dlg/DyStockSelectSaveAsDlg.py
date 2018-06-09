from PyQt5.QtWidgets import QDialog, QGridLayout, QPushButton, QRadioButton, QButtonGroup, QApplication


class DyStockSelectSaveAsDlg(QDialog):

    def __init__(self, data, strategyName, parent=None):
        super().__init__(parent)

        self._data = data

        self._initUi(strategyName)

    def _initUi(self, strategyName):
        self.setWindowTitle('[{0}]另存为'.format(strategyName))
 
        allRadioButton = QRadioButton('所有'); allRadioButton.setChecked(True)
        highlightRadioButton = QRadioButton('高亮')

        # 添加到QButtonGroup
        self._buttonGroup = QButtonGroup()
        self._buttonGroup.addButton(allRadioButton, 1); 
        self._buttonGroup.addButton(highlightRadioButton, 2)

        cancelPushButton = QPushButton('Cancel')
        okPushButton = QPushButton('OK')
        cancelPushButton.clicked.connect(self._cancel)
        okPushButton.clicked.connect(self._ok)

        # 布局
        grid = QGridLayout()
        grid.setSpacing(10)
 
        grid.addWidget(allRadioButton, 1, 0)
        grid.addWidget(highlightRadioButton, 1, 1)

        grid.addWidget(okPushButton, 2, 1)
        grid.addWidget(cancelPushButton, 2, 0)
 
        self.setLayout(grid)
        self.setMinimumWidth(QApplication.desktop().size().width()//5)

    def _ok(self):
        checkedButton = self._buttonGroup.checkedButton()
        text = checkedButton.text()
        self._data['all'] = True if text == '所有' else False

        self.accept()

    def _cancel(self):
        self.reject()
