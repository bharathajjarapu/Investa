import os
import io
import atexit
import tempfile
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv
from groq import Groq
import yfinance as yf
from duckduckgo_search import DDGS
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
import pandas as pd
import bcrypt
import sqlite3
from functools import wraps
import plotly.graph_objects as go

load_dotenv()
now = datetime.now()
current_time = now.strftime("%Y-%m-%d %H:%M:%S")
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

st.set_page_config(
    page_title="Investa Analyzr",
    page_icon=":chart_with_upwards_trend:",
    menu_items={
        'Report a bug': "mailto:itsbharathajjarapu@gmail.com",
        'About': "This is a Streamlit app that generates investment reports for stocks using LLM and Yahoo Finance API."
    }
)

# Database setup
conn = sqlite3.connect('users.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users
             (username TEXT PRIMARY KEY, password TEXT, usage_count INTEGER, last_reset DATE)''')
conn.commit()

# User authentication functions
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(stored_password, provided_password):
    return bcrypt.checkpw(provided_password.encode('utf-8'), stored_password.encode('utf-8'))

def create_user(username, password):
    hashed_password = hash_password(password)
    try:
        c.execute("INSERT INTO users (username, password, usage_count, last_reset) VALUES (?, ?, ?, ?)",
                  (username, hashed_password, 0, datetime.now().date()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def authenticate_user(username, password):
    c.execute("SELECT password FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    if result and verify_password(result[0], password):
        return True
    return False

def reset_usage_if_new_day(username):
    c.execute("SELECT last_reset FROM users WHERE username = ?", (username,))
    last_reset = c.fetchone()[0]
    if last_reset != datetime.now().date():
        c.execute("UPDATE users SET usage_count = 0, last_reset = ? WHERE username = ?",
                  (datetime.now().date(), username))
        conn.commit()

def increment_usage(username):
    reset_usage_if_new_day(username)
    c.execute("UPDATE users SET usage_count = usage_count + 1 WHERE username = ?", (username,))
    conn.commit()

def get_usage_count(username):
    c.execute("SELECT usage_count FROM users WHERE username = ?", (username,))
    return c.fetchone()[0]

def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'username' not in st.session_state:
            st.warning("Please log in to access this feature.")
            return None
        return func(*args, **kwargs)
    return wrapper

# Caching for performance improvement
@st.cache_data(ttl=3600)
def get_stock_info(ticker_input):
    ticker = yf.Ticker(ticker_input)
    return ticker.info

@st.cache_data(ttl=3600)
def get_company_news(ticker_input):
    ddgs = DDGS()
    return list(ddgs.news(keywords=ticker_input, max_results=5))

@st.cache_data(ttl=3600)
def get_analyst_recommendations(ticker_symbol):
    ticker = yf.Ticker(ticker_symbol)
    return ticker.recommendations

@st.cache_data(ttl=3600)
def get_stock_history(ticker_symbol, period='1y'):
    ticker = yf.Ticker(ticker_symbol)
    return ticker.history(period=period)

def generate_report(report_input):
    description = "You are a Senior Investment Analyst for Goldman Sachs tasked with producing a research report for a very important client."
    instructions = [
        "You will be provided with a stock and information from junior researchers.",
        "Carefully read the research and generate a final - Goldman Sachs worthy investment report.",
        "Make your report engaging, informative, and well-structured.",
        "When you share numbers, make sure to include the units (e.g., millions/billions) and currency.",
        "REMEMBER: This report is for a very important client, so the quality of the report is important.",
        "Make sure your report is properly formatted in md and follows the <report_format> provided below.",
        "IMPORTANT: Make sure to say whether to invest in the given stock or not.",
    ]
    report_format = """
    # [Company Name]: Investment Report

    ### Overview
    {give a brief introduction of the company and why the user should read this report}
    {make this section engaging and create a hook for the reader}

    ### Core Metrics
    {provide a summary of core metrics and show the latest data}
    - Current price: {current price}
    - 52-week high: {52-week high}
    - 52-week low: {52-week low}
    - Market Cap: {Market Cap} in billions
    - P/E Ratio: {P/E Ratio}
    - Earnings per Share: {EPS}
    - 50-day average: {50-day average}
    - 200-day average: {200-day average}
    - Analyst Recommendations: {buy, hold, sell} (number of analysts)

    ### Financial Performance
    {provide a detailed analysis of the company's financial performance}

    ### Growth Prospects
    {analyze the company's growth prospects and future potential}

    ### News and Updates
    {summarize relevant news that can impact the stock price}

    ### Upgrades and Downgrades
    {share 2 upgrades or downgrades including the firm, and what they upgraded/downgraded to}
    {this should be a paragraph not a table}

    ### Summary
    {give a summary of the report and what are the key takeaways}

    ### Recommendation
    {provide a recommendation on the stock along with a thorough reasoning}

    Report generated on: {current_time}
    """
    prompt = f"{description}\n\nInstructions: {', '.join(instructions)}\n\nReport Format:\n{report_format}\n\nCompany Information: {report_input}\n\nCurrent Time : {current_time}\n\n"

    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.1-8b-instant",
    )

    return chat_completion.choices[0].message.content

def generate_pdf(content):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY))

    flowables = []

    for line in content.split('\n'):
        if line.startswith('# '):
            flowables.append(Paragraph(line[2:], styles['Title']))
            flowables.append(Spacer(1, 12))
        elif line.startswith('### '):
            flowables.append(Paragraph(line[4:], styles['Heading3']))
            flowables.append(Spacer(1, 6))
        elif line.startswith('- '):
            flowables.append(Paragraph(f"• {line[2:]}", styles['BodyText']))
        else:
            flowables.append(Paragraph(line, styles['Justify']))

        flowables.append(Spacer(1, 6))

    doc.build(flowables)
    buffer.seek(0)
    return buffer

@login_required
def main():
    username = st.session_state['username']
    usage_count = get_usage_count(username)
    st.write(f"Reports generated today: {usage_count}/5")
    if st.session_state['logged_in']:
        st.markdown(
            """
            <style>
            .main .block-container{
                max-width: 100%;
                padding-top: 4rem;
                padding-right: 2rem;
                padding-left: 2rem;
                padding-bottom: 1rem;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

    if usage_count >= 5:
        st.warning("You have reached your daily limit of 5 reports. Please try again tomorrow.")
        return

    ticker_input = st.text_input(
        ":money_with_wings: Enter a ticker to research",
        value="NVDA",
    )

    generate_report_btn = st.button("Generate Report")
    download_report_btn = st.button("Download PDF")

    # Customization options
    st.sidebar.header("Customization")
    report_template = st.sidebar.selectbox(
        "Report Template",
        ["Standard", "Detailed", "Executive Summary"],
        index = 2,
    )
    time_period = st.sidebar.selectbox(
        "Historical Data Period",
        ["1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"],
        index = 3,
    )

    if generate_report_btn or download_report_btn:
        increment_usage(username)
        st.session_state["topic"] = ticker_input
        report_topic = st.session_state["topic"]

        report_input = ""

        # Get Company Info from YFinance
        with st.status("Getting Company Info") as status:
            try:
                company_info_full = get_stock_info(ticker_input)
                if company_info_full:
                    company_info_cleaned = {
                        "Name": company_info_full.get("shortName"),
                        "Symbol": company_info_full.get("symbol"),
                        "Current Stock Price": f"{company_info_full.get('regularMarketPrice', company_info_full.get('currentPrice'))} {company_info_full.get('currency', 'USD')}",
                        "Market Cap": f"{company_info_full.get('marketCap', company_info_full.get('enterpriseValue'))} {company_info_full.get('currency', 'USD')}",
                        "Sector": company_info_full.get("sector"),
                        "Industry": company_info_full.get("industry"),
                        "Address": company_info_full.get("address1"),
                        "City": company_info_full.get("city"),
                        "State": company_info_full.get("state"),
                        "Zip": company_info_full.get("zip"),
                        "Country": company_info_full.get("country"),
                        "EPS": company_info_full.get("trailingEps"),
                        "P/E Ratio": company_info_full.get("trailingPE"),
                        "52 Week Low": company_info_full.get("fiftyTwoWeekLow"),
                        "52 Week High": company_info_full.get("fiftyTwoWeekHigh"),
                        "50 Day Average": company_info_full.get("fiftyDayAverage"),
                        "200 Day Average": company_info_full.get("twoHundredDayAverage"),
                        "Website": company_info_full.get("website"),
                        "Summary": company_info_full.get("longBusinessSummary"),
                        "Analyst Recommendation": company_info_full.get("recommendationKey"),
                        "Number Of Analyst Opinions": company_info_full.get("numberOfAnalystOpinions"),
                        "Employees": company_info_full.get("fullTimeEmployees"),
                        "Total Cash": company_info_full.get("totalCash"),
                        "Free Cash flow": company_info_full.get("freeCashflow"),
                        "Operating Cash flow": company_info_full.get("operatingCashflow"),
                        "EBITDA": company_info_full.get("ebitda"),
                        "Revenue Growth": company_info_full.get("revenueGrowth"),
                        "Gross Margins": company_info_full.get("grossMargins"),
                        "Ebitda Margins": company_info_full.get("ebitdaMargins"),
                    }
                    company_info_md = "## Company Info\n\n"
                    for key, value in company_info_cleaned.items():
                        if value:
                            company_info_md += f"  - {key}: {value}\n\n"
                    report_input += "This section contains information about the company.\n\n"
                    report_input += company_info_md
                    report_input += "---\n"
                status.update(label="Company Info available", state="complete", expanded=False)
            except Exception as e:
                st.error(f"An error occurred while retrieving company info: {e}")

        # Get Company News from DuckDuckGo
        with st.status("Getting Company News") as status:
            try:
                company_news = get_company_news(ticker_input)
                if len(company_news) > 0:
                    company_news_md = "## Company News\n\n\n"
                    for news_item in company_news:
                        company_news_md += f"#### {news_item['title']}\n\n"
                        if "date" in news_item:
                            company_news_md += f"  - Date: {news_item['date']}\n\n"
                        if "url" in news_item:
                            company_news_md += f"  - Link: {news_item['url']}\n\n"
                        if "source" in news_item:
                            company_news_md += f"  - Source: {news_item['source']}\n\n"
                        if "body" in news_item:
                            company_news_md += f"{news_item['body']}"
                        company_news_md += "\n\n"
                    report_input += "This section contains the most recent news articles about the company.\n\n"
                    report_input += company_news_md
                    report_input += "---\n"
                status.update(label="Company News available", state="complete", expanded=False)
            except Exception as e:
                st.error(f"An error occurred while retrieving company news: {e}")

        # Get Analyst Recommendations
        with st.status("Getting Analyst Recommendations") as status:
            try:
                analyst_recommendations = get_analyst_recommendations(ticker_input)
                if analyst_recommendations is not None and not analyst_recommendations.empty:
                    analyst_recommendations_md = analyst_recommendations.to_markdown()
                    report_input += "## Analyst Recommendations\n\n"
                    report_input += "This table outlines the most recent analyst recommendations for the stock.\n\n"
                    report_input += f"{analyst_recommendations_md}\n"
                    report_input += "---\n"
                status.update(label="Analyst Recommendations available", state="complete", expanded=False)
            except Exception as e:
                st.error(f"An error occurred while retrieving analyst recommendations: {e}")

        # Get Upgrades/Downgrades
        with st.status("Getting Upgrades/Downgrades") as status:
            try:
                upgrades_downgrades = get_analyst_recommendations(ticker_input)
                if upgrades_downgrades is not None and not upgrades_downgrades.empty:
                    upgrades_downgrades = upgrades_downgrades[upgrades_downgrades['Action'].isin(['upgraded', 'downgraded'])].head(2)
                    if not upgrades_downgrades.empty:
                        upgrades_downgrades_md = ""
                        for _, row in upgrades_downgrades.iterrows():
                            upgrades_downgrades_md += f"- {row['Firm']} {row['Action']} the stock to {row['To Grade']}.\n"
                        report_input += "## Upgrades/Downgrades\n\n"
                        report_input += "This section outlines the most recent upgrades and downgrades for the stock.\n\n"
                        report_input += f"{upgrades_downgrades_md}\n"
                        report_input += "---\n"
                else:
                    st.info("No recent upgrades or downgrades available.")

            except Exception as e:
                st.error(f"An error occurred while retrieving upgrades/downgrades: {e}")
            status.update(label="Upgrades/Downgrades checked", state="complete", expanded=False)

        # Get Historical Data
        with st.spinner("Getting Historical Data"):
            try:
                historical_data = get_stock_history(ticker_input, period=time_period)
                if not historical_data.empty:
                    fig = go.Figure(data=[go.Candlestick(x=historical_data.index,
                                open=historical_data['Open'],
                                high=historical_data['High'],
                                low=historical_data['Low'],
                                close=historical_data['Close'])])
                    fig.update_layout(title=f'{ticker_input} Stock Price', xaxis_title='Date', yaxis_title='Price')
                    st.plotly_chart(fig)
                    st.success("Historical Data retrieved successfully")
            except Exception as e:
                st.error(f"An error occurred while retrieving historical data: {e}")

        # Generate the final report
        with st.spinner("Generating Report"):
            try:
                final_report = generate_report(report_input)
                st.markdown(final_report)
            except Exception as e:
                st.error(f"An error occurred while generating the report: {e}")

        if download_report_btn:
            try:
                pdf_buffer = generate_pdf(final_report)
                report_date = datetime.now().strftime("%Y-%m-%d")
                filename = f"{ticker_input}_{report_date}_Report.pdf"
                st.download_button(
                    label="Download PDF",
                    data=pdf_buffer,
                    file_name=filename,
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"An error occurred while generating the PDF: {e}")

def app():
    st.title("Investa Analyzr :moneybag:")

    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False


    if not st.session_state['logged_in']:
        tab1, tab2 = st.tabs(["Login", "Sign Up"])

        with tab1:
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("Login", key="login_button"):
                if authenticate_user(username, password):
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = username
                    st.rerun()
                else:
                    st.error("Invalid username or password")

        with tab2:
            new_username = st.text_input("New Username", key="signup_username")
            new_password = st.text_input("New Password", type="password", key="signup_password")
            if st.button("Sign Up", key="signup_button"):
                if create_user(new_username, new_password):
                    st.success("Account created successfully! Please log in.")
                else:
                    st.error("Username already exists")
    else:
        st.write(f"Welcome, {st.session_state['username']}!")
        if st.button("Logout", key="logout_button"):
            st.session_state['logged_in'] = False
            del st.session_state['username']
            st.rerun()
        main()

if __name__ == "__main__":
    app()

atexit.register(conn.close)
