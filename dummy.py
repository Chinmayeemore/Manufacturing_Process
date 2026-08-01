import streamlit as st

st.title("Manufacturing Process Automation")
st.header("Welcome to the Manufacturing Process Automation")

process_name = st.text_input("Enter the process name")

if st.button("create process"):
    st.success(f"Process {process_name} created successfully")

if st.button("add machines"):
    machine_name = st.text_input("Enter the machine name")
    machine_capacity = st.number_input("Enter the machine capacity")
    machine_status = st.selectbox("Select the machine status",["Running","Pending","Completed"])
    st.success(f"machines added successfully")
    machine_data = {
        "machine_name": machine_name,
        "machine_capacity": machine_capacity,
        "machine_status": machine_status
    }
    st.dataframe(machine_data)

if st.button("add tasks"):
    task_name = st.text_input("Enter the task name")
    task_description = st.text_area("Enter the task description")
    task_status = st.selectbox("Select the task status",["Pending","Completed"])
    st.success(f"tasks added successfully")
    task_data = {
        "task_name": task_name,
        "task_description": task_description,
        "task_status": task_status
    }
    st.dataframe(task_data)

if st.button("start production"):
    st.success("production started successfully")
    st.dataframe(task_data)
    st.bar_chart(machine_capacity)