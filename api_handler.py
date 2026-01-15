# api_handler.py
from neo_api_client import NeoAPI
import logging
import pandas as pd
import datetime as dt
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)

# --- WebSocket Callback Functions ---
def on_message(message):
    logger.info(f"WebSocket Message: {message}")

def on_error(error_message):
    logger.error(f"WebSocket Error: {error_message}")

def on_open(message):
    logger.info(f"WebSocket Opened: {message}")

def on_close(message):
    logger.info(f"WebSocket Closed: {message}")

def on_order_message(message):
    logger.info(f"Order Feed Message: {message}")

def on_order_error(error_message):
    logger.error(f"Order Feed Error: {error_message}")

def on_order_close():
    logger.info("Order Feed Closed.")


class APIHandler:
    def __init__(self, config):
        self.config = config
        self.client = None
        self.kotak_config = self.config['KOTAK']

    def autologin(self):
        """Performs an automated TOTP-based login."""
        try:
            import pyotp

            self.client = NeoAPI(
                consumer_key=self.kotak_config['consumer_key'],
                environment='prod'
            )

            # Assign callbacks
            self.client.on_open = on_open
            self.client.on_message = on_message
            self.client.on_error = on_error
            self.client.on_close = on_close
            self.client.on_order_message = on_order_message
            self.client.on_order_error = on_order_error
            self.client.on_order_close = on_order_close

            self.client.totp_login(
                mobile_number=self.kotak_config['mobile'],
                ucc=self.kotak_config['ucc'],
                totp=pyotp.TOTP(self.kotak_config['totp_key']).now()
            )
            self.client.totp_validate(mpin=self.kotak_config['mpin'])

            import threading
            threading.Thread(target=self.client.subscribe_to_orderfeed).start()

            logger.info("Auto-login successful and subscribed to order feed.")
            return True
        except Exception as e:
            logger.error(f"Auto-login failed: {e}")
            return False

    def get_quotes(self, instrument_tokens, quote_type="ltp"):
        """Fetches quotes for a list of instrument tokens."""
        if not self.client:
            logger.error("Client not logged in.")
            return None
        try:
            response = self.client.quotes(instrument_tokens=instrument_tokens, quote_type=quote_type)

            # A successful response is a list of quote dictionaries.
            if isinstance(response, list):
                return response

            # An unsuccessful response is a dictionary.
            elif isinstance(response, dict):
                logger.error(f"Error in quotes API response: {response}")
                return None

            # Handle any other unexpected format.
            else:
                logger.warning(f"Unexpected response format from quotes API: {response}")
                return None

        except Exception as e:
            # Catch potential exceptions from the API call itself.
            logger.error(f"Exception while fetching quotes: {e}")
            return None

    def get_scrip_master(self, exchange='NFO'):
        """Gets the URL for the scrip master file."""
        if not self.client:
            logger.error("Client not logged in.")
            return None
        try:
            url = self.client.scrip_master(exchange_segment=exchange)
            logger.info(f"Scrip master URL for {exchange} received.")
            return url
        except Exception as e:
            logger.error(f"Error getting scrip master URL: {e}")
            return None

    def get_trading_symbols(self, scrip_master_url):
        """Returns a list of unique trading symbols from the scrip master."""
        try:
            df = pd.read_csv(scrip_master_url)
            return sorted(df['pSymbolName'].unique().tolist())
        except Exception as e:
            logger.error(f"Error reading trading symbols from scrip master: {e}")
            return []

    def get_expiries(self, symbol, scrip_master_url):
        """Returns a list of expiry dates for a given symbol."""
        try:
            df = pd.read_csv(scrip_master_url)
            df = df[(df['pSymbolName'] == symbol) & (df['pInstType'] == 'OPTIDX')]

            # Convert epoch to datetime, apply date logic
            df['pExpiryDate'] = df['pExpiryDate'].apply(
                lambda x: (dt.datetime.fromtimestamp(x).date() +
                           relativedelta(years=10) -
                           pd.Timedelta(days=1)).strftime('%Y-%m-%d')
            )

            all_expiries = sorted(set(df['pExpiryDate']))
            return all_expiries
        except Exception as e:
            logger.error(f"Error reading expiries from scrip master: {e}")
            return []

    def get_instrument_token(self, symbol_name, scrip_master_url):
        """Finds the instrument token for a given symbol name from the cash market scrip master."""
        try:
            df = pd.read_csv(scrip_master_url)
            # Find the exact match for the symbol name. Note: 'pSymbolName' might be different from the display name.
            # We will search for common index names. A more robust solution might need a mapping.
            if symbol_name == "NIFTY 50":
                instrument = df[df['pSymbolName'] == 'Nifty 50'].iloc[0]
            elif symbol_name == "BANKNIFTY":
                instrument = df[df['pSymbolName'] == 'Nifty Bank'].iloc[0]
            # Add other indices as needed
            else:
                instrument = df[df['pSymbolName'] == symbol_name].iloc[0]

            return instrument['pSymbol']
        except Exception as e:
            logger.error(f"Could not find instrument token for {symbol_name}: {e}")
            return None

    def get_atm_strikes(self, symbol, expiry):
        # Placeholder for fetching ATM strikes
        return {"ce_strike": 61300.0, "pe_strike": 61300.0}

    def get_ltp(self, instrument_token, exchange_segment):
        """Fetches the LTP for a single instrument."""
        quotes = self.get_quotes(instrument_tokens=[{'instrument_token': instrument_token, 'exchange_segment': exchange_segment}])
        if quotes and len(quotes) > 0:
            return quotes[0]['last_traded_price']
        return 0.0

    def get_strike_for_ltp(self, symbol, expiry, target_ltp, option_type, scrip_master_url):
        """Finds the strike price with the LTP closest to the target LTP."""
        try:
            df = pd.read_csv(scrip_master_url)

            # Apply the same date logic to the dataframe for consistent filtering
            df['pExpiryDate'] = df['pExpiryDate'].apply(
                lambda x: (dt.datetime.fromtimestamp(x).date() +
                           relativedelta(years=10) -
                           pd.Timedelta(days=1)).strftime('%Y-%m-%d')
            )

            # Filter for the specific symbol, expiry, and option type
            filtered_df = df[(df['pSymbolName'] == symbol) &
                             (df['pExpiryDate'] == expiry) &
                             (df['pOptionType'] == option_type)]

            if filtered_df.empty:
                logger.warning(f"No instruments found for {symbol} {expiry} {option_type}")
                return None

            # Get quotes for all filtered instruments
            instrument_tokens = [{'instrument_token': row['pSymbol'], 'exchange_segment': row['pExchSeg']} for index, row in filtered_df.iterrows()]
            quotes = self.get_quotes(instrument_tokens=instrument_tokens, quote_type='ltp')

            if not quotes:
                logger.warning("Could not fetch quotes for strike selection.")
                return None

            # Create a DataFrame from the quotes and merge with instrument details
            quotes_df = pd.DataFrame(quotes)
            quotes_df = quotes_df.rename(columns={'instrument_token': 'pSymbol'})
            merged_df = pd.merge(filtered_df, quotes_df, on='pSymbol')

            # Find the strike with the LTP closest to the target
            merged_df['ltp_diff'] = abs(merged_df['last_traded_price'] - target_ltp)
            closest_strike = merged_df.loc[merged_df['ltp_diff'].idxmin()]

            return closest_strike.to_dict()

        except Exception as e:
            logger.error(f"Error getting strike for LTP: {e}")
            return None

    def place_order(self, trading_symbol, price, quantity, transaction_type, product_type='MIS', order_type='MKT', validity='DAY', variety='REGULAR', trigger_price=None, stop_loss_value=None, target_value=None):
        """Places an order."""
        if not self.client:
            logger.error("Client not logged in.")
            return None
        try:
            order_params = {
                "instrument_token": trading_symbol,
                "price": price,
                "quantity": quantity,
                "transaction_type": transaction_type,
                "product": product_type,
                "order_type": order_type,
                "validity": validity,
                "variety": variety,
                "trigger_price": trigger_price,
                "stop_loss_value": stop_loss_value,
                "target_value": target_value
            }
            # Remove None values
            order_params = {k: v for k, v in order_params.items() if v is not None}

            order_res = self.client.place_order(**order_params)
            logger.info(f"Order placed: {order_res}")
            return order_res
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None
