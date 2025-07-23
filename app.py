import io
import os
import sqlite3
from datetime import date, datetime
import bcrypt
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from dotenv import load_dotenv
from groq import Groq
from duckduckgo_search import DDGS
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
LIMIT = 5

st.set_page_config(
    page_title="Investa Analyzr",
    layout="wide",
    menu_items={
        "Report a bug": "mailto:itsbharathajjarapu@gmail.com",
        "About": "Generates stock investment reports using an LLM and Yahoo Finance.",
    },
)

db = sqlite3.connect("users.db")
db.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, usage_count INTEGER, last_reset DATE)")

FIELDS = {
    "Name": "shortName",
    "Symbol": "symbol",
    "Sector": "sector",
    "Industry": "industry",
    "Address": "address1",
    "City": "city",
    "State": "state",
    "Zip": "zip",
    "Country": "country",
    "EPS": "trailingEps",
    "P/E Ratio": "trailingPE",
    "52 Week Low": "fiftyTwoWeekLow",
    "52 Week High": "fiftyTwoWeekHigh",
    "50 Day Average": "fiftyDayAverage",
    "200 Day Average": "twoHundredDayAverage",
    "Website": "website",
    "Summary": "longBusinessSummary",
    "Analyst Recommendation": "recommendationKey",
    "Number Of Analyst Opinions": "numberOfAnalystOpinions",
    "Employees": "fullTimeEmployees",
    "Total Cash": "totalCash",
    "Free Cash flow": "freeCashflow",
    "Operating Cash flow": "operatingCashflow",
    "EBITDA": "ebitda",
    "Revenue Growth": "revenueGrowth",
    "Gross Margins": "grossMargins",
    "Ebitda Margins": "ebitdaMargins",
}

PROMPT = """You are a Senior Investment Analyst for Goldman Sachs tasked with producing a research report for a very important client.

Instructions:
- You will be provided with a stock and information from junior researchers.
- Carefully read the research and generate a final - Goldman Sachs worthy investment report.
- Make your report engaging, informative, and well-structured.
- When you share numbers, include the units (e.g., millions/billions) and currency.
- Format the report in markdown following the report format below.
- IMPORTANT: Say whether to invest in the given stock or not.

Report Format:
# [Company Name]: Investment Report

### Overview
{brief, engaging introduction of the company}

### Core Metrics
- Current price, 52-week high, 52-week low, Market Cap (billions), P/E Ratio, EPS, 50-day average, 200-day average
- Analyst Recommendations: {buy, hold, sell} (number of analysts)

### Financial Performance
### Growth Prospects
### News and Updates
### Upgrades and Downgrades
{2 upgrades or downgrades with the firm and new grade, as a paragraph}
### Summary
### Recommendation
{recommendation with thorough reasoning}

Report generated on: {time}

Company Information:
"""


# Create a user, False if the name is taken
def signup(name, password):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        db.execute("INSERT INTO users VALUES (?, ?, 0, ?)", (name, hashed, date.today().isoformat()))
        db.commit()
        return True
    except sqlite3.IntegrityError:
        return False


# Check a user's password
def login(name, password):
    row = db.execute("SELECT password FROM users WHERE username = ?", (name,)).fetchone()
    return bool(row) and bcrypt.checkpw(password.encode(), row[0].encode())


# Reports used today, reset on a new day
def usage(name):
    today = date.today().isoformat()
    db.execute("UPDATE users SET usage_count = 0, last_reset = ? WHERE username = ? AND last_reset != ?", (today, name, today))
    db.commit()
    return db.execute("SELECT usage_count FROM users WHERE username = ?", (name,)).fetchone()[0]


# Company info from Yahoo Finance
@st.cache_data(ttl=3600)
def info(ticker):
    return yf.Ticker(ticker).info


# Latest news from DuckDuckGo
@st.cache_data(ttl=3600)
def news(ticker):
    return list(DDGS().news(keywords=ticker, max_results=5))


# Analyst recommendations
@st.cache_data(ttl=3600)
def ratings(ticker):
    return yf.Ticker(ticker).recommendations


# Price history for a period
@st.cache_data(ttl=3600)
def history(ticker, period):
    return yf.Ticker(ticker).history(period=period)


# Company facts as markdown
def facts(ticker):
    data = info(ticker)
    currency = data.get("currency", "USD")
    rows = {
        "Current Stock Price": f"{data.get('regularMarketPrice', data.get('currentPrice'))} {currency}",
        "Market Cap": f"{data.get('marketCap', data.get('enterpriseValue'))} {currency}",
    }
    rows |= {label: data.get(key) for label, key in FIELDS.items()}
    return "## Company Info\n\n" + "".join(f"  - {label}: {value}\n\n" for label, value in rows.items() if value)


# News articles as markdown
def headlines(ticker):
    text = ""
    for item in news(ticker):
        text += f"#### {item['title']}\n\n"
        text += "".join(f"  - {key.title()}: {item[key]}\n\n" for key in ("date", "url", "source") if key in item)
        text += item.get("body", "") + "\n\n"
    return text and "## Company News\n\n" + text


# Analyst recommendations as markdown
def analysts(ticker):
    table = ratings(ticker)
    if table is None or table.empty:
        return ""
    return "## Analyst Recommendations\n\n" + table.to_markdown() + "\n"


# Recent upgrades and downgrades as markdown
def grades(ticker):
    table = ratings(ticker)
    if table is None or table.empty:
        return ""
    table = table[table["Action"].isin(["upgraded", "downgraded"])].head(2)
    lines = "".join(f"- {row['Firm']} {row['Action']} the stock to {row['To Grade']}.\n" for _, row in table.iterrows())
    return lines and "## Upgrades/Downgrades\n\n" + lines


# Run one research step in a status box
def step(label, fetch, ticker):
    with st.status(f"Getting {label}") as box:
        try:
            text = fetch(ticker)
        except Exception as error:
            st.error(f"Could not get {label}: {error}")
            return ""
        box.update(label=f"{label} available", state="complete", expanded=False)
        return text + "---\n" if text else ""


# Ask the LLM for the report
def report(research):
    prompt = PROMPT.replace("{time}", datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + research
    reply = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.1-8b-instant",
    )
    return reply.choices[0].message.content


# Render markdown report to a PDF buffer
def pdf(content):
    buffer = io.BytesIO()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Justify", alignment=TA_JUSTIFY))
    blocks = []
    for line in content.split("\n"):
        if line.startswith("# "):
            blocks += [Paragraph(line[2:], styles["Title"]), Spacer(1, 12)]
        elif line.startswith("### "):
            blocks += [Paragraph(line[4:], styles["Heading3"]), Spacer(1, 6)]
        elif line.startswith("- "):
            blocks.append(Paragraph(f"• {line[2:]}", styles["BodyText"]))
        else:
            blocks.append(Paragraph(line, styles["Justify"]))
        blocks.append(Spacer(1, 6))
    SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18).build(blocks)
    buffer.seek(0)
    return buffer


# Report screen for a logged in user
def main(name):
    used = usage(name)
    st.write(f"Reports generated today: {used}/{LIMIT}")
    if used >= LIMIT:
        st.warning(f"You have reached your daily limit of {LIMIT} reports. Please try again tomorrow.")
        return

    ticker = st.text_input("Enter a ticker to research", value="NVDA")
    generate = st.button("Generate Report")
    download = st.button("Download PDF")
    st.sidebar.header("Customization")
    period = st.sidebar.selectbox("Historical Data Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"], index=3)

    if not (generate or download):
        return

    db.execute("UPDATE users SET usage_count = usage_count + 1 WHERE username = ?", (name,))
    db.commit()

    research = step("Company Info", facts, ticker)
    research += step("Company News", headlines, ticker)
    research += step("Analyst Recommendations", analysts, ticker)
    research += step("Upgrades/Downgrades", grades, ticker)

    with st.spinner("Getting Historical Data"):
        try:
            prices = history(ticker, period)
            if not prices.empty:
                chart = go.Figure(data=[go.Candlestick(x=prices.index, open=prices["Open"], high=prices["High"], low=prices["Low"], close=prices["Close"])])
                chart.update_layout(title=f"{ticker} Stock Price", xaxis_title="Date", yaxis_title="Price")
                st.plotly_chart(chart)
        except Exception as error:
            st.error(f"Could not get historical data: {error}")

    with st.spinner("Generating Report"):
        try:
            text = report(research)
            st.markdown(text)
        except Exception as error:
            st.error(f"Could not generate the report: {error}")
            return

    if download:
        st.download_button(
            label="Download PDF",
            data=pdf(text),
            file_name=f"{ticker}_{date.today()}_Report.pdf",
            mime="application/pdf",
        )


# Login gate, then the report screen
def app():
    st.title("Investa Analyzr")
    name = st.session_state.get("username")

    if name:
        st.write(f"Welcome, {name}!")
        if st.button("Logout"):
            del st.session_state["username"]
            st.rerun()
        main(name)
        return

    signin, register = st.tabs(["Login", "Sign Up"])
    with signin:
        user = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            if login(user, password):
                st.session_state["username"] = user
                st.rerun()
            st.error("Invalid username or password")
    with register:
        user = st.text_input("New Username", key="signup_username")
        password = st.text_input("New Password", type="password", key="signup_password")
        if st.button("Sign Up"):
            if signup(user, password):
                st.success("Account created successfully! Please log in.")
            else:
                st.error("Username already exists")


app()
