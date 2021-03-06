from multiprocessing.dummy import Pool as ThreadPool
import time
import pandas as pd
import numpy as np
from quartz_extensions import neutralize, standardize, winsorize
import gevent


############################################################################################
# Usage: get_data_items(set_universe("A"), ['20070101', '20080104'], ['LCAP', 'PE'])
############################################################################################
# 取优矿中的因子库因子数据
def get_data_items(universe_list, date_list, factor_list, adj=None, thread_count=16, use_datacube=False):
    '''
    universe_list: ['000001.XSHE', '600036.XSHG', ...]
    date_list:数据日期列表，["2007001", "20180706", '...']
    factor_list: 要取的数据列表(data_cube支持的)
    adj: 数据复权方式（比如取closeprice时）， None/pre
    thread_count: 取数据的线程数，默认16个
    返回:
        frame_list:[frame_t0, frame_t1, ...frame_tn], frame_tn为tn日对应的因子dataframe
        frame_tn的列为: ticker, tradeDate, factor_list, tradeDate格式为"%Y%m%d"
    '''

    t_start = time.time()
    pool = ThreadPool(processes=16)

    # 获取给定日期的因子信息
    def get_factor_by_day(parms):
        '''
        参数：
            params = [my_universe, tdate, data_item_list]
            my_universe: secID的列表
            tdate: 时间， %Y%m%d
            data_item_list: 要取的数据列表
        返回:
            DataFrame, 返回给定日期的因子值
        '''

        tdate, data_item_list, my_universe = parms

        cnt = 0
        while True:
            try:
                if use_datacube:
                    data = get_data_cube(my_universe, ['ticker', 'tradeDate'] + data_item_list, tdate, tdate,
                                         style='tas', adj=adj)
                    tmp_frame = data[tdate]
                else:
                    tmp_frame = DataAPI.MktStockFactorsOneDayProGet(tradeDate=tdate, secID=u"", ticker=u"",
                                                                    field=['ticker', 'tradeDate'] + data_item_list,
                                                                    pandas="1")
                tmp_frame['tradeDate'] = tdate.replace("-", "")
                return tmp_frame

            except Exception as e:
                cnt += 1
                print
                "get data failed in get_factors, reason:%s, retry again, retry count:%s" % (e, cnt)
                if cnt >= 3:
                    print
                    "max get data retry, will exit"
                    raise Exception(e)
            return

    pool_args = zip(date_list, [factor_list] * len(date_list), [universe_list] * len(date_list))
    frame_list = pool.map(get_factor_by_day, pool_args)
    pool.close()
    pool.join()
    t_end = time.time()
    print
    "[quant_util.get_data_items] finished!, time cost:%s" % (t_end - t_start)
    return frame_list


############################################################################################
# Usage: add_indu_col(factor_frame, indu_name='industryName1')
############################################################################################
# 在dataframe后增加一列，表示对应的申万行业分类
def add_indu_col(dframe, indu_name='industryName1'):
    '''
    dframe: panel/横截面/时间序列数据，至少包含[ticker, tradeDate]列， tradeDate为"%Y%m%d"格式
    返回：
          dframe，增加一列，标识对应的申万行业分类
    '''
    # 先拿到申万一级行业的分类
    sw_frame = DataAPI.EquIndustryGet(ticker=np.unique(dframe.ticker.values), industryVersionCD=u"010303",
                                      field=["ticker", indu_name, 'intoDate'], pandas="1")
    sw_frame['tradeDate'] = sw_frame['intoDate'].apply(lambda x: x.replace("-", ""))

    # 标志dframe原有的行
    dframe['original_row'] = 1

    # 合并行业分类
    dframe = dframe.merge(sw_frame[['ticker', 'tradeDate', indu_name]], on=['ticker', 'tradeDate'], how='outer')
    # 排序后，按股票的历史上行业分类进行前向填充
    dframe.sort_values(by=['ticker', 'tradeDate'], ascending=[True, True], inplace=True)
    dframe[indu_name] = dframe.groupby(['ticker']).apply(lambda x: x[indu_name].fillna(method='ffill')).values

    # 删除非dframe原有的行，保证输入输出的日期是一样的
    dframe.dropna(subset=['original_row'], inplace=True)
    del dframe['original_row']
    return dframe


############################################################################################
# Usage: zscore_by_indu(factor_frame,['LCAP', 'PE'])
############################################################################################
# 各个因子在行业内进行标准化(ZSCORE)
def zscore_by_indu(dframe, col_list, indu_name='industryName1'):
    '''
    dframe: panel/横截面/时间序列数据, 列至少包括: ['ticker','tradeDate', col_list], tradeDate为 "%Y%m%d"
    col_list: 需要进行中性化的因子列表
    返回：
         dframe，和输入dframe相比，多了indu_name一列
    '''
    # 得到对应的行业分类
    dframe = add_indu_col(dframe, indu_name=indu_name)

    # 对df的col_list每一列进行zscore标准化
    def zscore_frame(df, col_list):
        df[col_list] = (df[col_list] - df[col_list].mean()) / df[col_list].std()
        return df

    # 按行业进行ZSCORE
    dframe = dframe.groupby(['tradeDate', indu_name]).apply(zscore_frame, col_list)
    return dframe


############################################################################################
# Usage: fillna_indu_median(factor_frame,['LCAP', 'PE'])
############################################################################################
# 用行业内中位数填充因子空值
def fillna_indu_median(dframe, col_list, indu_name='industryName1'):
    '''
    dframe: panel/横截面/时间序列数据, 至少包含 ['ticker', 'tradeDate', col_list], tradeDate为"%Y%m%d"
    col_list: 需要进行中性化的因子列表
    返回：
        经过空值填充的dframe
    '''
    if indu_name not in dframe.columns:
        dframe = add_indu_col(dframe, indu_name=indu_name)

    # 中位数填充空值
    def fill_na_media(df, col):
        df[col] = df[col].fillna(df[col].median())
        return df

    dframe = dframe.groupby(['tradeDate', indu_name]).apply(fill_na_media, col_list)
    return dframe


############################################################################################
# Usage: netralize_dframe(factor_frame,['LCAP', 'PE'], exclude_stype=['BETA', 'SIZE', 'Bank'])
############################################################################################
def netralize_dframe(dframe, col_list, exclude_style=[]):
    '''
    dframe: panel/横截面/时间序列数据, 列至少包括['ticker', 'tradeDate', col_list]
    col_list: 需要进行中性化的因子列表
    exclude_style: 不进行中性的风格
    返回：
         经过中性化后的dframe
    '''

    # 在某一天对col_list的每一个因子进行中性化
    def neutralize_by_date(params):
        '''
        params=[dframe_by_tdate, col_list, exclude_style]
        dframe_by_tdate: tdate日的dframe，列至少包括['ticker', 'tradeDate', col_list]
        exclude_style: 不进行中性化的风格, list
        '''
        dframe_by_tdate, col_list, exclude_style = params
        tdate = dframe_by_tdate.tradeDate.values[0]
        # 对每个因子进行中性化
        for col in col_list:
            if len(dframe_by_tdate[col].dropna()) < 11:
                # print "Netralize skipped for %s, %s because  too many nan factor values" %(col, tdate)
                continue
            dframe_by_tdate[col] = neutralize(dframe_by_tdate[col], target_date=tdate, exclude_style_list=exclude_style)
        return dframe_by_tdate

    dframe.set_index('ticker', inplace=True)
    # 将dframe拆成list，便于利用协程加快计算
    col_lists = []
    frame_list = []
    exclude_lists = []
    for tdate, tdframe in dframe.groupby(['tradeDate']):
        col_lists.append(col_list)
        frame_list.append(tdframe)
        exclude_lists.append(exclude_style)
    # 利用协程进行计算
    jobs = [gevent.spawn(neutralize_by_date, value) for value in zip(frame_list, col_lists, exclude_lists)]
    gevent.joinall(jobs)
    new_frame_list = [result.value for result in jobs]
    dframe = pd.concat(new_frame_list, axis=0)
    dframe.reset_index(inplace=True)
    return dframe


############################################################################################
# Usage: netralize_dframe(factor_frame,['LCAP', 'PE'], sigma_n=3)
############################################################################################
# 绝对中位数差法
def mad_winsorize(dframe, col_list, sigma_n=3):
    '''
    dframe: panel/横截面/时间序列数据, 列至少包括: ['ticker','tradeDate', col_list], tradeDate为 "%Y%m%d"
    col_list: 需要进行winsorize的因子列表
    '''

    def mad_winsor_by_day(dframe_tdate, col_list, sigma_n):
        '''
        按照[dm+sigma_n*dm1, dm-sigma_n*dm1]进行winsorize
        dm: median
        dm1: median(abs(origin_data - median)), 即 MAD值
        参数:
            dframe_tdate: 某一期的多个因子值的dataframe
        返回:
            去极值后的dframe_tdate
        '''
        dm = dframe_tdate[col_list].median()
        dm1 = (dframe_tdate[col_list] - dm).abs().median()

        upper = dm + sigma_n * dm1
        lower = dm - sigma_n * dm1
        for col in col_list:
            tmp_col = dframe_tdate[col]
            tmp_col[tmp_col > upper[col]] = upper[col]
            tmp_col[tmp_col < lower[col]] = lower[col]
            dframe_tdate[col] = tmp_col
        return dframe_tdate

    dframe = dframe.groupby(['tradeDate']).apply(mad_winsor_by_day, col_list, sigma_n)
    return dframe


############################################################################################
# Usage: calc_ic(factor_frame, return_df, ['LCAP', 'PE'], ic_type='spearman')
############################################################################################
# 给定factor_df， return_df，计算对于的IC
def calc_ic(factor_df, return_df, factor_list, return_col_name='target_return', ic_type='spearman'):
    """
    计算因子IC值, 本月和下月因子值的秩相关
    params:
            factor_df: DataFrame, columns=['ticker', 'tradeDate', factor_list]
            return_df: DataFrame, colunms=['ticker, 'tradeDate'， return_col_name], 预先计算好的未来的收益率
            factor_list:　list， 需要计算IC的因子名list
            return_col_name: str, return_df中的收益率列名
            method: : {'spearman', 'pearson'}, 默认'spearman', 指定计算rank IC('spearman')或者Normal IC('pearson')
    return:
            DataFrame, 返回各因子的IC序列， 列为: ['tradeDate', factor_list]
    """
    merge_df = factor_df.merge(return_df, on=['ticker', 'tradeDate'])
    # 遍历每个因子，计算对应的IC
    factor_ic_list = []
    for factor_name in factor_list:
        tmp_factor_ic = merge_df.groupby(['tradeDate']).apply(
            lambda x: x[[factor_name, return_col_name]].corr(method=ic_type).values[0, 1])
        tmp_factor_ic.name = factor_name
        factor_ic_list.append(tmp_factor_ic)
    factor_ic_frame = pd.concat(factor_ic_list, axis=1)
    factor_ic_frame.reset_index(inplace=True)
    return factor_ic_frame


############################################################################################
# Usage: monthly_factor_ic(factor_frame,['LCAP', 'PE'], month_len=3)
############################################################################################
# 输入因子的dataframe，计算月度因子的IC序列（未来1个月，n个月，可自定义）
def monthly_factor_ic(factor_df, factor_list, start_date=None, end_date=None, ic_type='spearman', month_len=1):
    '''
    factor_df: panel/横截面/时间序列数据, 列至少包括: ['ticker','tradeDate', factor_list], tradeDate为 "%Y%m%d", 必须为月末日期
    factor_list: 需要计算IC的factor名list
    start_date: 返回的IC序列的最早时间，默认为None，和factor_df的最早时间保持一致；如果不为None, 格式为"%Y%m%d, 必须为月末日期
    end_date: 返回的IC序列的最大时间，默认为None，和factor_df的最大时间保持一致；如果不为None, 格式为"%Y%m%d， 必须为月末日期
    ic_type: spearman/pearson
    month_len: 计算IC时，看和未来N期收益的关系
    返回：
         IC的dataframe，columns为：[tradeDate, factor1_name, factor2_name,..., factorn_name]]
    '''
    if start_date is None:
        start_date = min(factor_df.tradeDate.values)
    else:
        start_date = max(str(start_date).replace("-", ""), min(factor_df.tradeDate.values))

    if end_date is None:
        end_date = max(factor_df.tradeDate.values)
    else:
        end_date = min(str(end_date).replace("-", ""), max(factor_df.tradeDate.values))
    factor_df = factor_df.query("(tradeDate>=@start_date) & (tradeDate<=@end_date)")

    # 由于计算IC用到未来期的收益，所以取行情数据的截止日应该比因子的截止日多month_len期
    date_frame = DataAPI.TradeCalGet(exchangeCD=u"XSHG", beginDate=end_date, field=u"", pandas="1")
    date_frame = date_frame.query("isMonthEnd==1")
    if len(date_frame) < (month_len + 1):
        raise Exception(u"计算月度IC时，交易日历中取不到%s的下个月月末日期，请检查%s是否为月末交易日" % (end_date, end_date))
    data_end_date = date_frame.head(month_len + 1).calendarDate.values[-1].replace("-", "")

    ticker_list = list(np.unique(factor_df.ticker.values))

    # 获得月收益率
    month_return = DataAPI.MktEqumGet(ticker=ticker_list, beginDate=start_date, endDate=data_end_date,
                                      field=["ticker", "endDate", "closePrice"], pandas="1")
    month_return.rename(columns={'endDate': 'tradeDate'}, inplace=True)
    month_return['tradeDate'] = month_return['tradeDate'].apply(lambda x: x.replace("-", ""))
    month_return.sort_values(['ticker', 'tradeDate'], inplace=True)
    # 计算未来month_len期的累计收益率
    month_return['target_closePrice'] = month_return.groupby('ticker')['closePrice'].shift(-1 * month_len)
    month_return['target_return'] = (month_return['target_closePrice'] - month_return['closePrice']) / month_return[
        'closePrice']
    month_return = month_return[['ticker', 'tradeDate', 'target_return', 'closePrice']]
    month_return.dropna(inplace=True)

    # 得到IC值
    factor_ic_frame = calc_ic(factor_df, month_return, factor_list)
    factor_ic_frame = factor_ic_frame[['tradeDate'] + factor_list]
    factor_return_frame = factor_df.merge(month_return, on=['ticker', 'tradeDate'])
    return factor_ic_frame, factor_return_frame


############################################################################################
# Usage: multifactor_icir_comb(factor_frame,['LCAP', 'PE'], 3, month_len=3)
############################################################################################
# 根据过去N期的IC_IR，得到因子的权重和加权得到的因子值
def multifactor_icir_comb(factor_df, factor_list, window, ic_type='spearman', month_len=1, start_date=None,
                          end_date=None):
    '''
    factor_df: panel数据, 列至少包括: ['ticker','tradeDate', factor_list], tradeDate为 "%Y%m%d", 必须为月末日期
    factor_list: 参与权重分配的factor名list
    start_date: 返回权重的最早时间，默认为None，和factor_df的最早时间保持一致；如果不为None, 格式为"%Y%m%d, 必须为月末日期
    end_date: 返回的权重的最大时间，默认为None，和factor_df的最大时间保持一致；如果不为None, 格式为"%Y%m%d， 必须为月末日期
    ic_type: spearman/pearson
    返回：
         factor_weight_frame： 列为: ['tradeDate', factor_name1, factor_name2, ...factor_nameN], 同一个tradeDate，权重之和为1
         factor_frame：加上了合成因子值后的factor_frame, 列为['ticker', 'tradeDate', factor_list(原始因子值), 'multifactor_comb_value']
    '''
    # 调整factor_df的index，防止有duplicated的index
    ori_factor_df_index = factor_df.index.values
    factor_df.index = range(len(factor_df))
    factor_df = factor_df[['ticker', 'tradeDate'] + factor_list]
    # 得到因子每个月的IC
    factor_ic_frame, factor_return_frame = monthly_factor_ic(factor_df, factor_list)
    # 计算IC_IR值
    factor_ic_frame.sort_values(by=['tradeDate'], inplace=True)
    factor_icir_frame = factor_ic_frame.copy()
    factor_icir_frame[factor_list] = factor_ic_frame[factor_list].shift(month_len).rolling(window=window).apply(
        lambda x: x.mean() / x.std())
    # 得到因子的权重值（根据横截面的IC_IR做归一化）, 权重frame的列为
    factor_weight_frame = factor_icir_frame.copy()

    # 将因子权重乘以原始因子值，得到合成之后的因子值
    factor_df = factor_df.merge(factor_weight_frame, on=['tradeDate'], how='left', suffixes=("", "_weight"))
    weight_cols = [x + "_weight" for x in factor_list]
    factor_df['multifactor_comb_value'] = (np.array(factor_df[factor_list]) * (np.array(factor_df[weight_cols]))).sum(
        axis=1)

    if start_date is None:
        start_date = min(factor_df.tradeDate.values)
    else:
        start_date = max(str(start_date).replace("-", ""), min(factor_df.tradeDate.values))

    if end_date is None:
        end_date = max(factor_df.tradeDate.values)
    else:
        end_date = min(str(end_date).replace("-", ""), max(factor_df.tradeDate.values))
    factor_df = factor_df.query("(tradeDate>=@start_date) & (tradeDate<=@end_date)")
    factor_weight_frame = factor_weight_frame.query("(tradeDate>=@start_date) & (tradeDate<=@end_date)")
    return factor_df, [factor_weight_frame, factor_return_frame]


############################################################################################
# Usage: fin_data_pit2cont(factor_frame,'20160101', '20171231')
############################################################################################
# 将PIT数据转成连续数据
def fin_data_pit2cont(pit_data_frame, sdate, edate):
    """
    将PIT数据转成连续数据
    pit_data_frame: 财务报表数据, column= ['ticker','pub_date',[fin_value]], index=num, pub_date='%Y%m%d'
    sdate: 起始时间, '%Y%m%d'
    edate: 终止时间, '%Y%m%d'
    返回：
         连续日的因子值dataframe, 列为：['ticker','pub_date',[fin_value]]
    """

    trade_date_frame = DataAPI.TradeCalGet(exchangeCD=u"XSHE", beginDate='20060101', endDate=edate,
                                           field=['calendarDate', 'isOpen'])
    trade_date_frame.rename(columns={"calendarDate": "pub_date"}, inplace=True)
    trade_date_frame['pub_date'] = trade_date_frame['pub_date'].apply(lambda x: str(x).replace('-', ''))

    tmp_frame = pit_data_frame.groupby(['ticker']).apply(lambda x: x.merge(trade_date_frame,
                                                                           on=['pub_date'], how='outer'))
    del tmp_frame['ticker']
    tmp_frame.reset_index(inplace=True)
    del tmp_frame['level_1']

    tmp_frame = tmp_frame.sort_values(by=['ticker', 'pub_date'], ascending=True)
    tmp_frame = tmp_frame.groupby(['ticker']).apply(lambda x: x.fillna(method='pad'))
    tmp_frame.dropna(inplace=True)
    tmp_frame = tmp_frame[tmp_frame.pub_date >= sdate]
    tmp_frame = tmp_frame[tmp_frame.isOpen == 1]
    del tmp_frame['isOpen']
    return tmp_frame


############################################################################################
# Usage: stock_special_tag('20160101', '20171231')
############################################################################################
# 某一时间区间内，根据股票的是否满足某些条件，打上标签
def stock_special_tag(start_date, end_date, halt=1, st=1, pre_new=1, pre_new_length=60):
    '''
    某一时间区间内，根据股票的是否满足某些条件，打上标签
    start_date: 起始时间, %Y%m%d
    end_date: 结束时间, %Y%m%d
    halt: 停牌
    st: 正处于ST状态
    pre_new: 次新股
    pre_new_length: 定义新股上市后 pre_new_length的股票为次新股
    返回：
         tag_df：包含标签的dataframe， 列为： ['ticker', 'tradeDate', 'special_flag']
         special_flag为：{如果停牌，则为'halt'， 如果ST，则为'ST', 如果次新股，则为'new'}，一个股票在同一天如果满足多个条件，会有多条记录（多行）
    '''
    # 获取交易日历
    trade_calendar = DataAPI.TradeCalGet(exchangeCD=U"XSHG", field=u"calendarDate,isOpen,isMonthEnd")

    # 获得交易日历
    calendar = trade_calendar[trade_calendar['isOpen'] == 1]
    calendar = calendar['calendarDate'].tolist()

    # 次新股
    new_df = pd.DataFrame()
    if pre_new:
        ipo_info = DataAPI.SecIDGet(assetClass=u"E", field=['ticker', 'listDate'], pandas="1")
        ipo_info.dropna(inplace=True)
        ticker_list = [ticker for ticker in ipo_info['ticker'] if len(ticker) == 6 and ticker[0] in ['0', '3', '6']]
        ipo_info = ipo_info[ipo_info['ticker'].isin(ticker_list)]
        ipo_info['permit_date'] = [
            calendar[calendar.index(date) + int(pre_new_length)] if date in calendar else calendar[0] for date in
            ipo_info['listDate']]

        calendar = np.array(calendar)
        new_df_list = []
        for date in calendar[(calendar > start_date) & (calendar < end_date)]:
            new_list = ipo_info[(ipo_info['permit_date'] >= date) & (ipo_info['listDate'] <= date)]['ticker'].values
            d_new_df = pd.DataFrame({'tradeDate': [date] * len(new_list), 'ticker': new_list})
            new_df_list.append(d_new_df)

        new_df = pd.concat(new_df_list, axis=0)
        new_df['special_flag'] = 'new'

    # ST股
    st_df = pd.DataFrame()
    if st:
        st_info = DataAPI.SecSTGet(beginDate=start_date, endDate=end_date, field=['tradeDate', 'ticker'], pandas="1")
        st_df = st_info.copy()
        st_df['special_flag'] = 'st'

    # 停牌
    halt_frame = pd.DataFrame()
    if halt:
        halt_info = DataAPI.SecHaltGet(beginDate=start_date, endDate=end_date,
                                       field=['ticker', 'haltBeginTime', 'haltEndTime'], pandas="1")
        halt_info.fillna(calendar[-1], inplace=True)
        halt_info['haltBeginTime'] = halt_info['haltBeginTime'].apply(lambda x: x[:10])
        halt_info['haltEndTime'] = halt_info['haltEndTime'].apply(lambda x: x[:10])

        halt_frame_list = []
        for date in calendar[(calendar > start_date) & (calendar < end_date)]:
            halt_list = halt_info[(halt_info['haltEndTime'] >= date) & (halt_info['haltBeginTime'] <= date)][
                'ticker'].values
            d_halt_df = pd.DataFrame({'tradeDate': [date] * len(halt_list), 'ticker': halt_list})
            halt_frame_list.append(d_halt_df)

        halt_df = pd.concat(halt_frame_list, axis=0)
        halt_df['special_flag'] = 'halt'

    tag_df = pd.concat([new_df, st_df, halt_df], axis=0)
    tag_df = tag_df[['ticker', 'tradeDate', 'special_flag']]
    tag_df['tradeDate'] = tag_df['tradeDate'].apply(lambda x: x.replace("-", ""))
    return tag_df


############################################################################################
# Usage: get_performance(bt)
############################################################################################
# 根据优矿的回测结果（或者类似的回测数据）计算净值和回撤
def get_performance(bt, excess=False):
    '''
    得到回测结果的净值和回撤
    bt: dataframe，columns至少为：['tradeDate', u'portfolio_value',u'benchmark_return']
    excess: 如果为True, 则收益代表超额收益，否则为绝对收益
    返回：
         return_data: 净值序列dataframe, 列为:['tradeDate', 'portfolio_value','portfolio_return','target_return'], 'target_return'为绝对或者超额的累计收益率
         drawback_data:最大回撤序列
    '''
    return_data = bt[[u'tradeDate', u'portfolio_value', u'benchmark_return']].set_index('tradeDate')
    if type(bt.tradeDate.values[0]) == np.datetime64:
        return_data.index = pd.to_datetime(return_data.index)
    return_data['portfolio_return'] = return_data.portfolio_value.pct_change()
    return_data['portfolio_return'].ix[0] = 1
    if excess:
        return_data['target_return'] = return_data.portfolio_return - data.benchmark_return
    else:
        return_data['target_return'] = return_data.portfolio_return
    return_data['target'] = return_data.target_return + 1.0
    return_data['target_return'] = return_data.target.cumprod()
    del return_data['target']

    df_cum_rets = return_data['portfolio_return']
    running_max = np.maximum.accumulate(df_cum_rets)
    drawback_data = -((running_max - df_cum_rets) / running_max)
    return return_data, drawback_data
