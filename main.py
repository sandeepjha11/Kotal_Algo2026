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
       
    client = NeoAPI(environment='prod', access_token=None, neo_fin_key=None, consumer_key=config.consumer_key)
    client.totp_login(mobile_number=config.Mob, ucc=config.ucc, totp=pyotp.TOTP(config.totp).now())
    client.totp_validate(mpin=config.MPIN)
    #logger.info(f'{sesRes}') 
    #threading.Thread(target = client.subscribe_to_orderfeed).start() 
    return client


def initializer():
    config.NEO_OBJ : NeoAPI  = login()
    cashUrl = config.NEO_OBJ.scrip_master(exchange_segment = "NSE")
    nfoUrl = config.NEO_OBJ.scrip_master(exchange_segment = "NFO")
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


import pandas as pd

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
    for col in ['ltp', 'pSymbol', 'pTrdSymbol']:
        if col not in df.columns:
            df[col] = None

    return df


# Usage inside your function
def getQuotes(instList):
    x = config.NEO_OBJ.quotes(instrument_tokens=instList, quote_type="")
    Quotedf = parse_quotes(x)
    return Quotedf


def getCEPESymbols(cePremium, pePremium):
    symbolOpt = config.TOKEN_MAP
    ceStrikedf = symbolOpt[symbolOpt.pOptionType == 'CE']
    peStrikedf = symbolOpt[symbolOpt.pOptionType == 'PE']
    lotSize = int(peStrikedf.iloc[0]['lLotSize'])
    ceInstList = []
    for i in ceStrikedf.index:
        strikeInfo = ceStrikedf.loc[i]
        ceInstList.append({'instrument_token' : strikeInfo['pSymbol'] , "exchange_segment": strikeInfo['pExchSeg']})
    ceQuotedf = getQuotes(ceInstList)
    ceStrike =  getNearStrike(ceQuotedf,cePremium)
    logger.info(f'Selected Strike CE {ceStrike}')

    peInstList = []
    for i in peStrikedf.index:
        strikeInfo = peStrikedf.loc[i]
        peInstList.append({'instrument_token' : strikeInfo['pSymbol'] , "exchange_segment": strikeInfo['pExchSeg']})
    peQuotedf = getQuotes(peInstList)
    peStrike =  getNearStrike(peQuotedf,pePremium)
    logger.info(f'Selected Strike PE {peStrike}')
    return ceStrike , peStrike , lotSize

def placeEntryOrder():
    neoOrderApi = KotakAPI(config.NEO_OBJ)
    if not getTimeCondition():
        msg = f'Time out'    
        logger.info(msg)
        return msg
    
    ceStrike , peStrike, lotSize = getCEPESymbols(100, 100)   # CE , PE
    transType = 'S'
    ceTsym = ceStrike.get('pTrdSymbol') or ceStrike.get('trading_symbol')
    if not ceTsym:
        raise ValueError(f"Missing trading symbol in ceStrike: {ceStrike}")
    quantity = config.QTY*lotSize
    ceEntryOrderid = neoOrderApi.placeOrder(ceTsym,transType,quantity,order_type ='MKT',productType= 'MIS' )
    
       
    peTsym = peStrike.get('pTrdSymbol') or peStrike.get('trading_symbol')
    if not peTsym:
        raise ValueError(f"Missing trading symbol in peStrike: {peStrike}")
    quantity = config.QTY*lotSize
    peEntryOrderid = neoOrderApi.placeOrder(peTsym,transType,quantity,order_type ='MKT',productType= 'MIS' )

    isAllTrigger = False
    for i in range(10):
        isAllTrigger,orderdf  = neoOrderApi.isAllOrderTrigger([ceEntryOrderid,peEntryOrderid])
        if isAllTrigger:
            ceEntryInfo= orderdf[orderdf.nOrdNo == ceEntryOrderid].iloc[0].to_dict()
            cetradedPrice = float(ceEntryInfo['avgPrc'])
            
            
            peEntryInfo = orderdf[orderdf.nOrdNo == peEntryOrderid].iloc[0].to_dict()
            petradedPrice = float(peEntryInfo['avgPrc'])
            logger.info(f'Entry Order traded CE  {cetradedPrice}   PE {petradedPrice} .Place SL Order ')
            
            ceSLOrderid  = placeSLOrder(neoOrderApi, ceEntryInfo)
            peSLOrderid  = placeSLOrder(neoOrderApi, peEntryInfo)
            break
        sleep(i)

    if not isAllTrigger:
        logger.info(f'Order not executed Completly. Cancel Open Order.')
        neoOrderApi.exitAllPosition()
    
    else:
        square_off_positons()   
        
       
def placeSLOrder(neoOrderApi : KotakAPI, entryInfo:dict):
    tsym = entryInfo['trdSym']
    quantity =  abs(int(entryInfo['qty']))
    tradedPrice = float(entryInfo['avgPrc'])
    if entryInfo['trnsTp'] == 'B':
        mSL  = neoOrderApi.truncate(tradedPrice*(1 - config.SL/100)  )
        mLimit = mSL - config.SL_LIMIT
        mTransType = 'S'
                    
    else:
        mSL  =  neoOrderApi.truncate(tradedPrice*(1 + config.SL/100)  )
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
    startTime =  datetime.now(config.TIME_ZONE)
    closingTime = startTime.replace(hour=9, minute=15,second=0,microsecond=0)
    interval = max(0, (closingTime - startTime).total_seconds())
    logger.info(f'System will Start after  {interval} sec' )
    sleep(interval)
    initializer()
    
    closingTime = startTime.replace(hour=config.ENTRY_TIME[0], minute=config.ENTRY_TIME[1],second=config.ENTRY_TIME[2],microsecond=0)
    interval = max(0, (closingTime - datetime.now(config.TIME_ZONE)).total_seconds())
    logger.info(f'Order will Place  after  {interval} sec' )
    sleep(interval)
    placeEntryOrder()
    
 
    
    
  
   

