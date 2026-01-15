# api_handler.py
from neo_api_client import NeoAPI
import logging
import pandas as pd

logger = logging.getLogger(__name__)

# --- WebSocket Callback Functions ---
def on_message(message):
    logger.info(f"WebSocket Message: {message}")

def on_error(error_message):
    logger.error(f"WebSocket Error: {error_message}")

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
                consumer_key=self.kotak_config['CONSUMER_KEY'],
                consumer_secret=self.kotak_config['API_SECRET'],
                environment='prod',
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_order_message=on_order_message,
                on_order_error=on_order_error,
                on_order_close=on_order_close
            )

            self.client.totp_login(
                mobile_number=self.kotak_config['MOBILE'],
                ucc=self.kotak_config['UCC'],
                totp=pyotp.TOTP(self.kotak_config['TOTP_KEY']).now()
            )
            self.client.totp_validate(mpin=self.kotak_config['MPIN'])

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
            quotes = self.client.quotes(instrument_tokens=instrument_tokens, quote_type=quote_type)
            return quotes['message']
        except Exception as e:
            logger.error(f"Error fetching quotes: {e}")
            return None

    def get_scrip_master(self, exchange='NFO'):
        """Downloads and caches the scrip master file."""
        if not self.client:
            logger.error("Client not logged in.")
            return None
        try:
            self.client.scrip_master(exchange_segment=exchange)
            logger.info(f"Scrip master for {exchange} downloaded.")
            return True
        except Exception as e:
            logger.error(f"Error downloading scrip master: {e}")
            return False

    def get_trading_symbols(self, exchange='NFO'):
        """Returns a list of unique trading symbols from the scrip master."""
        try:
            df = pd.read_csv(f'scripmaster_{exchange}.csv')
            return sorted(df['pSymbolName'].unique().tolist())
        except FileNotFoundError:
            logger.error("Scrip master file not found. Please download it first.")
            return []

    def get_expiries(self, symbol, exchange='NFO'):
        """Returns a list of expiry dates for a given symbol."""
        try:
            df = pd.read_csv(f'scripmaster_{exchange}.csv')
            expiries = df[df['pSymbolName'] == symbol]['lExpiryDate'].unique().tolist()
            return sorted(expiries)
        except FileNotFoundError:
            logger.error("Scrip master file not found.")
            return []

    def get_atm_strikes(self, symbol, expiry):
        # Placeholder for fetching ATM strikes
        return {"ce_strike": 61300.0, "pe_strike": 61300.0}

    def get_ltp(self, instrument_token, exchange_segment):
        """Fetches the LTP for a single instrument."""
        quotes = self.get_quotes(instrument_tokens=[{'instrument_token': instrument_token, 'exchange_segment': exchange_segment}])
        if quotes and len(quotes) > 0:
            return quotes[0]['last_traded_price']
        return 0.0

    def get_strike_for_ltp(self, symbol, expiry, target_ltp, option_type):
        """Finds the strike price with the LTP closest to the target LTP."""
        try:
            df = pd.read_csv('scripmaster_NFO.csv')

            # Filter for the specific symbol, expiry, and option type
            filtered_df = df[(df['pSymbolName'] == symbol) &
                             (df['lExpiryDate'] == expiry) &
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
