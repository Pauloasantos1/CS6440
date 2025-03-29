import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import time

# Endpoints (increased _count parameters)
FHIR_PATIENT_ENDPOINT = "http://hapi.fhir.org/baseR4/Patient?_count=100"
FHIR_CONDITION_ENDPOINT_BASE = "http://hapi.fhir.org/baseR4/Condition?patient="

def fetch_patient_data():
    response = requests.get(FHIR_PATIENT_ENDPOINT)
    if response.status_code == 200:
        data = response.json()
        entries = data.get('entry', [])
        patients = []
        for entry in entries:
            resource = entry.get('resource', {})
            patient_id = resource.get('id', 'N/A')
            name_info = resource.get('name', [{}])[0]
            given = " ".join(name_info.get('given', []))
            family = name_info.get('family', '')
            full_name = f"{given} {family}".strip() if (given or family) else "Unknown"
            gender = resource.get('gender', 'N/A')
            birth_date = resource.get('birthDate', 'N/A')
            
            # Use country from the first address as a proxy for race if available
            country = None
            if "address" in resource and resource["address"]:
                country = resource["address"][0].get("country", None)
            race_val = country if country else "Unknown"
            group = "Minority" if (country and country.upper() != "USA") else "Majority"
            
            patients.append({
                "ID": patient_id,
                "Name": full_name,
                "Gender": gender,
                "Birth Date": birth_date,
                "Race": race_val,
                "Group": group
            })
        return pd.DataFrame(patients)
    else:
        st.error("Error fetching patient data")
        return pd.DataFrame()

def fetch_conditions_for_patient(patient_id):
    # Increase _count for condition queries to 50
    url = f"{FHIR_CONDITION_ENDPOINT_BASE}{patient_id}&_count=50"
    response = requests.get(url)
    conditions = []
    if response.status_code == 200:
        data = response.json()
        entries = data.get('entry', [])
        for entry in entries:
            resource = entry.get('resource', {})
            # Extract condition description from the first coding entry
            condition_desc = "Unknown"
            if "code" in resource and "coding" in resource["code"]:
                coding = resource["code"]["coding"]
                if coding and isinstance(coding, list):
                    condition_desc = coding[0].get("display", "Unknown")
            # Extract patient id from the subject reference (format "Patient/ID")
            subject_ref = resource.get("subject", {}).get("reference", "")
            subj_id = subject_ref.split("Patient/")[-1] if "Patient/" in subject_ref else "Unknown"
            conditions.append({
                "Patient_ID": subj_id,
                "Condition": condition_desc,
                "ClinicalStatus": resource.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "Unknown")
            })
    return pd.DataFrame(conditions)

def fetch_all_conditions(patient_ids):
    all_conditions = []
    progress_text = "Fetching condition data for patients..."
    my_bar = st.progress(0, text=progress_text)
    n = len(patient_ids)
    for i, pid in enumerate(patient_ids):
        cond_df = fetch_conditions_for_patient(pid)
        if not cond_df.empty:
            all_conditions.append(cond_df)
        my_bar.progress((i+1)/n, text=f"Fetching conditions for patient {pid}")
        time.sleep(0.1)  # slight delay to be gentle on the server
    if all_conditions:
        return pd.concat(all_conditions, ignore_index=True)
    else:
        return pd.DataFrame()

# Dashboard Title
st.title("Healthcare Dashboard: Multi-Patient Analysis")
st.write("This dashboard fetches data for up to 100 patients and their associated conditions, then visualizes condition prevalence by race.")

# Fetch patient data
st.header("Patient Data")
patient_df = fetch_patient_data()
st.dataframe(patient_df)

if not patient_df.empty:
    # Get the list of patient IDs
    patient_ids = patient_df["ID"].tolist()
    
    # Fetch conditions for all patients
    st.header("Condition Data")
    condition_df = fetch_all_conditions(patient_ids)
    st.dataframe(condition_df)
    
    # Merge the two DataFrames on the patient ID
    merged_df = pd.merge(patient_df, condition_df, left_on="ID", right_on="Patient_ID", how="inner")
    st.header("Merged Patient & Condition Data")
    st.dataframe(merged_df)
    
    if not merged_df.empty:
        # Create a filter to select a specific condition
        condition_options = ["All"] + sorted(merged_df["Condition"].unique().tolist())
        selected_condition = st.selectbox("Filter by Condition", options=condition_options)
        
        if selected_condition != "All":
            filtered_df = merged_df[merged_df["Condition"] == selected_condition]
        else:
            filtered_df = merged_df
        
        st.write(f"Displaying data for condition: {selected_condition}")
        st.dataframe(filtered_df)
        
        # Visualization: Frequency of Conditions by Race
        condition_counts = filtered_df.groupby(["Race", "Condition"]).size().reset_index(name="Count")
        st.header("Condition Prevalence by Race")
        fig = px.bar(condition_counts, x="Race", y="Count", color="Condition",
                     barmode="group", title="Condition Prevalence by Race")
        st.plotly_chart(fig)
    else:
        st.write("No merged data available for visualization.")
else:
    st.write("No patient data available.")