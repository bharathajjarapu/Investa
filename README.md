# Investa Analyzr 📈

## AI-Powered Financial Analysis Platform

Investa Analyzr is a financial analysis tool that harnesses the power of AI to deliver comprehensive, institutional-grade stock reports. Tailored for professional investors, financial analysts, and investment banks, it provides deep insights and data-driven recommendations.

https://github.com/bharathajjarapu/investa/Investa.webm

*Disclaimer : Investa Analyzr is a tool for informational purposes only. It does not provide investment advice. Always conduct thorough research and consult with a qualified financial advisor before making investment decisions.*

## 🔍 Financial Analysis Capabilities

Investa Analyzr excels in providing in-depth financial analysis:

- **Fundamental Analysis**: Comprehensive evaluation of financial statements, including:
  - Balance Sheet Analysis
  - Income Statement Breakdown
  - Cash Flow Statement Examination
- **Ratio Analysis**: 
  - Liquidity Ratios (Current Ratio, Quick Ratio)
  - Profitability Ratios (ROE, ROA, Profit Margins)
  - Valuation Ratios (P/E, P/B, EV/EBITDA)
- **Discounted Cash Flow (DCF) Modeling**
- **Comparative Analysis**: Peer comparison and industry benchmarking
- **Technical Analysis**: 
  - Moving Averages
  - Relative Strength Index (RSI)
  - MACD (Moving Average Convergence Divergence)
- **Risk Assessment**: 
  - Beta calculation
  - Value at Risk (VaR) estimation

## 🚀 Key Features

- **AI-Driven Insights**: Leverages advanced language models for nuanced financial interpretation
- **Real-Time Market Data**: Integration with Yahoo Finance API
- **News Sentiment Analysis**: Aggregates and analyzes recent news for market sentiment
- **Interactive Visualizations**: Dynamic stock charts and financial metric graphs
- **Automated Reporting**: Generates comprehensive PDF reports for professional presentations
- **User Authentication**: Secure login system with usage tracking

## 🛠️ Tech Stack

- **Backend**: Python, Streamlit
- **AI/ML**: Groq API (LLaMA 3.1 model)
- **Data Sources**: Yahoo Finance, DuckDuckGo News API
- **Visualization**: Plotly
- **PDF Generation**: ReportLab
- **Database**: SQLite
- **Authentication**: bcrypt

## 📊 Sample Analysis Output

```markdown
# AAPL: Comprehensive Financial Analysis

## Executive Summary
Apple Inc. demonstrates strong financial health with robust revenue growth and profitability...

## Financial Metrics
- Revenue Growth (YoY): 8.1%
- Gross Margin: 43.3%
- Operating Margin: 30.3%
- Net Profit Margin: 25.5%
- Return on Equity (ROE): 160.9%
- Debt-to-Equity Ratio: 2.31

## Valuation
- P/E Ratio: 30.2
- Forward P/E: 28.5
- PEG Ratio: 2.5
- EV/EBITDA: 22.7

... [Additional sections]

## Investment Recommendation
Based on our comprehensive analysis, we maintain a STRONG BUY recommendation for Apple (AAPL)...
```

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/investa-analyzr.git

# Navigate to the project directory
cd investa-analyzr

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
echo "GROQ_API_KEY=your_api_key_here" > .env

# Run the application
streamlit run app.py
```

## 📜 License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.
