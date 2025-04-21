# Healthcare Equity Dashboard

![Streamlit](https://img.shields.io/badge/Platform-Streamlit-blue) ![Python](https://img.shields.io/badge/Python-3.8%2B-yellow)

Our Streamlit application that helps us uncover disparities in disease prevalence between minority and majority patient groups by combining live FHIR R4 data with synthetic Synthea records.

## Features

- **Live FHIR Integration**: Fetches patients and conditions in real time from any FHIR R4 endpoint (default: `r4.smarthealthit.org`).
- **Synthetic Data Augmentation**: Loads Synthea-generated CSVs for robust sample size and diverse demographics.
- **Interactive Tables & KPIs**: Explore combined demographic and condition data with sortable, filterable tables and key metrics.
- **100% Stacked Bar Charts**: Visualize group share per condition with live filtering.
- **Statistical Disparity Analysis**: Compute risk ratios and χ² p-values to highlight significant disparities.
- **Top Disparities & Heatmap**: Identify the most skewed conditions and present raw counts by demographic group.
- **Caching for Performance**: API calls are cached for up to 1 hour for fast reloads.


## Repository Structure

```text
├── dashboard.py          # Main Streamlit app
├── requirements.txt      # Python dependencies
├── data/
│   ├── patients.csv      # Synthea patient demographics
│   └── conditions.csv    # Synthea condition records
├── push_gt.sh            # Helper script to sync to GT Enterprise GitHub
└── README.md             # This file
```

## Installation & Setup

1. **Clone the repo**
   ```bash
   git clone git@github.com:<your_personal_user>/<repo>.git
   cd <repo>
   ```
2. **Install dependencies**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. **Verify data files**
   Ensure `data/patients.csv` and `data/conditions.csv` are present (replace with your own if desired).
4. **(Optional) Configure FHIR endpoint**
   ```bash
   export FHIR_BASE=https://your.fhir.server/fhir
   ```
5. **Run the app locally**
   ```bash
   streamlit run dashboard.py
   ```
   Open your browser at <http://localhost:8501>.

## Configuration

| Variable       | Description                                | Default                             |
|----------------|--------------------------------------------|-------------------------------------|
| `FHIR_BASE`    | Base URL of the FHIR R4 server             | `https://r4.smarthealthit.org`      |
| `MAX_PAGES`    | Number of FHIR bundles to page through     | `10`                                |
| `MIN_CASES`    | Minimum patient count per group for stats  | `5`                                 |

## Usage Guide

1. **Explore Tables**: Sort and filter demographics and conditions.  
2. **View KPIs**: Quick glance at total Minority vs Majority counts.  
3. **Stacked Bar Chart**: See group share per condition; filter specific conditions.  
4. **Disparity Table**: Review risk ratios and p-values for significant gaps.  
5. **Top Disparities & Heatmap**: Identify and visualize the most pronounced inequities.
