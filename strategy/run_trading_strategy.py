from trend_following import run

#settings
#-------------------------------
#Running this strategy on two stocks : AAPL and AMZN
#with with trade quantity of 50 and 20 respectively
#both share same setting for Bollinger Bands lookback i.e. 50 bars
#and TP/SL as 2/1
symbols = {'AAPL' : ['volume_bar', 50, 15, 2, 1],
           'AMZN' : ['volume_bar', 30, 15, 2, 1]}
bars_per_day = 5000
#passing the symbols and running it.
run(symbols, bars_per_day)
