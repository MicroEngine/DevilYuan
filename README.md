# DevilYuan股票量化系统
### 简介
DevilYuan股票量化系统由python编写，支持python3.4+，有如下功能：
- 可视化（基于PyQT的界面）
- 多线程事件引擎
- 四大功能
    - 股票数据
    - 选股
    - 策略回测
    - 实盘交易
- 历史数据均免费来自于网络
    - Wind免费个人接口
    - TuShare
- 实盘微信提醒及交互
- 一键挂机
- 全自动交易
- 模拟交易，支持9个模拟账号
- 实盘和回测共用同一策略代码
- 实盘策略编写模板
- 选股策略编写模板
- 自动下载历史数据到MongoDB数据库
    - 股票代码表
    - 交易日数据
    - 个股，指数和ETF历史日线数据
    - 个股和ETF历史分笔数据
- 集成基本的统计功能
- 实盘单账户多策略

### 运行后的界面

# 运行前的准备
- 支持的操作系统：Windows 7/8/10
- 安装[Anaconda](https://www.anaconda.com/download/)，python3.4+ 64位版本
- 安装[MongoDB](https://www.mongodb.com/download-center#production)，并将[MongoDB配置为系统服务](hhttps://docs.mongodb.com/manual/tutorial/install-mongodb-on-windows/#configure-a-windows-service-for-mongodb-community-edition)
    -  由于个股历史分笔数据比较大，建议配备1T以上的硬盘
-  实盘交易现在支持的是银河证券，请安装对应的PC客户端
    - 银河证券的客户端需要做如下配置，不然会导致下单时价格出错以及客户端超时锁定
        - 系统设置 > 界面设置: 界面不操作超时时间设为 0
        - 系统设置 > 交易设置: 默认买入价格/买入数量/卖出价格/卖出数量 都设置为 空
        - 同时客户端不能最小化也不能处于精简模式
- 安装[Wind个人免费Python接口](http://dajiangzhang.com/document) **(可选)**
    - 若不安装Wind接口，股票代码表，交易日数据和历史日线数据将使用TuShare接口。TuShare这一块的数据更新速度比较慢。并且Wind的复权因子数据比较准确，建议安装Wind。但Wind的接口对数据流量有限制。
- 到[Server酱](http://sc.ftqq.com/3.version)注册一个SCKEY，这样实盘时的信号可以铃声通知 **(可选)**
- 安装[Vistual Studio社区版](https://www.visualstudio.com/zh-hans/)，并勾选Python插件 **(可选)**
    - 本项目是用VS2017开发的。你可以选择是用VS2017，或者用其他IDE 
- 需要安装的Python包
    - tushare
    - pymongo
    - qdarkstyle
    - pytesseract
    - pywinauto
    - talib，请到[这儿](https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib)安装对应的whl版本
    - aiohttp
    - pyqrcode
    - mpl_finance
        - `pip install https://github.com/matplotlib/mpl_finance/archive/master.zip`
    - pypng
- VS调试时报异常的包，不调试时不会报错，可选安装
    - datrie
    - crypto
    - gunicorn

# 运行
`python DyMainWindow.py`

# 运行后的步骤
1. 配置DeviYuan系统
2. 下载历史数据
3. 写一个实盘策略

# 感谢
项目的开发过程中借鉴了如下几个开源项目，向以下项目的作者表示衷心的感谢
- [vnpy](https://github.com/vnpy/vnpy)
- [tushare](https://github.com/waditu/tushare)
- [easyquotation](https://github.com/shidenggui/easyquotation)
- [easytrader](https://github.com/shidenggui/easytrader)


# 交流

QQ群：293368752

# License
MIT

