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
# Imports
import logging
import talib as ta
import numpy as np
import pandas as pd
from time import sleep
from bars import EventDrivenBars
from connection import Client

# logging init
logging.basicConfig(
    filename='error.log',
    level=logging.WARNING,
    format='%(asctime)s:%(levelname)s:%(message)s')

# setup the connection with the API
client = Client()
conn = client.connect()
api = client.api()


class TrendFollowing:
    """
    A class for the trend-following strategy.
    """

    def __init__(
            self,
            symbol: str,
            bar_type: str,
            TP: int = 2,
            SL: int = 1,
            qty: int = 1,
            window_size: int = 22):
        """
        :param symbol : (str) the asset symbol for the strategy.
        :param bar_type : (str) the type of the alternative bars.
        :param TP : (int) the take-profit multiple.
        :param SL : (int) the stop-loss multiple.
        :param qty : (int) the number quantities to buy and sell.
        :param window_size : (int) the lookback window for the Bollinger Band.
        """
        # Initialize model parameters like TP, SL, thresholds etc.
        self.TP = TP  # times the current volatility.
        self.SL = SL  # times the current volatility.
        self.window = window_size  # window size for bollinger bands
        self.symbol = symbol  # ticker symbol for the asset
        self.bar_type = bar_type  # bar_type for the strategy
        # a flag to know if the strategy is in a bar collecting mode
        self.collection_mode = True
        self.active_trade = False  # to know if any active trade is present
        self.qty = qty  # quantity to trade (buy or sell)
        self.open_order = None  # to know if any open orders exists
        self.sl = None  # stop-loss of current position
        self.tp = None  # take-profit of current position
        self.prices = pd.Series()
        # check if historical data exists
        if self.read_data():
            self.collection_mode = False
        else:
            print(f'on collection mode for {symbol}')

    def read_data(self):
        """
        A function to read the historical bar data.
        """
        try:
            df = pd.read_csv(
                f'data/{self.bar_type}.csv',
                index_col=[0],
                parse_dates=[0],
                usecols=[
                    'timestamp',
                    'symbol',
                    'close'])
            # the length of minimum data will be the window size +1 of BB
            if not df.empty:
                prices = df[df['symbol'] == self.symbol]['close']
                if len(prices) > self.window:
                    self.prices = prices[-self.window + 1:]
                    del df
                    return True

        except FileNotFoundError as e:
            pass

        return False

    def get_volatility(self, frequency: str = '1H'):
        """
        A function to get hourly volatility if enough data exists.
        Else will output minimum window_size volatility. The volatility
        will be used to set the TP an SL of a position.
        """
        ret = self.prices.pct_change()[1:]
        # get hourly volatility
        vol = ret.groupby(pd.Grouper(freq=frequency)).std()[-1]
        return vol

    def liquidate_position(self):
        # check for brackets orders are present
        self.cancel_orders()
        try:
            # close the position
            res = api.close_position(self.symbol)
            # check if filled
            status = api.get_order(res.id).status
            # reset
            self.active_trade = False
            self.sl = None
            self.tp = None
        except Exception as e:
            logging.exception(e)

    def cancel_orders(self):
        """
        A function to handle cancelation of a open order.
        """
        try:
            api.cancel_order(self.open_order.id)
            self.open_order = None
        except Exception as e:
            if e.status_code == 404:
                # order not found
                logging.exception(e)

            if e.status_code == 422:
                # the order status is not cancelable.
                logging.exception(e)
                # break

    def check_open_position(self):
        """
        Get any open position for the symbol
        if exists.
        """
        try:
            pos = api.get_position(self.symbol)
            self.active_trade = [pos.side, pos.qty]
        except Exception as e:
            if e.status_code == 404:
                # position doesn't exist in the asset
                self.active_trade = False

    def RMS(self, price: float):
        """
        If a position exists than check if take-profit or
        stop-loss is reached. It is a simple risk-management
        function.

        :param price :(float) last trade price.
        """

        self.check_open_position()
        if self.active_trade:
            # check SL  and TP
            if price <= self.sl or price >= self.tp:
                # close the position
                self.liquidate_position()

    def OMS(self, BUY: bool = False, SELL: bool = False):
        """
        An order management system that handles the orders and positions for given
        asset.

        :param BUY :(bool) If True will buy given quantity of asset at market price.
                    If a short sell position is active, it will close the short position.
        :param SELL :(bool) if True will sell given quantity of asset at market price.
                    If a long BUY position is active, it will close the long position.
        """

        # check for open position
        self.check_open_position()
        # calculate the current volatility
        vol = self.get_volatility()

        if BUY:
            # check if counter position exists
            if self.active_trade and self.active_trade[0] == 'short':
                # exit the previous short SELL position
                self.liquidate_position()
            # calculate TP and SL for BUY order
            self.tp = self.prices[-1] + (self.prices[-1] * self.TP * vol)
            self.sl = self.prices[-1] - (self.prices[-1] * self.SL * vol)
            side = 'buy'

        if SELL:
            # check if counter position exists
            if self.active_trade and self.active_trade[0] == 'long':
                # exit the previous long BUY position
                self.liquidate_position()
            # calculate TP and SL for SELL order
            self.tp = self.prices[-1] - (self.prices[-1] * self.TP * vol)
            self.sl = self.prices[-1] + (self.prices[-1] * self.SL * vol)
            side = 'sell'

        # check for time till market closing.
        clock = api.get_clock()
        closing = clock.next_close - clock.timestamp
        market_closing = round(closing.seconds / 60)

        if market_closing > 30 and (BUY or SELL):
            # no more new trades after 30 mins till market close.

            if self.open_order is not None:
                # cancel any open orders before sending a new order
                self.cancel_orders()
            # submit a simple order.
            self.open_order = api.submit_order(
                symbol=self.symbol,
                qty=self.qty,
                side=side,
                type='market',
                time_in_force='day')

    def on_bar(self, bar: dict):
        """
        This function will be called everytime a new bar is formed. It
        will calculate the entry logic using the Bollinger Bands.

        :param bar : (dict) a Alternative bar generated from EventDrivenBars class.
        """
        if self.collection_mode:
            self.prices = self.prices.append(pd.Series(
                [bar['close']], index=[pd.to_datetime(bar['timestamp'])]))
            if len(self.prices) > self.window:
                self.collection_mode = False

        if not self.collection_mode:
            # append the current bar to the prices series
            self.prices = self.prices.append(pd.Series(
                [bar['close']], index=[pd.to_datetime(bar['timestamp'])]))
            # get the BB
            UB, MB, LB = ta.BBANDS(
                self.prices, timeperiod=self.window, nbdevup=2, nbdevdn=2, matype=0)
            # check for entry conditions
            if self.prices[-2] <= UB[-1] and self.prices[-1] > UB[-1]:
                # previous price was at or below the Upper BB and current price
                # is above it.
                self.OMS(BUY=True)
                # GOING LONG
            elif self.prices[-2] >= LB[-1] and self.prices[-1] < LB[-1]:
                # previous price was at or above the Upper BB and current price
                # is below it.
                self.OMS(SELL=True)
                # GOING SHORT


def get_current_thresholds(symbol: str, bars_per_day: int, lookback: int):
    """
    Compute the dynamic threshold for a given asset symbol.
    The threshold is computed using exponentially weight average
    of daily volumes for a given decay span. The result is divided
    by 50 to yield approx. 50 bars a day.

    :param symbol : (str) asset symbol.
    :param lookback : (int) lookback window/ span.
    :param bars_per_day : (int) number bars to yield per day.
    """
    df = api.get_barset(symbol, '1D', limit=lookback).df
    thres = df[symbol]['volume'].ewm(span=lookback).mean()[-1]
    return int(thres / bars_per_day)


def get_instances(symbols: dict, bars_per_day: int = 50):
    """
    Generate instances for multiple symbols and configurations for the trend trend following
    strategy.

    :param symbols : (dict) a dictionary with keys as the asset symbols and values as a list of
                    following - [bar_type, quantity, window_size, TP, SL] all in the given order.
    :param bars_per_day : (int) number bars to yield per day.
    """
    instances = {}
    # directory to save the bars
    save_to = 'data'
    for symbol in symbols.keys():
        # create a seperate instance for each symbols
        # thresholds are generated as last 5 days exponential weighted avg. / 50.
        # why 50 ?? to  yield approx. 50 bars a day.
        bar_type = symbols[symbol][0]
        qty = symbols[symbol][1]
        TP = symbols[symbol][3]
        SL = symbols[symbol][4]
        window = symbols[symbol][2]
        # create objects of both the classes
        instances[symbol] = [
            EventDrivenBars(
                bar_type, get_current_thresholds(
                    symbol, bars_per_day, lookback=5), save_to), TrendFollowing(
                symbol, bar_type, TP, SL, qty, window)]

    return instances


def close_all():
    """
    A funtion to close all existing orders and
    positions for a account.
    """

    try:
        api.cancel_all_orders()
    except Exception as e:
        if e.status_code == 404:
            # no orders found
            logging.exception(e)
            pass

    try:
        api.close_all_positions()
    except Exception as e:
        if e.status_code == 500:
            # failed to liquidate
            logging.exception(e)
            # break
            pass


def run(assets: dict, bars_per_day: int = 50):
    """
    The main function that run the strategy.

    :param assets : (dict) a dictionary with keys as the asset symbols and values as a list of
                    following - [bar_type, quantity, window_size, TP, SL] all in the given order.
    :param bars_per_day : (int) number bars to yield per day.
    """
    # a variable that signifies if the strategy is running or not
    STRATEGY_ON = True
    clock = api.get_clock()
    if clock.is_open:
        pass
    else:
        time_to_open = clock.next_open - clock.timestamp
        print(
            f"Market is closed now going to sleep for {time_to_open.total_seconds()//60} minutes")
        sleep(time_to_open.total_seconds())

    # close any open positions or orders
    close_all()

    channels = ['trade_updates'] + ['T.' + sym.upper()
                                    for sym in assets.keys()]

    # generate instances
    instances = get_instances(assets, bars_per_day)

    @conn.on(r'T$')
    async def on_trade(conn, channel, data):
        if data.symbol in instances and data.price > 0 and data.size > 0:
            bar = instances[data.symbol][0].aggregate_bar(data)
            instances[data.symbol][1].RMS(data.price)  # check TP & SL
            if bar:
                instances[data.symbol][1].on_bar(bar)

    conn.run(channels)

    while True:
        clock = api.get_clock()
        closing = clock.next_close - clock.timestamp
        market_closing = round(closing.seconds / 60)

        if market_closing < 10 and STRATEGY_ON:
            # liquidate all positions at 10 mins to market close.
            close_all()
            STRATEGY_ON = False

        if not clock.is_open:
            # keep collecting bars till the end of the market hours
            next_market_open = clock.next_open - clock.timestamp
            sleep(next_market_open.total_seconds())
            # reseting the thresholds and created new instances
            instances = get_instances(assets)
            STRATEGY_ON = True
