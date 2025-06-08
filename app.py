import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# CONFIG
st.set_page_config(page_title="📈 Market Breadth Dashboard", layout="wide")

# Load Sector Mapping (Assuming file exists locally)
sector_df = pd.read_csv("data/ind_niftytotalmarket_list.csv")
sector_df.columns = sector_df.columns.str.upper().str.strip()
sector_df = sector_df[["SYMBOL", "INDUSTRY"]]
symbols = sector_df["SYMBOL"].unique().tolist()
symbol_map_yahoo = {s: s + ".NS" for s in symbols}

# Download last 1 year of price data
with st.spinner("⏳ Fetching price data from Yahoo Finance... please wait"):
    price_data = yf.download(
        tickers=list(symbol_map_yahoo.values()),
        period="1y",
        interval="1d",
        group_by="ticker",
        progress=False,
        auto_adjust=False
    )

# ----- SECTION 1: Advance/Decline Ratio (Last 15 Days) -----
st.header("🔄 Advance / Decline Ratio (Last 15 Days)")
ad_summary = []
for i in range(15):
    day = datetime.today() - timedelta(days=i)
    advances = 0
    declines = 0
    for sym in symbols:
        try:
            df = price_data[symbol_map_yahoo[sym]]["Close"].dropna()
            if len(df) < 2:
                continue
            day_data = df[df.index.date == day.date()]
            prev_day_data = df[df.index.date == (day - timedelta(days=1)).date()]
            if len(day_data) == 1 and len(prev_day_data) == 1:
                change_pct = ((day_data.iloc[0] - prev_day_data.iloc[0]) / prev_day_data.iloc[0]) * 100
                if change_pct > 1:
                    advances += 1
                elif change_pct < -1:
                    declines += 1
        except:
            continue
    ratio = round(advances / max(declines, 1), 2)
    ad_summary.append({"DATE": day.date(), "ADVANCERS": advances, "DECLINERS": declines, "RATIO": ratio})

ad_df = pd.DataFrame(ad_summary).sort_values("DATE")
st.dataframe(ad_df, use_container_width=True)

# ----- SECTION 2: Sector-wise Breadth (DMA) -----
st.header("🏭 Sector-wise Breadth (50 DMA & 200 DMA)")
dma_results = []
for sym in symbols:
    try:
        df = price_data[symbol_map_yahoo[sym]]["Close"].dropna()
        if len(df) < 200:
            continue
        close = df.iloc[-1]
        dma_50 = df.rolling(window=50).mean().iloc[-1]
        dma_200 = df.rolling(window=200).mean().iloc[-1]
        dma_results.append({
            "SYMBOL": sym,
            "CLOSE": close,
            "50DMA": dma_50,
            "200DMA": dma_200,
            "Above_50DMA": close > dma_50,
            "Above_200DMA": close > dma_200
        })
    except:
        continue

dma_df = pd.DataFrame(dma_results).merge(sector_df, on="SYMBOL", how="left")
sectoral_breadth = dma_df.groupby("INDUSTRY").agg(
    Total_Stocks=("SYMBOL", "count"),
    Above_50DMA_Count=("Above_50DMA", "sum"),
    Above_200DMA_Count=("Above_200DMA", "sum")
).reset_index()
sectoral_breadth["% Above 50DMA"] = (sectoral_breadth["Above_50DMA_Count"] / sectoral_breadth["Total_Stocks"] * 100).round(1)
sectoral_breadth["% Above 200DMA"] = (sectoral_breadth["Above_200DMA_Count"] / sectoral_breadth["Total_Stocks"] * 100).round(1)
st.dataframe(sectoral_breadth, use_container_width=True)

# ----- SECTION 3: RS Breakout Stocks -----
st.header("🚀 3-Month RS Breakout Stocks")
rs_results = []
for sym in symbols:
    try:
        df = price_data[symbol_map_yahoo[sym]]["Close"].dropna()
        if len(df) < 65:
            continue
        last_close = df.iloc[-1]
        prev_close = df.iloc[-2]
        max_3mo = df.rolling(window=65).max().iloc[-2]
        if last_close >= max_3mo:
            rs_results.append({
                "SYMBOL": sym,
                "CLOSE": round(last_close, 2),
                "CHANGE_TODAY%": round(((last_close - prev_close) / prev_close) * 100, 2)
            })
    except:
        continue

rs_df = pd.DataFrame(rs_results).merge(sector_df, on="SYMBOL", how="left")
industry_count = rs_df["INDUSTRY"].nunique()
st.markdown(f"**🧩 Unique Industries in Breakout List:** {industry_count}")
st.dataframe(rs_df.sort_values("CHANGE_TODAY%", ascending=False), use_container_width=True)

# Count total stocks in each industry from full universe
industry_total = sector_df.groupby("INDUSTRY").agg(
    Total_Industry_Stocks=("SYMBOL", "count")
).reset_index()

# Count of RS breakouts per industry
industry_breakouts = rs_df.groupby("INDUSTRY").agg(
    RS_Breakout_Count=("SYMBOL", "count")
).reset_index()

# Merge both
industry_stats = pd.merge(industry_breakouts, industry_total, on="INDUSTRY", how="left")

# Calculate % representation in RS breakout
industry_stats["% in Breakout"] = (
    industry_stats["RS_Breakout_Count"] / industry_stats["Total_Industry_Stocks"] * 100
).round(2)

# Show in Streamlit
st.subheader("📊 RS Breakout by Industry (% Representation)")
st.dataframe(industry_stats.sort_values("% in Breakout", ascending=False), use_container_width=True)


# ----- SECTION 4: Index-wise Breadth (50 DMA & 200 DMA) -----
st.header("📊 Index-wise Breadth (50 DMA & 200 DMA)")
#INDEX FILES (must have SYMBOL column)
index_files = {
    "Nifty 50": "data/ind_nifty50_list.csv",
    "Nifty Defence": "data/ind_niftyindiadefence_list.csv",
    "Bank Nifty": "data/ind_niftybank_list.csv",
    "Nifty Smallcap 250": "data/ind_niftysmallcap250_list.csv",
    "Nifty Midcap 150": "data/ind_niftymidcap150_list.csv",
    "Nifty IT": "data/ind_niftyit_list.csv"
}

# Extract all symbols across indices
all_index_symbols = []
for index_name, path in index_files.items():
    df = pd.read_csv(path)
    df.columns = df.columns.str.upper().str.strip()
    all_index_symbols.extend(df["SYMBOL"].tolist())

unique_symbols = list(set(all_index_symbols))
symbol_map_yahoo = {s: s + ".NS" for s in unique_symbols}

# Fallback if RS breakout df not present
try:
    breakout_symbols = rs_df["SYMBOL"].unique().tolist()
except:
    breakout_symbols = []

# Download price data
with st.spinner("⏳ Fetching price data from Yahoo Finance... please wait"):
    price_data = yf.download(
        tickers=list(symbol_map_yahoo.values()),
        period="1y",
        interval="1d",
        group_by="ticker",
        progress=False,
        auto_adjust=False
    )

# Index-wise breadth calculation
index_breadth = []

for index_name, path in index_files.items():
    df = pd.read_csv(path)
    df.columns = df.columns.str.upper().str.strip()
    symbols = df["SYMBOL"].tolist()

    total = 0
    above_50 = 0
    above_200 = 0
    breakout_count = 0

    for sym in symbols:
        try:
            price_series = price_data[sym + ".NS"]["Close"].dropna()
            if len(price_series) < 200:
                continue

            last_close = price_series.iloc[-1]
            sma_50 = price_series.rolling(50).mean().iloc[-1]
            sma_200 = price_series.rolling(200).mean().iloc[-1]

            total += 1
            above_50 += int(last_close > sma_50)
            above_200 += int(last_close > sma_200)
            breakout_count += int(sym in breakout_symbols)
        except:
            continue

    index_breadth.append({
        "INDEX": index_name,
        "Total Stocks": total,
        ">50 DMA Count": above_50,
        "% Above 50 DMA": round((above_50 / total) * 100, 1) if total else 0,
        ">200 DMA Count": above_200,
        "% Above 200 DMA": round((above_200 / total) * 100, 1) if total else 0,
        "RS Breakouts": breakout_count,
        "% in RS Breakout": round((breakout_count / total) * 100, 1) if total else 0
    })

# Display results
st.subheader("📘 Index-wise Breadth + RS Breakout Stats")
index_breadth_df = pd.DataFrame(index_breadth)
st.dataframe(index_breadth_df, use_container_width=True)

# ----- SECTION 5: RS Breakout Stocks by Index -----
st.header("🔍 RS Breakout Stocks by Index")
# Dropdown to select index
selected_index = st.selectbox("🔍 Select an Index to View RS Breakout Stocks", index_breadth_df["INDEX"])

# Load that index's symbol list
selected_path = index_files[selected_index]
selected_df = pd.read_csv(selected_path)
selected_df.columns = selected_df.columns.str.upper().str.strip()
selected_symbols = selected_df["SYMBOL"].tolist()

# Filter RS breakout symbols from this index
if rs_df is not None and not rs_df.empty:
    rs_in_index = rs_df[rs_df["SYMBOL"].isin(selected_symbols)]
    st.subheader(f"📌 RS Breakout Stocks in **{selected_index}**")
    
    if not rs_in_index.empty:
        st.dataframe(rs_in_index[["SYMBOL", "INDUSTRY", "CLOSE", "CHANGE_TODAY%"]].sort_values("CHANGE_TODAY%", ascending=False))
    else:
        st.info("No RS breakout stocks in this index.")