"""
This script contains a simple (intraday) trend following strategy using a bollinger band.

Strategy -
1) BUY when the price crosses the Upper Band from below.
2) SELL when the price crosses the Lower Band from above.
3) Close the positions at Take Profit or Stop Loss or
when counter positions needed to be taken.
4) If we get following signal same as the previous signal then
we increase the position size.
"""
#Imports

import talib as ta
import numpy as np
import pandas as pd
from time import sleep
from .bars import EventDrivenBars
from .connection import Client

client = Client()
conn = client.connect()
api = client.api()

#Initialize the API

class TrendFollowing:
    """
    A class for the trend-following strategy.
    """
    def __init__(self, symbol:str, bar_type:str, TP:int = 2, SL:int = 1, qty:int=1, window_size:int = 22):
        """
        :param symbol : (str) the asset symbol for the strategy.
        :param bar_type : (str) the type of the alternative bars.
        :param TP : (int) the take-profit multiple.
        :param SL : (int) the stop-loss multiple.
        :param qty : (int) the number quantities to buy and sell.
        :param window_size : (int) the lookback window for the Bollinger Band.
        """
        #Initialize model parameters like TP, SL, thresholds etc.
        self.TP = 2 # times the current volatility.
        self.SL = 1 # times the current volatility.
        self.window = window_size
        self.symbol = symbol
        self.bar_type = bar_type
        self.collection_mode = True
        self.active_trade = False
        self.qty = qty
        self.orders = []

    def read_data(self):
        """
        A function to read the historical bar data.
        """
        try:
            df = pd.read_csv(f'data/{bar_type}.csv', index_col=[0],
                                parse_dates=[0], usecols=['symbol','close'])
            price = df[df.symbol == self.symbol]['close']
            #the length of minimum data will be the window size +1 of BB
            if not price.empty and len(price) > self.window:
                self.prices = price
                return True
        except:
            pass
        return False


    def get_volatility(self):
        """
        A function to get hourly volatility if enough data exists.
        Else will output minimum window_size volatility. The volatility
        will be used to set the TP an SL of a position.
        """
        ret = self.prices.pct_change()[1:]
        try:
            #get hourly volatility
            vol = ret.groupby(pd.Grouper(freq='1H')).std()[-1]
            return vol
        except:
            pass
        return ret[-self.window:].std()

    def check_orders(self, side:str):
        if len(self.orders) > 0:
            #previous orders exists
            if orders[0] == side:
                try:
                    api.cancel_by_client_order_id(order[1])
                    return True
                except:
                    return False

    def OMS(self, BUY:bool, SELL:bool):
        """
        An order management system that handles the orders and positions for given
        asset.

        :param BUY :(bool) If True will buy given quantity of asset at market price.
                    If a short sell position is active, it will close the short position.
        :param SELL :(bool) if True will sell given quantity of asset at market price.
                    If a long BUY position is active, it will close the long position.
        """
        #check for time till market closing.
        clock = api.get_clock()
    	closing = clock.next_close - clock.timestamp
    	market_closing =  round(closing.seconds/60)

        #check for open position
        try:
            pos = api.get_position(self.symbol)
            self.active_trade = [pos["side"], pos["qty"]]
        except Exception as e:
            if e.status_code == 404:
                self.active_trade = False

        #calculate the volatility
        vol = self.get_volatility()

        if BUY:
            #check if counter position exists
            if self.active_trade and self.active_trade[0]=='short':
                #exit the previous short SELL position
                api.close_position(self.symbol)
            #enter a new BUY
            tp = self.price[-1] + (self.price[-1] * self.TP * vol)
            sl = self.price[-1] - (self.price[-1] * self.SL * vol)
            side = 'buy'


        if SELL:
            #check if counter position exists
            if self.active_trade and self.active_trade[0]=='long':
                #exit the previous long BUY position
                api.close_position(self.symbol)
            #enter a new BUY
            tp = self.price[-1] - (self.price[-1] * self.TP * vol)
            sl = self.price[-1] + (self.price[-1] * self.SL * vol)
            side = 'sell'

        if market_closing > 30 :
            #no more new trades after 30 mins till market close.
            #cancel all orders before sending a new order
            api.cancel_all_orders()
            #submit a bracket order.
            api.submit_order(symbol=self.symbol, qty=self.qty, side=side,
                             type='market', time_in_force='day',
                             order_class='bracket', stop_loss=dict(stop_price=str(sl)),
                             take_profit=dict(limit_price=str(tp)))

    def on_bar(self, bar:dict):
        """
        This function will be called everytime a new bar is formed. It
        will calculate the entry logic using the Bollinger Bands.

        :param bar : (dict) a Alternative bar generated from EventDrivenBars class.
        """
        if collection_mode:
            if self.read_data:
                self.collection_mode = False
        else:
            #append the current bar to the prices series
            self.prices.append(bar.close, index=bar.timestamp)
            #get the BB
            UB, MB, LB = ta.BBANDS(self.price, timeperiod=self.window, nbdevup=2, nbdevdn=2, matype=0)
            #check for entry conditions
            if price[-2] <= UB[-1] and price[-1] > UB[-1]:
                #previous price was at or below the Upper BB and current price is above it.
                self.OMS(BUY=True)
            elif price[-2] >= LB[-1] and price[-1] < LB[-1]:
                #previous price was at or above the Upper BB and current price is below it.
                self.OMS(SELL=True)

def get_current_thresholds(symbol:str, lookback:int):
    """
    Compute the dynamic threshold for a given asset symbol.
    The threshold is computed using exponentially weight average
    of daily volumes for a given decay span. The result is divided
    by 50 to yield approx. 50 bars a day.

    :param symbol : (str) asset symbol.
    :param lookback : (int) lookback window/ span.
    """
    df = api.get_barset(symbol, '1D', limit=lookback).df
    thres = df[symbol]['volume'].ewm(span=lookback).mean()[-1]
    return int(thres/50)

def get_instances(symbols:dict):
    """
    Generate instances for multiple symbols and configurations for the trend trend following
    strategy.

    :param symbols : (dict) a dictionary with keys as the asset symbols and values as a list of
                    following - [bar_type, quantity, window_size] all in the given order.
    """
    instances = {}
    if isinstance(symbols, list):
        #multi-symbol
        for symbol in symbols.keys():
            #create a seperate instance for each symbols
            #thresholds are generated as last 5 days exponential weighted avg. // 50.
            #why 50 ?? to  yield approx. 50 bars a day.
            instances[symbol] = [EventDrivenBars(symbols[symbol][0], get_current_thresholds(symbol, lookback=5), save_to),
                                 TrendFollowing(symbol, bar_type=symbols[symbol][0], TP=2, SL=1,
                                 qty=symbols[symbol][1], window_size=symbols[symbol][2])]
    else:

        #threshold is given as a int type
        instances[symbols] = [EventDrivenBars(symbols[symbol][0], get_current_thresholds(symbol, lookback=5), save_to),
                              TrendFollowing(symbol, bar_type=symbols[symbol][0], TP=2, SL=1,
                              qty=symbols[symbol][1], window_size=symbols[symbol][2])]
    return instances

def run(symbols:dict:dict):
    """
    The main function that run the strategy.

    :param symbols : (dict) a dictionary with keys as the asset symbols and values as a list of
                    following - [bar_type, quantity, window_size] all in the given order.
    """
    clock = api.get_clock()
    if clock.is_open:
	       pass
    else:
    	time_to_open = clock.next_open - clock.timestamp
    	sleep(time_to_open.total_seconds())

    channels = ['trade_updates'] + ['T.'+sym.upper() for sym in symbols.keys()]
    #generate instances
    instances = get_instances(symbols)

    @conn.on(r'T$')
    async def on_trade(conn, channel, data):
         if data.symbol in instances and data.price > 0 and data.size > 0:
             bar = instances[data.symbol][0].aggregate_bar(data)
             if bar:
                instances[data.symbol][1].on_bar(bar)

    conn.run(channels)

    while True:

        clock = api.get_clock()
    	closing = clock.next_close - clock.timestamp
    	market_closing =  round(closing.seconds/60)

        if market_closing < 10 :
            #liquidate all positions at 10 mins to market close.
            api.close_all_positions()
			next_market_open = clock.next_open - clock.timestamp
			sleep(next_market_open.total_seconds())
            #resting the thresholds
            instances = get_instances(symbols)
