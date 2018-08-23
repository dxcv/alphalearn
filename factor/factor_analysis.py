#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import scipy as sp
import seaborn as sns
# import datetime
# from utils.tool import auto_sample
# from alphalens import *
from alphalens.performance import create_pyfolio_input
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
    quantiles=10,
    binning_by_group=True,
    periods=(1, 5, 10),
    filter_zscore=None)

create_full_tear_sheet(factor_data, long_short=False, group_neutral=True, by_group=True)
# create_summary_tear_sheet(factor_data, long_short=True, group_neutral=True)
# create_event_returns_tear_sheet(factor_data, stock_close, avgretplot=(3, 11),
#                                 long_short=False, group_neutral=True, by_group=True)
# create_event_study_tear_sheet(factor_data, stock_close)
# returns, positions, benchmark_rets = create_pyfolio_input(factor_data,
#                                                           period='1D',
#                                                           capital=None,
#                                                           long_short=False,
#                                                           group_neutral=True,
#                                                           equal_weight=False,
#                                                           quantiles=None,
#                                                           groups=None,
#                                                           benchmark_period='1D')
factor_data
