import sqlite3
import os
from datetime import datetime, timezone

DB_FILE = "production.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema and seeds initial data if empty."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Create machines table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS machines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT,
            status TEXT NOT NULL DEFAULT 'idle', -- 'idle', 'active', 'maintenance'
            details TEXT
        );
    """)
    
    # 2. Create processes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS processes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            details TEXT,
            machine_id INTEGER,
            target_duration INTEGER, -- target duration in seconds
            elapsed_seconds INTEGER DEFAULT 0, -- accumulated active run-time
            delay_seconds INTEGER DEFAULT 0, -- accumulated delay time
            status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'running', 'paused', 'delayed', 'completed'
            last_status_change TEXT, -- ISO timestamp of the last status update
            FOREIGN KEY(machine_id) REFERENCES machines(id) ON DELETE SET NULL
        );
    """)
    
    # 3. Create logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            process_id INTEGER,
            machine_id INTEGER,
            event_type TEXT NOT NULL, -- 'pending', 'running', 'paused', 'delayed', 'completed'
            delay_reason TEXT,
            timestamp TEXT NOT NULL, -- ISO timestamp
            duration_seconds INTEGER DEFAULT 0, -- elapsed time for that log record
            FOREIGN KEY(process_id) REFERENCES processes(id) ON DELETE CASCADE,
            FOREIGN KEY(machine_id) REFERENCES machines(id) ON DELETE SET NULL
        );
    """)
    
    conn.commit()
    
    # Check if empty to seed
    cursor.execute("SELECT COUNT(*) FROM machines")
    if cursor.fetchone()[0] == 0:
        # Seed machines
        machines = [
            ("CNC Milling Machine", "Machining", "idle", "High-precision CNC mill for steel and aluminum parts."),
            ("Injection Molder 3000", "Molding", "idle", "300-ton hydraulic injection molding system."),
            ("Robotic Assembly Arm", "Assembly", "idle", "6-axis robotic arm for component assembly and packing."),
            ("Laser Cutter X5", "Cutting", "idle", "150W CO2 laser cutting system for metal sheets.")
        ]
        cursor.executemany(
            "INSERT INTO machines (name, type, status, details) VALUES (?, ?, ?, ?)",
            machines
        )
        conn.commit()
        
        # Get machine IDs
        cursor.execute("SELECT id, name FROM machines")
        machine_map = {row["name"]: row["id"] for row in cursor.fetchall()}
        
        # Seed processes
        processes = [
            ("Gearbox Housing Milling", "Mill aluminum casing for standard gearboxes.", machine_map["CNC Milling Machine"], 300),
            ("Custom Casing Molding", "Molding plastic outer covers for electronic devices.", machine_map["Injection Molder 3000"], 180),
            ("Wire Harness Assembly", "Robotic assembly of internal vehicle wiring harnesses.", machine_map["Robotic Assembly Arm"], 240)
        ]
        cursor.executemany(
            "INSERT INTO processes (name, details, machine_id, target_duration, status) VALUES (?, ?, ?, ?, 'pending')",
            processes
        )
        conn.commit()
        
    conn.close()

def get_current_iso_timestamp():
    return datetime.now(timezone.utc).isoformat()

def parse_iso_timestamp(ts_str):
    if not ts_str:
        return datetime.now(timezone.utc)
    # Handle older python versions that might fail standard fromisoformat if timezone character is Z
    if ts_str.endswith('Z'):
        ts_str = ts_str[:-1] + '+00:00'
    try:
        return datetime.fromisoformat(ts_str)
    except ValueError:
        return datetime.now(timezone.utc)

def calculate_live_times(process):
    """Calculates the real-time elapsed and delay seconds for a process since its last_status_change."""
    status = process["status"]
    last_change_str = process["last_status_change"]
    elapsed = process["elapsed_seconds"] or 0
    delay = process["delay_seconds"] or 0
    
    if status in ("running", "delayed") and last_change_str:
        now = datetime.now(timezone.utc)
        last_change = parse_iso_timestamp(last_change_str)
        delta_seconds = int((now - last_change).total_seconds())
        if delta_seconds > 0:
            if status == "running":
                elapsed += delta_seconds
            elif status == "delayed":
                delay += delta_seconds
                
    return elapsed, delay

def get_machines():
    conn = get_db_connection()
    machines = conn.execute("SELECT * FROM machines").fetchall()
    conn.close()
    return [dict(m) for m in machines]

def add_machine(name, type_name, details):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO machines (name, type, status, details) VALUES (?, ?, 'idle', ?)",
        (name, type_name, details)
    )
    conn.commit()
    conn.close()

def update_machine_status(machine_id, status):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE machines SET status = ? WHERE id = ?", (status, machine_id))
    conn.commit()
    conn.close()

def get_processes():
    """Fetches all processes and calculates their live progress on the fly."""
    conn = get_db_connection()
    # Fetch with machine name
    query = """
        SELECT p.*, m.name as machine_name 
        FROM processes p 
        LEFT JOIN machines m ON p.machine_id = m.id
    """
    rows = conn.execute(query).fetchall()
    conn.close()
    
    processes_list = []
    for row in rows:
        p_dict = dict(row)
        live_elapsed, live_delay = calculate_live_times(p_dict)
        p_dict["live_elapsed_seconds"] = live_elapsed
        p_dict["live_delay_seconds"] = live_delay
        processes_list.append(p_dict)
        
    return processes_list

def add_process(name, details, machine_id, target_duration):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO processes (name, details, machine_id, target_duration, status) VALUES (?, ?, ?, ?, 'pending')",
        (name, details, machine_id, target_duration)
    )
    conn.commit()
    conn.close()

def transition_process(process_id, new_status, delay_reason=None):
    """
    State machine transition for processes. Updates elapsed/delay times 
    up to current moment, updates database, writes to logs, and 
    automatically adjusts machine state.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Fetch current process state
    process = cursor.execute("SELECT * FROM processes WHERE id = ?", (process_id,)).fetchone()
    if not process:
        conn.close()
        return False
        
    process_dict = dict(process)
    old_status = process_dict["status"]
    machine_id = process_dict["machine_id"]
    
    # Avoid transition to same state (unless we are changing delay reason or starting)
    if old_status == new_status and new_status != "delayed":
        conn.close()
        return True
        
    # 2. Calculate live running and delay times up to now
    live_elapsed, live_delay = calculate_live_times(process_dict)
    
    # Calculate duration of the state we are leaving
    now_str = get_current_iso_timestamp()
    duration_of_prev_state = 0
    if process_dict["last_status_change"]:
        last_change = parse_iso_timestamp(process_dict["last_status_change"])
        now = datetime.now(timezone.utc)
        duration_of_prev_state = int((now - last_change).total_seconds())
        if duration_of_prev_state < 0:
            duration_of_prev_state = 0
            
    # 3. Update the process in DB
    # If starting for the first time, set last_status_change
    cursor.execute("""
        UPDATE processes 
        SET status = ?, 
            last_status_change = ?, 
            elapsed_seconds = ?, 
            delay_seconds = ? 
        WHERE id = ?
    """, (new_status, now_str, live_elapsed, live_delay, process_id))
    
    # 4. Insert log entry
    cursor.execute("""
        INSERT INTO logs (process_id, machine_id, event_type, delay_reason, timestamp, duration_seconds)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (process_id, machine_id, new_status, delay_reason, now_str, duration_of_prev_state))
    
    # 5. Automatically manage machine status based on processes
    # Find if there are other running processes on the machine
    if machine_id:
        if new_status == "running":
            cursor.execute("UPDATE machines SET status = 'active' WHERE id = ?", (machine_id,))
        else:
            # Check if any other process is running on this machine
            cursor.execute(
                "SELECT COUNT(*) FROM processes WHERE machine_id = ? AND status = 'running' AND id != ?",
                (machine_id, process_id)
            )
            running_count = cursor.fetchone()[0]
            if running_count == 0:
                # Set machine back to idle (unless it's in maintenance)
                cursor.execute("SELECT status FROM machines WHERE id = ?", (machine_id,))
                machine_status = cursor.fetchone()[0]
                if machine_status != "maintenance":
                    cursor.execute("UPDATE machines SET status = 'idle' WHERE id = ?", (machine_id,))
                    
    conn.commit()
    conn.close()
    return True

def get_logs():
    conn = get_db_connection()
    query = """
        SELECT l.*, p.name as process_name, m.name as machine_name 
        FROM logs l
        LEFT JOIN processes p ON l.process_id = p.id
        LEFT JOIN machines m ON l.machine_id = m.id
        ORDER BY l.id DESC
    """
    rows = conn.execute(query).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_analytics_data():
    """Aggregates times, delays, and statuses for machine efficiency analysis."""
    conn = get_db_connection()
    
    # 1. Total uptime and delay by machine
    # Note that we sum the finalized elapsed_seconds and delay_seconds from completed/paused/delayed processes
    # plus any running process calculation. We can just use the synced lists of processes.
    processes_list = get_processes()
    
    # Group by machine
    machine_stats = {}
    # Initialize with all machines
    machines = conn.execute("SELECT id, name FROM machines").fetchall()
    for m in machines:
        machine_stats[m["id"]] = {
            "machine_name": m["name"],
            "total_elapsed": 0,
            "total_delay": 0,
            "processes_count": 0,
            "completed_count": 0
        }
        
    for p in processes_list:
        mid = p["machine_id"]
        if mid in machine_stats:
            machine_stats[mid]["total_elapsed"] += p["live_elapsed_seconds"]
            machine_stats[mid]["total_delay"] += p["live_delay_seconds"]
            machine_stats[mid]["processes_count"] += 1
            if p["status"] == "completed":
                machine_stats[mid]["completed_count"] += 1
                
    # 2. Group logs for delay reason distribution
    delay_logs = conn.execute("""
        SELECT delay_reason, COUNT(*) as count, SUM(duration_seconds) as total_duration
        FROM logs 
        WHERE event_type = 'delayed' AND delay_reason IS NOT NULL AND delay_reason != ''
        GROUP BY delay_reason
    """).fetchall()
    
    delay_distribution = [dict(r) for r in delay_logs]
    
    conn.close()
    return list(machine_stats.values()), delay_distribution
