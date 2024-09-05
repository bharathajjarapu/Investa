import os
import io
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

load_dotenv()
now = datetime.now()
current_time = now.strftime("%Y-%m-%d %H:%M:%S")
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

st.set_page_config(
    page_title="Investment Assistant",
    page_icon=":moneybag:",
)

st.title(":moneybag: Investment Assistant")

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

def main() -> None:
    ticker_input = st.text_input(
        ":money_with_wings: Enter a ticker to research",
        value="NVDA",
    )
    generate_report_btn = st.button("Generate Investment Report")
    download_report_btn = st.button("Download Report as PDF")

    if generate_report_btn or download_report_btn:
        st.session_state["topic"] = ticker_input
        report_topic = st.session_state["topic"]

        ticker = yf.Ticker(ticker_input)
        report_input = ""

        # Get Company Info from YFinance
        with st.status("Getting Company Info", expanded=True) as status:
            company_info_full = ticker.info
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

        # Get Company News from DuckDuckGo
        with st.status("Getting Company News", expanded=True) as status:
            ddgs = DDGS()
            company_news = ddgs.news(keywords=ticker_input, max_results=5)
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

        # Get Analyst Recommendations & Upgrades from YFinance
        with st.status("Getting Analyst Recommendations", expanded=True) as status:
            analyst_recommendations = ticker.recommendations
            if analyst_recommendations is not None and not analyst_recommendations.empty:
                analyst_recommendations_md = analyst_recommendations.to_markdown()
                report_input += "## Analyst Recommendations\n\n"
                report_input += "This table outlines the most recent analyst recommendations for the stock.\n\n"
                report_input += f"{analyst_recommendations_md}\n"
                report_input += "---\n"
            status.update(label="Analyst Recommendations available", state="complete", expanded=False)

        with st.status("Getting Upgrades/Downgrades", expanded=True) as status:
            try:
                upgrades_downgrades = ticker.recommendations
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

        # Generate the final report
        with st.spinner("Generating Report"):
            final_report = generate_report(report_input)
            st.markdown(final_report)

        if download_report_btn:
            pdf_buffer = generate_pdf(final_report)
            report_date = datetime.now().strftime("%Y-%m-%d")
            filename = f"{ticker_input}_{report_date}_Report.pdf"
            st.download_button(
                label="Download PDF",
                data=pdf_buffer,
                file_name=filename,
                mime="application/pdf"
            )

if __name__ == "__main__":
    main()