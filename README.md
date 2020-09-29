# Alternative-Bars
Generate Alternative Bars in real-time leveraging Alpaca API. User can generate bars like tick bars, volume bars and dollar bars.

This project was inspired by the book [Advances in Financial Machine Learning](https://www.amazon.co.uk/Advances-Financial-Machine-Learning-Marcos/dp/1119482089).

## Installation
The algorithm was tested on the Alpaca Trade API version mentioned the requirements file and is considered as the stable version for this project.

```bash

pip install -r requirements.txt
```

For running the trend-following strategy user need have [ta-lib](https://mrjbq7.github.io/ta-lib/doc_index.html) a python package for technical indicators. If pip
install fails user can refer this [blog post](https://blog.quantinsti.com/install-ta-lib-python/) to install TA-Lib.

## Usage

To generate Alternative user first need to have a Alpaca API either from a Paper Trading account or a Brokerage account. If you don't have one you can open a paper trade account  for free by visiting [Alpaca.market]([alpaca.market) and signing up.

### 1) Setting up the config file

User first need to set-up the [config file](https://github.com/Harkishan-99/Alternative-Bars/blob/master/config.cfg) with there Alpaca API credentials.

```python
[alpaca]
api_key = "enter your api key here without quotes"
api_secret = "enter your api secret here without quotes"
base_url = https://paper-api.alpaca.markets
```

### 2) Getting Bars

```python
from bars import get_tick_bars, get_volume_bars, get_dollar_bars

#assets for receiving the event-driven bars
symbols = ['AAPL','TSLA','AMZN']
#setting static threshold for individual stocks for different bars
tick_bar_threshold = {'AAPL':1000,'TSLA':1000,'AMZN':1000}
volume_bar_threshold = {'AAPL':50000,'TSLA':5000,'AMZN':50000}
dollar_bar_threshold = {'AAPL':2000000,'TSLA':2000000,'AMZN':2000000}

#setup for receiving tick bars for given thresholds
get_tick_bars(symbols, tick_bar_threshold, 'sample_datasets')
#setup for receiving volume bars for given thresholds
get_volume_bars(symbols, volume_bar_threshold, 'sample_datasets')
#setup for receiving tdollar bars for given thresholds
get_dollar_bars(symbols, dollar_bar_threshold, 'sample_datasets')
```

### 3) Trading Strategy

To run the strategy user is need to initialize the algorithm with assets dictionary and a sampling frequency for Alternative Bars.
The assets dictionary must have a list with values as bar_type, quantity to trade, bollinger bands window size, Take Profit and Stop-Loss, respectively
as values and assets symbol as key. These are also the parameters that can be tweaked. The ```bars_per_day ``` variable is to control the bar size.

```python
from trend_following import run

#settings
#-------------------------------
#Running this strategy on two stocks : AAPL and AMZN
#with with trade quantity of 50 and 30 respectively
#both share same setting for Bollinger Bands lookback i.e. 15 bars
#and TP/SL as 2/1
symbols = {'AAPL' : ['volume_bar', 50, 15, 2, 1],
           'AMZN' : ['volume_bar', 30, 15, 2, 1]}
bars_per_day = 50 #sampling frequency i.e. number of bars per day
#here we aiming to achieve approx. 50 bars per day
#passing the symbols and running it.
run(symbols, bars_per_day)
```

### Disclaimer
The trading strategy discussed here is for educational purpose only doesn't guarantee to make profit. Trading involves a high risk of losing money.
Use the code provided here at your own risk. The author and AlpacaDB, Inc. are not responsible for your trading results i.e. any profit or loss caused
by the algorithm.
A user is advised to run the code on paper trading account only to understand the risk involved.
