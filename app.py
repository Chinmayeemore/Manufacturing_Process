import streamlit as st
import numpy as np
import pandas as pd

st.title("Manufacturing Process Dashboard")

st.header("1. Add Raw Materials")
materials = st.text_input("Enter the raw material")
if st.button("Add Materials"):
    st.success(f"added the raw material {materials}")

st.header("2. Create Process")
process_name = st.text_input("Enter the process name")
if st.button("Create Process"):
    st.success(f"process {process_name} created successfully")

st.header("3. Add Machines")
machine_name = st.text_input("Enter the machine name")

capacity = {st.number_input(
    "Capacity (min)",
    min_value=1,
    step=1)
}
time_required = {st.number_input(
    "processing time (minutes)",
    min_value=1,
    step=1)
}
work_status = st.selectbox("select the task status",["pending","completed"])

if "machine" not in st.session_state:
    st.session_state.machine = []

if st.button("Add Machine"):
    st.session_state.machine.append({
        "machine": machine_name,
        "capacity": capacity,
        "time": time_required,
        "status" : work_status
    })
    
if st.session_state.machine:
    st.subheader("Machine List")
    df = pd.DataFrame(st.session_state.machine)
    st.dataframe(df)

st.header("4. Start Production")
if st.session_state.machine:
    if st.button("Start Production"):
        st.success("Production started!")
else:
    st.info("Add machines before starting production")

st.header("5. Production Dashboard")
if st.session_state.machine:
    total_machines = len(st.session_state.machine)
    st.metric("Total Machine",total_machines)
    for machine in st.session_state.machine:
        st.write(f"{machine['machine']}")
        st.progress(50)
else:
    st.info("Add machines to start dashboards")