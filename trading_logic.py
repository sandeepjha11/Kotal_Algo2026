# trading_logic.py
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class TradingLogic:
    def __init__(self, api_handler):
        self.api_handler = api_handler

    def get_instrument_token(self, symbol_name, scrip_master_url):
        """Finds the instrument token for a given symbol name from the cash market scrip master."""
        try:
            df = pd.read_csv(scrip_master_url)
            # The scrip master uses "NIFTY" and "BANKNIFTY" directly.
            # No mapping is needed, just a direct lookup.
            instrument = df[df['pSymbolName'] == symbol_name].iloc[0]
            return instrument['pSymbol']
        except Exception as e:
            logger.error(f"Could not find instrument token for {symbol_name}: {e}")
            return None

    def get_atm_strikes(self, symbol, expiry, nfo_scrip_master_url, cm_scrip_master_url):
        """
        Calculates the At-The-Money (ATM) strike price for a given symbol
        and fetches the full instrument data for the CE and PE options at that strike.
        """
        try:
            # 1. Get the spot price of the underlying index
            index_token = self.get_instrument_token(symbol, cm_scrip_master_url)
            if not index_token:
                logger.error(f"Could not get token for the index: {symbol}")
                return None, None

            quotes = self.api_handler.get_quotes(
                instrument_tokens=[{'instrument_token': index_token, 'exchange_segment': 'nse_cm'}],
                quote_type='ltp'
            )
            if not quotes or 'last_traded_price' not in quotes[0]:
                logger.error("Could not fetch spot price for ATM calculation.")
                return None, None

            spot_price = float(quotes[0]['last_traded_price'])

            # 2. Read the NFO scrip master to find the closest strike
            df = pd.read_csv(nfo_scrip_master_url)
            df['pStrikePrice'] = pd.to_numeric(df['pStrikePrice'], errors='coerce')

            # Filter for the symbol and expiry
            options_df = df[(df['pSymbolName'] == symbol) & (df['pInstType'] == 'OPTIDX')]

            # Find the strike price closest to the spot price
            atm_strike = options_df.iloc[(options_df['pStrikePrice'] - spot_price).abs().argsort()[:1]].iloc[0]
            atm_strike_price = atm_strike['pStrikePrice']

            # 3. Find the CE and PE instruments for that ATM strike
            ce_instrument = options_df[(options_df['pStrikePrice'] == atm_strike_price) & (options_df['pOptionType'] == 'CE')].iloc[0].to_dict()
            pe_instrument = options_df[(options_df['pStrikePrice'] == atm_strike_price) & (options_df['pOptionType'] == 'PE')].iloc[0].to_dict()

            # 4. Get live quotes for these instruments
            instrument_tokens = [
                {'instrument_token': ce_instrument['pSymbol'], 'exchange_segment': 'NFO'},
                {'instrument_token': pe_instrument['pSymbol'], 'exchange_segment': 'NFO'}
            ]
            live_quotes = self.api_handler.get_quotes(instrument_tokens)

            # 5. Add the live LTP to the instrument data
            if live_quotes:
                for quote in live_quotes:
                    if quote['instrument_token'] == ce_instrument['pSymbol']:
                        ce_instrument['last_traded_price'] = quote['last_traded_price']
                    if quote['instrument_token'] == pe_instrument['pSymbol']:
                        pe_instrument['last_traded_price'] = quote['last_traded_price']

            return ce_instrument, pe_instrument

        except Exception as e:
            logger.exception(f"Error calculating ATM strikes: {e}")
            return None, None
