import pandas as pd
from datetime import datetime,time
from dateutil.relativedelta import relativedelta
import threading
import config
from KotakOrder import  KotakAPI
from time  import sleep
from logger import logger
import warnings
import pyotp
from neo_api_client import NeoAPI
from excel_reader import load_credentials_and_settings, read_trading_signals
from excel_interface import update_option_chain, update_trading_sheet, create_excel_file
import os
warnings.filterwarnings('ignore')




def on_order_error(error_message =None):
    logger.info(f'Error from Order websocket  {error_message}')

def on_order_close():
    logger.info(f'Order Websocket Close')

def on_order_message(message =None):
    logger.info(f'Order feed : {message}')

def on_error(error_message):
        logger.info(f'Error from websocket  {error_message}')

def on_close(message):
    logger.info(f'Websocket Close {message}')

def on_message(message):
    logger.info(f'Websocket: {message}')

def login():
    client = NeoAPI(environment='prod', access_token=None, neo_fin_key=None, consumer_key=config.consumer_key, consumer_secret=config.CS)
    mobile_number = str(config.Mob).replace("+91", "")
    login_response = client.totp_login(mobile_number=f"+91{mobile_number}", ucc=config.ucc, totp=pyotp.TOTP(config.totp).now())
    if 'Error Message' in login_response:
        logger.fatal(f"Login failed: {login_response['Error Message']}")
        exit()

    validation_response = client.totp_validate(mpin=config.MPIN)
    if 'Error Message' in validation_response:
        logger.fatal(f"MPIN validation failed: {validation_response['Error Message']}")
        exit()

    return client


def initializer():
    config.NEO_OBJ : NeoAPI  = login()
    cashUrl = config.NEO_OBJ.scrip_master(exchange_segment = "NSE")
    nfoUrl = config.NEO_OBJ.scrip_master(exchange_segment = "NFO")

    if isinstance(cashUrl, dict) and 'Error Message' in cashUrl:
        logger.fatal(f"Failed to get cash scrip master: {cashUrl['Error Message']}")
        exit()

    if isinstance(nfoUrl, dict) and 'Error Message' in nfoUrl:
        logger.fatal(f"Failed to get NFO scrip master: {nfoUrl['Error Message']}")
        exit()

    logger.info(f'{cashUrl} \n {nfoUrl}')

    nfodf = pd.read_csv(nfoUrl)
    nfodf.columns = [c.strip() for c in nfodf.columns.values.tolist()]
    nfodf['lExpiryDate'] = pd.to_datetime(nfodf['lExpiryDate'],unit='s').apply(lambda x: x.date() + relativedelta(years=10) )

    eqdf = pd.read_csv(cashUrl)
    eqdf.columns = [c.strip() for c in eqdf.columns.values.tolist()]


    weekly_expiry =nfodf[(nfodf.pInstType == 'OPTIDX') & (nfodf.pSymbolName == config.SYMBOL)]['lExpiryDate'].tolist()
    weekly_expiry.sort()
    exp = weekly_expiry[config.EXPIRY_OFFSET]
    config.TOKEN_MAP  = nfodf[(nfodf.pInstType == 'OPTIDX') & (nfodf.pSymbolName == config.SYMBOL) & (nfodf['lExpiryDate'] == exp)]
    config.SPOT_TOKEN = eqdf[eqdf.pSymbolName == config.SYMBOL].iloc[0]['pSymbol']
    logger.info(f'TOKEN MAP {config.TOKEN_MAP}')




def getNearStrike(Quotedf,premium):
    Quotedf['diff'] = abs(Quotedf.ltp - premium)
    Quotedf.sort_values(by = 'diff', inplace =True)
    return  Quotedf.iloc[0].to_dict()


def parse_quotes(x):
    """
    Generic parser for API responses that may be dict or list.
    Normalizes into a DataFrame with consistent columns.
    """

    # Case 1: If x is a dict
    if isinstance(x, dict):
        # If it has 'message' key and that's a list/dict
        if 'message' in x:
            data = x['message']
            # Ensure it's a list of dicts
            if isinstance(data, dict):
                data = [data]
        else:
            # Treat dict itself as one record
            data = [x]

    # Case 2: If x is a list
    elif isinstance(x, list):
        # If list contains dicts → use directly
        if all(isinstance(item, dict) for item in x):
            data = x
        else:
            # If list of lists → convert to DataFrame directly
            return pd.DataFrame(x)

    else:
        raise TypeError(f"Unsupported type: {type(x)}")

    # Build DataFrame
    df = pd.DataFrame(data)

    # Try to standardize column names if present
    rename_map = {
        'last_traded_price': 'ltp',
        'instrument_token': 'pSymbol',
        'trading_symbol': 'pTrdSymbol',
        'display_symbol': 'pTrdSymbol'   # <-- NEW mapping
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # Ensure numeric conversion for ltp if exists
    if 'ltp' in df.columns:
        df['ltp'] = pd.to_numeric(df['ltp'], errors='coerce')
    # Enforce schema: add missing columns with None
    for col in ['ltp', 'pSymbol', 'pTrdSymbol', 'open', 'high', 'low', 'close', 'volume']:
        if col not in df.columns:
            df[col] = None

    return df


# Usage inside your function
def getQuotes(instList):
    x = config.NEO_OBJ.quotes(instrument_tokens=instList, quote_type="ohlc")
    Quotedf = parse_quotes(x)
    return Quotedf



def get_trading_symbol(strike_price, option_type):
    symbolOpt = config.TOKEN_MAP.copy()
    # remove spaces from pStrike to match with strike_price
    symbolOpt['pStrike'] = symbolOpt['pStrike'].astype(str).str.replace(".0", "").str.strip()
    strike_price = str(strike_price).strip()
    option_type = option_type.strip()

    instrument = symbolOpt[(symbolOpt.pStrike == strike_price) & (symbolOpt.pOptionType == option_type)]
    if not instrument.empty:
        return instrument.iloc[0]['pTrdSymbol']
    return None

def get_lot_size(trading_symbol):
    symbolOpt = config.TOKEN_MAP.copy()
    instrument = symbolOpt[symbolOpt.pTrdSymbol == trading_symbol]
    if not instrument.empty:
        return int(instrument.iloc[0]['lLotSize'])
    return 0

def update_option_chain_data():
    symbolOpt = config.TOKEN_MAP
    spot_ltp = getQuotes([{'instrument_token' : config.SPOT_TOKEN , "exchange_segment": "NSE"}]).iloc[0]['ltp']
    atm_strike = round(spot_ltp / 50) * 50

    strike_range = 5
    instList = []
    for i in range(atm_strike - strike_range * 50, atm_strike + (strike_range + 1) * 50, 50):
        for option_type in ['CE', 'PE']:
            instrument = symbolOpt[(symbolOpt.pStrike == str(i)) & (symbolOpt.pOptionType == option_type)]
            if not instrument.empty:
                instList.append({'instrument_token' : instrument.iloc[0]['pSymbol'] , "exchange_segment": instrument.iloc[0]['pExchSeg']})

    quotedf = getQuotes(instList)
    # format the data to be written to excel
    option_chain_data = []
    for index, row in quotedf.iterrows():
        # extract strike price from trading symbol
        strike_price = ''.join(filter(str.isdigit, row['pTrdSymbol']))
        option_chain_data.append([strike_price, row['ltp'], row.get('open'), row.get('high'), row.get('low'), row.get('close'), row.get('volume')])
    update_option_chain(option_chain_data)

def place_order_from_signals():
    neoOrderApi = KotakAPI(config.NEO_OBJ)
    signals = read_trading_signals()
    for signal in signals:
        if not getTimeCondition():
            msg = f'Time out'
            logger.info(msg)
            return

        row_index = signal['row_index']
        strike_price = signal['strike_price']
        option_type = signal['option_type']
        buy_sell = signal['buy_sell']
        sl = signal['sl']

        if not isinstance(sl, (int, float)):
            logger.error(f"Invalid SL value for strike {strike_price}. Please enter a valid number.")
            continue

        tsym = get_trading_symbol(strike_price, option_type)
        if not tsym:
            logger.error(f"Could not find trading symbol for strike {strike_price} and option type {option_type}")
            continue

        lot_size = get_lot_size(tsym)
        quantity = config.QTY * lot_size

        order_id = neoOrderApi.placeOrder(tsym, buy_sell, quantity, order_type='MKT', productType='MIS')

        if order_id:
            trade = read_trading_signals(all_trades=True)
            trade = [t for t in trade if t['row_index'] == row_index][0]
            # Update the trading sheet with the order status
            update_trading_sheet(row_index, [strike_price, option_type, buy_sell, "Placed", trade['entry_price'], trade['exit_price'], sl, trade.get('mtm')])

            for i in range(10):
                sleep(1) # wait for order to get executed
                order_history = neoOrderApi.getOrderbook()
                if order_history:
                    order_df = pd.DataFrame(order_history['data'])
                    order = order_df[order_df['nOrdNo'] == order_id]
                    if not order.empty:
                        order = order.iloc[0]
                        if order['ordSt'] == 'complete':
                            entry_price = float(order['avgPrc'])
                            update_trading_sheet(row_index, [strike_price, option_type, buy_sell, "Executed", entry_price, trade['exit_price'], sl, trade.get('mtm')])
                            placeSLOrder(neoOrderApi, order.to_dict(), sl)
                            break
                        elif order['ordSt'] == 'rejected':
                            update_trading_sheet(row_index, [strike_price, option_type, buy_sell, "Rejected", trade['entry_price'], trade['exit_price'], sl, trade.get('mtm')])
                            break


def update_mtm():
    neoOrderApi = KotakAPI(config.NEO_OBJ)
    positions = neoOrderApi.getPosition()
    if not (positions and 'data' in positions):
        return

    trades = read_trading_signals(all_trades=True)
    if not trades:
        return

    for position in positions['data']:
        for trade in trades:
            if get_trading_symbol(trade['strike_price'], trade['option_type']) == position['trdSym']:
                ltp = getQuotes([{'instrument_token' : position['pSymbol'] , "exchange_segment": position['pExchSeg']}])
                if not ltp.empty:
                    ltp = ltp.iloc[0]['ltp']
                    mtm = (ltp - trade['entry_price']) * int(position['flBuyQty']) if trade['buy_sell'] == 'B' else (trade['entry_price'] - ltp) * int(position['flSellQty'])
                    update_trading_sheet(trade['row_index'], [trade['strike_price'], trade['option_type'], trade['buy_sell'], trade['status'], trade['entry_price'], trade['exit_price'], trade.get('sl'), mtm])


def placeSLOrder(neoOrderApi : KotakAPI, entryInfo:dict, sl:float):
    tsym = entryInfo['trdSym']
    quantity =  abs(int(entryInfo['qty']))
    tradedPrice = float(entryInfo['avgPrc'])
    if entryInfo['trnsTp'] == 'B':
        mSL  = neoOrderApi.truncate(tradedPrice*(1 - sl/100)  )
        mLimit = mSL - config.SL_LIMIT
        mTransType = 'S'

    else:
        mSL  =  neoOrderApi.truncate(tradedPrice*(1 + sl/100)  )
        mLimit = mSL + config.SL_LIMIT
        mTransType = 'B'
    logger.info(f'Placing {tsym} SL Order.  SL: {mSL} {mLimit} Qty: {quantity}')
    mSLOrderid = neoOrderApi.placeOrder(tsym,mTransType,quantity,order_type ='SL',productType= entryInfo['prod'] ,trigger_price=mSL,limitPrice=mLimit )
    return mSLOrderid

def getTimeCondition():
    startTime =  datetime.now(config.TIME_ZONE)
    closingTime = startTime.replace(hour=config.EXIT_TIME[0], minute=config.EXIT_TIME[1],second=config.EXIT_TIME[2])
    return datetime.now(config.TIME_ZONE) < closingTime  and config.RUN_PROCESS

def square_off_positons():
    startTime = datetime.today()
    closingTime = startTime.replace(hour=config.EXIT_TIME[0], minute=config.EXIT_TIME[1],second=0)
    interval = (closingTime - startTime).total_seconds()
    logger.info(f"All open Positions  closed after : {interval/60}  mins")
    if interval > 0 :
        neoOrderApi = KotakAPI(config.NEO_OBJ)
        threading.Timer(interval, neoOrderApi.exitAllPosition).start()

if __name__ == '__main__':
    if not os.path.exists("trading_system.xlsx"):
        create_excel_file()
    load_credentials_and_settings()

    # Validate critical credentials
    critical_credentials = ['consumer_key', 'CS', 'Mob', 'Pwd', 'MPIN', 'totp', 'ucc']
    if any(not getattr(config, cred) for cred in critical_credentials):
        logger.fatal("Critical credentials are not set. Please fill out the 'Credentials' sheet in trading_system.xlsx and restart the application.")
        exit()

    startTime =  datetime.now(config.TIME_ZONE)
    closingTime = startTime.replace(hour=9, minute=15,second=0,microsecond=0)
    interval = max(0, (closingTime - startTime).total_seconds())
    logger.info(f'System will Start after  {interval} sec' )
    sleep(interval)
    initializer()

    while True:
        update_option_chain_data()
        place_order_from_signals()
        update_mtm()
        sleep(5) # Update every 5 seconds
