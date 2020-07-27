from bars import get_tick_bars, get_volume_bars, get_dollar_bars

symbols = ['AAPL','TSLA','AMZN']
tick_threshold = {'AAPL':1000,'TSLA':1000,'AMZN':1000}
volume_threshold = {'AAPL':50000,'TSLA':5000,'AMZN':50000}
dollar_threshold = {'AAPL':2000000,'TSLA':2000000,'AMZN':2000000}


# get_tick_bars(symbols, tick_threshold, 'sample_datasets')
# get_volume_bars(symbols, volume_threshold, 'sample_datasets')
get_dollar_bars(symbols, dollar_threshold, 'sample_datasets')
