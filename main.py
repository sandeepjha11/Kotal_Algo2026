import tkinter as tk
from tkinter import ttk
import time
from api_handler import APIHandler
import configparser
from tkinter import messagebox

class TradingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Scalpy Pro (KotakNeo)")
        self.root.configure(bg="#212121")
        self.root.geometry("850x450")

        # --- Config and API ---
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        self.api_handler = APIHandler(self.config)

        # --- Styles ---
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TCombobox", fieldbackground="#3a3a3a", background="#212121", foreground="white", arrowcolor="white")
        self.style.map('TCombobox', fieldbackground=[('readonly', '#3a3a3a')])

        # --- Auto-login ---
        if self.api_handler.autologin():
            self.build_main_ui()
        else:
            messagebox.showerror("Login Failed", "Auto-login failed. Please check your credentials and try again.")
            self.root.quit()

    def build_main_ui(self):
        """Builds the main UI after a successful login."""
        # --- Get Scrip Master URL ---
        self.scrip_master_url = self.api_handler.get_scrip_master()
        if not self.scrip_master_url:
            messagebox.showerror("Error", "Failed to get scrip master. The application will close.")
            self.root.quit()
            return

        # --- Menu ---
        menubar = tk.Menu(self.root, bg="#212121", fg="white")
        self.root.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0, bg="#3a3a3a", fg="white")
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        help_menu = tk.Menu(menubar, tearoff=0, bg="#3a3a3a", fg="white")
        help_menu.add_command(label="About")
        menubar.add_cascade(label="Help", menu=help_menu)

        self.create_widgets()
        self.update_clock()
        self.update_index_prices()
        self.update_atm_strikes()

    def update_clock(self):
        now = time.strftime("%H:%M:%S %p")
        self.clock_label.config(text=now)
        self.root.after(1000, self.update_clock)

    def update_index_prices(self):
        """Fetches and updates the index prices."""
        index_tokens = [
            {'instrument_token': 26000, "exchange_segment": 'nse_cm'}, # NIFTY 50
            {'instrument_token': 26009, "exchange_segment": 'nse_cm'}, # BANKNIFTY
            # Add FINNIFTY and MIDCPNIFTY tokens here
        ]

        quotes = self.api_handler.get_quotes(instrument_tokens=index_tokens)

        if quotes:
            for i, quote in enumerate(quotes):
                if i < len(self.index_price_labels):
                    self.index_price_labels[i].config(text=f"{quote['last_traded_price']:.2f}")

        self.root.after(2000, self.update_index_prices) # Update every 2 seconds

    def update_atm_strikes(self, event=None):
        """Fetches and updates the ATM strike prices and their LTPs."""
        symbol = self.symbol_var.get()
        expiry = self.expiry_var.get()

        if not symbol or not expiry:
            return

        # For simplicity, we'll get the spot LTP and assume ATM is the closest strike.
        # A more robust solution would involve getting the actual spot price.
        spot_ltp = 0.0 # Placeholder
        nifty_token = 26000 # NIFTY 50 token
        spot_ltp = self.api_handler.get_ltp(instrument_token=nifty_token, exchange_segment='nse_cm')


        # Find the closest CE and PE strikes to the spot price
        # This is a simplification. The real logic would be more complex.
        self.ce_strike_info = self.api_handler.get_strike_for_ltp(symbol, expiry, spot_ltp, 'CE', self.scrip_master_url)
        self.pe_strike_info = self.api_handler.get_strike_for_ltp(symbol, expiry, spot_ltp, 'PE', self.scrip_master_url)

        if self.ce_strike_info:
            self.ce_strike_label.config(text=f"{self.ce_strike_info['pStrikePrice']:.1f}")
            self.ce_ltp_label.config(text=f"{self.ce_strike_info['last_traded_price']:.2f}")

        if self.pe_strike_info:
            self.pe_strike_label.config(text=f"{self.pe_strike_info['pStrikePrice']:.1f}")
            self.pe_ltp_label.config(text=f"{self.pe_strike_info['last_traded_price']:.2f}")

        self.root.after(5000, self.update_atm_strikes) # Update every 5 seconds


    def update_expiries(self, event=None):
        """Updates the expiry dropdown based on the selected symbol."""
        symbol = self.symbol_var.get()
        expiries = self.api_handler.get_expiries(symbol, self.scrip_master_url)
        self.combo_expiry['values'] = expiries
        if expiries:
            self.expiry_var.set(expiries[0]) # Set to the first available expiry

    def place_order(self, option_type, transaction_type):
        """Places an order based on the UI selections."""
        symbol = self.symbol_var.get()
        expiry = self.expiry_var.get()

        if option_type == 'CE' and hasattr(self, 'ce_strike_info'):
            trading_symbol = self.ce_strike_info['pTrdSymbol']
            instrument_token = self.ce_strike_info['pSymbol']
        elif option_type == 'PE' and hasattr(self, 'pe_strike_info'):
            trading_symbol = self.pe_strike_info['pTrdSymbol']
            instrument_token = self.pe_strike_info['pSymbol']
        else:
            from tkinter import messagebox
            messagebox.showerror("Error", "No instrument selected. Please wait for data to load.")
            return

        quantity = 15 # Placeholder
        order_type = self.order_type_var.get()
        product_type = self.product_type_var.get()
        quantity = int(self.quantity_var.get())

        stop_loss = None
        target = None
        variety = 'REGULAR'
        if product_type == 'BO':
            variety = 'BO'
            try:
                stop_loss = float(self.sl_var.get())
                target = float(self.tg_var.get())
            except ValueError:
                from tkinter import messagebox
                messagebox.showerror("Error", "Invalid Stop Loss or Target value for Bracket Order.")
                return

        res = self.api_handler.place_order(
            trading_symbol=instrument_token,
            price=0, # Market order for now
            quantity=quantity,
            transaction_type=transaction_type,
            product_type=product_type,
            order_type=order_type,
            variety=variety,
            stop_loss_value=stop_loss,
            target_value=target
        )

        if res:
            # In a real app, you would show a more informative message
            from tkinter import messagebox
            messagebox.showinfo("Success", "Order placed successfully!")
        else:
            from tkinter import messagebox
            messagebox.showerror("Error", "Failed to place order.")


    def create_widgets(self):
        # --- Top Frame ---
        top_frame = tk.Frame(self.root, bg="#212121")
        top_frame.pack(pady=5, padx=10, fill='x')

        btn_logout = tk.Button(top_frame, text="Logout", bg="#4a4a4a", fg="white", relief="flat")
        btn_logout.pack(side="left", padx=(0, 10))

        self.index_price_labels = []
        indices = {"NIFTY 50": "24654.7", "BANKNIFTY": "54389.35", "FINNIFTY": "25985.25", "MIDCPNIFTY": "12563.35"}
        for name, price in indices.items():
            frame = tk.Frame(top_frame, bg="#3a3a3a", bd=1, relief="solid")
            lbl_name = tk.Label(frame, text=name, bg="#3a3a3a", fg="white", font=("Arial", 9, "bold"))
            lbl_name.pack(padx=10, pady=(2,0))
            lbl_price = tk.Label(frame, text=price, bg="#3a3a3a", fg="#00b050", font=("Arial", 10, "bold"))
            lbl_price.pack(padx=10, pady=(0,2))
            self.index_price_labels.append(lbl_price)
            frame.pack(side="left", padx=5)

        self.clock_label = tk.Label(top_frame, text="", bg="#00b050", fg="black", font=("Arial", 12, "bold"), padx=10)
        self.clock_label.pack(side="left", padx=10)

        btn_logs = tk.Button(top_frame, text="Logs", bg="#4a4a4a", fg="white", relief="flat")
        btn_logs.pack(side="left", padx=10)

        # --- Main Frame ---
        main_frame = tk.Frame(self.root, bg="#212121")
        main_frame.pack(pady=5, padx=10, fill="both", expand=True)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)

        # --- Left Frame ---
        left_frame = tk.Frame(main_frame, bg="#212121")
        left_frame.grid(row=0, column=0, padx=(0, 5), sticky="nsew")

        # Symbol & Expiry
        tk.Label(left_frame, text="Symbol:", bg="#212121", fg="white").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        symbol_frame = tk.Frame(left_frame, bg="#212121")
        symbol_frame.grid(row=0, column=1, sticky="w")

        self.symbol_var = tk.StringVar()
        self.combo_symbol = ttk.Combobox(symbol_frame, textvariable=self.symbol_var, width=10)
        self.combo_symbol['values'] = self.api_handler.get_trading_symbols(self.scrip_master_url)
        self.combo_symbol.pack(side="left")
        self.symbol_var.set("NIFTY") # Default symbol
        self.combo_symbol.bind("<<ComboboxSelected>>", self.update_expiries)

        tk.Button(symbol_frame, text="[+]", bg="#4a4a4a", fg="white", relief="flat", width=2).pack(side="left", padx=2)

        tk.Label(left_frame, text="Expiry:", bg="#212121", fg="white").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.expiry_var = tk.StringVar()
        self.combo_expiry = ttk.Combobox(left_frame, textvariable=self.expiry_var, width=10)
        self.combo_expiry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        self.update_expiries() # Initial population
        self.combo_expiry.bind("<<ComboboxSelected>>", self.update_atm_strikes)


        # Margin & MTM
        tk.Label(left_frame, text="Margin:", bg="#212121", fg="white").grid(row=0, column=2, padx=(20, 5), pady=5, sticky="w")
        tk.Label(left_frame, text="0.0", bg="#212121", fg="white").grid(row=0, column=3, padx=5, pady=5, sticky="w")
        tk.Label(left_frame, text="MTM:", bg="#212121", fg="white").grid(row=1, column=2, padx=(20, 5), pady=5, sticky="w")
        tk.Label(left_frame, text="0.0", bg="#212121", fg="white").grid(row=1, column=3, padx=5, pady=5, sticky="w")

        # Order Controls
        order_frame = tk.Frame(left_frame, bg="#212121")
        order_frame.grid(row=2, column=0, columnspan=4, pady=10, sticky="w")

        self.quantity_var = tk.StringVar(value="15")
        tk.Entry(order_frame, textvariable=self.quantity_var, width=8, bg="#d4aa00", relief="flat").pack(side="left", padx=5)

        self.order_type_var = tk.StringVar(value="MKT")
        ttk.Combobox(order_frame, textvariable=self.order_type_var, values=["MKT", "LMT"], width=5).pack(side="left", padx=5)

        self.product_type_var = tk.StringVar(value="BO")
        ttk.Combobox(order_frame, textvariable=self.product_type_var, values=["BO", "MIS", "NRML"], width=5).pack(side="left", padx=5)

        self.sl_var = tk.StringVar(value="10")
        tk.Entry(order_frame, textvariable=self.sl_var, width=4).pack(side="left", padx=5)

        self.tg_var = tk.StringVar(value="20")
        tk.Entry(order_frame, textvariable=self.tg_var, width=4).pack(side="left", padx=5)

        # Action Buttons
        action_frame = tk.Frame(left_frame, bg="#212121")
        action_frame.grid(row=3, column=0, columnspan=4, pady=5, sticky="w")
        tk.Button(action_frame, text="Positions", bg="#4a4a4a", fg="white", relief="flat").pack(side="left", padx=5)
        tk.Button(action_frame, text="Cancel", bg="#4a4a4a", fg="white", relief="flat").pack(side="left", padx=5)
        tk.Button(action_frame, text="Exit", bg="#4a4a4a", fg="white", relief="flat").pack(side="left", padx=5)
        tk.Entry(action_frame, width=4).pack(side="left", padx=5)
        tk.Button(action_frame, text="Modify", bg="#4a4a4a", fg="white", relief="flat").pack(side="left", padx=5)

        # AutoTrail
        autotrail_frame = tk.Frame(left_frame, bg="#212121")
        autotrail_frame.grid(row=4, column=0, columnspan=4, pady=10, sticky="w")
        tk.Checkbutton(autotrail_frame, text="AutoTrail", bg="#212121", fg="white", selectcolor="#212121", activebackground="#212121", activeforeground="white", highlightthickness=0).pack(side="left", padx=5)
        ttk.Combobox(autotrail_frame, values=["None"], width=8).pack(side="left", padx=5)

        # --- Right Frame ---
        right_frame = tk.Frame(main_frame, bg="#212121")
        right_frame.grid(row=0, column=1, padx=(5, 0), sticky="nsew")
        right_frame.grid_columnconfigure((0,1), weight=1)

        # ATM selection
        combo_ce_atm = ttk.Combobox(right_frame, values=["ATM"], width=8)
        combo_ce_atm.grid(row=0, column=0, pady=5, sticky="ew")
        combo_ce_atm.set("ATM")
        combo_pe_atm = ttk.Combobox(right_frame, values=["ATM"], width=8)
        combo_pe_atm.grid(row=0, column=1, pady=5, sticky="ew")
        combo_pe_atm.set("ATM")

        # Strike prices
        self.ce_strike_label = tk.Label(right_frame, text="0.0", bg="#3a3a3a", fg="white", font=("Arial", 10, "bold"))
        self.ce_strike_label.grid(row=1, column=0, pady=2, sticky="ew")
        self.pe_strike_label = tk.Label(right_frame, text="0.0", bg="#3a3a3a", fg="white", font=("Arial", 10, "bold"))
        self.pe_strike_label.grid(row=1, column=1, pady=2, sticky="ew")

        # LTP
        self.ce_ltp_label = tk.Label(right_frame, text="0.00", bg="#00b050", fg="black", font=("Arial", 10, "bold"))
        self.ce_ltp_label.grid(row=2, column=0, pady=2, sticky="ew")
        self.pe_ltp_label = tk.Label(right_frame, text="0.00", bg="#00b050", fg="black", font=("Arial", 10, "bold"))
        self.pe_ltp_label.grid(row=2, column=1, pady=2, sticky="ew")

        # Buttons
        tk.Button(right_frame, text="Buy CE", bg="#4a4a4a", fg="white", relief="flat", command=lambda: self.place_order('CE', 'B')).grid(row=3, column=0, pady=2, sticky="ew")
        tk.Button(right_frame, text="Buy PE", bg="#4a4a4a", fg="white", relief="flat", command=lambda: self.place_order('PE', 'B')).grid(row=3, column=1, pady=2, sticky="ew")
        tk.Button(right_frame, text="Sell CE", bg="#d9534f", fg="white", relief="flat", command=lambda: self.place_order('CE', 'S')).grid(row=4, column=0, pady=2, sticky="ew")
        tk.Button(right_frame, text="Sell PE", bg="#d9534f", fg="white", relief="flat", command=lambda: self.place_order('PE', 'S')).grid(row=4, column=1, pady=2, sticky="ew")
        tk.Button(right_frame, text="Exit CE", bg="#f0ad4e", fg="black", relief="flat").grid(row=5, column=0, pady=2, sticky="ew")
        tk.Button(right_frame, text="Exit PE", bg="#f0ad4e", fg="black", relief="flat").grid(row=5, column=1, pady=2, sticky="ew")
        tk.Button(right_frame, text="Exit All", bg="#f0ad4e", fg="black", relief="flat").grid(row=6, column=0, columnspan=2, pady=10, sticky="ew")

        # --- Bottom Frame ---
        bottom_frame = tk.Frame(self.root, bg="#212121")
        bottom_frame.pack(pady=5, padx=10, fill='x')

        tk.Label(bottom_frame, text="CE: BANKEX25OCT61300CE\nPE: BANKEX25OCT61300PE", bg="#212121", fg="red", justify="left").pack(side="left")
        tk.Label(bottom_frame, text="v3.0", bg="#212121", fg="grey").pack(side="right")


if __name__ == "__main__":
    root = tk.Tk()
    app = TradingApp(root)
    root.mainloop()
