import streamlit as st
import pandas as pd

st.title("Manufacturing Process Dashboard")

data = {
    "Machine": ["M1", "M2", "M3"],
    "Capacity_per_min": [100, 80, 120],
    "Progress": [70, 40, 90],
    "Status": ["Running", "Pending", "Completed"]
}
df = pd.DataFrame(data)

st.subheader("Machine Status Table")
st.dataframe(df)

st.subheader("Machine Capacity Chart")
st.bar_chart(df["Capacity_per_min"])

st.subheader("Production Metrics")

col1, col2, col3 = st.columns(3)

col1.metric("Total Machines", 3)
col2.metric("Completed", 1)
col3.metric("Running", 1)