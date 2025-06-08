import tkinter as tk
from tkinter import ttk
import threading
import ccxt

exchanges_info = {
    'kraken': {'spot': 'XMR/USDT', 'future': 'XMR/USD:USD'},
    'bitfinex2': {'spot': 'XMR/USDT', 'future': 'XMR/USDT:USDT'},
    'marblefx': {'spot': 'XMR/USDT', 'future': 'XMR/USDT:USDT'},
    'htx': {'spot': 'XMR/USDT', 'future': 'XMR/USDT:USDT'},
    'mexc': {'spot': 'XMR/USDT', 'future': 'XMR/USDT:USDT'},
    'coinex': {'spot': 'XMR/USDT', 'future': 'XMR/USDT:USDT'},
    'kucoin': {'spot': 'XMR/USDT', 'future': 'XMR/USDT:USDT'},
    'bitmart': {'spot': 'XMR/USDT', 'future': 'XMR/USDT:USDT'},
    'whitebit': {'spot': 'XMR/USDT', 'future': 'XMR/USDT:USDT'},
    'xt': {'spot': 'XMR/USDT', 'future': 'XMR/USDT:USDT'},
}

class XMRTerminal(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MarbleView")
        self.geometry("1000x450")

        # Track current theme
        self.current_theme = "light"
        self.style = ttk.Style(self)
        self.configure_themes()

        # Theme toggle button
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)

        theme_btn = ttk.Button(btn_frame, text="#", command=self.toggle_theme)
        theme_btn.pack(side=tk.LEFT, padx=5)

        refresh_btn = ttk.Button(btn_frame, text="###", command=self.refresh_all)
        refresh_btn.pack(side=tk.LEFT, padx=5)

        columns = ("Exchange", "Spot Price", "Spot Volume", "Futures Price", "Futures Volume", "TrueRate (%)", "Funding Rate (%)")
        self.tree = ttk.Treeview(self, columns=columns, show='headings')
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor=tk.CENTER, width=130)
        self.tree.pack(expand=True, fill=tk.BOTH)

        self.apply_theme(self.current_theme)

        self.exchange_items = {}
        for ex_id in sorted(exchanges_info.keys()):
            item_id = self.tree.insert("", tk.END, values=(ex_id, "Loading...", "", "", "", "", ""))
            self.exchange_items[ex_id] = item_id

        self.refresh_all()
        self.auto_refresh_interval_ms = 5_000
        self.after(self.auto_refresh_interval_ms, self.auto_refresh)

    def configure_themes(self):
        self.style.theme_use('clam')  # More customizable than default themes

        # Light theme
        self.style.configure("light.Treeview", 
                             background="white", 
                             foreground="black",
                             fieldbackground="white")
        self.style.configure("light.Treeview.Heading", 
                             background="#e1e1e1", 
                             foreground="black")
        self.style.configure("light.TFrame", background="#f0f0f0")
        self.style.configure("light.TButton",
                             background="#e0e0e0",
                             foreground="black")
    
        # Dark theme
        self.style.configure("dark.Treeview", 
                             background="#2e2e2e", 
                             foreground="white", 
                             fieldbackground="#2e2e2e")
        self.style.configure("dark.Treeview.Heading", 
                             background="#444", 
                             foreground="white")
        self.style.configure("dark.TFrame", background="#2e2e2e")
        self.style.configure("dark.TButton",
                             background="#444",
                             foreground="white")
        
    def apply_theme(self, theme_name):
        self.tree.configure(style=f"{theme_name}.Treeview")
        if theme_name == "dark":
            self.configure(bg="#2e2e2e")
        else:
            self.configure(bg="#f0f0f0")


    def toggle_theme(self):
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        self.apply_theme(self.current_theme)

    def refresh_all(self):
        for ex_id in exchanges_info.keys():
            threading.Thread(target=self.fetch_exchange_data, args=(ex_id,), daemon=True).start()

    def auto_refresh(self):
        self.refresh_all()
        self.after(self.auto_refresh_interval_ms, self.auto_refresh)

    def fetch_exchange_data(self, ex_id):
        def update_ui(*values):
            self.after(0, self._update_row, ex_id, *values)

        symbols = exchanges_info[ex_id]
        try:
            if ex_id == 'kraken':
                spot_exchange = ccxt.kraken({'enableRateLimit': True})
                future_exchange = ccxt.krakenfutures({'enableRateLimit': True})
            elif ex_id == 'kucoin':
                spot_exchange = ccxt.kucoin({'enableRateLimit': True})
                future_exchange = ccxt.kucoinfutures({'enableRateLimit': True})
            else:
                exchange_class = getattr(ccxt, ex_id)
                spot_exchange = future_exchange = exchange_class({'enableRateLimit': True})

            spot_exchange.load_markets()
            future_exchange.load_markets()

            spot_symbol = symbols['spot']
            future_symbol = symbols['future']

            spot_ticker = spot_exchange.fetch_ticker(spot_symbol)
            future_ticker = future_exchange.fetch_ticker(future_symbol)

            spot_price = spot_ticker.get('last') or ((spot_ticker.get('bid') or 0) + (spot_ticker.get('ask') or 0)) / 2
            futures_price = future_ticker.get('last') or ((future_ticker.get('bid') or 0) + (future_ticker.get('ask') or 0)) / 2
            spot_volume = spot_ticker.get('quoteVolume') or 0
            futures_volume = future_ticker.get('quoteVolume') or 0

            if (not spot_price) or (not futures_price):
                raise ValueError("Missing price data")

            funding_rate = (futures_price - spot_price) / spot_price * 100

            def fmt_vol(vol):
                return f"{vol:,.0f}" if vol > 0 else "-"

            exchange_funding_rate = "-"
            try:
                if hasattr(future_exchange, 'fetch_funding_rate') and future_exchange.has.get('fetchFundingRate'):
                    fr_data = future_exchange.fetch_funding_rate(future_symbol)
                    exchange_funding_rate = f"{fr_data.get('fundingRate', 0) * 100:+.4f}%"
            except Exception:
                print('exchange funding rate not supported for', ex_id)
                pass  # if not supported

            update_ui(
                f"{spot_price:.2f}",
                fmt_vol(spot_volume),
                f"{futures_price:.2f}",
                fmt_vol(futures_volume),
                f"{funding_rate:+.2f}%",
                exchange_funding_rate
            )
        except Exception as e:
            update_ui("", "", "", "", f"Error: {str(e)}")

    def _update_row(self, ex_id, spot, spot_vol, futures, futures_vol, truerate, funding_rate):
        item_id = self.exchange_items.get(ex_id)
        if item_id:
            self.tree.set(item_id, "Spot Price", spot)
            self.tree.set(item_id, "Spot Volume", spot_vol)
            self.tree.set(item_id, "Futures Price", futures)
            self.tree.set(item_id, "Futures Volume", futures_vol)
            self.tree.set(item_id, "TrueRate (%)", truerate)
            self.tree.set(item_id, "Funding Rate (%)", funding_rate)

if __name__ == '__main__':
    app = XMRTerminal()
    app.mainloop()
