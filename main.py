import tkinter as tk
from tkinter import ttk, messagebox
import time, json, configparser
import queue
from api_handler import APIHandler
from trading_logic import TradingLogic


class TradingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SAN Pro (KotakNeo)")
        self.root.configure(bg="#212121")
        self.root.geometry("850x450")

        # Overlay behavior
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.85)

        # --- Config and API ---
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        self.api_handler = APIHandler(self.config)
        self.trading_logic = TradingLogic(self.api_handler)
        self.tick_queue = queue.Queue()
        self.live_prices = {}

        # --- Styles ---
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure(
            "TCombobox",
            fieldbackground="#3a3a3a",
            background="#212121",
            foreground="white",
            arrowcolor="white"
        )
        self.style.map('TCombobox', fieldbackground=[('readonly', '#3a3a3a')])

        # Prepare empty mapping so callback never fails
        self.token_label_map = {}

        # --- Auto-login ---
        if self.api_handler.autologin(root=self.root):
            # Bind websocket callbacks
            self.api_handler.client.on_message = self.on_message
            self.api_handler.client.on_error = self.on_error
            self.api_handler.client.on_open = self.on_open
            self.api_handler.client.on_close = self.on_close

            # Subscribe to indexes (use names, not numeric IDs)
            inst_tokens = [
                {"instrument_token": "Nifty 50", "exchange_segment": "nse_cm"},
                {"instrument_token": "Nifty Bank", "exchange_segment": "nse_cm"},
                {"instrument_token": "SENSEX", "exchange_segment": "bse_cm"}
            ]
            self.api_handler.client.subscribe(
                instrument_tokens=inst_tokens,
                isIndex=True,
                isDepth=False
            )

            self.build_main_ui()
        else:
            self.root.quit()

    def build_main_ui(self):
        """Builds the main UI after a successful login."""

        # --- Update title with client name ---
        client_name = None
        if hasattr(self.api_handler, "login_payload"):
            client_name = self.api_handler.login_payload.get("data", {}).get("greetingName")
        if client_name:
            self.root.title(f"SAN Pro (KotakNeo) - {client_name}")

        # --- Get Scrip Master URLs ---
        self.nfo_scrip_master_url = self.api_handler.get_scrip_master(exchange='NFO')
        self.cm_scrip_master_url = self.api_handler.get_scrip_master(exchange='nse_cm')

        if not self.nfo_scrip_master_url or not self.cm_scrip_master_url:
            messagebox.showerror("Error", "Failed to get scrip master files. The application will close.")
            self.root.quit()
            return

        # ✅ Success message
        messagebox.showinfo("Success", f"Scrip master files loaded successfully for {client_name}!")

        # --- Menu ---
        menubar = tk.Menu(self.root, bg="#212121", fg="white")
        self.root.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0, bg="#3a3a3a", fg="white")
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        help_menu = tk.Menu(menubar, tearoff=0, bg="#3a3a3a", fg="white")
        help_menu.add_command(label="About")
        menubar.add_cascade(label="Help", menu=help_menu)

        # --- Build widgets and start updates ---
        self.create_widgets()
        self.update_clock()
        self.process_queue()  # Start the queue processor
        self.update_atm_strikes()

    def update_clock(self):
        """Updates the clock label every second."""
        now = time.strftime("%I:%M:%S %p")
        self.clock_label.config(text=now)
        self.root.after(1000, self.update_clock)

    def process_queue(self):
        """Processes ticks from the queue and updates the UI in the main thread."""
        try:
            while not self.tick_queue.empty():
                token, ltp = self.tick_queue.get_nowait()

                # Cache the raw price
                self.live_prices[token] = ltp

                # Update the UI label
                if token in self.token_label_map and ltp is not None:
                    try:
                        new_text = f"{float(ltp):.2f}"
                        self.token_label_map[token].set(new_text)
                    except (ValueError, TypeError):
                        self.token_label_map[token].set(str(ltp))
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)

    # --- WebSocket Callbacks ---
    def on_message(self, message):
        """Callback from the WebSocket, runs in a background thread."""
        try:
            if isinstance(message, str):
                message = json.loads(message)

            data = message.get("data", [])
            if isinstance(data, str):
                return  # ignore order feed

            if isinstance(data, dict):
                data = [data]

            for tick in data:
                token = tick.get("tk") or tick.get("instrument_token")
                ltp = tick.get("iv") or tick.get("ltp")

                # Put the tick data into the queue for the main thread to process
                if token and ltp is not None:
                    self.tick_queue.put((token, ltp))

        except Exception as e:
            print("Tick parse error:", e)
            print("Raw message:", message)

    def on_error(self, message):
        print("[OnError]:", message)

    def on_open(self, message):
        print("[OnOpen]: Callback fired")


    def on_close(self, message):
        print("[OnClose]:", message)

    def update_atm_strikes(self, event=None):
        """Fetches and updates the ATM strike prices and their LTPs using the live spot price."""
        symbol = self.symbol_var.get()
        expiry = self.expiry_var.get()
        if not symbol or not expiry:
            return

        # Map the UI symbol to the one used in WebSocket ticks (e.g., "NIFTY" -> "Nifty 50")
        symbol_map = {
            "NIFTY": "Nifty 50",
            "BANKNIFTY": "Nifty Bank"
        }
        tick_symbol = symbol_map.get(symbol, symbol)

        # Get the live spot price from our cache
        spot_price = self.live_prices.get(tick_symbol)
        if not spot_price:
            # If the price isn't in the cache yet, reschedule and wait for the next tick
            self.root.after(1000, self.update_atm_strikes)
            return

        ce_info, pe_info = self.trading_logic.get_atm_strikes(
            symbol, expiry, float(spot_price), self.nfo_scrip_master_url
        )
        self.ce_strike_info, self.pe_strike_info = ce_info, pe_info

        # --- Update CE labels ---
        if isinstance(ce_info, dict):
            try:
                strike = float(ce_info.get('pStrikePrice', 0.0))
                ltp = float(ce_info.get('last_traded_price', 0.0))
                self.ce_strike_label.config(text=f"{strike:.1f}")
                self.ce_ltp_label.config(text=f"{ltp:.2f}")
            except (ValueError, TypeError):
                self.ce_strike_label.config(text="Error")
                self.ce_ltp_label.config(text="Error")

        # --- Update PE labels ---
        if isinstance(pe_info, dict):
            try:
                strike = float(pe_info.get('pStrikePrice', 0.0))
                ltp = float(pe_info.get('last_traded_price', 0.0))
                self.pe_strike_label.config(text=f"{strike:.1f}")
                self.pe_ltp_label.config(text=f"{ltp:.2f}")
            except (ValueError, TypeError):
                self.pe_strike_label.config(text="Error")
                self.pe_ltp_label.config(text="Error")

        # --- Schedule next update ---
        self.root.after(5000, self.update_atm_strikes)


    def update_expiries(self, event=None):
        """Updates the expiry dropdown based on the selected symbol."""
        symbol = self.symbol_var.get()
        expiries = self.api_handler.get_expiries(symbol, self.nfo_scrip_master_url)
        self.combo_expiry['values'] = expiries
        if expiries:
            self.expiry_var.set(expiries[0]) # Set to the first available expiry

    def place_order(self, option_type: str, transaction_type: str):
        """Places an order based on the UI selections."""

        # --- Validate strike info ---
        if option_type == 'CE' and hasattr(self, 'ce_strike_info'):
            strike_info = self.ce_strike_info
        elif option_type == 'PE' and hasattr(self, 'pe_strike_info'):
            strike_info = self.pe_strike_info
        else:
            messagebox.showerror("Error", "No instrument selected. Please wait for data to load.")
            return

        trading_symbol = strike_info.get('pTrdSymbol')
        instrument_token = strike_info.get('pSymbol')

        # --- Order parameters ---
        try:
            quantity = int(self.quantity_var.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid quantity.")
            return

        order_type = self.order_type_var.get()
        product_type = self.product_type_var.get()
        variety = 'BO' if product_type == 'BO' else 'REGULAR'

        stop_loss = None
        target = None
        if product_type == 'BO':
            try:
                stop_loss = float(self.sl_var.get())
                target = float(self.tg_var.get())
            except ValueError:
                messagebox.showerror("Error", "Invalid Stop Loss or Target value for Bracket Order.")
                return

        # --- Place order via API handler ---
        res = self.api_handler.place_order(
            trading_symbol=instrument_token,
            price=0,  # Market order for now
            quantity=quantity,
            transaction_type=transaction_type,
            product_type=product_type,
            order_type=order_type,
            variety=variety,
            stop_loss_value=stop_loss,
            target_value=target
        )

        # --- Feedback to user ---
        if res:
            messagebox.showinfo("Success", f"Order placed successfully!\nDetails: {res}")
        else:
            messagebox.showerror("Error", "Failed to place order.")

    def create_widgets(self):
        top_frame = tk.Frame(self.root, bg="#212121")
        top_frame.pack(pady=5, padx=10, fill='x')

        btn_logout = tk.Button(top_frame, text="Logout", bg="#4a4a4a", fg="white", relief="flat")
        btn_logout.pack(side="left", padx=(0, 10))

        # --- Index labels using StringVar ---
        self.index_vars = {}
        indices = ["Nifty 50", "Nifty Bank", "SENSEX"]

        for name in indices:
            frame = tk.Frame(top_frame, bg="#3a3a3a", bd=1, relief="solid")
            lbl_name = tk.Label(frame, text=name, bg="#3a3a3a", fg="white", font=("Arial", 9, "bold"))
            lbl_name.pack(padx=10, pady=(2,0))

            var = tk.StringVar(value="0.00")   # start with 0.00
            lbl_price = tk.Label(frame, textvariable=var, bg="#3a3a3a", fg="#00b050", font=("Arial", 10, "bold"))
            lbl_price.pack(padx=10, pady=(0,2))

            self.index_vars[name] = var
            frame.pack(side="left", padx=5)

        # ✅ Mapping moved here so ticks can update immediately
        self.token_label_map = {
            "Nifty 50": self.index_vars["Nifty 50"],
            "Nifty Bank": self.index_vars["Nifty Bank"],
            "SENSEX": self.index_vars["SENSEX"]
        }

        btn_logs = tk.Button(top_frame, text="logs", bg="#4a4a4a", fg="white", relief="flat")
        btn_logs.pack(side="right", padx=10)

        self.clock_label = tk.Label(top_frame, text="", bg="#00b050", fg="black", font=("Arial", 12, "bold"), padx=10)
        self.clock_label.pack(side="right", padx=10)

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
        self.combo_symbol['values'] = self.api_handler.get_trading_symbols(self.nfo_scrip_master_url)
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

        self.margin_var = tk.StringVar(value="0.0")
        self.mtm_var = tk.StringVar(value="0.0")

        tk.Label(left_frame, text="Margin:", bg="#212121", fg="white").grid(
            row=0, column=2, padx=(20, 5), pady=5, sticky="w"
        )
        tk.Label(left_frame, textvariable=self.margin_var, bg="#212121", fg="white").grid(
            row=0, column=3, padx=5, pady=5, sticky="w"
        )

        tk.Label(left_frame, text="MTM:", bg="#212121", fg="white").grid(
            row=1, column=2, padx=(20, 5), pady=5, sticky="w"
        )
        tk.Label(left_frame, textvariable=self.mtm_var, bg="#212121", fg="white").grid(
            row=1, column=3, padx=5, pady=5, sticky="w"
        )

        # Order Controls
        order_frame = tk.Frame(left_frame, bg="#212121")
        order_frame.grid(row=2, column=0, columnspan=4, pady=10, sticky="w")

        self.quantity_var = tk.StringVar(value="65")
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

        # Container for CE + PE
        ce_pe_container = tk.Frame(right_frame, bg="#212121")
        ce_pe_container.pack(side="top", fill="both", expand=True)

        # CE frame stretches equally
        ce_frame = tk.Frame(ce_pe_container, bg="#212121")
        ce_frame.pack(side="left", fill="both", expand=True, padx=(0, 20))

        # PE frame stretches equally
        pe_frame = tk.Frame(ce_pe_container, bg="#212121")
        pe_frame.pack(side="left", fill="both", expand=True)

        # --- CE widgets ---
        combo_ce_atm = ttk.Combobox(ce_frame, values=["ATM"])
        combo_ce_atm.pack(pady=5, fill="x")
        combo_ce_atm.set("ATM")

        self.ce_strike_label = tk.Label(ce_frame, text="0.0", bg="#3a3a3a", fg="white", font=("Arial", 10, "bold"))
        self.ce_strike_label.pack(pady=2, fill="x")

        self.ce_ltp_label = tk.Label(ce_frame, text="0.00", bg="#00b050", fg="black", font=("Arial", 10, "bold"))
        self.ce_ltp_label.pack(pady=2, fill="x")

        tk.Button(ce_frame, text="Buy CE", bg="#4a4a4a", fg="white", relief="flat",
                command=lambda: self.place_order('CE', 'B')).pack(pady=2, fill="x")
        tk.Button(ce_frame, text="Sell CE", bg="#d9534f", fg="white", relief="flat",
                command=lambda: self.place_order('CE', 'S')).pack(pady=2, fill="x")
        tk.Button(ce_frame, text="Exit CE", bg="#f0ad4e", fg="black", relief="flat").pack(pady=2, fill="x")

        # --- PE widgets ---
        combo_pe_atm = ttk.Combobox(pe_frame, values=["ATM"])
        combo_pe_atm.pack(pady=5, fill="x")
        combo_pe_atm.set("ATM")

        self.pe_strike_label = tk.Label(pe_frame, text="0.0", bg="#3a3a3a", fg="white", font=("Arial", 10, "bold"))
        self.pe_strike_label.pack(pady=2, fill="x")

        self.pe_ltp_label = tk.Label(pe_frame, text="0.00", bg="#00b050", fg="black", font=("Arial", 10, "bold"))
        self.pe_ltp_label.pack(pady=2, fill="x")

        tk.Button(pe_frame, text="Buy PE", bg="#4a4a4a", fg="white", relief="flat",
                command=lambda: self.place_order('PE', 'B')).pack(pady=2, fill="x")
        tk.Button(pe_frame, text="Sell PE", bg="#d9534f", fg="white", relief="flat",
                command=lambda: self.place_order('PE', 'S')).pack(pady=2, fill="x")
        tk.Button(pe_frame, text="Exit PE", bg="#f0ad4e", fg="black", relief="flat").pack(pady=2, fill="x")

        # --- Exit All button (below both frames) ---
        tk.Button(right_frame, text="Exit All", bg="#f0ad4e", fg="black", relief="flat").pack(
            side="bottom", pady=10, fill="x"
        )
        # --- Bottom Frame ---
        bottom_frame = tk.Frame(self.root, bg="#212121")
        bottom_frame.pack(pady=5, padx=10, fill='x')

        tk.Label(bottom_frame, text="CE: BANKEX25OCT61300CE\nPE: BANKEX25OCT61300PE", bg="#212121", fg="red", justify="left").pack(side="left")
        tk.Label(bottom_frame, text="v3.0", bg="#212121", fg="grey").pack(side="right")


if __name__ == "__main__":
    root = tk.Tk()
    app = TradingApp(root)
    root.mainloop()
