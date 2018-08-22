#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import scipy as sp
import seaborn
# import vnpy as vp
# import datetime
# from utils.tool import auto_sample
# from alphalens import *
from numpy import nan
from pandas import (DataFrame, date_range)
import matplotlib.pyplot as plt
from dataProvider.dataapi import da
from alphalens.tears import (create_returns_tear_sheet,
                             create_information_tear_sheet,
                             create_turnover_tear_sheet,
                             create_summary_tear_sheet,
                             create_full_tear_sheet,
                             create_event_returns_tear_sheet,
                             create_event_study_tear_sheet)

from alphalens.utils import get_clean_factor_and_forward_returns

# price_index = date_range(start='2015-1-10', end='2015-2-28')
# price_index.name = 'date'
# tickers = ['A', 'B', 'C', 'D', 'E', 'F']
# data = [[1.0025 ** i, 1.005 ** i, 1.00 ** i, 0.995 ** i, 1.005 ** i, 1.00 ** i]
#         for i in range(1, 51)]
# prices = DataFrame(index=price_index, columns=tickers, data=data)
#
# #
# # build factor
# #
# factor_index = date_range(start='2015-1-15', end='2015-2-13')
# factor_index.name = 'date'
# factor = DataFrame(index=factor_index, columns=tickers,
#                    data=[[3, 4, 2, 1, nan, nan], [3, nan, nan, 1, 4, 2],
#                          [3, 4, 2, 1, nan, nan], [3, 4, 2, 1, nan, nan],
#                          [3, 4, 2, 1, nan, nan], [3, 4, 2, 1, nan, nan],
#                          [3, nan, nan, 1, 4, 2], [3, nan, nan, 1, 4, 2],
#                          [3, 4, 2, 1, nan, nan], [3, 4, 2, 1, nan, nan],
#                          [3, nan, nan, 1, 4, 2], [3, nan, nan, 1, 4, 2],
#                          [3, nan, nan, 1, 4, 2], [3, nan, nan, 1, 4, 2],
#                          [3, nan, nan, 1, 4, 2], [3, nan, nan, 1, 4, 2],
#                          [3, nan, nan, 1, 4, 2], [3, nan, nan, 1, 4, 2],
#                          [3, nan, nan, 1, 4, 2], [3, nan, nan, 1, 4, 2],
#                          [3, 4, 2, 1, nan, nan], [3, 4, 2, 1, nan, nan],
#                          [3, 4, 2, 1, nan, nan], [3, 4, 2, 1, nan, nan],
#                          [3, 4, 2, 1, nan, nan], [3, 4, 2, 1, nan, nan],
#                          [3, 4, 2, 1, nan, nan], [3, 4, 2, 1, nan, nan],
#                          [3, nan, nan, 1, 4, 2], [3, nan, nan, 1, 4, 2]]).stack()
# factor_groups = {'A': 'Group1', 'B': 'Group2', 'C': 'Group1', 'D': 'Group2', 'E': 'Group1', 'F': 'Group2'}
#
# prices.plot()
# plt.show()
#
# factor_data = get_clean_factor_and_forward_returns(
#     factor,
#     prices,
#     groupby=factor_groups,
#     quantiles=4,
#     periods=(1, 3),
#     filter_zscore=None)
#
# create_full_tear_sheet(factor_data, long_short=False, group_neutral=False, by_group=False)
# create_event_returns_tear_sheet(factor_data, prices, avgretplot=(3, 11),
#                                 long_short=False, group_neutral=False, by_group=False)
#
#
# create_full_tear_sheet(factor_data, long_short=True, group_neutral=False, by_group=True)
# create_event_returns_tear_sheet(factor_data, prices, avgretplot=(3, 11),
#                                 long_short=True, group_neutral=False, by_group=True)
#
#
# create_event_study_tear_sheet(event_data, prices, avgretplot=(5, 10))

######################################################################################
#                              市值因子分析
######################################################################################
#   基础数据
start_date = '20170101'
end_date = '20180822'
index_weight = da.index_weight()
sw_industry = da.sw_weight()
code_list = index_weight['code'].unique()
stock_bar = da.stock_bar(code_list, start_date, end_date)
#   数据准备和清洗
stock_bar['trade_date'] = pd.to_datetime(stock_bar['trade_date'])
stock_init = stock_bar.set_index(['trade_date', 'code'])
stock_factor = stock_init['amount']
stock_close = stock_init['close'].unstack()
industry_dict = sw_industry.set_index('code')['index_code'].to_dict()
industry_labels = sw_industry.set_index('index_code')['index_name'].to_dict()

#   分析因子
factor_data = get_clean_factor_and_forward_returns(
    stock_factor,
    stock_close,
    groupby=industry_dict,
    quantiles=5,
    binning_by_group=True,
    periods=(1, 5, 10),
    filter_zscore=None)

create_full_tear_sheet(factor_data, long_short=False, group_neutral=True, by_group=True)
create_event_returns_tear_sheet(factor_data, stock_close, avgretplot=(3, 11),
                                long_short=False, group_neutral=True, by_group=True)

factor_data
