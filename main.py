import flet as ft
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import tempfile
import os

def fetch_and_backtest(symbol, s_ema, m_ema, l_ema, capital, sl_pct, tp_pct):
    data = yf.download(symbol, period="1y", interval="1d", progress=False, auto_adjust=True)
    if data.empty or len(data) < l_ema + 5:
        return None, f"Data kam hai ya symbol galat hai (min {l_ema+5} din chahiye)"

    close = data['Close'].squeeze()
    ema_s = close.ewm(span=s_ema, adjust=False).mean()
    ema_m = close.ewm(span=m_ema, adjust=False).mean()
    ema_l = close.ewm(span=l_ema, adjust=False).mean()

    signal = ((ema_s > ema_m) & (ema_m > ema_l)).astype(int)

    cap = capital
    shares = 0
    buy_price = 0
    trades = []
    equity = []
    dates = list(close.index)

    for i in range(len(close)):
        price = float(close.iloc[i])

        if shares > 0:
            if price <= buy_price * (1 - sl_pct / 100):
                cap = shares * price
                trades.append(cap - shares * buy_price)
                shares = 0
            elif price >= buy_price * (1 + tp_pct / 100):
                cap = shares * price
                trades.append(cap - shares * buy_price)
                shares = 0

        if signal.iloc[i] == 1 and shares == 0:
            shares = cap / price
            buy_price = price
            cap = 0
        elif signal.iloc[i] == 0 and shares > 0:
            cap = shares * price
            trades.append(cap - shares * buy_price)
            shares = 0

        equity.append(cap + shares * price)

    if shares > 0:
        cap = shares * float(close.iloc[-1])
        trades.append(cap - shares * buy_price)

    final = cap if shares == 0 else cap
    total_return = ((final - capital) / capital) * 100
    wins = len([t for t in trades if t > 0])
    win_rate = (wins / len(trades) * 100) if trades else 0

    peak = equity[0] if equity else capital
    max_dd = 0
    for v in equity:
        if v > peak: peak = v
        dd = ((peak - v) / peak) * 100
        if dd > max_dd: max_dd = dd

    fig, ax = plt.subplots(figsize=(10, 5), facecolor='#1a1a1a')
    ax.set_facecolor('#1a1a1a')
    ax.plot(dates, close.values, label='Price', color='#888', linewidth=1)
    ax.plot(dates, ema_s.values, label=f'EMA {s_ema}', color='#00e5ff', linewidth=1.5)
    ax.plot(dates, ema_m.values, label=f'EMA {m_ema}', color='#ffeb3b', linewidth=1.5)
    ax.plot(dates, ema_l.values, label=f'EMA {l_ema}', color='#ff4081', linewidth=1.5)
    ax.legend(loc='upper left', facecolor='#1a1a1a', labelcolor='white')
    ax.tick_params(colors='white', labelsize=8)
    for spine in ax.spines.values(): spine.set_color('#444')
    ax.grid(alpha=0.2, color='#444')
    ax.set_title(f'{symbol} — 1 Year', color='white')
    fig.autofmt_xdate()
    chart_path = os.path.join(tempfile.gettempdir(), 'chart.png')
    plt.tight_layout()
    plt.savefig(chart_path, dpi=100, facecolor='#1a1a1a')
    plt.close(fig)

    return {
        'initial': capital,
        'final': final,
        'return': total_return,
        'trades': len(trades),
        'wins': wins,
        'win_rate': win_rate,
        'max_dd': max_dd,
        'chart': chart_path,
    }, None

def main(page: ft.Page):
    page.title = "Swing Trade Tester"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO
    page.bgcolor = "#0f0f0f"

    title = ft.Text("📈 Swing Trade Tester", size=26, weight=ft.FontWeight.BOLD, color="#ffeb3b")
    subtitle = ft.Text("NSE Stocks • 44/99/200 EMA Strategy", size=13, color="#888")

    stock = ft.TextField(label="Stock Symbol", value="RELIANCE.NS", width=340)
    row_ema = ft.Row([
        ft.TextField(label="EMA 1", value="44", width=105),
        ft.TextField(label="EMA 2", value="99", width=105),
        ft.TextField(label="EMA 3", value="200", width=105),
    ], alignment=ft.MainAxisAlignment.CENTER)
    row_risk = ft.Row([
        ft.TextField(label="Capital ₹", value="100000", width=160),
        ft.TextField(label="SL %", value="3", width=80),
        ft.TextField(label="TP %", value="6", width=80),
    ], alignment=ft.MainAxisAlignment.CENTER)

    status = ft.Text("", size=13, color="#888")
    result_col = ft.Column(visible=False, spacing=8)
    progress = ft.ProgressBar(width=340, visible=False)

    def run_click(e):
        status.value = "⏳ Fetching data & backtesting..."
        progress.visible = True
        result_col.visible = False
        page.update()

        try:
            r, err = fetch_and_backtest(
                stock.value.strip().upper(),
                int(row_ema.controls[0].value),
                int(row_ema.controls[1].value),
                int(row_ema.controls[2].value),
                float(row_risk.controls[0].value),
                float(row_risk.controls[1].value),
                float(row_risk.controls[2].value),
            )
            progress.visible = False

            if err:
                status.value = f"❌ {err}"
                page.update()
                return

            ret_color = "#4caf50" if r['return'] > 0 else "#f44336"
            result_col.controls = [
                ft.Divider(),
                ft.Text(f"📊 {stock.value.upper()}", size=18, weight=ft.FontWeight.BOLD, color="#ffeb3b"),
                ft.Row([ft.Text("Initial", width=120, color="#aaa"), ft.Text(f"₹{r['initial']:,.0f}")]),
                ft.Row([ft.Text("Final", width=120, color="#aaa"), ft.Text(f"₹{r['final']:,.0f}", color=ret_color, weight=ft.FontWeight.BOLD)]),
                ft.Row([ft.Text("Return", width=120, color="#aaa"), ft.Text(f"{r['return']:.2f}%", color=ret_color, weight=ft.FontWeight.BOLD)]),
                ft.Row([ft.Text("Total Trades", width=120, color="#aaa"), ft.Text(str(r['trades']))]),
                ft.Row([ft.Text("Win Rate", width=120, color="#aaa"), ft.Text(f"{r['win_rate']:.1f}%")]),
                ft.Row([ft.Text("Max Drawdown", width=120, color="#aaa"), ft.Text(f"{r['max_dd']:.2f}%")]),
                ft.Divider(),
                ft.Image(src=r['chart'], width=340),
            ]
            result_col.visible = True
            status.value = "✅ Backtest complete"
        except Exception as ex:
            progress.visible = False
            status.value = f"❌ Error: {ex}"

        page.update()

    run_btn = ft.ElevatedButton(
        "🚀 Run Backtest", on_click=run_click, width=340, height=50,
        style=ft.ButtonStyle(bgcolor="#ffeb3b", color="black", shape=ft.RoundedRectangleBorder(radius=8))
    )

    page.add(ft.Column([
        title, subtitle, ft.Divider(),
        stock, row_ema, row_risk,
        run_btn, progress, status,
        result_col,
    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12))

ft.app(target=main)
