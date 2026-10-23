# 🚗 Car Price Estimator

Upload or paste photos of a car and get an AI-generated used-price estimate,
built with **Streamlit** and **Google Gemini Flash**.

## Features
- Upload or paste (Ctrl+V / Cmd+V) up to 6 car photos
- Detects make, model, year range, condition and visible issues
- Returns a price range plus a best guess in your chosen currency
- Optional inputs (country, mileage, notes) for better accuracy

> Estimates are based on photos only and are **not** a professional appraisal.

## Run locally
1. Get a free API key at https://aistudio.google.com/apikey
2. Install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Create `.streamlit/secrets.toml`:
   ```toml
   GEMINI_API_KEY = "your-key-here"
   # GEMINI_MODEL = "gemini-2.5-flash"   # optional override
   ```
4. Start the app:
   ```bash
   streamlit run app.py
   ```

## Deploy on Streamlit Community Cloud
1. Push this repo to GitHub (never commit `secrets.toml`).
2. Go to https://share.streamlit.io and click **Create app**.
3. Pick your repo, branch `main`, and main file `app.py`.
4. Open **Advanced settings > Secrets** and paste:
   ```toml
   GEMINI_API_KEY = "your-key-here"
   ```
5. Click **Deploy**.

## Configuration
| Setting | Where | Default |
|---|---|---|
| `GEMINI_API_KEY` | secrets or env var | required |
| `GEMINI_MODEL` | secrets or env var | `gemini-2.5-flash` |

## Project files
- `app.py` - Streamlit app and Gemini call
- `requirements.txt` - Python dependencies
- 
