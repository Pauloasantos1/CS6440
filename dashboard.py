import os
import time
from typing import List

import pandas as pd
import requests
import streamlit as st
import plotly.express as px
from scipy.stats import chi2_contingency

FHIR_BASE       = os.getenv("FHIR_BASE", "https://r4.smarthealthit.org")
PATIENT_EP      = f"{FHIR_BASE}/Patient?_count=200"        
CONDITION_EP    = f"{FHIR_BASE}/Condition?patient="       
MAX_PAGES       = 10     
MIN_CASES       = 5      

def _extract_race(res: dict) -> str:
    """Return US‑Core race display or fall back to address.country."""
    for ext in res.get("extension", []):
        if ext.get("url", "").endswith("us-core-race"):
            return ext.get("valueCodeableConcept", {}) \
                     .get("coding", [{}])[0].get("display", "Unknown")
    if res.get("address"):
        return res["address"][0].get("country", "Unknown")
    return "Unknown"


def _assign_group(val: str) -> str:
    """Map race / country string → Minority / Majority / Unknown."""
    v = str(val).strip().lower()
    if v in ("white", "usa", "united states", "united states of america"):
        return "Majority"
    if v == "unknown" or v == "":
        return "Unknown"
    return "Minority"


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_patients(max_pages: int = MAX_PAGES) -> pd.DataFrame:
    """Iterate through Patient bundles until `next` disappears or max_pages hit."""
    url, page, rows = PATIENT_EP, 0, []

    while url and page < max_pages:
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
        except Exception as e:
            st.warning(f"Patient fetch error: {e}")
            break

        bundle = r.json()
        for entry in bundle.get("entry", []):
            res = entry.get("resource", {})
            pid = res.get("id", "N/A")
            name_info = res.get("name", [{}])[0]
            full_name = (
                " ".join(name_info.get("given", [])) + " " + name_info.get("family", "")
            ).strip() or "Unknown"

            rows.append(
                {
                    "ID": pid,
                    "Name": full_name,
                    "Gender": res.get("gender", "Unknown"),
                    "Birth Date": res.get("birthDate", "Unknown"),
                    "Race": _extract_race(res),
                    "Group": _assign_group(_extract_race(res)),
                    "Source": "SMART‑on‑FHIR demo",
                }
            )

        page += 1
        url = next(
            (lnk.get("url") for lnk in bundle.get("link", []) if lnk.get("relation") == "next"),
            None,
        )

    return pd.DataFrame(rows)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_conditions_for_patient(pid: str) -> pd.DataFrame:
    url = f"{CONDITION_EP}{pid}&_count=200"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
    except Exception:
        return pd.DataFrame()

    rows = []
    for entry in r.json().get("entry", []):
        res = entry.get("resource", {})
        rows.append(
            {
                "Patient_ID": pid,
                "Condition": res.get("code", {}).get("coding", [{}])[0].get("display", "Unknown"),
                "ClinicalStatus": res.get("clinicalStatus", {})
                .get("coding", [{}])[0]
                .get("code", "Unknown"),
                "Source": "SMART‑on‑FHIR demo",
            }
        )
    return pd.DataFrame(rows)


def fetch_all_conditions(pids: List[str]) -> pd.DataFrame:
    dfs = []
    bar = st.progress(0, text="Fetching condition bundles…")
    for i, pid in enumerate(pids):
        df = fetch_conditions_for_patient(pid)
        if not df.empty:
            dfs.append(df)
        bar.progress((i + 1) / len(pids))
        time.sleep(0.02)
    bar.empty()
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_synthea():
    pats = pd.read_csv("data/patients.csv")
    conds = pd.read_csv("data/conditions.csv")

    pats.columns = pats.columns.str.lower()
    conds.columns = conds.columns.str.lower()
    pats = pats.rename(
        columns={
            "id": "ID",
            "birthdate": "Birth Date",
            "gender": "Gender",
            "first": "Name",
            "race": "Race",
        }
    )
    if "Race" not in pats.columns:
        pats["Race"] = "Unknown"

    pats["Group"] = pats["Race"].apply(_assign_group)
    pats["Source"] = "Synthea CSV"

    conds = conds.rename(columns={"patient": "Patient_ID", "description": "Condition"})
    conds["Source"] = "Synthea CSV"
    return pats, conds


st.set_page_config(page_title="Healthcare Equity Dashboard", layout="wide")

st.title("📊 Healthcare Dashboard: Minority Health Risk Analysis")
st.markdown(
    f"Live FHIR Data: `{FHIR_BASE}` (first {MAX_PAGES} bundles) • Synthetic: Synthea CSVs  \n"
    f"**Minority** = race ≠ White **OR** address.country ≠ USA."
)

syn_pat, syn_cond = load_synthea()
with st.spinner("Fetching live patients…"):
    live_pat = fetch_patients()
with st.spinner("Fetching live conditions…"):
    live_cond = fetch_all_conditions(live_pat["ID"].tolist()) if not live_pat.empty else pd.DataFrame()

all_pat = pd.concat([live_pat, syn_pat], ignore_index=True)
all_cond = pd.concat([live_cond, syn_cond], ignore_index=True)
merged = pd.merge(all_pat, all_cond, left_on="ID", right_on="Patient_ID", how="inner")

st.header("Patient Demographics (combined)")
st.dataframe(all_pat, use_container_width=True)

st.header("Patient Conditions (combined)")
st.dataframe(all_cond, use_container_width=True)

st.header("Merged Patient‑Condition Records")
st.dataframe(merged, use_container_width=True)

# c1, c2, c3 = st.columns(3)
# c1.metric("Minority patients", int(all_pat[all_pat["Group"] == "Minority"].shape[0]))
# c2.metric("Majority patients", int(all_pat[all_pat["Group"] == "Majority"].shape[0]))
# c3.metric("Unknown group", int(all_pat[all_pat["Group"] == "Unknown"].shape[0]))

st.divider()

if merged.empty:
    st.error("No data available for visualisation.")
    st.stop()

cond_opts = ["All"] + sorted(merged["Condition"].dropna().unique())
chosen = st.selectbox("Filter to a single condition", cond_opts)
filtered = merged if chosen == "All" else merged[merged["Condition"] == chosen]

share = (
    filtered.groupby(["Condition", "Group"]).size().reset_index(name="Count")
    .pipe(lambda df: df.join(df.groupby("Condition")["Count"].transform(lambda s: s / s.sum()).rename("Share")))
)

fig_share = px.bar(
    share,
    x="Condition",
    y="Share",
    color="Group",
    barmode="stack",
    title="Group share per condition (100 %)",
)
st.plotly_chart(fig_share, use_container_width=True)

cont = (
    merged.groupby(["Condition", "Group"])["Patient_ID"]
          .nunique()                             
          .unstack(fill_value=0)
          .reindex(columns=["Minority", "Majority"], fill_value=0)
)

cont = cont[(cont["Minority"] >= MIN_CASES) & (cont["Majority"] >= MIN_CASES)]

minor_tot = max(all_pat[all_pat["Group"] == "Minority"]["ID"].nunique(), 1)
major_tot = max(all_pat[all_pat["Group"] == "Majority"]["ID"].nunique(), 1)

records = []
for cond, row in cont.iterrows():
    other_minor = max(minor_tot - row["Minority"], 0)
    other_major = max(major_tot - row["Majority"], 0)

    chi2, p, *_ = chi2_contingency([[row["Minority"], row["Majority"]],
                                    [other_minor,     other_major]],
                                   correction=False)

    rr = (row["Minority"] / minor_tot) / (row["Majority"] / major_tot)
    records.append(
        dict(
            Condition   = cond,
            Minority    = int(row["Minority"]),
            Majority    = int(row["Majority"]),
            Risk_Ratio  = round(rr, 2),
            p_value     = round(p, 4),
        )
    )

res_df = pd.DataFrame(records).sort_values("Risk_Ratio", ascending=False)

sig_df = res_df[(res_df["Risk_Ratio"] > 1.2) & (res_df["p_value"] < 0.05)]
if not sig_df.empty:
    fig_rr = px.bar(
        sig_df.head(15),
        x="Risk_Ratio",
        y="Condition",
        orientation="h",
        title="Top conditions disproportionately affecting minorities (RR > 1.2, p < 0.05)",
        labels={"Risk_Ratio": "Risk Ratio"},
    )
    st.plotly_chart(fig_rr, use_container_width=True)
else:
    st.info("No condition met the RR > 1.2 & p < 0.05 threshold.")
# Attempt at heat map
heat_df = merged.groupby(["Condition", "Group"]).size().reset_index(name="Count")
fig_heat = px.density_heatmap(
    heat_df,
    x="Group",
    y="Condition",
    z="Count",
    title="Condition frequency heatmap by demographic group",
    color_continuous_scale="Viridis",
)
st.plotly_chart(fig_heat, use_container_width=True)