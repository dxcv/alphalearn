#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import pandas as pd
import numpy as np
import scipy as sp
import tushare as ts
from opendatatools import swindex
from dataProvider.trading_calendar import *
from utils.constants import *
from utils.tool import *

__ALL__ = [
    'index_weight',
    'sw_weight',
    'daily',
    'daily_basic'
]


class DataApi(object):
    def __init__(self):
        ts.set_token('0503684c1ca87a31116049960065adbf985e0c052adb268a2b5397dd')
        self.pro = ts.pro_api()
        self.today = datetime.datetime.now().strftime('%Y%m%d')
        self.stock_store = os.path.join(os.path.dirname(__file__), 'cache/stock_store.h5')
        log_name = os.path.join(os.path.dirname(__file__), "log_dir/analysis_%s.log" % self.today)
        get_logger(log_name)

    def trading_day(self, start_date='', end_date=''):
        res = self.pro.trade_cal(exchange_id='SSE', start_date=start_date, end_date=end_date, is_open='1')[
            'cal_date'].tolist()
        return res

    def delete_quote(self, dir=None):
        # 每日重新更新行情缓存
        if dir is None:
            cache_dir = os.path.join(os.path.dirname(__file__), "cache/")
            f_list = os.listdir(cache_dir)
            #   删除所有csv的缓存文件
            for fileNAME in f_list:
                if os.path.splitext(fileNAME)[1] == '.h5':
                    os.remove(os.path.join(cache_dir, fileNAME))
            logging.info('remove all data')
        else:
            os.remove(os.path.join(self.dataProvider_dir, dir))
            logging.info('remove %s', dir)

    def _index_weight(self):
        #   输入列表['000300.SH','399905.SZ','000016.SH']获取对应指数成分股
        hs300 = ts.get_hs300s()
        zz500 = ts.get_zz500s()
        sz50 = ts.get_sz50s()
        hs300['index_code'] = '000300.SH'
        zz500['index_code'] = '399905.SZ'
        sz50['index_code'] = '000016.SH'
        # 汇总数据
        res = pd.concat([hs300, zz500, sz50], ignore_index=True, sort=False)
        #   标准化code
        res['code'] = [i + '.SH' if i[0] == '6' else i + '.SZ' for i in res['code']]
        res['update_time'] = self.today
        return res

    def index_weight(self, index_code=None):
        #   输入列表['000300.SH','399905.SZ','000016.SH']获取对应指数成分股
        try:
            data = pd.read_hdf(self.stock_store, 'index_weight')
            if data['update_time'].max() != self.today:
                data = self._index_weight()
                data.to_hdf(self.stock_store, 'index_weight', complevel=9)
        except Exception as e:
            data = self._index_weight()
            data.to_hdf(self.stock_store, 'index_weight', complevel=9)
        if index_code is None:
            index_code = ['000300.SH', '399905.SZ', '000016.SH']
        res = data[data['index_code'].isin(index_code)]
        return res

    def _stock_bar(self, start_date=None, end_date=None, field='daily'):
        data = pd.DataFrame()
        trading_day_list = get_trading_day_range(start_date, end_date)
        for day in trading_day_list:
            temp = da.pro.query(field, trade_date=day)
            data = data.append(temp, ignore_index=True)
            logging.info('stock_%s:%s', field, day)
        res = data.drop_duplicates(['ts_code', 'trade_date'])
        res.rename(columns={'ts_code': 'code'}, inplace=True)
        return res

    def stock_bar(self, code=None, start_date=None, end_date=None, field='daily'):
        #   如不输入code则返回所有股票行情，不输入起始时间则返回前一交易日行情
        lastTradingDay = get_pre_trading_day()
        if start_date is None:
            start_date = lastTradingDay
        if end_date is None or end_date >= lastTradingDay:
            end_date = lastTradingDay
        try:
            data = pd.read_hdf(self.stock_store, field)
            if data['trade_date'].max() < end_date:
                new_data = self._stock_bar(data['trade_date'].max(), lastTradingDay, field)
                data = data.append(new_data, ignore_index=True)
                data = data.drop_duplicates(['code', 'trade_date'])
                data.to_hdf(self.stock_store, field, complevel=9)
        except Exception as e:
            data = self._stock_bar(MIN_BEGIN_DAY, lastTradingDay, field)
            data.to_hdf(self.stock_store, field, complevel=9)
        res = data.loc[(data['trade_date'] >= start_date) & (data['trade_date'] <= end_date)]
        if code is None:
            return res
        else:
            return res.loc[res['code'].isin(code)]

    def _sw_weight(self):
        res = pd.DataFrame()
        #   获取申万一级行业成份股
        for index_code, index_name in INDUSTRY_SW.items():
            temp = swindex.get_index_cons(index_code)[0]
            temp.rename(columns={'index_code': 'code', 'index_name': 'name'}, inplace=True)
            temp['index_code'] = index_code + '.SI'
            temp['index_name'] = index_name
            res = res.append(temp, ignore_index=True)
        res['code'] = [i + '.SH' if i[0] == '6' else i + '.SZ' for i in res['code']]
        res['update_time'] = self.today
        return res

    def sw_weight(self):
        #   输入列表['000300.SH','399905.SZ','000016.SH']获取对应指数成分股
        try:
            data = pd.read_hdf(self.stock_store, 'sw_weight')
            if data['update_time'].max() != self.today:
                data = self._sw_weight()
                data.to_hdf(self.stock_store, 'sw_weight', complevel=9)
        except Exception as e:
            data = self._sw_weight()
            data.to_hdf(self.stock_store, 'sw_weight', complevel=9)
        return data


da = DataApi()
if __name__ == '__main__':
    da = DataApi()
    weight = da.index_weight()
    sw_weight = da.sw_weight()
    stock_quote = da.stock_bar(weight['code'].unique())
    stock_basic = da.stock_bar(weight['code'].unique(), field='daily_basic')
    weight
