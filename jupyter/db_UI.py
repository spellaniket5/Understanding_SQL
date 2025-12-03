# CLINIC MANAGEMENT UI – Rewritten for SQLite
import streamlit as st
import pandas as pd
# NOTE: Need to ensure you have 'streamlit', 'pandas', and 'SQLAlchemy' installed:
# pip install streamlit pandas SQLAlchemy

from sqlalchemy import create_engine, text

# --- CONFIGURATION (CHANGED FOR SQLITE) ---
# NOTE: This path must be correct relative to where you run the Streamlit app!
# Based on your previous setup, the path is relative to the project root.
SQLITE_DB_PATH = "sqlite:///../Clinic.db" 
# Use 'sqlite:///Clinic.db' if the file is in the same directory as this script.

# Create the SQLAlchemy engine for SQLite
# SQLite does not use a username/password, just the file path.
engine = create_engine(SQLITE_DB_PATH)

# --- CONNECTION TEST ---
with st.spinner("Connecting to SQLite database..."):
    try:
        # Using a simple query to confirm the connection is active
        pd.read_sql("SELECT 1", engine)
        st.success("Successfully connected to the Clinic database!")
    except Exception as e:
        st.error(f"Cannot connect to the database file: {e}")
        st.error(f"Please ensure the database file exists at the path: {SQLITE_DB_PATH}")
        st.stop()
        
# --- STREAMLIT UI ---
st.title("🏥 Clinic Management System")
st.caption("Simple UI to manage Doctors, Patients, Appointments, and Treatments.")

menu = st.sidebar.selectbox("Go to", [
    "Doctors", "Patients", "Appointments", "Treatments", "Raw SQL"
])

# Utility function to handle INSERT and RERUN
def execute_query(sql_query, params=None, success_msg="Operation successful!"):
    try:
        with engine.begin() as conn:
            if params:
                conn.execute(sql_query, params)
            else:
                conn.execute(sql_query)
        st.success(success_msg)
        st.rerun()
    except Exception as e:
        st.error(f"Database Error: {e}")


# DOCTORS
if menu == "Doctors":
    st.subheader("👨‍⚕️ Doctors")
    
    # READ/DISPLAY
    if st.button("Refresh Doctors", key="refresh_docs"):
        df = pd.read_sql("SELECT * FROM Doctors ORDER BY doctor_id", engine)
        st.dataframe(df, use_container_width=True)

    # CREATE/ADD NEW DOCTOR
    with st.expander("➕ Add new doctor"):
        with st.form("add_doctor"):
            col1, col2 = st.columns(2)
            with col1:
                fname = st.text_input("First name", max_chars=50)
                specialty = st.text_input("Specialty", placeholder="e.g. Cardiology", max_chars=50)
            with col2:
                rate = st.number_input("Hourly rate ($)", min_value=0.0, format="%.2f")
            
            if st.form_submit_button("Save doctor"):
                if not fname or not specialty:
                    st.error("First name and Specialty are required.")
                else:
                    # NOTE: SQLite uses '?' as the placeholder, but SQLAlchemy's text() works with %s,
                    # which it translates properly for SQLite/MySQL/etc., but we will use '?' for clean SQLite
                    # The original %s will work with SQLAlchemy when using the conn.execute() method as a proxy.
                    sql = text("INSERT INTO Doctors (first_name, specialty, hourly_rate) VALUES (:fname, :spec, :rate)")
                    execute_query(sql, {"fname": fname, "spec": specialty, "rate": rate}, "Doctor added!")

# PATIENTS
if menu == "Patients":
    st.subheader("🧑‍🦱 Patients")
    
    # READ/DISPLAY
    if st.button("Refresh Patients", key="refresh_pats"):
        df = pd.read_sql("SELECT * FROM Patients ORDER BY patient_id DESC", engine)
        st.dataframe(df, use_container_width=True)

    # CREATE/REGISTER NEW PATIENT
    with st.expander("➕ Register new patient"):
        with st.form("add_patient"):
            name = st.text_input("Full name", max_chars=50)
            phone = st.text_input("Phone", placeholder="e.g. 9848000001", max_chars=15)
            
            if st.form_submit_button("Register patient"):
                if not name or not phone:
                    st.error("Name and phone required")
                else:
                    sql = text("INSERT INTO Patients (name, phone) VALUES (:name, :phone)")
                    execute_query(sql, {"name": name, "phone": phone}, f"Patient {name} registered!")


# APPOINTMENTS
if menu == "Appointments":
    st.subheader("🗓️ Appointments")
    
    # READ/DISPLAY
    if st.button("Refresh Appointments", key="refresh_apps"):
        query = """
        SELECT a.appoint_id,
              p.name AS patient,
              d.first_name AS doctor,
              d.specialty,
              a.appoint_date,
              a.status
        FROM Appointments a
        JOIN Patients p ON a.patient_id = p.patient_id
        JOIN Doctors d ON a.doctor_id = d.doctor_id
        ORDER BY a.appoint_date DESC, a.appoint_id DESC
        """
        df = pd.read_sql(query, engine)
        st.dataframe(df, use_container_width=True)

    # CREATE/BOOK NEW APPOINTMENT
    with st.expander("➕ Book new appointment"):
        with st.form("new_appointment"):
            # Fetch lists for selection boxes
            patients = pd.read_sql("SELECT patient_id, name FROM Patients", engine)
            doctors = pd.read_sql("SELECT doctor_id, first_name, specialty FROM Doctors", engine)

            # Dropdown options
            patient_name_list = patients["name"].tolist()
            doctor_combo_list = doctors.apply(lambda x: f"Dr. {x.first_name} - {x.specialty}", axis=1).tolist()
            
            patient_name = st.selectbox("Patient", patient_name_list, key="pat_select")
            doctor_combo = st.selectbox("Doctor", doctor_combo_list, key="doc_select")
            
            appoint_date = st.date_input("Appointment date")
            status = st.selectbox("Status", ["Scheduled", "Completed", "Cancelled"])

            if st.form_submit_button("Book appointment"):
                # Get actual IDs based on selected names/combos
                pat_id = patients.loc[patients["name"] == patient_name, "patient_id"].iloc[0]
                doc_id = doctors.loc[doctors.apply(lambda x: f"Dr. {x.first_name} - {x.specialty}", axis=1) == doctor_combo, "doctor_id"].iloc[0]
                
                sql = text("INSERT INTO Appointments (patient_id, doctor_id, appoint_date, status) VALUES (:pat_id, :doc_id, :app_date, :status)")
                params = {"pat_id": pat_id, "doc_id": doc_id, "app_date": appoint_date, "status": status}
                
                execute_query(sql, params, "Appointment booked!")

# TREATMENTS
if menu == "Treatments":
    st.subheader("💉 Treatments / Services Performed")
    
    # READ/DISPLAY
    if st.button("Refresh Treatments", key="refresh_treat"):
        query = """
        SELECT t.treatment_id, t.service_name, t.cost,
               a.appoint_date,
               p.name AS patient,
               d.first_name AS doctor
        FROM Treatments t
        JOIN Appointments a ON t.appoint_id = a.appoint_id
        JOIN Patients p ON a.patient_id = p.patient_id
        JOIN Doctors d ON a.doctor_id = d.doctor_id
        ORDER BY t.treatment_id DESC
        """
        df = pd.read_sql(query, engine)
        st.dataframe(df, use_container_width=True)

    # CREATE/ADD NEW TREATMENT
    with st.expander("➕ Add treatment (after appointment)"):
        with st.form("add_treatment"):
            # Fetch appointments for selection
            appointments = pd.read_sql("""
                SELECT appoint_id, 
                       DATE(appoint_date) as date,
                       p.name, d.first_name
                FROM Appointments a
                JOIN Patients p ON a.patient_id = p.patient_id
                JOIN Doctors d ON a.doctor_id = d.doctor_id
            """, engine)

            # Create readable appointment choice string
            appoint_choice_list = appointments.apply(lambda x: f"{x.date} - {x.name} with Dr. {x.first_name}", axis=1).tolist()
            
            appoint_choice = st.selectbox("Appointment", appoint_choice_list)
            
            # Find the ID of the chosen appointment
            appoint_id = appointments.loc[appointments.apply(lambda x: f"{x.date} - {x.name} with Dr. {x.first_name}", axis=1) == appoint_choice, "appoint_id"].iloc[0]

            service = st.text_input("Service name", max_chars=50)
            cost = st.number_input("Cost ($)", min_value=0.0, format="%.2f")

            if st.form_submit_button("Record treatment"):
                if not service:
                    st.error("Service name is required.")
                else:
                    sql = text("INSERT INTO Treatments (appoint_id, service_name, cost) VALUES (:app_id, :service, :cost)")
                    params = {"app_id": appoint_id, "service": service, "cost": cost}
                    execute_query(sql, params, "Treatment recorded!")

# RAW SQL
if menu == "Raw SQL":
    st.subheader("💻 Raw SQL Query Interface")
    st.warning("Danger zone – full SQL access. Use SELECT for read operations only.")
    q = st.text_area("Query", "SELECT * FROM Appointments LIMIT 5", height=150)
    
    col1, col2 = st.columns([1, 4])
    with col1:
        run_button = st.button("Run SELECT Query")
    with col2:
        st.caption("Only SELECT queries are fully supported here.")
        
    if run_button:
        try:
            df = pd.read_sql(q, engine)
            st.dataframe(df, use_container_width=True)
            st.info(f"{len(df)} rows returned.")
        except Exception as e:
            st.error(f"SQL Error: {e}")