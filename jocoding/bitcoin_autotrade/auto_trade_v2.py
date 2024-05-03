import os
from dotenv import load_dotenv
load_dotenv()
from openai import OpenAI
import pyupbit
import pandas as pd
import pandas_ta as ta
import json
import schedule
import time
import requests
from datetime import datetime
import sqlite3

# openai & upbit setup
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
upbit = pyupbit.Upbit(os.getenv("UPBIT_ACCESS_KEY"), os.getenv("UPBIT_SECRET_KEY"))

# completion = client.chat.completions.create(
#   model="gpt-3.5-turbo",
#   messages=[
#     {"role": "system", "content": "You are a helpful assistant."},
#     {"role": "user", "content": "Hello!"}
#   ]
# )

# print(completion.choices[0].message)
# print(upbit.get_balance("KRW"))         # 보유 현금 조회

def initialize_db(db_path='trading_decisions.sqlite'):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        # REAL은 숫자 값을 의미
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS decisions (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       timestamp DATETIME,
                       decision TEXT,
                       percentage REAL,
                       reason TEXT,
                       btc_balance REAL,
                       krw_balance REAL,
                       btc_avg_buy_price REAL,
                       btc_krw_price REAL
            );         
        ''')

        conn.commit()

def save_decision_to_db(decision, current_status):
    db_path = 'trading_decisions.sqlite'
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Parsing current_status from JSON to Python dict
        status_dict = json.loads(current_status)
        current_price = pyupbit.get_orderbook(ticker="KRW-BTC")['orderbook_units'][0]["ask_price"]

        # Preparing data for insertion
        data_to_insert = (
            decision.get('decision'),
            decision.get('percentage', 100),  # Defaulting to 100 if not provided
            decision.get('reason', ''),       # Defaulting to an empty string if not provided
            status_dict.get('btc_balance'),
            status_dict.get('krw_balance'),
            status_dict.get('btc_avg_buy_price'),
            current_price
        )

        # Inserting data into the database
        cursor.execute('''
            INSERT INTO decisions (timestamp, decision, percentage, reason, btc_balance, krw_balance, btc_avg_buy_price, btc_krw_price)
            VALUES (datetime('now', 'localtime'), ?, ?, ?, ?, ?, ?, ?)
        ''', data_to_insert)

        conn.commit()

def fetch_last_decisions(db_path='trading_decisions.sqlite', num_decisions=10):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT timestamp, decision, percentage, reason, btc_balance, krw_balance, btc_avg_buy_price FROM decisions
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (num_decisions,))
        decisions = cursor.fetchall()

        if decisions:
            formatted_decisions = []
            for decision in decisions:
                # Converting timestamp to milliseconds since the Unix epoch
                ts = datetime.strptime(decision[0], "%Y-%m-%d %H:%M:%S")
                ts_millis = int(ts.timestamp() * 1000)

                formatted_decision = {
                    "timestamp": ts_millis,
                    "decision": decision[1],
                    "percentage": decision[2],
                    "reason": decision[3],
                    "btc_balance": decision[4],
                    "krw_balance": decision[5],
                    "btc_avg_buy_price": decision[6]
                }
                formatted_decisions.append(str(formatted_decision))
            return "\n".join(formatted_decisions)
        else:
            return "No decision found."

def get_current_status():
    orderbook = pyupbit.get_orderbook(ticker="KRW-BTC")
    # 호가창 기준으로 현재 TimeStamp를 가져옴
    current_time = orderbook['timestamp']
    btc_balance = 0
    krw_balance = 0
    btc_avg_buy_price = 0
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == "BTC":
            btc_balance = b['balance']
            btc_avg_buy_price = b['avg_buy_price']
        if b['currency'] == "KRW":
            krw_balance = b['balance']

    current_status = {'current_time': current_time, 'orderbook' : orderbook, 'btc_balance':btc_balance, 'krw_balance': krw_balance, 'btc_avg_buy_price': btc_avg_buy_price}
    return json.dumps(current_status)

def get_news_data():
    ### Get news data from SERPAPI
    url = "https://serpapi.com/search.json?engine=google_news&q=btc&api_key=" + os.getenv("SERP_API_KEY")
    result = "No news data available."

    try:
        response = requests.get(url)
        news_results = response.json()['news_results']

        simplified_news = []

        for news_item in news_results:
            # Check if this news item contains 'stories'
            if 'stories' in news_item:
                for story in news_item['stories']:
                    timestamp = int(datetime.strptime(story['date'], '%m/%d/%Y, %H:%M %p, %z %Z').timestamp() * 1000)
                    simplified_news.append((story['title'], story.get('source', {}).get('name', 'Unknown source'), timestamp))
            else:
                # Process news items that are not categorized under stories but check date first
                if news_item.get('date'):
                    timestamp = int(datetime.strptime(news_item['date'], '%m/%d/%Y, %H:%M %p, %z %Z').timestamp() * 1000)
                    simplified_news.append((news_item['title'], news_item.get('source', {}).get('name', 'Unknown source'), timestamp))
                else:
                    simplified_news.append((news_item['title'], news_item.get('source', {}).get('name', 'Unknown source'), 'No timestamp provided'))
        
        result = str(simplified_news)
    
    except Exception as e:
        print(f"Error fetching news date: {e}")

    return result

def fetch_fear_and_greed_index(limit=1, date_format=''):
    """
    Fetches the latest Fear and Greed Index data.
    Parameters:
    - limit (int): Number of results to return. Default is 1.
    - date_format (str): Date format ('us', 'cn', 'kr', 'world'). Default is '' (unixtime).
    Returns:
    - dict or str: The Fear and Greed Index data in the specified format.
    """
    base_url = "https://api.alternative.me/fng/"
    params = {
        'limit': limit,
        'format': 'json',
        'date_format': date_format
    }
    response = requests.get(base_url, params=params)
    myData = response.json()['data']
    resStr = ""

    for data in myData:
        resStr += str(data)
    
    return resStr

def fetch_and_prepare_data():
    # Fetch data
    # 기간별 데이터 추출
    df_daily = pyupbit.get_ohlcv("KRW-BTC", "day", count=30)
    df_hourly = pyupbit.get_ohlcv("KRW-BTC", interval="minute60", count=24)

    # Define a helper function to add indicators
    def add_indicators(df):
        # Moving Averages
        df['SMA_10'] = ta.sma(df['close'], length=10)
        df['EMA_10'] = ta.ema(df['close'], length=10)

        # RSI
        df['RSI_14'] = ta.rsi(df['close'], length=14)

        # Stochastic Oscillator
        stoch = ta.stoch(df['high'], df['low'], df['close'], k=14, d=3, smooth_k=3)
        df = df.join(stoch)

        # MACD
        ema_fast = df['close'].ewm(span=12, adjust=False).mean()
        ema_slow = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = ema_fast - ema_slow
        df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Histogram'] = df['MACD'] - df['Signal_Line']

        # Bollinger Bands
        df['Middle_Band'] = df['close'].rolling(window=20).mean()
        # Calculate the standard deviation of closing prices over the last 20 days
        std_dev = df['close'].rolling(window=20).std()
        # Calculate the upper band (Middle Band + 2 * Standard Deviation)
        df['Upper_Band'] = df['Middle_Band'] + (std_dev * 2)
        # Calculate the lower band (Middle Band - 2 * Standard Deviation)
        df['Lower_Band'] = df['Middle_Band'] - (std_dev * 2)

        return df
    
    # Add indicators to both dataframes
    df_daily = add_indicators(df_daily)
    df_hourly = add_indicators(df_hourly)

    # 1달, 24시간 데이터를 모두 합쳐서 하나의 JSON 파일로 통합
    combined_df = pd.concat([df_daily, df_hourly], keys=['daily', 'hourly'])
    # orient 따라 작아지는게 있고 길어지는게 있어서 split으로 최대한 데이터 사이즈가 작아지도록 함
    combined_data = combined_df.to_json(orient='split')

    # make combined data as string and print length
    print(len(combined_data))

    return json.dumps(combined_data)

def get_instructions(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            instructions = file.read()
        return instructions
    except FileNotFoundError:
        print("File not found")
    except Exception as e:
        print("An error occurred while reading the file:", e)

def analyze_data_with_gpt4(news_data, data_json, last_decisions, fear_and_greed, current_status):
    instructions_path = "./instructions_v2.md"
    
    try:
        instructions = get_instructions(instructions_path)
        if not instructions:
            print("No instructions found.")
            return None
        
        current_status = get_current_status()
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": news_data},
                {"role": "user", "content": data_json},
                {"role": "user", "content": last_decisions},
                {"role": "user", "content": fear_and_greed},
                {"role": "user", "content": current_status},
            ],
            # 응답 형식을 JSON_OBJECT로 고정시켜야 함
            response_format={"type":"json_object"}
        )
        advice = response.choices[0].message.content
        return advice
    except Exception as e:
        print(f"Error in analyzing data with GPT-4: {e}")
        return None

def execute_buy(percentage):
    print("Attempting to buy BTC with a percentage of KRW balance...")
    try:
        # v1
        # krw = upbit.get_balance("KRW")
        # if krw > 5000:
        #     result = upbit.buy_market_order("KRW-BTC", krw*0.9995)
        #     print("Buy order successful:", result)

        krw_balance = upbit.get_balance("KRW")
        amount_to_invest = krw_balance * (percentage / 100)
        if amount_to_invest > 5000:                                                 # Ensure the order is above the minimum threshold
            result = upbit.buy_market_order("KRW-BTC", amount_to_invest * 0.9995)   # Adjust for fees
            print("Buy order successful:", result)
    except Exception as e:
        print(f"Failed to execute buy order: {e}")

def execute_sell(percentage):
    print("Attempting to sell a percentage of BTC...")
    try:
        # v1
        # btc = upbit.get_balance("BTC")
        # current_price = pyupbit.get_orderbook(ticker="KRW-BTC")['orderbook_units'][0]["ask_price"]
        # if current_price*btc > 5000:
        #     result = upbit.sell_market_order("KRW-BTC", btc)
        #     print("Sell order successful:", result)

        btc_balance = upbit.get_balance("BTC")
        amount_to_sell = btc_balance * (percentage / 100)
        current_price = pyupbit.get_orderbook(ticker="KRW-BTC")['orderbook_units'][0]["ask_price"]

        if current_price * amount_to_sell > 5000:
            result = upbit.sell_market_order("KRW-BTC", amount_to_sell)
            print("Sell order successful:", result)
    except Exception as e:
        print(f"Failed to execute sell order: {e}")

def make_decision_and_execute():
    print("Making decision and executing...")

    # v1
    # 30일 + 24시간 데이터 + 보조 지표 합친 데이터를 JSON 형태로 가져옴 
    # data_json = fetch_and_prepare_data()
    # GPT-4로 해당 데이터를 분석하고 결과를 받아옴
    # advice = analyze_data_with_gpt4(data_json)

    # try:
    #     decision = json.loads(advice)
    #     print(decision)
    #     if decision.get('decision') == "buy":
    #         execute_buy()
    #     elif decision.get('decision') == "sell":
    #         execute_sell()
    # except Exception as e:
    #     print(f"Failed to parse the advice as JSON: {e}")

    try:
        news_data = get_news_data()
        data_json = fetch_and_prepare_data()
        last_decisions = fetch_last_decisions()
        fear_and_greed = fetch_fear_and_greed_index(limit=30)
        current_status = get_current_status()
    except Exception as e:
        print(f"Error: {e}")
    else:
        max_retries = 5
        retry_delay_seconds = 5
        decision = None

        for attempt in range(max_retries):
            try:
                advice = analyze_data_with_gpt4(news_data, data_json, last_decisions, fear_and_greed, current_status)
                decision = json.loads(advice)
                break
            except json.JSONDecodeError as e:
                print(f"JSON parsing failed: {e}. Retrying in {retry_delay_seconds} seconds...")
                time.sleep(retry_delay_seconds)
                print(f"Attempt {attempt + 2} of {max_retries}")
        
        if not decision:
            print("Failed to make a decision after maximum retries.")
            return
        else:
            try:
                percentage = decision.get('percentage', 100)

                if decision.get('decision') == "buy":
                    execute_buy(percentage)
                elif decision.get('decision') == "sell":
                    execute_sell(percentage)

                save_decision_to_db(decision, current_status)
            except Exception as e:
                print(f"Failed to execute the decision or save to DB: {e}")

  
if __name__ == "__main__":
    # v1
    # make_decision_and_execute()
    # schedule.every().minute.at(":01").do(make_decision_and_execute)

    # v2
    initialize_db()

    # schedule.every().day.at("00:01").do(make_decision_and_execute)
    # schedule.every().day.at("08:01").do(make_decision_and_execute)
    # schedule.every().day.at("16:01").do(make_decision_and_execute)
    schedule.every().minute.at(":01").do(make_decision_and_execute)

    while True:
      schedule.run_pending()
      time.sleep(1)
