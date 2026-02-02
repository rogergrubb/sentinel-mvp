"""technical.py
Simple technical indicators: SMA, RSI, velocity
"""
from datetime import datetime, timezone, timedelta

def sma(prices, period):
    if not prices or period<=0: return None
    if len(prices) < period: return sum(prices)/len(prices)
    return sum(prices[-period:])/period

def rsi(prices, period=14):
    if not prices or len(prices)<2:
        return None
    gains = []
    losses = []
    for i in range(1,len(prices)):
        diff = prices[i]-prices[i-1]
        if diff>0: gains.append(diff)
        else: losses.append(-diff)
    avg_gain = sum(gains)/period if len(gains)>=period else (sum(gains)/len(gains) if gains else 0)
    avg_loss = sum(losses)/period if len(losses)>=period else (sum(losses)/len(losses) if losses else 0)
    if avg_loss==0:
        return 100.0 if avg_gain>0 else 50.0
    rs = avg_gain/avg_loss
    return 100 - (100/(1+rs))

def price_velocity(prices, minutes_window=10):
    # prices: list of (time_iso, price) sorted ascending
    if not prices or len(prices)<2: return {'price_pct_per_min':0,'mentions_per_min':0}
    # compute pct change over last window (assume prices spaced irregular)
    end_price = prices[-1][1]
    # find timestamp window minutes ago
    end_time = datetime.fromisoformat(prices[-1][0].replace('Z','+00:00'))
    start_time = end_time - timedelta(minutes=minutes_window)
    start_price = None
    count = 0
    for t,p in reversed(prices):
        tt = datetime.fromisoformat(t.replace('Z','+00:00'))
        if tt <= start_time:
            start_price = p
            break
        count += 1
    if not start_price and len(prices)>1:
        start_price = prices[-2][1]
    if not start_price:
        return {'price_pct_per_min':0,'mentions_per_min':0}
    pct_change = (end_price - start_price)/start_price*100 if start_price else 0
    return {'price_pct_per_min': pct_change/minutes_window, 'points_in_window': count}

# export
__all__ = ['sma','rsi','price_velocity']
