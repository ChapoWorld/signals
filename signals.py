import time
import requests
import datetime
import pandas as pd

# ==================== НАСТРОЙКИ (КОНФИГУРИРАНИ) ====================
TELEGRAM_TOKEN = "8862491975:AAH4gz4BqPTKUBsAEKY1SKDbo1Rwa-LdozY"
CHAT_ID = "7731160065"

# Тъй като ще го пуснем в Европа, използваме оригиналните фючърсни символи!
ASSETS = [
    {"name": "Злато (XAUUSDT)", "symbol": "XAUUSDT"},
    {"name": "Петрол (CLUSDT)", "symbol": "CLUSDT"}
]
# ===================================================================

def send_telegram_message(message):
    """Изпраща съобщение в твоя Telegram чат"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Грешка при връзка с Telegram: {e}")

def get_binance_futures_data(symbol):
    """Дърпа последните 100 свещи (15m) от Binance Futures API"""
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {
        "symbol": symbol,
        "interval": "15m",
        "limit": 100
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            print(f"[{symbol}] Грешка от Binance: {response.text}")
            return None
            
        data = response.json()
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume', 
            'close_time', 'qav', 'num_trades', 'tbb', 'tbq', 'ignore'
        ])
        df['close'] = df['close'].astype(float)
        return df
    except Exception as e:
        print(f"[{symbol}] Грешка при връзка с API: {e}")
        return None

def main():
    print("🚀 Стартиране на Фючърс Мулти-Бот (Злато + Петрол)...")
    
    send_telegram_message("🤖 *Фючърс Ботът е ОНЛАЙН!*\nСледя на 15м таймфрейм:\n🥇 Злато (XAUUSDT)\n🛢 Петрол (CLUSDT)")
    
    last_states = {asset['symbol']: None for asset in ASSETS}
    last_heartbeat_minute = -1

    while True:
        try:
            current_prices = {}
            
            for asset in ASSETS:
                symbol = asset['symbol']
                name = asset['name']
                
                df = get_binance_futures_data(symbol)
                
                if df is not None and not df.empty:
                    current_price = df['close'].iloc[-1]
                    current_prices[name] = current_price
                    
                    # Изчисляване на EMA 9 и EMA 21
                    df['EMA_9'] = df['close'].ewm(span=9, adjust=False).mean()
                    df['EMA_21'] = df['close'].ewm(span=21, adjust=False).mean()
                    
                    ema9 = df['EMA_9'].iloc[-1]
                    ema21 = df['EMA_21'].iloc[-1]
                    
                    if ema9 > ema21:
                        current_state = "BUY"
                    else:
                        current_state = "SELL"
                    
                    if last_states[symbol] is None:
                        last_states[symbol] = current_state
                        print(f"Първоначален тренд за {name}: {current_state}")
                    
                    # Сигнал при пресичане
                    if current_state != last_states[symbol]:
                        if current_state == "BUY":
                            msg = f"🚀 *СИГНАЛ ЗА ПОКУПКА (BUY)* 🚀\n\n📌 **Актив:** {name}\n📈 **EMA 9 пресече НАД EMA 21**\n💰 Цена: ${current_price:.2f}\n⏱ Таймфрейм: 15м"
                        else:
                            msg = f"🔻 *СИГНАЛ ЗА ПРОДАЖБА (SELL)* 🔻\n\n📌 **Актив:** {name}\n📉 **EMA 9 пресече ПОД EMA 21**\n💰 Цена: ${current_price:.2f}\n⏱ Таймфрейм: 15м"
                        
                        send_telegram_message(msg)
                        last_states[symbol] = current_state
                        
            # === 30-Минутен Пулс ===
            now = datetime.datetime.now()
            if now.minute in [0, 30] and now.minute != last_heartbeat_minute:
                if current_prices:
                    time_str = now.strftime("%H:%M")
                    status_msg = f"⏱ *[Пулс на бота]* — {time_str}\n"
                    for asset_name, price in current_prices.items():
                        status_msg += f"💰 {asset_name}: ${price:.2f}\n"
                    send_telegram_message(status_msg)
                    last_heartbeat_minute = now.minute
                    
        except Exception as e:
            print(f"Грешка: {e}")
            
        time.sleep(15)

if __name__ == "__main__":
    main()