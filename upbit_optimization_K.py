# 자료불러오기
import time
import pyupbit
import datetime
import schedule
import pandas as pd
from itertools import product
import numpy as np

access = ""
secret = ""

df = pyupbit.get_ohlcv("KRW-DOGE", interval="minute720", count = 760)
df['range'] = df['high'] - df['low']
df['10_MA'] = df['close'].rolling(window=10).mean()
df['20_MA'] = df['close'].rolling(window=20).mean()
df = df.drop(df.index[:20])

def volatility_breakout_buy_strategy(df, k):
   df['target'] = df['open'] + df['range'] * k
   fee = 0.05
   df['ret'] = np.where(df['close'] > df['10_MA'],
                         np.where(df['high'] > df['target'], df['close'] / df['10_MA'] - fee, 1),
                         1)
   df['cum_ret'] = df['ret'].cumprod()
   return df

def optimize_k(df):
    k_values = np.linspace(0.01, 1, 100)  # 0.01부터 1까지 0.01 간격의 k 값 생성
    results = []
    for k in k_values:
        df_copy = df.copy()
        result = volatility_breakout_buy_strategy(df_copy, k)
        # k 값에 따른 최종 누적 수익률을 결과 리스트에 추가
        results.append((k, result['cum_ret'].iloc[-1]))

    # 결과를 데이터프레임으로 변환하고, 최대 누적 수익률을 가진 k 값을 찾아 반환
    results_df = pd.DataFrame(results, columns=['k', 'cum_ret'])
    optimal_k = results_df.loc[results_df['cum_ret'].idxmax(), 'k']

    return optimal_k
optimal_k = optimize_k(df)

def get_target_price(ticker, optimal_k):
    target_price = df.iloc[-1]['open'] + df.iloc[-1]['range'] * optimal_k
    return target_price

def get_ma10(ticker):
    """10일 이동 평균선 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=10)
    ma10 = df['close'].rolling(10).mean().iloc[-1]
    return ma10

def get_start_time(ticker):
    """시작 시점"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=1)
    start_time = df.index[0]
    return start_time

def get_balance(ticker):
    """잔고 조회"""
    upbit = pyupbit.Upbit(access, secret)
    balances = pyupbit.Upbit.get_balances()
    for b in balances:
        if b['currency'] == ticker:
            if b['balance'] is not None:
                return float(b['balance'])
            else:
                return 0
    return 0

def get_current_price(ticker):
    """현재가 조회"""
    return pyupbit.get_orderbook(ticker=ticker)["orderbook_units"][0]["ask_price"]

upbit = pyupbit.Upbit(access, secret)
print("autotrade start")

while True:
    try:
        now = datetime.datetime.now()
        start_time = get_start_time("KRW-DOGE")
        end_time = start_time + datetime.timedelta(days=1)

        if start_time < now < end_time - datetime.timedelta(seconds=10):
            target_price = get_target_price("KRW-DOGE", optimal_k)
            ma10 = get_ma10("KRW-DOGE")
            current_price = get_current_price("KRW-DOGE")
            if target_price < current_price and ma10 < current_price:
                krw = get_balance("KRW")
                if krw > 5000:
                    upbit.buy_market_order("KRW-DOGE", krw*0.9995)
        else:
            btc = get_balance("KRW-DOGE")
            if btc > 50:
                upbit.sell_market_order("KRW-DOGE", btc*0.9995)
        time.sleep(1)
    except Exception as e:
        print(e)
        time.sleep(1)
