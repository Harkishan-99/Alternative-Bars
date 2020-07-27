"""
This script will server backends for all Alternative Bars
"""
import os
from typing import Union

import asyncio
import time
import numpy as np
import pandas as pd

from connection import Client

conn = Client().connect()

class EventDrivenBars:

    def __init__(self, bar_type:str, threshold:int, savefile:str):
        """
        :param bar_type :(str) Type of bar to form. Either "tick_bar", "volume_bar" or "dollar_bar"
        :param threshold :(int) threshold value for sampling.
        :param savefile :(str) the path to store the bars as CSV.
        """
        #initialize the threshold
        self.threshold = threshold
        #a variable to store the previous trade price
        self.prev_price = None
        #store price volume and trade_side
        self.price, self.volume, self.trade_side = [], [], []
        #aggregated values count (cumulative metrics)
        self.cum_count = {'cum_tick': 0,'cum_volume' : 0 ,'cum_dollar_value': 0,
                          'cum_buy_tick' : 0, 'cum_buy_volume' : 0, 'cum_buy_dollar_value' : 0}
        #setting tracking metric
        if bar_type == 'dollar_bar':
            self.stat = 'cum_dollar_value'
        elif bar_type == 'volume_bar':
            self.stat = 'cum_volume'
        elif bar_type == 'tick_bar':
            self.stat = 'cum_tick'
        else:
            raise ValueError(f'{bar_type} is not a valid bar. Please enter either "dollar_bar","volume_bar" or "tick_bar"')
        #flag to indicate header of the csv file
        self.header = True
        #create a save file
        savefile = savefile + '/' + bar_type
        if not os.path.exists(savefile):
            os.makedirs(savefile)
        self.save = savefile + '/' + str(int(time.time())) + '.csv'

    def _reset_cache(self):
        """
        A function to reset the aggregated values and variables.
        """
        self.cum_count = {'cum_tick': 0,'cum_volume' : 0 ,'cum_dollar_value': 0,
                          'cum_buy_tick' : 0, 'cum_buy_volume' : 0, 'cum_buy_dollar_value' : 0}
        self.price, self.volume, self.trade_side = [], [], []

    def _check_tick_sign(self, price:float):
        """
        A function to calculate the side of the trade based on tick rule.

        :param price :(float) current price.
        """
        if self.prev_price is None:
            self.prev_price = price
            return 0
        sign = np.sign(price - self.prev_price)
        self.prev_price = price
        return sign

    def save_bar(self, bar:dict):
        """
        Append the bars to the CSV using pandas.

        :param bar :(dict)  the dictionary of a bar containing the aggregated values.
        """
        #save the bars to csv
        pd.DataFrame(bar).to_csv(self.save, header=self.header, index=False, mode='a')
        self.header = False

    def aggregate_bar(self, data):
        """
        Aggregate with the arrival of new trades data

        :param data : A data object containing the ticks of a single timestamp or tick.
        """
        self.cum_count['cum_tick'] += 1
        self.cum_count['cum_volume'] += data.size
        self.cum_count['cum_dollar_value'] += data.price*data.size
        self.price.append(data.price)
        self.volume.append(data.size)
        #check the side of the trade
        tick_sign = self._check_tick_sign(data.price)
        if tick_sign > 0:
            self.cum_count['cum_buy_tick'] += 1
            self.cum_count['cum_buy_volume'] += data.size
            self.cum_count['cum_buy_dollar_value'] += data.price*data.size

        if self.cum_count[self.stat] >= self.threshold:
            vwap = np.multiply(self.price, self.volume).sum() / sum(self.volume) #getting the vwap
            bar = {'timestamp': [str(data.timestamp)] ,'open':[self.price[0]], 'high':[max(self.price)],
                   'low': [min(self.price)], 'close': [data.price], 'vwap' : vwap}
            bar.update(self.cum_count)
            self.save_bar(bar)
            bar.update({"symbol" : data.symbol}) #to display the bar
            print(bar)
            self._reset_cache()
            return bar
        return False

def get_bars(bar_type:str, symbols:Union[str, list], threshold:Union[int, dict], save_to:str):
    """
    Get the realtime bar using the Streaming API.

    :param bar_type :(str) Type of bar to form. Either "tick_bar", "volume_bar" or "dollar_bar".
    :param symbols :(str or list) a ticker symbol or a list of ticker symbols to generate the bars.
    :param threshold :(int or dict) threshold for bar formation or sampling. A dictionary must be
                      given if bars to generated for multiple symbols. The dictionary keys are
                      ticker symbols and values are the thresholds respectively.
    :param save_to :(str) the path to store the bars.
    """
    instances = {} #to initiate instances of
    if isinstance(symbols, list):
        #multi-symbol
        channels = ['trade_updates'] + ['T.'+sym.upper() for sym in symbols]
        for symbol in symbols:
            save = save_to + f'/{symbol}'
            instances[symbol] = EventDrivenBars(bar_type, threshold[symbol], save)
    else:
        #single symbols
        channels = ['trade_updates', f'T.{symbols.upper()}']
        save = save_to + f'/{symbols}'
        if isinstance(threshold, int):
            instances[symbols] = EventDrivenBars(bar_type, threshold, save)
        else:
            instances[symbols] = EventDrivenBars(bar_type, threshold[symbol], save)

    @conn.on(r'T$')
    async def on_trade(conn, channel, data):
         if data.symbol in instances and data.price > 0 and data.size > 0:
             bar = instances[data.symbol].aggregate_bar(data)

    conn.run(channels)

def get_tick_bars(symbols:Union[str, list], threshold:Union[int, dict], save_to:str):
    """
    Get RealTime Tick Bars.

    :param symbols :(str or list) a ticker symbol or a list of ticker symbols to generate the bars.
    :param threshold :(int or dict) threshold for bar formation or sampling. A dictionary must be
                      given if bars to generated for multiple symbols. The dictionary keys are
                      ticker symbols and values are the thresholds respectively.
    :param save_to :(str) the path to store the bars.
    """
    get_bars('tick_bar', symbols, threshold, save_to)

def get_volume_bars(symbols:Union[str, list], threshold:Union[int, dict], save_to:str):
        """
        Get RealTime Volume Bars.

        :param symbols :(str or list) a ticker symbol or a list of ticker symbols to generate the bars.
        :param threshold :(int or dict) threshold for bar formation or sampling. A dictionary must be
                          given if bars to generated for multiple symbols. The dictionary keys are
                          ticker symbols and values are the thresholds respectively.
        :param save_to :(str) the path to store the bars.
        """
        get_bars('volume_bar', symbols, threshold, save_to)

def get_dollar_bars(symbols:Union[str, list], threshold:Union[int, dict], save_to:str):
        """
        Get RealTime Dollar Bars.

        :param symbols :(str or list) a ticker symbol or a list of ticker symbols to generate the bars.
        :param threshold :(int or dict) threshold for bar formation or sampling. A dictionary must be
                          given if bars to generated for multiple symbols. The dictionary keys are
                          ticker symbols and values are the thresholds respectively.
        :param save_to :(str) the path to store the bars.
        """
        get_bars('dollar_bar', symbols, threshold, save_to)
