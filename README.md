# 📊 Data Analysis App 2.0

**Enterprise-Grade Data Analysis Platform** — Built with Python & Streamlit

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Application
```bash
streamlit run app.py
```

App opens at: `http://localhost:8501`

### 3. Default Admin Account
| Field    | Value         |
|----------|---------------|
| Username | `admin`       |
| Password | `Admin@12345` |

---

## 📁 Project Structure

```
DataAnalyzerPro/
├── app.py                      ← Main entry point
├── requirements.txt            ← Dependencies
│
├── modules/                    ← Core logic
│   ├── auth.py                 ← Secure auth (bcrypt + rate limiting)
│   ├── database.py             ← SQLite context manager
│   ├── data_utils.py           ← Cleaning operations
│   ├── chart_utils.py          ← 14 chart types, 6 themes
│   ├── dashboard_utils.py      ← Save/load/export dashboards
│   └── theme_utils.py          ← Dark/Light CSS themes
│
├── pages/                      ← UI pages
│   ├── pg_login.py             ← Login & Signup
│   ├── pg_home.py              ← File upload + demo data
│   ├── pg_cleaning.py          ← Data Cleaning Studio
│   ├── pg_analysis.py          ← Dashboard Analysis
│   ├── pg_canvas.py            ← Power BI style Canvas (NEW)
│   ├── pg_search.py            ← Data Search (NEW)
│   ├── pg_mydashboards.py      ← Saved Dashboards Manager
│   ├── pg_insights.py          ← Statistical Insights
│   ├── pg_about.py             ← About & Feedback
│   └── pg_admin.py             ← Admin Panel (secured)
│
├── data/                       ← Auto-created at runtime
│   └── app.db                  ← SQLite database
│
└── .streamlit/
    └── config.toml             ← App configuration
```

---

## ✨ Features

### 🔍 Data Search (NEW)
- Simple search (text aur numbers)
- Regex search (patterns)
- Column filter (operators: ==, >, contains, etc.)
- Numeric range filter
- Multi-column AND search
- Export search results (CSV/Excel)
- Quick charts from results

### 🎨 Canvas Builder (Power BI Style)
- **14 chart types:** Bar, Line, Area, Scatter, Pie, Donut, Histogram, Box, Heatmap, Funnel, Violin, Bubble, Table, KPI
- **6 chart themes:** Default, Dark, Ocean, Sunset, Corporate, Forest
- Grid layout (1/2/3 columns)
- Full width / half width / one-third charts
- Move up/down, duplicate, delete charts
- Undo (30 steps)
- Save to database, Load saved dashboards
- Export as HTML (self-contained, shareable)
- Export as JSON

### 🛠️ Data Cleaning Studio
- Problem Scanner (auto-detect issues)
- One-click Auto Clean
- 15+ manual operations:
  - Remove empty/duplicate rows
  - Fill missing (mean/median/zero/ffill/bfill/custom)
  - Trim spaces, proper case, lowercase, uppercase
  - Remove outliers (IQR method)
  - Remove negatives
  - Fix invalid emails
  - Convert numeric/datetime

### 📈 Analysis
- KPI overview
- Distribution analysis (histogram + box)
- Correlation heatmap + scatter matrix
- Descriptive statistics
- Cross analysis (bar/line/box/violin/scatter)

### 🤖 AI Insights
- Dataset summary
- Time-based trends
- Top correlations
- Outlier analysis
- Normality test (Shapiro-Wilk)
- T-test (two group comparison)
- Smart recommendations

---

## 🔐 Security

| Feature | Status |
|---------|--------|
| Password hashing | ✅ bcrypt (12 rounds) |
| Session storage | ✅ st.session_state (no plain-text file) |
| Session timeout | ✅ 60 minutes |
| Rate limiting | ✅ 5 failures → 15-min lockout |
| Admin check | ✅ DB `is_admin` column |
| Password export | ✅ NEVER exported |
| SQL injection | ✅ Parameterized queries |
| CSRF | ✅ Streamlit built-in |

### Password Rules
- Minimum 8 characters
- At least 1 uppercase letter (A-Z)
- At least 1 digit (0-9)
- At least 1 special character (!@#$%...)

---

## 🌙 Themes
- **Light Mode** (default)
- **Dark Mode** — sidebar se switch karo

---

## 📦 Dependencies

```
streamlit>=1.32.0
pandas>=2.1.0
numpy>=1.26.0
plotly>=5.18.0
openpyxl>=3.1.2
scipy>=1.11.4
scikit-learn>=1.3.2
bcrypt>=4.1.1
kaleido>=0.2.1
Pillow>=10.1.0
```

---

## 🔧 Configuration

`.streamlit/config.toml` edit karo:
```toml
[server]
maxUploadSize = 200    # MB me (change kar sakte hain)
```

---

## 📅 Changelog

### v2.0 (2026)
- ✅ Complete security overhaul
- ✅ File-based session → st.session_state
- ✅ Login rate limiting
- ✅ Password export permanently removed
- ✅ Admin check via DB column
- ✅ NEW: Data Search page
- ✅ NEW: Power BI Canvas improvements
- ✅ NEW: Dark/Light theme
- ✅ NEW: 6 chart themes
- ✅ Deprecated pandas methods fixed
- ✅ requirements.txt corrected
- ✅ Code split into modules
- ✅ Context manager for all DB connections

---

**Data Analysis App** © 2026 — Developed by Aditya Kumar
