# Purdue University Minor Optimizer

A Streamlit application that recommends Purdue University minors based on your completed courses. It scrapes minor requirement pages and displays personalized optimization with pending requirements.

## Features

- Scrapes Purdue Catalog minor pages for course requirements
- Allows users to enter completed Purdue courses (with semester) and external credits
- Calculates completion percentage and pending requirements per section
- Displays recommendations sorted by highest completion percentage

## Requirements

- Python 3.8+
- Windows / macOS / Linux

## Installation

1. Clone the repository:
   ```powershell
   git clone https://github.com/arnavsiva/Purdue-University-Minor-Optimizer
   ```

2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

## Usage

Launch the Streamlit app:
```powershell
python -m streamlit run app.py
```

Enter your completed courses and current semester in the sidebar, then click **Find minor optimization** to see personalized minor recommendations.

## Project Structure

- `app.py` — Main Streamlit application UI and logic
- `scraper.py` — Web scraper for Purdue Catalog minor requirement pages
- `requirements.txt` — Python package dependencies

## Troubleshooting

- Ensure you have an active internet connection for scraping catalog pages
- If scraping fails, check network/firewall settings or update scraping logic in `scraper.py`

## License

This project is open-source under the MIT License.
