# api_handler.py
import configparser
from neo_api_client import NeoAPI
import logging
import pandas as pd
import datetime as dt
from dateutil.relativedelta import relativedelta
import pyotp

logger = logging.getLogger(__name__)

class APIHandler:
    def __init__(self, config):
        self.config = config
        self.client = None
        self.kotak_config = self.config['KOTAK']

    def autologin(self, root=None):
        """Performs an automated TOTP-based login with diagnostic popup."""
        try:
            import pyotp

            # Create NeoAPI client
            self.client = NeoAPI(
                environment='prod',
                access_token=None,
                neo_fin_key=None,
                consumer_key=self.kotak_config['consumer_key']
            )

            # Assign callbacks to dummy lambdas or leave them unset here
            # The TradingApp will override them later
            self.client.on_open = None
            self.client.on_message = None
            self.client.on_error = None
            self.client.on_close = None
            self.client.on_order_message = None
            self.client.on_order_error = None
            self.client.on_order_close = None

            # Perform TOTP login
            payload = self.client.totp_login(
                mobile_number=self.kotak_config['mobile'],
                ucc=self.kotak_config['ucc'],
                totp=pyotp.TOTP(self.kotak_config['totp_key']).now()
            )

            # Save payload for later use (title, etc.)
            self.login_payload = payload

            # Validate with MPIN
            self.client.totp_validate(mpin=self.kotak_config['mpin'])

            # Subscribe to order feed in background
            import threading
            threading.Thread(target=self.client.subscribe_to_orderfeed, daemon=True).start()

            logger.info("Auto-login successful and subscribed to order feed.")

            # --- Diagnostic popup ---
            if root:
                from tkinter import messagebox
                root.after(100, lambda: messagebox.showinfo("Login Status", "Auto-login successful!"))

            return True

        except Exception as e:
            logger.error(f"Auto-login failed: {e}")
            if root:
                from tkinter import messagebox
                error_msg = f"Auto-login failed:\n{e}"   # capture into a local variable
                root.after(100, lambda: messagebox.showerror("Login Status", error_msg))
            return False

    def get_quotes(self, instrument_tokens, quote_type="ltp"):
        if not self.client:
            return None
        try:
            response = self.client.quotes(instrument_tokens=instrument_tokens, quote_type=quote_type)
            if isinstance(response, list):
                return response
            elif isinstance(response, dict):
                logger.error(f"Error in quotes API response: {response}")
                return None
            else:
                logger.warning(f"Unexpected response format from quotes API: {response}")
                return None
        except Exception as e:
            logger.error(f"Exception while fetching quotes: {e}")
            return None

    def get_scrip_master(self, exchange='NFO'):
        if not self.client:
            return None
        try:
            url = self.client.scrip_master(exchange_segment=exchange)
            return url
        except Exception as e:
            logger.error(f"Error getting scrip master URL: {e}")
            return None

    def get_trading_symbols(self, scrip_master_url):
        try:
            df = pd.read_csv(scrip_master_url)
            return sorted(df['pSymbolName'].unique().tolist())
        except Exception as e:
            logger.error(f"Error reading trading symbols: {e}")
            return []

    def get_expiries(self, symbol, scrip_master_url):
        try:
            df = pd.read_csv(scrip_master_url)
            df = df[(df['pSymbolName'] == symbol) & (df['pInstType'] == 'OPTIDX')]
            df['pExpiryDate'] = df['pExpiryDate'].apply(
                lambda x: (dt.datetime.fromtimestamp(x).date() +
                           relativedelta(years=10) -
                           pd.Timedelta(days=1)).strftime('%Y-%m-%d')
            )
            return sorted(set(df['pExpiryDate']))
        except Exception as e:
            logger.error(f"Error reading expiries: {e}")
            return []

    def place_order(self, trading_symbol, price, quantity, transaction_type, product_type='MIS', order_type='MKT', validity='DAY', variety='REGULAR', trigger_price=None, stop_loss_value=None, target_value=None):
        if not self.client:
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
            order_params = {k: v for k, v in order_params.items() if v is not None}
            order_res = self.client.place_order(**order_params)
            logger.info(f"Order placed: {order_res}")
            return order_res
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None
