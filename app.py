import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timezone
import database
import time

# 1. Page Configuration and Theme Initialization
st.set_page_config(
    page_title="ShopFloor Automation Hub",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Database
database.init_db()

# 2. Inject Premium Custom CSS (Dark Glassmorphic UI)
st.markdown("""
<style>
    /* Global style overrides */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Inter:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .main-title {
        font-family: 'Outfit', sans-serif;
        font-weight: 800;
        background: linear-gradient(135deg, #00F2FE 0%, #4FACFE 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.8rem;
        margin-bottom: 0.2rem;
    }
    
    .subtitle {
        font-family: 'Inter', sans-serif;
        font-weight: 300;
        color: #8A99AD;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }

    /* Glassmorphic card wrapper */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.07);
        padding: 24px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        margin-bottom: 20px;
    }
    
    .glass-stat-card {
        background: rgba(255, 255, 255, 0.02);
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        padding: 16px;
        text-align: center;
        box-shadow: 0 4px 16px 0 rgba(0, 0, 0, 0.15);
    }
    
    .stat-label {
        font-size: 0.85rem;
        color: #8A99AD;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 4px;
    }
    
    .stat-val {
        font-family: 'Outfit', sans-serif;
        font-size: 1.8rem;
        font-weight: 600;
        color: #FFFFFF;
    }
    
    /* LED status indicators */
    .led-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 8px;
    }
    
    .led-active {
        background-color: #00E676;
        box-shadow: 0 0 10px #00E676, 0 0 20px rgba(0, 230, 118, 0.5);
        animation: pulse-green 2s infinite alternate;
    }
    
    .led-idle {
        background-color: #29B6F6;
        box-shadow: 0 0 10px #29B6F6;
    }
    
    .led-maintenance {
        background-color: #EF5350;
        box-shadow: 0 0 10px #EF5350, 0 0 20px rgba(239, 83, 80, 0.5);
        animation: pulse-red 2s infinite alternate;
    }
    
    .led-running {
        background-color: #00E676;
        box-shadow: 0 0 10px #00E676;
        animation: pulse-green 1.5s infinite alternate;
    }
    
    .led-delayed {
        background-color: #FFA726;
        box-shadow: 0 0 10px #FFA726, 0 0 20px rgba(255, 167, 38, 0.5);
        animation: pulse-orange 1.5s infinite alternate;
    }
    
    .led-paused {
        background-color: #AB47BC;
        box-shadow: 0 0 10px #AB47BC;
    }
    
    .led-pending {
        background-color: #78909C;
        box-shadow: 0 0 5px #78909C;
    }
    
    .led-completed {
        background-color: #00E676;
        box-shadow: 0 0 5px #00E676;
    }
    
    /* Animations */
    @keyframes pulse-green {
        0% { opacity: 0.6; }
        100% { opacity: 1; }
    }
    @keyframes pulse-orange {
        0% { opacity: 0.6; }
        100% { opacity: 1; }
    }
    @keyframes pulse-red {
        0% { opacity: 0.6; }
        100% { opacity: 1; }
    }

    /* Style improvements for buttons and sidebar */
    .stButton>button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }
    .stButton>button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0, 242, 254, 0.2);
    }
</style>
""", unsafe_allow_html=True)

# 3. Helper formatting utilities
def format_seconds(seconds):
    """Formats seconds into human-readable HH:MM:SS format."""
    if seconds is None:
        return "00:00:00"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def get_led_html(status):
    """Returns HTML for LED status indicator."""
    status = status.lower()
    if status in ("active", "running", "completed"):
        return f'<span class="led-indicator led-active"></span>'
    elif status in ("idle", "pending"):
        return f'<span class="led-indicator led-idle"></span>'
    elif status == "maintenance":
        return f'<span class="led-indicator led-maintenance"></span>'
    elif status == "delayed":
        return f'<span class="led-indicator led-delayed"></span>'
    elif status == "paused":
        return f'<span class="led-indicator led-paused"></span>'
    return f'<span class="led-indicator led-pending"></span>'

# 4. Streamlit Dialog Modal for Reporting Delay
@st.dialog("⚠️ Report Process Delay")
def report_delay_dialog(process_id, process_name):
    st.markdown(f"Select the delay reason for **{process_name}**.")
    reason = st.selectbox(
        "Delay Category",
        ["Material Shortage", "Mechanical Failure", "Operator Absence", "Equipment Calibration", "Quality Standard Check", "Power Fluctuation", "Other"]
    )
    custom_reason = ""
    if reason == "Other":
        custom_reason = st.text_input("Specify Custom Reason")
        
    st.write("")
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Cancel", use_container_width=True):
            st.rerun()
    with col2:
        if st.button("Confirm Delay", type="primary", use_container_width=True):
            final_reason = custom_reason if reason == "Other" else reason
            if final_reason == "":
                final_reason = "Unspecified Reason"
            # Update database status to delayed
            database.transition_process(process_id, "delayed", final_reason)
            st.toast(f"Process #{process_id} reported as delayed: {final_reason}", icon="⚠️")
            st.rerun()

# 5. Page Definitions
def render_dashboard():
    st.markdown('<div class="main-title">🏭 Real-Time ShopFloor Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Live tracking of active production stages and machine utilization. Updates in real-time.</div>', unsafe_allow_html=True)
    
    # Overview metrics
    machines = database.get_machines()
    processes = database.get_processes()
    
    total_m = len(machines)
    active_m = len([m for m in machines if m["status"] == "active"])
    maintenance_m = len([m for m in machines if m["status"] == "maintenance"])
    idle_m = total_m - active_m - maintenance_m
    
    running_p = len([p for p in processes if p["status"] == "running"])
    delayed_p = len([p for p in processes if p["status"] == "delayed"])
    pending_p = len([p for p in processes if p["status"] == "pending"])
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="glass-card glass-stat-card">
            <div class="stat-label">Active Machines</div>
            <div class="stat-val" style="color: #00E676;">{active_m} <span style="font-size: 0.9rem; color: #8A99AD;">/ {total_m}</span></div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="glass-card glass-stat-card">
            <div class="stat-label">Running Processes</div>
            <div class="stat-val" style="color: #00F2FE;">{running_p}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="glass-card glass-stat-card">
            <div class="stat-label">Delayed Processes</div>
            <div class="stat-val" style="color: #FFA726;">{delayed_p}</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="glass-card glass-stat-card">
            <div class="stat-label">Maintenance States</div>
            <div class="stat-val" style="color: #EF5350;">{maintenance_m}</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.write("")
    
    # Left column: Active Processes tracking, Right column: Machine LED status grid
    left_col, right_col = st.columns([3, 2])
    
    with right_col:
        st.markdown('<h3 style="font-family: Outfit; font-weight: 600;">⚙️ Machine Status Matrix</h3>', unsafe_allow_html=True)
        st.write("")
        for m in machines:
            status_text = m["status"].upper()
            led = get_led_html(m["status"])
            
            # Find active processes on this machine
            machine_procs = [p for p in processes if p["machine_id"] == m["id"] and p["status"] in ("running", "delayed")]
            proc_info = ""
            if machine_procs:
                proc_names = ", ".join([p["name"] for p in machine_procs])
                proc_info = f"<br/><span style='font-size: 0.85rem; color: #8A99AD;'>Processing: {proc_names}</span>"
            else:
                proc_info = f"<br/><span style='font-size: 0.85rem; color: #5C6F84;'>No active workload</span>"
                
            st.markdown(f"""
            <div class="glass-card" style="padding: 16px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong style="font-size: 1.1rem; color: white;">{m["name"]}</strong>
                        <span style="font-size: 0.85rem; color: #8A99AD; margin-left: 8px;">({m["type"]})</span>
                        {proc_info}
                    </div>
                    <div style="display: flex; align-items: center; background: rgba(0,0,0,0.2); padding: 6px 12px; border-radius: 20px;">
                        {led}
                        <span style="font-size: 0.85rem; font-weight: 600; color: white;">{status_text}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
    with left_col:
        st.markdown('<h3 style="font-family: Outfit; font-weight: 600;">🔄 Real-Time Process Execution</h3>', unsafe_allow_html=True)
        st.write("")
        
        # Real-time state fragment to update progress every second
        @st.fragment(run_every=1.0)
        def show_progress_cards():
            # Query fresh processes
            live_procs = database.get_processes()
            
            # Filter to active/ongoing processes (pending, running, paused, delayed)
            active_list = [p for p in live_procs if p["status"] != "completed"]
            
            if not active_list:
                st.info("No active processes scheduled. Go to 'Process Scheduler' to add one.")
                return
                
            for p in active_list:
                status = p["status"]
                target = p["target_duration"]
                elapsed = p["live_elapsed_seconds"]
                delay = p["live_delay_seconds"]
                
                # Calculate progress percentage
                progress_pct = min(100, int((elapsed / target) * 100)) if target > 0 else 0
                
                # Check status styling
                led = get_led_html(status)
                status_color = "#00E676" if status == "running" else "#FFA726" if status == "delayed" else "#AB47BC" if status == "paused" else "#8A99AD"
                
                # Extra alert header for delayed
                delay_reason_text = ""
                if status == "delayed":
                    # Find last delay reason from logs
                    logs = database.get_logs()
                    p_logs = [l for l in logs if l["process_id"] == p["id"] and l["event_type"] == "delayed"]
                    reason = p_logs[0]["delay_reason"] if p_logs else "Unknown Issue"
                    delay_reason_text = f"<div style='color: #FFA726; font-size: 0.85rem; font-weight: 600; margin-top: -6px; margin-bottom: 8px;'>⚠️ DELAYED: {reason}</div>"
                
                st.markdown(f"""
                <div class="glass-card" style="margin-bottom: 16px; border-left: 4px solid {status_color};">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                        <div>
                            <span style="font-size: 0.8rem; text-transform: uppercase; color: #8A99AD; letter-spacing: 0.5px;">Machine: {p["machine_name"] or "Unassigned"}</span>
                            <h4 style="margin: 4px 0; font-family: Outfit; font-weight: 600; color: white;">{p["name"]}</h4>
                        </div>
                        <div style="display: flex; align-items: center; background: rgba(255,255,255,0.05); padding: 4px 10px; border-radius: 20px;">
                            {led}
                            <span style="font-size: 0.8rem; font-weight: 600; color: white; text-transform: uppercase;">{status}</span>
                        </div>
                    </div>
                    {delay_reason_text}
                    
                    <div style="font-size: 0.85rem; color: #D1DBE5; margin-bottom: 12px;">{p["details"]}</div>
                    
                    <!-- Progress Bar -->
                    <div style="background-color: rgba(255,255,255,0.08); border-radius: 6px; height: 10px; width: 100%; margin-bottom: 8px; overflow: hidden;">
                        <div style="background: linear-gradient(90deg, #4FACFE 0%, #00F2FE 100%); height: 100%; width: {progress_pct}%; border-radius: 6px;"></div>
                    </div>
                    
                    <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: #8A99AD; margin-bottom: 16px;">
                        <div>Target: {format_seconds(target)}</div>
                        <div>Elapsed: <strong>{format_seconds(elapsed)}</strong></div>
                        <div>Delay: <strong style="color: #FFA726;">{format_seconds(delay)}</strong></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Interactive Control Buttons next to each process
                btn_cols = st.columns([1, 1, 1, 1])
                with btn_cols[0]:
                    if status in ("pending", "paused", "delayed"):
                        if st.button("▶️ Start / Resume", key=f"start_{p['id']}", use_container_width=True):
                            database.transition_process(p["id"], "running")
                            st.toast(f"Started process: {p['name']}", icon="▶️")
                            st.rerun()
                with btn_cols[1]:
                    if status == "running":
                        if st.button("⏸️ Pause", key=f"pause_{p['id']}", use_container_width=True):
                            database.transition_process(p["id"], "paused")
                            st.toast(f"Paused process: {p['name']}", icon="⏸️")
                            st.rerun()
                with btn_cols[2]:
                    if status == "running":
                        if st.button("⚠️ Report Delay", key=f"delay_{p['id']}", use_container_width=True):
                            report_delay_dialog(p["id"], p["name"])
                with btn_cols[3]:
                    if status in ("running", "paused", "delayed"):
                        if st.button("✅ Complete", key=f"complete_{p['id']}", type="primary", use_container_width=True):
                            database.transition_process(p["id"], "completed")
                            st.toast(f"Completed process: {p['name']}", icon="✅")
                            st.rerun()
                            
                st.markdown("<hr style='border: 0; border-top: 1px solid rgba(255,255,255,0.07); margin: 20px 0;'>", unsafe_allow_html=True)

        show_progress_cards()

def render_machines():
    st.markdown('<div class="main-title">⚙️ Machine Registry</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Register shopfloor equipment, monitor capacity, and toggle operational states.</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown('<h3 style="font-family: Outfit; font-weight: 600;">➕ Register New Machine</h3>', unsafe_allow_html=True)
        st.write("")
        with st.form("machine_form", clear_on_submit=True):
            m_name = st.text_input("Machine Name", placeholder="e.g. Laser Engraver Mark IV")
            m_type = st.selectbox("Machine Type / Category", ["Machining", "Molding", "Assembly", "Cutting", "Welding", "Packaging", "Other"])
            m_details = st.text_area("Machine Details / Specifications", placeholder="e.g. 500W fiber laser cutter, standard power grid requirement.")
            
            submitted = st.form_submit_button("Register Machine", use_container_width=True)
            if submitted:
                if m_name.strip() == "":
                    st.error("Machine name is required!")
                else:
                    database.add_machine(m_name, m_type, m_details)
                    st.success(f"Registered machine {m_name} successfully!")
                    st.rerun()
                    
    with col2:
        st.markdown('<h3 style="font-family: Outfit; font-weight: 600;">📋 Configured Machines</h3>', unsafe_allow_html=True)
        st.write("")
        
        machines = database.get_machines()
        
        for m in machines:
            led = get_led_html(m["status"])
            st.markdown(f"""
            <div class="glass-card" style="margin-bottom: 16px;">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <h4 style="margin: 0 0 4px 0; font-family: Outfit; color: white;">{m["name"]}</h4>
                        <span style="font-size: 0.85rem; color: #8A99AD;">Type: <strong>{m["type"]}</strong></span>
                    </div>
                    <div style="display: flex; align-items: center; background: rgba(0,0,0,0.2); padding: 4px 10px; border-radius: 20px;">
                        {led}
                        <span style="font-size: 0.8rem; font-weight: 600; color: white; text-transform: uppercase;">{m["status"]}</span>
                    </div>
                </div>
                <div style="font-size: 0.85rem; color: #D1DBE5; margin-top: 10px; margin-bottom: 16px;">{m["details"]}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Interactive toggle for machine maintenance state
            btn_cols = st.columns([2, 1, 1])
            with btn_cols[1]:
                if m["status"] != "maintenance":
                    if st.button("🔧 Maintenance", key=f"maint_{m['id']}", use_container_width=True):
                        database.update_machine_status(m["id"], "maintenance")
                        st.toast(f"Machine {m['name']} put in maintenance", icon="🔧")
                        st.rerun()
            with btn_cols[2]:
                if m["status"] == "maintenance":
                    if st.button("✅ Operational", key=f"op_{m['id']}", use_container_width=True):
                        database.update_machine_status(m["id"], "idle")
                        st.toast(f"Machine {m['name']} is operational", icon="✅")
                        st.rerun()
            st.write("")

def render_processes():
    st.markdown('<div class="main-title">🔄 Process Scheduler</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Set up manufacturing tasks, estimate time bounds, and allocate target equipment.</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown('<h3 style="font-family: Outfit; font-weight: 600;">➕ Create Process Run</h3>', unsafe_allow_html=True)
        st.write("")
        
        # Fetch machines to assign
        machines = database.get_machines()
        machine_options = {m["id"]: f"{m['name']} ({m['type']})" for m in machines if m["status"] != "maintenance"}
        
        if not machine_options:
            st.warning("No operational machines available! Please register or make a machine operational in 'Machine Registry'.")
            # Create a form that is disabled or show error
        
        with st.form("process_form", clear_on_submit=True):
            p_name = st.text_input("Process / Operation Name", placeholder="e.g. Steel Bracket Polishing")
            p_details = st.text_area("Process Details / Instructions", placeholder="e.g. Grade 4 abrasive finish, target thickness 2mm.")
            
            selected_m_id = st.selectbox(
                "Assign Machine", 
                options=list(machine_options.keys()), 
                format_func=lambda x: machine_options[x]
            ) if machine_options else None
            
            st.write("Target Completion Duration")
            dur_cols = st.columns(3)
            with dur_cols[0]:
                hours = st.number_input("Hours", min_value=0, max_value=24, value=0, step=1)
            with dur_cols[1]:
                minutes = st.number_input("Minutes", min_value=0, max_value=59, value=3, step=1)
            with dur_cols[2]:
                seconds = st.number_input("Seconds", min_value=0, max_value=59, value=0, step=1)
                
            submitted = st.form_submit_button("Schedule Process", use_container_width=True)
            if submitted:
                total_dur_seconds = (hours * 3600) + (minutes * 60) + seconds
                
                if p_name.strip() == "":
                    st.error("Process name is required!")
                elif not selected_m_id:
                    st.error("An operational machine must be assigned!")
                elif total_dur_seconds <= 0:
                    st.error("Target duration must be greater than 0!")
                else:
                    database.add_process(p_name, p_details, selected_m_id, total_dur_seconds)
                    st.success(f"Successfully scheduled process {p_name}!")
                    st.rerun()
                    
    with col2:
        st.markdown('<h3 style="font-family: Outfit; font-weight: 600;">📋 Scheduled Processes</h3>', unsafe_allow_html=True)
        st.write("")
        
        processes = database.get_processes()
        
        if not processes:
            st.info("No processes configured.")
        else:
            # Table-like display
            for p in processes:
                led = get_led_html(p["status"])
                status_color = "#00E676" if p["status"] == "completed" else "#FFA726" if p["status"] == "delayed" else "#AB47BC" if p["status"] == "paused" else "#8A99AD"
                
                st.markdown(f"""
                <div class="glass-card" style="margin-bottom: 12px; padding: 16px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="font-size: 0.85rem; color: #8A99AD;">#{p["id"]} - Machine: <strong>{p["machine_name"]}</strong></span>
                            <h4 style="margin: 4px 0; font-family: Outfit; color: white;">{p["name"]}</h4>
                            <span style="font-size: 0.85rem; color: #8A99AD;">Target Duration: {format_seconds(p["target_duration"])}</span>
                        </div>
                        <div style="display: flex; align-items: center; background: rgba(0,0,0,0.2); padding: 4px 10px; border-radius: 20px;">
                            {led}
                            <span style="font-size: 0.8rem; font-weight: 600; color: white; text-transform: uppercase;">{p["status"]}</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

def render_analytics():
    st.markdown('<div class="main-title">📈 Analytics & Reports</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Audit active runtime versus delay losses to optimize shopfloor productivity.</div>', unsafe_allow_html=True)
    
    machine_data, delay_distribution = database.get_analytics_data()
    
    if not machine_data:
        st.warning("No analytics data available. Create and execute processes to generate stats.")
        return
        
    # Convert data for plotting
    df_machines = pd.DataFrame(machine_data)
    
    # Check if there is data
    has_time_data = df_machines["total_elapsed"].sum() > 0 or df_machines["total_delay"].sum() > 0
    
    if not has_time_data:
        st.info("Processes exist, but no run or delay hours have accumulated yet. Start some processes on the Dashboard!")
    else:
        # Chart 1: Uptime vs Downtime/Delay by Machine
        st.markdown('<h3 style="font-family: Outfit; font-weight: 600;">📊 Machine Efficiency (Active vs Delay Seconds)</h3>', unsafe_allow_html=True)
        st.write("")
        
        # Melt dataframe to structure for stacked bar chart
        df_melt = pd.melt(
            df_machines, 
            id_vars=["machine_name"], 
            value_vars=["total_elapsed", "total_delay"],
            var_name="Time Category", 
            value_name="Seconds"
        )
        # Rename category names for display
        df_melt["Time Category"] = df_melt["Time Category"].replace({
            "total_elapsed": "Active Run Time",
            "total_delay": "Delay Time"
        })
        
        fig = px.bar(
            df_melt, 
            x="machine_name", 
            y="Seconds", 
            color="Time Category",
            title="Accumulated Time Distribution per Machine",
            color_discrete_map={"Active Run Time": "#00E676", "Delay Time": "#FFA726"},
            barmode="stack",
            template="plotly_dark"
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_family="Inter",
            font_color="#FFFFFF"
        )
        st.plotly_chart(fig, use_container_width=True)
        
    st.write("")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown('<h3 style="font-family: Outfit; font-weight: 600;">⚠️ Delay Causes Distribution</h3>', unsafe_allow_html=True)
        st.write("")
        
        if not delay_distribution:
            st.info("No delays recorded yet. The system is operating at peak performance!")
        else:
            df_delays = pd.DataFrame(delay_distribution)
            fig_pie = px.pie(
                df_delays, 
                values="total_duration", 
                names="delay_reason",
                title="Proportion of Total Delay Time by Reason",
                color_discrete_sequence=px.colors.sequential.Oranges_r,
                template="plotly_dark"
            )
            fig_pie.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_family="Inter",
                font_color="#FFFFFF"
            )
            st.plotly_chart(fig_pie, use_container_width=True)
            
    with col2:
        st.markdown('<h3 style="font-family: Outfit; font-weight: 600;">📋 System Operational Log</h3>', unsafe_allow_html=True)
        st.write("")
        
        logs = database.get_logs()
        if not logs:
            st.info("No system events logged yet.")
        else:
            # Format and display log entries
            log_entries = []
            for l in logs:
                # Format time to local
                try:
                    ts = datetime.fromisoformat(l["timestamp"])
                    local_time = ts.replace(tzinfo=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")
                except:
                    local_time = l["timestamp"]
                    
                duration_text = format_seconds(l["duration_seconds"]) if l["duration_seconds"] > 0 else "-"
                
                # Format event type text
                evt = l["event_type"].upper()
                reason = f" ({l['delay_reason']})" if l["delay_reason"] else ""
                
                log_entries.append({
                    "Timestamp": local_time,
                    "Process": l["process_name"] or f"Proc #{l['process_id']}",
                    "Machine": l["machine_name"] or "None",
                    "Event": f"{evt}{reason}",
                    "Prev State Duration": duration_text
                })
                
            df_logs = pd.DataFrame(log_entries)
            st.dataframe(
                df_logs, 
                use_container_width=True,
                height=400
            )

# 6. Main Routing
def main():
    # Sidebar navigation
    st.sidebar.markdown("""
        <div style="text-align: center; margin-bottom: 20px;">
            <span style="font-size: 3rem;">🏭</span>
            <h2 style="font-family: Outfit; font-weight: 800; color: white; margin-top: 5px; margin-bottom: 0;">ShopFloor</h2>
            <span style="font-size: 0.8rem; text-transform: uppercase; color: #00F2FE; letter-spacing: 1.5px; font-weight: 600;">Automation Hub</span>
        </div>
    """, unsafe_allow_html=True)
    
    st.sidebar.write("")
    
    page = st.sidebar.radio(
        "Navigation Menu", 
        ["📊 Real-Time Dashboard", "⚙️ Machine Registry", "🔄 Process Scheduler", "📈 Analytics & Reports"]
    )
    
    st.sidebar.markdown("<hr style='border: 0; border-top: 1px solid rgba(255,255,255,0.07); margin: 30px 0;'>", unsafe_allow_html=True)
    st.sidebar.markdown("""
        <div style="font-size: 0.8rem; color: #5C6F84; text-align: center;">
            ShopFloor v1.0.0<br/>
            Running on SQLite & Streamlit
        </div>
    """, unsafe_allow_html=True)
    
    if page == "📊 Real-Time Dashboard":
        render_dashboard()
    elif page == "⚙️ Machine Registry":
        render_machines()
    elif page == "🔄 Process Scheduler":
        render_processes()
    elif page == "📈 Analytics & Reports":
        render_analytics()

if __name__ == "__main__":
    main()
