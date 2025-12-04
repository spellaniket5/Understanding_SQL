import sqlite3
import streamlit as st
import pandas as pd
from datetime import date

# --- Database Setup & Functions ---
DB_NAME = "clinic.db"

def init_db():
    """Initializes the DB with the schema provided."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Enable foreign keys
    c.execute("PRAGMA foreign_keys = ON;")
    
    # Create Tables
    c.execute('''CREATE TABLE IF NOT EXISTS Doctors (
        doctor_id INTEGER PRIMARY KEY,
        first_name VARCHAR(50) NOT NULL,
        specialty VARCHAR(50) NOT NULL,
        hourly_rate DECIMAL(8, 2)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS Patients (
        patient_id INTEGER PRIMARY KEY,
        name VARCHAR(50) NOT NULL,
        phone VARCHAR(15) UNIQUE
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS Appointments (
        appoint_id INTEGER PRIMARY KEY,
        patient_id INT NOT NULL,
        doctor_id INT NOT NULL,
        appoint_date DATE NOT NULL,
        status TEXT CHECK(status IN ('Scheduled', 'Completed', 'Cancelled')),
        FOREIGN KEY (patient_id) REFERENCES Patients(patient_id),
        FOREIGN KEY (doctor_id) REFERENCES Doctors(doctor_id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS Treatments (
        treatment_id INTEGER PRIMARY KEY,
        appoint_id INT NOT NULL,
        service_name VARCHAR(50) NOT NULL,
        cost DECIMAL(8, 2) NOT NULL,
        FOREIGN KEY (appoint_id) REFERENCES Appointments(appoint_id)
    )''')

    # Seed Data (Only if empty)
    c.execute("SELECT count(*) FROM Doctors")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO Doctors (first_name, specialty, hourly_rate) VALUES ('Dr. House', 'Diagnostician', 200), ('Dr. Grey', 'Surgeon', 300)")
        c.execute("INSERT INTO Patients (name, phone) VALUES ('John Doe', '555-0101'), ('Jane Smith', '555-0102')")
        conn.commit()

    conn.close()

def run_query(query, params=()):
    """Helper to run queries safely."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute(query, params)
        conn.commit()
        return c
    except Exception as e:
        st.error(f"Database Error: {e}")
    finally:
        conn.close()

def get_df(query, params=()):
    """Helper to get data as a Pandas DataFrame for display."""
    conn = sqlite3.connect(DB_NAME)
    try:
        df = pd.read_sql_query(query, conn, params=params)
        return df
    finally:
        conn.close()

# --- The UI Application ---

st.set_page_config(page_title="Clinic Manager", layout="wide")
init_db() # Ensure DB exists on load

st.title("🏥 Clinic Management System")
st.markdown("---")

# Sidebar for Navigation
menu = st.sidebar.radio("Navigate", ["Dashboard", "Manage Appointments", "Patient Records", "Billing & Treatments"])

# --- TAB 1: DASHBOARD ---
if menu == "Dashboard":
    st.header("Daily Overview")
    
    col1, col2, col3 = st.columns(3)
    
    # Metric: Total Appointments
    count_appt = get_df("SELECT COUNT(*) as count FROM Appointments").iloc[0]['count']
    col1.metric("Total Appointments", count_appt)
    
    # Metric: Total Patients
    count_pat = get_df("SELECT COUNT(*) as count FROM Patients").iloc[0]['count']
    col2.metric("Total Patients", count_pat)
    
    # Metric: Revenue
    revenue = get_df("SELECT SUM(cost) as total FROM Treatments").iloc[0]['total']
    revenue = revenue if revenue else 0
    col3.metric("Total Revenue", f"${revenue:,.2f}")

    st.subheader("Recent Activity")
    df_recent = get_df("""
        SELECT A.appoint_date, P.name as Patient, D.first_name as Doctor, A.status 
        FROM Appointments A
        JOIN Patients P ON A.patient_id = P.patient_id
        JOIN Doctors D ON A.doctor_id = D.doctor_id
        ORDER BY A.appoint_date DESC LIMIT 5
    """)
    st.dataframe(df_recent, use_container_width=True)

# --- TAB 2: MANAGE APPOINTMENTS ---
elif menu == "Manage Appointments":
    st.header("📅 Appointment Center")
    
    # Form to Add Appointment
    with st.expander("Book New Appointment"):
        with st.form("book_appt"):
            col1, col2 = st.columns(2)
            
            # Fetch lists for dropdowns (Abstracting IDs)
            pats = get_df("SELECT patient_id, name FROM Patients")
            docs = get_df("SELECT doctor_id, first_name FROM Doctors")
            
            pat_dict = dict(zip(pats['name'], pats['patient_id']))
            doc_dict = dict(zip(docs['first_name'], docs['doctor_id']))
            
            sel_pat = col1.selectbox("Select Patient", pat_dict.keys())
            sel_doc = col2.selectbox("Select Doctor", doc_dict.keys())
            date_input = st.date_input("Date")
            
            submitted = st.form_submit_button("Book Appointment")
            if submitted:
                run_query("INSERT INTO Appointments (patient_id, doctor_id, appoint_date, status) VALUES (?, ?, ?, ?)",
                          (pat_dict[sel_pat], doc_dict[sel_doc], date_input, 'Scheduled'))
                st.success(f"Appointment booked for {sel_pat} with {sel_doc}!")
                st.rerun()

    # View Appointments Table
    st.subheader("Scheduled Appointments")
    
    # Filter by Status
    status_filter = st.selectbox("Filter by Status", ["All", "Scheduled", "Completed", "Cancelled"])
    
    base_query = """
        SELECT A.appoint_id, A.appoint_date, P.name as Patient, D.first_name as Doctor, A.status 
        FROM Appointments A
        JOIN Patients P ON A.patient_id = P.patient_id
        JOIN Doctors D ON A.doctor_id = D.doctor_id
    """
    
    if status_filter != "All":
        df_appt = get_df(base_query + " WHERE A.status = ?", (status_filter,))
    else:
        df_appt = get_df(base_query)
        
    st.dataframe(df_appt, use_container_width=True, hide_index=True)
    
    # Quick Action: Update Status
    st.markdown("### Update Status")
    c1, c2, c3 = st.columns([1, 2, 1])
    appt_id_input = c1.number_input("Enter Appointment ID", min_value=1, step=1)
    new_status = c2.selectbox("New Status", ["Completed", "Cancelled"])
    if c3.button("Update"):
        run_query("UPDATE Appointments SET status = ? WHERE appoint_id = ?", (new_status, appt_id_input))
        st.success("Status updated.")
        st.rerun()

# --- TAB 3: PATIENT RECORDS ---
elif menu == "Patient Records":
    st.header("👤 Patient Directory")
    
    # Add Patient
    with st.expander("Register New Patient"):
        with st.form("new_pat"):
            name = st.text_input("Full Name")
            phone = st.text_input("Phone Number")
            if st.form_submit_button("Register"):
                run_query("INSERT INTO Patients (name, phone) VALUES (?, ?)", (name, phone))
                st.success("Patient registered!")
                st.rerun()
    
    # Search Patient
    search_term = st.text_input("Search Patient by Name")
    if search_term:
        df_pat = get_df("SELECT * FROM Patients WHERE name LIKE ?", (f'%{search_term}%',))
    else:
        df_pat = get_df("SELECT * FROM Patients")
    
    st.dataframe(df_pat, use_container_width=True)

# --- TAB 4: BILLING ---
elif menu == "Billing & Treatments":
    st.header("💰 Billing & Treatments")
    
    # Add Treatment to Appointment
    st.subheader("Add Charge to Appointment")
    
    # Only show appointments that aren't cancelled
    appts = get_df("""
        SELECT A.appoint_id, P.name, A.appoint_date 
        FROM Appointments A 
        JOIN Patients P ON A.patient_id = P.patient_id 
        WHERE A.status != 'Cancelled'
    """)
    
    if not appts.empty:
        # Create a readable string for the dropdown
        appts['display'] = "ID " + appts['appoint_id'].astype(str) + " - " + appts['name'] + " (" + appts['appoint_date'] + ")"
        appt_dict = dict(zip(appts['display'], appts['appoint_id']))
        
        selected_appt_display = st.selectbox("Select Appointment", appt_dict.keys())
        service = st.text_input("Service Name (e.g., General Checkup)")
        cost = st.number_input("Cost ($)", min_value=0.0, step=10.0)
        
        if st.button("Add Charge"):
            run_query("INSERT INTO Treatments (appoint_id, service_name, cost) VALUES (?, ?, ?)", 
                      (appt_dict[selected_appt_display], service, cost))
            st.success("Charge added successfully!")
    else:
        st.info("No active appointments found.")

    st.markdown("---")
    st.subheader("Transaction Log")
    df_treat = get_df("""
        SELECT T.treatment_id, P.name as Patient, T.service_name, T.cost 
        FROM Treatments T
        JOIN Appointments A ON T.appoint_id = A.appoint_id
        JOIN Patients P ON A.patient_id = P.patient_id
    """)
    st.dataframe(df_treat, use_container_width=True) 