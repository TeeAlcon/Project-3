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
.src/
components/
│_  navigation.py
│_  table_styles.py

dashboard/               # pages
│_  audit_page.py
│_  data_page.py
│_  master_page.py
│_  output_page.py
│_  scrape_page.py

scrape/                  # browser automation for Expeditors
│_  scrape_doc.py
│_  combine_scrape.py
│_  login_popup.py

ui/
│_  styles.py

utils/                   # detecting data change
│_  file_analyzed.py
│_  file_utils.py
│_  find_columns.py

services/                # summary of audit status
│_  audit_status.py
│_  build_master_list.py
│_  document_status.py
│_  mapping.py
│_  output.py

app.py - entry point (run this)
config.py

```

