## Quick Start
**Requirements:** Python >= 3.12

```bash
# 1. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
streamlit run streamlit/app.py
```

App opens at `http://localhost:8501`. 

## Project Structure

```
.streamlit/
components/
│_  navigation.py
│_  status_panel.py
│_  table_styles.py

pages/
│_  audit_page.py
│_  data_page.py
│_  master_page.py
│_  output_page.py
│_  scrape_page.py

scrape/
│_  scrape_doc.py
│_  combine_scrape.py
│_  login_popup.py

ui/
│_  styles.py

utils/
│_  updated_data_detection.py - Data processing logic layer

app.py - entry point (run this)
config.py

```

