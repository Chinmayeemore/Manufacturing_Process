import pandas as pd

data = {
    "Machine": ["M1", "M2", "M3"],
    "Progress": [70, 100, 20],
    "Status": ["Running", "Completed", "Pending"]
}

df = pd.DataFrame(data)

import streamlit as st

st.dataframe(df)
st.bar_chart(df["Progress"])