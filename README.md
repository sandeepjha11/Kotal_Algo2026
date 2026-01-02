# Excel-Based Trading System for Kotak Neo

This project provides an Excel-based trading system for the Kotak Neo Broker. The system allows you to manage credentials, define trading settings, view a live option chain, and execute trades directly from an Excel spreadsheet.

## Installation

1.  **Prerequisites:**
    *   Python 3.x
    *   Pip

2.  **Install the required Python libraries:**

    ```bash
    pip install -r requirements.txt
    ```

    *Note: If a `requirements.txt` file is not available, you can install the libraries manually:*

    ```bash
    pip install pandas openpyxl neo-api-client pyotp
    ```

## Usage

1.  **Run the main script:**

    ```bash
    python3 main.py
    ```

    On the first run, the script will generate a `trading_system.xlsx` file in the same directory.

2.  **Configure the system:**

    Open the `trading_system.xlsx` file and fill in your credentials and trading settings in the "Credentials" and "Settings" sheets.

3.  **Start trading:**

    Once the system is configured, you can start trading by adding trade signals to the "Trading" sheet. The system will automatically execute the trades and update the status in the same sheet.

## Excel File Structure

The `trading_system.xlsx` file contains four sheets:

### 1. Credentials

This sheet is used to store your Kotak Neo API credentials.

| Column | Description |
| --- | --- |
| **Consumer Key** | Your API consumer key. |
| **Consumer Secret** | Your API consumer secret. |
| **Mobile Number** | Your registered mobile number. |
| **Password** | Your trading account password. |
| **MPIN** | Your MPIN. |
| **TOTP**| Your TOTP key for 2FA. |
| **UCC** | Your UCC. |

***

**SECURITY WARNING:** Storing your credentials in a plaintext file is a security risk. Anyone with access to this file can access your trading account.

***

### 2. Settings

This sheet is used to define your trading settings.

| Column | Description |
| --- | --- |
| **Underlying** | The underlying symbol (e.g., "NIFTY"). |
| **Lot Size** | The number of lots to trade. |
| **Premium Amount** | The premium amount for the options. |
| **Expiry Dates** | The expiry date for the options (YYYY-MM-DD). |
| **Entry Time** | The time to enter trades (HH:MM:SS). |
| **Exit Time** | The time to exit trades (HH:MM:SS). |
| **SL Limit** | The stop-loss limit as a percentage. |

### 3. Option Chain

This sheet displays the live option chain for the underlying symbol. The option chain is filtered to show the ATM strike price +/- 5 strikes.

| Column | Description |
| --- | --- |
| **Strike Price** | The strike price of the option. |
| **LTP** | The Last Traded Price. |
| **Open** | The open price. |
| **High** | The high price. |
| **Low** | The low price. |
| **Close** | The close price. |
| **Volume** | The trading volume. |

### 4. Trading

This sheet is used to initiate and monitor trades. To place a trade, add a new row with the strike price, option type, and buy/sell action. The system will automatically execute the trade and update the status, entry price, and MTM.

| Column | Description |
| --- | --- |
| **Strike Price** | The strike price of the option to trade. |
| **Option Type** | The option type (CE/PE). |
| **Buy/Sell** | The trade action (B/S). |
| **Status** | The status of the trade (e.g., "Placed," "Executed," "Rejected"). |
| **Entry Price** | The price at which the trade was executed. |
| **Exit Price** | The price at which the trade was exited. |
| **SL** | The stop-loss for the trade. |
| **MTM** | The Mark-to-Market profit/loss. |
