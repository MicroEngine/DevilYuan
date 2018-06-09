# 下载股票历史数据
股票历史数据支持的类型：
- 股票代码表
- 股票交易日数据
- 个股，指数和ETF历史日线数据，含如下指标
    - OHLCV
    - 成交额
    - 换手率
    - 复权因子
- 个股和ETF历史分笔数据
    - TuShare好像不支持大盘指数的历史分笔，如果策略需要参考指数分笔数据，可以用ETF50，ETF300，ETF500代替 

# 自动更新方式
1. 手动下载某一交易日的历史日线数据  
![image](https://github.com/moyuanz/DevilYuan/blob/master/docs/data/mannualDaysConfig.png)
2. 手动下载步骤1里的对应的交易日的历史分笔数据  
![image](https://github.com/moyuanz/DevilYuan/blob/master/docs/data/mannualTicksConfig.png)
3. 一键更新，自动更新历史日线和分笔数据到今天  
![image](https://github.com/moyuanz/DevilYuan/blob/master/docs/data/result.png)

# 手动更新方式
参考**自动更新方式**里的步骤1和2
