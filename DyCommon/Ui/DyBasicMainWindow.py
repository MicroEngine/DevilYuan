from PyQt5 import QtCore
from PyQt5.QtWidgets import QMainWindow, QDockWidget, QLabel

from EventEngine.DyEvent import *
from DyCommon.DyCommon import *
from Stock.Common.DyStockCommon import *


class DyBasicMainWindow(QMainWindow):

    name = 'DyBasicMainWindow'

    signalStopAck = QtCore.pyqtSignal(type(DyEvent()))
    signalFinish = QtCore.pyqtSignal(type(DyEvent()))
    signalFail = QtCore.pyqtSignal(type(DyEvent()))

    def __init__(self, eventEngine, info, parent=None, type='stock'):
        super().__init__(parent)
        
        self._info = info
        self.__type = type

        self._mutexActions = []
        self._runningAction = None
        self._runningActionText = None
        self._runningActionCount = 0

        if eventEngine is not None:
            self.__registerEvent(eventEngine)

        self.__initStatusBar()

    def __initStatusBar(self):
        if self.__type == 'stock':
            text = '股票历史日线数据源:{}'.format(','.join(DyStockCommon.defaultHistDaysDataSource))
            label = QLabel(text)
            self.statusBar().addPermanentWidget(label)

    def _addMutexAction(self, action):
        if action not in self._mutexActions:
            self._mutexActions.append(action)

    def _startRunningMutexAction(self, action, count=1):
        """
            @count: 并行运行操作的个数。也就是说当所有的操作都结束时，才能使能Action。
                    操作结束的种类：
                            失败
                            成功
                            停止
                    例子：
                        一键更新股票数据，包含2个独立并行操作，日线数据和历史分笔。
        """
        self._runningAction = action
        self._runningActionText = action.text()
        self._runningActionCount = count

        action.setText('停止')

        for action in self._mutexActions:
            if action != self._runningAction:
                action.setDisabled(True)

    def _endRunningMutexAction(self):
        """ called once finish, fail or stopAck event received """
        if self._runningAction is None: return False

        self._runningActionCount -= 1

        # all ended
        if self._runningActionCount == 0:
            self._runningAction.setText(self._runningActionText)

            self._runningAction = None
            self._runningActionText = None
            self._runningActionCount = 0

            for action in self._mutexActions:
                action.setEnabled(True)

            return True

        return False

    def _stopRunningMutexAction(self):
        self._runningAction.setDisabled(True)

    def _endHandler(self, event):
        """
            if program not processed carefully, event finish and stopAck might comming both.
            In that case, always ignore last one.
        """
        if event.type == DyEventType.finish:
            if self._endRunningMutexAction():
                self._info.print('成功完成', DyLogData.ind)

        elif event.type == DyEventType.fail:
            if self._endRunningMutexAction():
                self._info.print('失败', DyLogData.error)

        elif event.type == DyEventType.stopAck:
            if self._endRunningMutexAction():
                self._info.print('已经停止', DyLogData.ind)

    def __registerEvent(self, eventEngine):
        """注册GUI更新相关的事件监听"""
        self.signalStopAck.connect(self._endHandler)
        self.signalFinish.connect(self._endHandler)
        self.signalFail.connect(self._endHandler)

        eventEngine.register(DyEventType.stopAck, self.signalStopAck.emit)
        eventEngine.register(DyEventType.finish, self.signalFinish.emit)
        eventEngine.register(DyEventType.fail, self.signalFail.emit)

    def _saveWindowSettings(self):
        """保存窗口设置"""
        settings = QtCore.QSettings('DevilYuan', 'DevilYuanQuant')
        settings.setValue(self.name + 'State', self.saveState())
        settings.setValue(self.name + 'Geometry', self.saveGeometry())

    def _loadWindowSettings(self):
        """载入窗口设置"""
        settings = QtCore.QSettings('DevilYuan', 'DevilYuanQuant')
        try:
            ret = self.restoreState(settings.value(self.name + 'State'))
            ret = self.restoreGeometry(settings.value(self.name + 'Geometry'))    
        except Exception as ex:
            pass

    def closeEvent(self, event):
        self._saveWindowSettings()

        return super().closeEvent(event)

    def _createDock(self, widgetClass, widgetName, widgetArea, *param):
        """创建停靠组件"""

        widget = widgetClass(*param)

        dock = QDockWidget(widgetName, self)
        dock.setWidget(widget)
        dock.setObjectName(widgetName)
        dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.addDockWidget(widgetArea, dock)
        return widget, dock
