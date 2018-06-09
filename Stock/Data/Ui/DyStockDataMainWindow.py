from PyQt5.QtWidgets import QDockWidget

from DyCommon.DyScheduler import DyScheduler
from DyCommon.Ui.DyLogWidget import *
from DyCommon.Ui.DyProgressWidget import *
from DyCommon.Ui.DyBasicMainWindow import *
from DyCommon.Ui.DyDateDlg import *
from DyCommon.Ui.DyCodeDateDlg import *

from .Other.DyStockDataStrategyDataPrepareDlg import *
from .Other.DyStockDataHistTicksVerifyDlg import *
from .Other.DyStockDataHistDaysManualUpdateDlg import DyStockDataHistDaysManualUpdateDlg

from ..DyStockDataCommon import *
from EventEngine.DyEvent import *
from ..Engine.DyStockDataMainEngine import *
from ...Common.DyStockCommon import *
from ...Select.Ui.Other.DyStockSelectTestedStocksDlg import *


class DyStockDataMainWindow(DyBasicMainWindow):
    name = 'DyStockDataMainWindow'

    def __init__(self, parent=None):
        
        self._mainEngine = DyStockDataMainEngine()

        super().__init__(self._mainEngine.eventEngine, self._mainEngine.info, parent)
        
        self._initUi()

        self._initOthers()

    def _initOthers(self):
        DyStockDataCommon.logDetailsEnabled = False

        self._scheduler = DyScheduler()
        self._scheduler.addJob(self._timeOneKeyUpdateJob, {1, 2, 3, 4, 5, 6, 7}, '18:31:00')

    def _timeOneKeyUpdateJob(self):
        if self._oneKeyUpdateAction.text() == '一键更新':
            self._mainEngine._info.print('开始股票(指数,基金)历史数据定时一键更新...', DyLogData.ind)

            self._oneKeyUpdate()

    def _initUi(self):
        self.setWindowTitle('股票数据')

        self._initCentral()
        self._initMenu()
        self._initToolBar()

        self._loadWindowSettings()
        
    def _initCentral(self):
        widgetLog, dockLog = self._createDock(DyLogWidget, '日志', Qt.TopDockWidgetArea, self._mainEngine.eventEngine)
        widgetProgress, dockProgress = self._createDock(DyProgressWidget, '进度', Qt.BottomDockWidgetArea, self._mainEngine.eventEngine)
    
    def _histTicksMannualUpdate(self):
        if self._histTicksMannualUpdateAction.text() == '停止':
            self._mainEngine._info.print('停止股票(基金)历史分笔数据手动更新...', DyLogData.ind)

            # change UI
            self._stopRunningMutexAction()

            event = DyEvent(DyEventType.stopUpdateStockHistTicksReq)
            self._mainEngine.eventEngine.put(event)

        else: # 开始手动更新
            data = {}
            codeLabelText = '股票(基金)代码(空代表所有代码), e.g. 600016,510300,002213,...'
            if DyCodeDateDlg(codeLabelText, data, self).exec_():
                self._mainEngine._info.print('开始股票(基金)历史分笔数据手动更新...', DyLogData.ind)

                # change UI
                self._startRunningMutexAction(self._histTicksMannualUpdateAction)

                event = DyEvent(DyEventType.updateStockHistTicks)
                event.data = data
                event.data['codes'] = DyStockCommon.getDyStockCodes(event.data['codes'])

                self._mainEngine.eventEngine.put(event)

    def _histTicksVerifyAct(self):
        if self._histTicksVerifyAction.text() == '停止':
            self._mainEngine._info.print('停止股票(基金)历史分笔数据校验...', DyLogData.ind)

            # change UI
            self._stopRunningMutexAction()

            event = DyEvent(DyEventType.stopVerifyStockHistTicksReq)
            self._mainEngine.eventEngine.put(event)

        else: # 开始数据校验
            data = {}
            if DyStockDataHistTicksVerifyDlg(data, self).exec_():
                self._mainEngine._info.print('开始股票(基金)历史分笔数据校验...', DyLogData.ind)

                # change UI
                self._startRunningMutexAction(self._histTicksVerifyAction)

                event = DyEvent(DyEventType.verifyStockHistTicks)
                event.data = data

                self._mainEngine.eventEngine.put(event)

    def _manualUpdateSectorCodeTableAct(self):
        data = {'codes': list(DyStockCommon.sectors)}
        if DyCodeDateDlg('板块代码', data, self).exec_():
            self._mainEngine._info.print('开始{0}股票板块代码表更新[{1}, {2}]...'.format(data['codes'], data['startDate'], data['endDate']), DyLogData.ind)

            # change UI
            self._startRunningMutexAction(self._manualUpdateSectorCodeTableAction)

            event = DyEvent(DyEventType.updateStockSectorCodes)
            event.data = data
            event.data['sectorCode'] = data['codes']

            self._mainEngine.eventEngine.put(event)
              
    def _histDaysForcedUpdate(self):
        if self._histDaysForcedUpdateAction.text() == '停止':
            self._mainEngine._info.print('停止股票(指数)历史日线数据强制更新...', DyLogData.ind)

            # change UI
            self._stopRunningMutexAction()

            event = DyEvent(DyEventType.stopUpdateStockHistDaysReq)
            self._mainEngine.eventEngine.put(event)

        else: # 开始手动更新
            data = {}
            if DyDateDlg(data, self).exec_():
                self._mainEngine._info.print('开始股票(指数,基金)历史日线数据强制更新[{0}, {1}]...'.format(data['startDate'], data['endDate']), DyLogData.ind)

                # change UI
                self._startRunningMutexAction(self._histDaysForcedUpdateAction)

                event = DyEvent(DyEventType.updateStockHistDays)
                event.data = data
                event.data['indicators'] = DyStockDataCommon.dayIndicators
                event.data['forced'] = True

                self._mainEngine.eventEngine.put(event)
                 
    def _histDaysMannualUpdate(self):
        if self._histDaysMannualUpdateAction.text() == '停止':
            self._mainEngine._info.print('停止股票(指数)历史日线数据手动更新...', DyLogData.ind)

            # change UI
            self._stopRunningMutexAction()

            event = DyEvent(DyEventType.stopUpdateStockHistDaysReq)
            self._mainEngine.eventEngine.put(event)

        else: # 开始手动更新
            data = {}
            if DyStockDataHistDaysManualUpdateDlg(data, self).exec_():
                self._mainEngine._info.print('开始股票(指数,基金)历史日线数据手动更新[{0}, {1}]...'.format(data['startDate'], data['endDate']), DyLogData.ind)

                # change UI
                self._startRunningMutexAction(self._histDaysMannualUpdateAction)

                event = DyEvent(DyEventType.updateStockHistDays)
                event.data = data
                event.data['codes'] = DyStockCommon.getDyStockCodes(event.data['codes'])

                # 是否要更新指数的日线数据
                if event.data['index']:
                    if event.data['codes'] is None:
                        event.data['codes'] = []

                    event.data['codes'].extend(list(DyStockCommon.indexes))

                self._mainEngine.eventEngine.put(event)

    def _histDaysAutoUpdate(self):
        if self._histDaysAutoUpdateAction.text() == '停止':
            self._mainEngine._info.print('停止股票(指数,基金)历史日线数据自动更新...', DyLogData.ind)

            # change UI
            self._stopRunningMutexAction()

            event = DyEvent(DyEventType.stopUpdateStockHistDaysReq)
            self._mainEngine.eventEngine.put(event)

        else: # 开始自动更新
            self._mainEngine._info.print('开始股票(指数,基金)历史日线数据自动更新...', DyLogData.ind)

            # change UI
            self._startRunningMutexAction(self._histDaysAutoUpdateAction)

            event = DyEvent(DyEventType.updateStockHistDays)
            event.data = None # None means auto updating

            self._mainEngine.eventEngine.put(event)

    def _test(self):
        pass

    def _oneKeyUpdate(self):
        if self._oneKeyUpdateAction.text() == '停止':
            self._mainEngine._info.print('停止股票(指数,基金)历史数据一键更新...', DyLogData.ind)

            # change UI
            self._stopRunningMutexAction()

            self._mainEngine.eventEngine.put(DyEvent(DyEventType.stopStockOneKeyUpdateReq))

        else: # 开始一键更新
            self._mainEngine._info.print('开始股票(指数,基金)历史数据一键更新...', DyLogData.ind)

            # change UI
            self._startRunningMutexAction(self._oneKeyUpdateAction, 2)

            self._mainEngine.eventEngine.put(DyEvent(DyEventType.stockOneKeyUpdate))

    def _timeOneKeyUpdateAct(self):
        if self._timeOneKeyUpdateAction.text() == '停止定时一键更新':
            self._scheduler.shutdown()
            self._timeOneKeyUpdateAction.setText('启动定时一键更新')
        else:
            self._scheduler.start()
            self._timeOneKeyUpdateAction.setText('停止定时一键更新')

    def _initToolBar(self):
        """ 初始化工具栏 """
        # 添加工具栏
        toolBar = self.addToolBar('工具栏')
        toolBar.setObjectName('工具栏')

        self._oneKeyUpdateAction = QAction('一键更新', self)
        self._oneKeyUpdateAction.triggered.connect(self._oneKeyUpdate)
        toolBar.addAction(self._oneKeyUpdateAction)
        self._addMutexAction(self._oneKeyUpdateAction)

        self._timeOneKeyUpdateAction = QAction('启动定时一键更新', self)
        self._timeOneKeyUpdateAction.triggered.connect(self._timeOneKeyUpdateAct)
        toolBar.addAction(self._timeOneKeyUpdateAction)

        # 历史分笔数据源菜单Action
        self._histTicksDataSourceMenuAction = QAction('历史分笔数据源', self)
        toolBar.addAction(self._histTicksDataSourceMenuAction)
        self._histTicksDataSourceMenuAction.triggered.connect(self._histTicksDataSourceMenuAct)

        # 历史分笔数据源菜单
        self._histTicksDataSourceMenu = QMenu(self)

        # 创建历史分笔数据源菜单的操作
        actions = [QAction(x, self) for x in ['新浪', '腾讯', '智能']]
        for action in actions:
            action.setCheckable(True)
            action.triggered.connect(self._histTicksDataSourceAct)
            self._histTicksDataSourceMenu.addAction(action)

            # set default history ticks data source
            if action.text() == DyStockDataCommon.defaultHistTicksDataSource:
                action.setChecked(True)
                self._curHistTicksDataSourceAction = action
                self._histTicksDataSourceMenuAction.setText('历史分笔数据源:{0}'.format(DyStockDataCommon.defaultHistTicksDataSource))

    def _initMenu(self):
        """初始化菜单"""
        # 创建操作
        self._histTicksMannualUpdateAction = QAction('手动更新...', self)
        self._histTicksMannualUpdateAction.triggered.connect(self._histTicksMannualUpdate)
        self._addMutexAction(self._histTicksMannualUpdateAction)

        self._histTicksVerifyAction = QAction('数据校验...', self)
        self._histTicksVerifyAction.triggered.connect(self._histTicksVerifyAct)
        self._addMutexAction(self._histTicksVerifyAction)

        self._strategyDataPrepareAction = QAction('生成实盘策略准备数据...', self)
        self._strategyDataPrepareAction.triggered.connect(self._strategyDataPrepare)
        self._addMutexAction(self._strategyDataPrepareAction)

        self._histDaysMannualUpdateAction = QAction('手动更新...', self)
        self._histDaysMannualUpdateAction.triggered.connect(self._histDaysMannualUpdate)
        self._addMutexAction(self._histDaysMannualUpdateAction)

        self._histDaysAutoUpdateAction = QAction('自动更新', self)
        self._histDaysAutoUpdateAction.triggered.connect(self._histDaysAutoUpdate)
        self._addMutexAction(self._histDaysAutoUpdateAction)

        self._histDaysForcedUpdateAction = QAction('强制更新...', self)
        self._histDaysForcedUpdateAction.triggered.connect(self._histDaysForcedUpdate)
        self._addMutexAction(self._histDaysForcedUpdateAction)

        # 主要更新新添加的板块代码表
        # 手动更新，自动更新，强制更新，都会包含板块代码表的更新
        self._manualUpdateSectorCodeTableAction = QAction('手动更新板块代码表...', self)
        self._manualUpdateSectorCodeTableAction.triggered.connect(self._manualUpdateSectorCodeTableAct)
        self._addMutexAction(self._manualUpdateSectorCodeTableAction)

        self._testedStocksAction = QAction('调试股票...', self)
        self._testedStocksAction.triggered.connect(self._testedStocks)
        self._testedStocksAction.setCheckable(True)

        self._enableLogDetailsAction = QAction('打开日志细节', self)
        self._enableLogDetailsAction.triggered.connect(self._enableLogDetailsAct)
        self._enableLogDetailsAction.setCheckable(True)
        
        # 测试
        testAction = QAction('测试', self)
        testAction.triggered.connect(self._test)

        # 创建菜单
        menuBar = self.menuBar()
        
        # 添加菜单
        histTicksMenu = menuBar.addMenu('历史分笔')
        histTicksMenu.addAction(self._histTicksMannualUpdateAction)
        histTicksMenu.addAction(self._histTicksVerifyAction)

        # 添加菜单
        histDaysMenu = menuBar.addMenu('历史日线')
        histDaysMenu.addAction(self._histDaysAutoUpdateAction)
        histDaysMenu.addAction(self._histDaysMannualUpdateAction)
        histDaysMenu.addAction(self._histDaysForcedUpdateAction)
        histDaysMenu.addAction(self._manualUpdateSectorCodeTableAction)
    
        # 添加菜单
        dataMenu = menuBar.addMenu('数据')
        dataMenu.addAction(self._testedStocksAction)
        dataMenu.addAction(self._strategyDataPrepareAction)

        # 添加菜单
        settingMenu = menuBar.addMenu('设置')
        settingMenu.addAction(self._enableLogDetailsAction)

        # 添加菜单
        #testMenu = menuBar.addMenu('测试')
        #testMenu.addAction(testAction)

    def _strategyDataPrepare(self):
        if self._strategyDataPrepareAction.text() == '停止':
            self._mainEngine._info.print('停止实盘策略准备数据和持仓准备数据...', DyLogData.ind)

            # change UI
            self._stopRunningMutexAction()

            event = DyEvent(DyEventType.stopStockStrategyDataPrepareReq)
            self._mainEngine.eventEngine.put(event)

        else: # 开始策略准备数据
            data = {}
            if DyStockDataStrategyDataPrepareDlg(data, self).exec_():
                self._mainEngine._info.print('开始实盘策略准备数据和持仓准备数据...', DyLogData.ind)

                # change UI
                self._startRunningMutexAction(self._strategyDataPrepareAction)

                event = DyEvent(DyEventType.stockStrategyDataPrepare)
                event.data = data

                self._mainEngine.eventEngine.put(event)
        
    def closeEvent(self, event):
        """ 关闭事件 """
        self._mainEngine.exit()

        return super().closeEvent(event)

    def _testedStocks(self):
        isTested =  self._testedStocksAction.isChecked()

        codes = None
        if isTested:
            data = {}
            if DyStockSelectTestedStocksDlg(data).exec_():
                codes = data['codes']
            else:
                self._testedStocksAction.setChecked(False)

        # put event
        event = DyEvent(DyEventType.stockSelectTestedCodes)
        event.data = codes

        self._mainEngine.eventEngine.put(event)

    def _enableLogDetailsAct(self):
        DyStockDataCommon.logDetailsEnabled = self._enableLogDetailsAction.isChecked()

    def _histTicksDataSourceMenuAct(self):
        self._histTicksDataSourceMenu.popup(QCursor.pos())

    def _histTicksDataSourceAct(self):
        self._curHistTicksDataSourceAction.setChecked(False)

        # get triggered action
        for action in self._histTicksDataSourceMenu.actions():
            if action.isChecked():
                # 设置历史分笔数据源
                dataSource = action.text()

                event = DyEvent(DyEventType.updateHistTicksDataSource)
                event.data = dataSource

                self._mainEngine.eventEngine.put(event)

                self._curHistTicksDataSourceAction = action
                self._histTicksDataSourceMenuAction.setText('历史分笔数据源:{0}'.format(dataSource))
                break

        if not self._curHistTicksDataSourceAction.isChecked():
            self._curHistTicksDataSourceAction.setChecked(True)
        
