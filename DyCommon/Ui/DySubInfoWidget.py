from PyQt5 import QtCore
from PyQt5.QtWidgets import QWidget, QLabel, QProgressBar, QMenu
from PyQt5.Qt import QGridLayout, QAction, QCursor

from EventEngine.DyEvent import *
from .DyLogWidget import *


class DySubInfoWidget(QWidget):
    signalTotal = QtCore.pyqtSignal(type(DyEvent()))
    signalLog = QtCore.pyqtSignal(type(DyEvent()))
    
    def __init__(self, eventEngine, paramGroupNo, period, parent=None):
        super().__init__(parent)

        self._eventEngine = eventEngine
        self._paramGroupNo = paramGroupNo
        self._period = period
        
        self._logData = []
        self._logWidget = None
        self._logWarningCount = 0
        self._logErrorCount = 0

        self._initUi()
        self._registerEvent()

    def _initUi(self):
        """初始化界面"""

        self._progressTotal = QProgressBar(self)
        self._logDescriptionLabel = QLabel()
        self._logTimeLabel = QLabel()
        self._logWarningLabel = QLabel()
        self._logErrorLabel = QLabel()

        self._logWarningLabel.setStyleSheet('color:#FF6100')
        self._logErrorLabel.setStyleSheet('color:red')

        grid = QGridLayout()
        grid.addWidget(self._progressTotal, 0, 0)
        grid.addWidget(self._logErrorLabel, 0, 1)
        grid.addWidget(self._logWarningLabel, 0, 2)
        grid.addWidget(self._logTimeLabel, 0, 3)
        grid.addWidget(self._logDescriptionLabel, 0, 4)

        self.setLayout(grid)

        self._initMenu()

    def _updateProgressTotal(self, event):
        self._progressTotal.setValue(event.data)

    def _logHandler(self, event):
        data = event.data

        # save
        self._logData.append(data)

        if data.type == data.ind:
            self._logDescriptionLabel.setStyleSheet('color:darkGreen')

        elif data.type == data.error:
            self._logDescriptionLabel.setStyleSheet('color:red')
            self._logErrorCount += 1

        elif data.type == data.warning:
            self._logDescriptionLabel.setStyleSheet('color:#FF6100')
            self._logWarningCount += 1

        else:
            self._logDescriptionLabel.setStyleSheet('color:white')

        self._logTimeLabel.setText(data.time)
        self._logDescriptionLabel.setText(data.description)
        self._logWarningLabel.setText('警告: {0}'.format(self._logWarningCount))
        self._logErrorLabel.setText('错误: {0}'.format(self._logErrorCount))

    def _registerEvent(self):
        self.signalTotal.connect(self._updateProgressTotal)
        self.signalLog.connect(self._logHandler)

        self._eventEngine.register(DyEventType.subProgressTotal_ + '_' + str(self._paramGroupNo) + str(self._period), self.signalTotal.emit)
        self._eventEngine.register(DyEventType.subLog_ + '_' + str(self._paramGroupNo) + str(self._period), self.signalLog.emit)

    def _initMenu(self):
        """初始化右键菜单"""

        self._menu = QMenu(self)    
        
        showLogsAction = QAction('显示所有日志...', self)
        showLogsAction.triggered.connect(self._showLogs)
        
        self._menu.addAction(showLogsAction)

    def contextMenuEvent(self, event):
        """右键点击事件"""

        self._menu.popup(QCursor.pos())

    def _showLogs(self):
        self._logWidget = DyLogWidget()
        self._logWidget.append(self._logData)

        self._logWidget.showMaximized()
        self._logWidget.setWindowTitle('日志' + str(self._period))