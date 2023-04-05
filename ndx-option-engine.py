# -*- coding: utf-8 -*-
"""
Created on Mon Apr  3 18:14:31 2023

@author: Quant Galore
"""

import math
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
import numpy as np
import pytz
import tda 
import json
import time

from scipy.stats import norm
from datetime import datetime, timedelta
from yahoo_fin import stock_info as si
from selenium import webdriver
from alpaca.data import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from pandas.tseries.offsets import BDay

def round_to_multiple(number, multiple):
    return multiple * round(number / multiple)


def date_to_days(date):
    
    date = pd.to_datetime(date)
    time_to_maturity = date - datetime.today()
    total_seconds = time_to_maturity.total_seconds()
    
    days_to_maturity = total_seconds / (24 * 3600)
    
    return days_to_maturity

# API Connections

API_KEY = 'your api key'
TOKEN_PATH = 'your api key path'
REDIRECT_URL = 'http://localhost'

# Options = webdriver.ChromeOptions()
# Options.binary_location = 'chrome.exe'
# Chrome_driver_binary = 'chromedriver.exe'
# Driver = webdriver.Chrome(Chrome_driver_binary, chrome_options=Options)

# Connect = tda.auth.client_from_login_flow(Driver, API_KEY, REDIRECT_URL, TOKEN_PATH, redirect_wait_time_seconds=0.1, max_waits=3000, asyncio=False, token_write_func=None, enforce_enums=True)
Connect2 = tda.auth.client_from_token_file(TOKEN_PATH, API_KEY, asyncio=False, enforce_enums=True)

Alpaca_API_KEY = ''
Alpaca_SECRET_KEY = ''

Stock_Client = StockHistoricalDataClient(Alpaca_API_KEY,  Alpaca_SECRET_KEY)

#


def Get_Strikes(ticker, volatility_ticker, expiration, vol_adjustment, increment):
    
    days_to_maturity = date_to_days(expiration)
    
    if days_to_maturity < 0:
        
        days_to_maturity = 0.29
        print("Adjusted time to maturity to 7-hours.")
    
    Stock_1 = json.loads(Connect2.get_quotes(ticker).content)[ticker]
    Volatility_Index = json.loads(Connect2.get_quotes(volatility_ticker).content)[volatility_ticker]['lastPrice'] / 100 

    vol = Volatility_Index * vol_adjustment
    
    # derive the theoretical per-day volatility
    Daily_Volatility = vol / np.sqrt(252)
    
    # derive the theoretical underlying volatilty for the lifetime of the optione
    Period_Volatility = (Daily_Volatility * np.sqrt(days_to_maturity))
    
    # create stock-price bounds which will serve as the basis of what strikes are selected
    Implied_Expiration_Low = Stock_1['lastPrice'] - (Stock_1['lastPrice']*Period_Volatility)
    Implied_Expiration_High = Stock_1['lastPrice'] + (Stock_1['lastPrice']*Period_Volatility)
    
    # strike assembly
    
    Short_Call_Strike = round_to_multiple(Implied_Expiration_High,increment) + increment
    Long_Call_Strike = round_to_multiple(Implied_Expiration_High,increment) + increment*2
    
    Short_Put_Strike = round_to_multiple(Implied_Expiration_Low,increment) - increment
    Long_Put_Strike = round_to_multiple(Implied_Expiration_Low,increment) - increment*2
    
    # output
    
    print(f"\n-{Short_Call_Strike}/+{Long_Call_Strike} Call Spread")
    print(f"-{Short_Put_Strike}/+{Long_Put_Strike} Put Spread")
    print(f"-{Short_Put_Strike}/+{Long_Put_Strike} & -{Short_Call_Strike}/+{Long_Call_Strike} Iron Condor")
    print(f"Implied Move: {round(Period_Volatility*100,2)}%")
    
    
Get_Strikes(ticker = "$NDX.X", volatility_ticker = "$VXN.X",
            expiration = f"{datetime.today().strftime('%Y-%m-%d')}T15:00:00",
            vol_adjustment = 1.5, increment = 10)
