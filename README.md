# Investa Analyzr

Streamlit app that generates LLM-written stock research reports from market data, news and analyst ratings.

[Investa.webm](https://github.com/user-attachments/assets/0f32976d-8911-4bbc-88bd-cbc8ecafde6c)

*For informational purposes only. Not investment advice.*

## How It Works

1. **Auth**: users sign up and log in. Passwords are hashed with bcrypt and stored in `users.db` (SQLite).
2. **Quota**: each user gets 5 reports per day. The count resets on the first request of a new day.
3. **Research**: for the given ticker the app collects
   - company info and metrics from Yahoo Finance (`yfinance`)
   - the 5 latest news articles from DuckDuckGo (`duckduckgo_search`)
   - analyst recommendations and recent upgrades/downgrades
4. **Chart**: price history for the selected period is drawn as a Plotly candlestick chart.
5. **Report**: the research is converted to markdown and sent with a fixed report template to `llama-3.1-8b-instant` on Groq. The reply is rendered as the report.
6. **Export**: *Download PDF* renders the same markdown to a PDF with ReportLab.

Data fetches are cached for 1 hour with `st.cache_data`.

## Stack

Python, Streamlit, Groq, yfinance, DuckDuckGo Search, Plotly, ReportLab, SQLite, bcrypt.

## Setup

```bash
git clone https://github.com/bharathajjarapu/investa.git
cd investa
pip install -r requirements.txt
echo "GROQ_API_KEY=your_api_key_here" > .env
streamlit run app.py
```

## License

MIT, see [LICENSE](LICENSE).
