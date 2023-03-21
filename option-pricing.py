# -*- coding: utf-8 -*-
"""
Created on Fri Mar 17 09:40:36 2023

@author: Quant Galore
"""

from scipy.stats import norm

import math
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
import numpy as np
import pytz
import tda 
import json
import time

from datetime import datetime, timedelta
from yahoo_fin import stock_info as si
from selenium import webdriver


def round_to_multiple(number, multiple):
    return multiple * round(number / multiple)

def black_scholes(S, K, r, t, vol, option_type):
    d1 = (math.log(S / K) + (r + 0.5 * vol ** 2) * t) / (vol * math.sqrt(t))
    d2 = d1 - vol * math.sqrt(t)
    if option_type == 'call':
        price = S * norm.cdf(d1) - K * math.exp(-r * t) * norm.cdf(d2)
    elif option_type == 'put':
        price = K * math.exp(-r * t) * norm.cdf(-d2) - S * norm.cdf(-d1)
    else:
        raise ValueError('Invalid option type')
    return price

def d1(S, K, r, q, T, sigma):
    return (math.log(S / K) + (r - q + sigma**2/2) * T) / (sigma * math.sqrt(T))

def d2(S, K, r, q, T, sigma):
    return d1(S, K, r, q, T, sigma) - sigma * math.sqrt(T)

def implied_volatility(S, K, r, q, t, option_price, option_type):
    MAX_ITERATIONS = 100
    PRECISION = 1.0e-5
    
    sigma = 0.5
    for i in range(0, MAX_ITERATIONS):
        
        vol = sigma
        
        price = black_scholes(S, K, r, t, vol, option_type)
        
        vega = S * math.exp(-q * t) * norm.pdf(d1(S, K, r, q, t, sigma)) * math.sqrt(t)
        
        diff = option_price - price
        
        if (abs(diff) < PRECISION):
            return sigma
        
        sigma = sigma + diff/vega
        
    return sigma

def date_to_days(date):
    
    date = pd.to_datetime(date)
    time_to_maturity = date - datetime.today()
    total_seconds = time_to_maturity.total_seconds()
    
    days_to_maturity = total_seconds / (24 * 3600)
    
    return days_to_maturity

''' API authentication '''

API_KEY = 'yours@AMER.OAUTHAP'
TOKEN_PATH = 'C:\\yours\\tda.txt'
REDIRECT_URL = 'http://localhost'

# Options = webdriver.ChromeOptions()
# Options.binary_location = 'C:\\Users\\Local User\\Desktop\\Google\\Chrome\\Application\\chrome.exe'
# Chrome_driver_binary = 'C:\\Users\\Local User\\Documents\\Code\\chromedriver.exe'
# Driver = webdriver.Chrome(Chrome_driver_binary, chrome_options=Options)

# Connect = tda.auth.client_from_login_flow(Driver, API_KEY, REDIRECT_URL, TOKEN_PATH, redirect_wait_time_seconds=0.1, max_waits=3000, asyncio=False, token_write_func=None, enforce_enums=True)
Connect2 = tda.auth.client_from_token_file(TOKEN_PATH, API_KEY, asyncio=False, enforce_enums=True)

'''
S = 100   # Current stock price
K = 110   # Strike price
t = 30/365   # Time to expiration (in years)
r = 0.05   # Risk-free interest rate
vol = 0.3   # Implied volatility (estimated from market data)
q = 0.01 dividend yield
'''

# load stock data

Stock_1 = json.loads(Connect2.get_quotes("$SPX.X").content)['$SPX.X']
Stock_1_Object = yf.Ticker("SPY")
VIX = json.loads(Connect2.get_quotes("$VIX.X").content)['$VIX.X']

# assign underlying parameters

S = Stock_1['lastPrice']
days_to_maturity = date_to_days("2023-03-17T15:00:00")
t = days_to_maturity/365
r = 0.045
q = Stock_1_Object.dividends.iloc[-1] / Stock_1_Object.fast_info['last_price']


# we are modeling 0dte options, so increase theo vol
vol = VIX['lastPrice'] / 100 * 2

increment = 10

Option_Chain = pd.DataFrame(columns=['call_price', 'call_implied_vol', 'strike', 'put_price','put_implied_vol'])

# calculate option chain -10/+10 % from the current price

for strike in np.arange(round_to_multiple(S*.85,increment), round_to_multiple(S*1.15, increment), increment):
    
    K = strike
    
    #determine how far away the stock price is from the strike
    
    moneyness = abs(S - K) / S
    
    # first calculate the price via the black-scholes model using the VIX*2 as the volatility input
    
    call_price = black_scholes(S, K, r, t, vol, option_type = 'call')
    call_implied_vol = implied_volatility(S, K, r, q, t, call_price, option_type = 'call')
    
    # take the back-solved vol and multiply it by 1 - sqrt(moneyness), with that new vol, re-price the option
    
    call_implied_vol = call_implied_vol * (1+(1 - (np.sqrt(moneyness))))
    call_price = black_scholes(S, K, r, t, vol=call_implied_vol, option_type = 'call')
    
    put_price = black_scholes(S, K, r, t, vol, option_type = 'put')
    put_implied_vol = implied_volatility(S, K, r, q, t, put_price, option_type = 'put')
    
    put_implied_vol = put_implied_vol * (1+(1 - (np.sqrt(moneyness))))
    put_price = black_scholes(S, K, r, t, vol=put_implied_vol, option_type = 'put')
    
    Option_Chain = pd.concat([Option_Chain, pd.DataFrame([{'call_price': call_price, 'call_implied_vol': call_implied_vol, 'strike': K,'put_price': put_price, 'put_implied_vol': put_implied_vol}])])
    
    
# derive the theoretical per-day volatility
Daily_Volatility = vol / np.sqrt(252)

# derive the theoretical underlying volatilty for the lifetime of the optione
Period_Volatility = Daily_Volatility * np.sqrt(days_to_maturity)


# create stock-price bounds which will serve as the basis of what strikes are selected
Implied_Expiration_Low = S - (S*Period_Volatility)
Implied_Expiration_High = S + (S*Period_Volatility)

price_adjustment = .50

# strike assembly

Short_Call = Option_Chain['call_price'][Option_Chain['strike'] == round_to_multiple(Implied_Expiration_High,increment) + increment] * price_adjustment
Short_Call_Strike = round_to_multiple(Implied_Expiration_High,increment) + increment

Long_Call = Option_Chain['call_price'][Option_Chain['strike'] == round_to_multiple(Implied_Expiration_High,increment) + increment*2] * price_adjustment
Long_Call_Strike = round_to_multiple(Implied_Expiration_High,increment) + increment*2

Short_Put = Option_Chain['put_price'][Option_Chain['strike'] == round_to_multiple(Implied_Expiration_Low,increment) - increment] * price_adjustment
Short_Put_Strike = round_to_multiple(Implied_Expiration_Low,increment) - increment

Long_Put = Option_Chain['put_price'][Option_Chain['strike'] == round_to_multiple(Implied_Expiration_Low,increment) - increment*2] * price_adjustment
Long_Put_Strike = round_to_multiple(Implied_Expiration_Low,increment) - increment*2

## calculate theo credit and risk

Theo_Call_Spread_Credit = (Short_Call.iloc[0] - Long_Call.iloc[0])
Theo_Call_Spread_Risk = abs(Short_Call_Strike - Long_Call_Strike) - Theo_Call_Spread_Credit

Theo_Put_Spread_Credit = Short_Put.iloc[0] - Long_Put.iloc[0]
Theo_Put_Spread_Risk = abs(Short_Put_Strike - Long_Put_Strike) - Theo_Put_Spread_Credit

Theo_Condor_Credit = Theo_Call_Spread_Credit + Theo_Put_Spread_Credit
Theo_Condor_Risk = ((abs(Short_Call_Strike - Long_Call_Strike) + abs(Short_Put_Strike - Long_Put_Strike)) / 2) - Theo_Condor_Credit

Theo_Call_Spread_Risk_Reward = Theo_Call_Spread_Credit / Theo_Call_Spread_Risk
Theo_Put_Spread_Risk_Reward = Theo_Put_Spread_Credit / Theo_Put_Spread_Risk
Theo_Condo_Risk_Reward = Theo_Condor_Credit / Theo_Condor_Risk

# output

print(f"\n-{Short_Call_Strike}/+{Long_Call_Strike} Call Spread for {round(Theo_Call_Spread_Risk_Reward*100,2)}%, Collateral: ${round(Theo_Call_Spread_Risk * 100, 2)}, Credit: ${round(Theo_Call_Spread_Credit*100,2)}")
print(f"-{Short_Put_Strike}/+{Long_Put_Strike} Put Spread for {round(Theo_Put_Spread_Risk_Reward*100,2)}%, Collateral: ${round(Theo_Put_Spread_Risk * 100, 2)}, Credit: ${round(Theo_Put_Spread_Credit*100,2)}")
print(f"-{Short_Put_Strike}/+{Long_Put_Strike} & -{Short_Call_Strike}/+{Long_Call_Strike} Iron Condor for {round(Theo_Condo_Risk_Reward*100,2)}%, Collateral: ${round(Theo_Condor_Risk * 100, 2)}, Credit: ${round(Theo_Condor_Credit*100,2)}")
print(f"Implied Move: {round(Period_Volatility*100,2)}%")

# for the remainder of the trading session, re-evaluate the spot price and identify probability

for minute in range(0, 3600):
    
    Spot_Price = json.loads(Connect2.get_quotes(ticker).content)[ticker]['lastPrice']
    
    Percent_Movement = (Spot_Price - S) / S
    
    Vol_Move_Covered = Percent_Movement / Period_Volatility
    
    if Vol_Move_Covered < 0:
        print(f"\nThe put leg has a {round(abs(Vol_Move_Covered)*100,2)}% probability of expiring ITM")    
    if Vol_Move_Covered > 0:
        print(f"\nThe call leg has a {round(Vol_Move_Covered*100,2)}% probability of expiring ITM")    
    if Vol_Move_Covered == 0:
        print(f"Both legs have an equal {round(Vol_Move_Covered*100,2)}% probability of expiring ITM")
    
    time.sleep(10)


    
    
