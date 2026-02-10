from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pyotp
from neo_api_client import NeoAPI
import logging
import os
app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
client = None
@app.route('/login', methods=['POST'])
def login():
    global client
    data = request.json
    ucc = data.get('ucc')
    try:
        client = NeoAPI(environment='prod', consumer_key=data.get('consumer_key'))
        client.totp_login(mobile_number=data.get('mobile_number'), ucc=ucc, totp=pyotp.TOTP(data.get('totp_key')).now())
        client.totp_validate(mpin=data.get('mpin'))
        return jsonify({"status": "success", "ucc": ucc})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400
@app.route('/instruments', methods=['GET'])
def get_instruments():
    global client
    if not client:
        return jsonify({"status": "error", "message": "Not logged in"}), 401
    symbol = request.args.get('symbol', 'NIFTY')
    nfo_url = client.scrip_master(exchange_segment="NFO")
    df = pd.read_csv(nfo_url)
    df.columns = [c.strip() for c in df.columns.values.tolist()]
    # Kotak Neo uses an epoch starting from 1980-01-01.
    # Standard Unix epoch starts from 1970-01-01.
    # We add 10 years to align the dates correctly.
    df['lExpiryDate'] = pd.to_datetime(df['lExpiryDate'], unit='s').apply(lambda x: x.date() + relativedelta(years=10))
    filtered_df = df[(df.pInstType == 'OPTIDX') & (df.pSymbolName == symbol)]
    expiries = sorted(filtered_df['lExpiryDate'].unique().tolist())
    return jsonify({"status": "success", "expiries": [str(e) for e in expiries]})
@app.route('/strikes', methods=['GET'])
def get_strikes():
    global client
    if not client:
        return jsonify({"status": "error", "message": "Not logged in"}), 401
    symbol = request.args.get('symbol', 'NIFTY')
    expiry = request.args.get('expiry')
    nfo_url = client.scrip_master(exchange_segment="NFO")
    df = pd.read_csv(nfo_url)
    df.columns = [c.strip() for c in df.columns.values.tolist()]
    # Kotak Neo uses an epoch starting from 1980-01-01.
    df['lExpiryDate'] = pd.to_datetime(df['lExpiryDate'], unit='s').apply(lambda x: x.date() + relativedelta(years=10))
    filtered_df = df[(df.pInstType == 'OPTIDX') & (df.pSymbolName == symbol) & (df['lExpiryDate'].astype(str) == expiry)]
    strikes = filtered_df[['pSymbol', 'pTrdSymbol', 'pStrikePrice', 'pOptionType', 'pLotSize']].to_dict(orient='records')
    return jsonify({"status": "success", "strikes": strikes})
@app.route('/quotes', methods=['POST'])
def get_quotes():
    global client
    if not client:
        return jsonify({"status": "error", "message": "Not logged in"}), 401
    quotes = client.quotes(instrument_tokens=request.json.get('tokens', []), quote_type="")
    return jsonify({"status": "success", "data": quotes})
@app.route('/place_order', methods=['POST'])
def place_order():
    global client
    if not client:
        return jsonify({"status": "error", "message": "Not logged in"}), 401
    data = request.json
    order_res = client.place_order(exchange_segment=data.get('exchange_segment', 'nse_fo'), product=data.get('product', 'MIS'), price=str(data.get('price', '0')), order_type=data.get('order_type', 'MKT'), quantity=str(data.get('quantity')), validity='DAY', trading_symbol=data.get('trading_symbol'), transaction_type=data.get('transaction_type'), amo="NO", disclosed_quantity="0", market_protection="0", pf="N", trigger_price=str(data.get('trigger_price', '0')), tag=data.get('tag', 'SAN_ALGO'))
    return jsonify({"status": "success", "data": order_res})
@app.route('/spot', methods=['GET'])
def get_spot():
    global client
    if not client:
        return jsonify({"status": "error", "message": "Not logged in"}), 401
    symbol = request.args.get('symbol', 'NIFTY')
    try:
        segment = "NSE"
        if symbol == 'SENSEX':
            segment = "BSE"

        cash_url = client.scrip_master(exchange_segment=segment)
        df = pd.read_csv(cash_url)
        df.columns = [c.strip() for c in df.columns.values.tolist()]

        # Mappings for spot symbols
        mapping = {
            'NIFTY': 'Nifty 50',
            'SENSEX': 'SENSEX'
        }
        search_symbol = mapping.get(symbol, symbol)

        filtered = df[df.pSymbolName == search_symbol]
        if filtered.empty:
            filtered = df[df.pSymbolName == symbol]

        if filtered.empty:
            return jsonify({"status": "error", "message": f"Spot symbol {symbol} not found in {segment} scrip master"}), 404

        spot_info = filtered.iloc[0]
        token = spot_info['pSymbol']
        exch = "nse_cm" if segment == "NSE" else "bse_cm"
        quote = client.quotes(instrument_tokens=[{"instrument_token": str(token), "exchange_segment": exch}], quote_type="")

        if quote.get('stat') != 'Ok':
            return jsonify({"status": "error", "message": quote.get('emsg', 'Failed to fetch quote')}), 400

        return jsonify({"status": "success", "symbol": symbol, "quote": quote})
    except Exception as e:
        logger.error(f"Error in get_spot: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
