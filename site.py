import streamlit as st
import pyodbc
import pandas as pd
from datetime import date, time, datetime, timedelta

# --- CONFIGURARE BAZA DE DATE ---
SERVER = 'Vlad-Dell'
DATABASE = 'Cabinet Medic de Familie'
DRIVER = '{ODBC Driver 17 for SQL Server}'

def get_connection():
    try:
        conn_str = f'DRIVER={DRIVER};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;'
        return pyodbc.connect(conn_str)
    except Exception as e:
        st.error(f"Eroare de conexiune la baza de date: {e}")
        return None

# --- CSS: Stiluri vizuale (Fără override la Tabs) ---
st.markdown("""
    <style>
    div[data-baseweb="select"] input { caret-color: transparent !important; cursor: pointer !important; }
    div[data-baseweb="select"] { cursor: pointer !important; }
    </style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---
def get_medici_dict():
    conn = get_connection()
    if not conn: return {}
    df = pd.read_sql("SELECT MedicID, Nume, Prenume FROM Medici", conn)
    conn.close()
    return {f"{row['Nume']} {row['Prenume']}": row['MedicID'] for index, row in df.iterrows()}

def get_pacienti_dict():
    conn = get_connection()
    if not conn: return {}
    df = pd.read_sql("SELECT PacientID, Nume, Prenume, CNP FROM Pacienti", conn)
    conn.close()
    return {f"{row['Nume']} {row['Prenume']} ({row['CNP']})": row['PacientID'] for index, row in df.iterrows()}

def get_programari_dict():
    conn = get_connection()
    if not conn: return {}
    sql = """
        SELECT PR.ProgramareID, PR.Data, P.Nume, P.Prenume 
        FROM Programari PR
        JOIN Pacienti P ON PR.PacientID = P.PacientID
    """
    df = pd.read_sql(sql, conn)
    conn.close()
    return {f"{row['Data']} | {row['Nume']} {row['Prenume']}": row['ProgramareID'] for index, row in df.iterrows()}

# --- FUNCȚIE EXECUȚIE REPORT ---
def execute_report(query_data, key):
    """Funcție helper pentru afișarea parametrilor și execuția interogărilor în tab-uri"""
    current_sql = query_data['sql']
    query_type = query_data['type']
    
    st.info(f"ℹ️ {query_data['desc']}")
    
    params_list = []
    
    # Logică Parametri
    if query_type == "param":
        col_input, _ = st.columns([1, 2])
        with col_input:
            if key == "Programările dintr-o anumită zi":
                val = st.date_input("Alege Data", value=date.today(), key=f"d_{key}")
                params_list.append(val)
            
            elif key == "Pacienți după tipul afecțiunii":
                optiuni = ["Cronic", "Acut", "Neurologic", "Oftalmologic", "Traumatism", "Psihiatric", "Digestiv", "ORL", "Dermatologic"]
                val = st.selectbox("Selectează Tipul Afecțiunii", optiuni, key=f"s_{key}")
                params_list.append(val)

            elif key == "Situația programărilor":
                optiuni = ["Programat", "Finalizat", "Anulat", "Neprezentat"]
                val = st.selectbox("Selectează Statusul", optiuni, key=f"st_{key}")
                params_list.append(val)

            elif key == "Top medici după volumul de muncă":
                c1, c2 = st.columns(2)
                d1 = c1.date_input("De la", key=f"d1_{key}")
                d2 = c2.date_input("Până la", key=f"d2_{key}")
                params_list.append(d1)
                params_list.append(d2)

            elif key == "Pacienți fără istoric medical (după asigurare)":
                optiuni = ["Asigurat", "Neasigurat", "Coasigurat", "Pensionar", "Student"]
                val = st.selectbox("Status Asigurare", optiuni, key=f"asig_{key}")
                params_list.append(val)

            elif key == "Pacienți cu afecțiuni multiple":
                val = st.number_input("Minim număr afecțiuni", min_value=1, value=2, step=1, key=f"nr_{key}")
                params_list.append(val)

            elif key == "Lista pacienților per medic":
                medici = get_medici_dict()
                nume_medic = st.selectbox("Alege Medicul", list(medici.keys()), key=f"med_{key}")
                params_list.append(medici[nume_medic])

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚀 Generează Raport", key=f"btn_{key}", type="primary"):
        conn = get_connection()
        if conn:
            try:
                df = pd.read_sql(current_sql, conn, params=params_list)
                st.subheader("Rezultate:")
                if not df.empty:
                    st.write(f"S-au găsit {len(df)} înregistrări.")
                    st.dataframe(df, width="stretch")
                else:
                    st.warning("Nu au fost găsite rezultate.")
            except Exception as e:
                st.error(f"Eroare SQL: {e}")
            finally:
                conn.close()

# ==============================================================================
# PAGINA 1: DASHBOARD
# ==============================================================================
def page_dashboard(conn):
    st.header("📊 Dashboard Clinică")
    
    # Definim subseturile de rapoarte
    QUERIES_MEDICI = {
        "Lista pacienților per medic": {
            "type": "param", 
            "desc": "Lista pacienților asignați unui anumit medic de familie.",
            "sql": """
                SELECT (P.Nume + ' ' + P.Prenume) AS Pacient, P.Telefon, P.StatusAsigurare
                FROM Pacienti P
                INNER JOIN Medici M ON P.MedicID = M.MedicID
                WHERE M.MedicID = ?
                ORDER BY P.Nume
            """
        },
        "Top medici după volumul de muncă": {
            "type": "param",
            "desc": "Numără toate programările (indiferent de status) între două date.",
            "sql": """
                SELECT TOP 5 (M.Nume + ' ' + M.Prenume) AS Medic, M.Specialitate, 
                       COUNT(PR.ProgramareID) AS TotalProgramari
                FROM Medici M
                JOIN Programari PR ON M.MedicID = PR.MedicID
                WHERE PR.Data BETWEEN ? AND ? 
                GROUP BY M.Nume, M.Prenume, M.Specialitate
                ORDER BY TotalProgramari DESC
            """
        },
        "Medici care au consultat pacienți neasigurați": {
            "type": "static",
            "desc": "Medici care au în istoric programări cu pacienți neasigurați.",
            "sql": """
                SELECT (M.Nume + ' ' + M.Prenume) AS Medic, M.Specialitate
                FROM Medici M
                WHERE M.MedicID IN (
                    SELECT DISTINCT PR.MedicID
                    FROM Programari PR
                    JOIN Pacienti P ON PR.PacientID = P.PacientID
                    WHERE P.StatusAsigurare = 'Neasigurat'
                )
            """
        }
    }

    QUERIES_PACIENTI = {
        "Detalii rețete prescrise": {
            "type": "static",
            "desc": "Legătura dintre rețetă, consultație, pacient și medic.",
            "sql": """
                SELECT R.DataEmiterii, (P.Nume + ' ' + P.Prenume) AS Pacient, 
                       (M.Nume + ' ' + M.Prenume) AS Medic, R.Medicamente, R.Valabilitate
                FROM Retete R
                JOIN Consultatii C ON R.ConsultatieID = C.ConsultatieID
                JOIN Pacienti P ON C.PacientID = P.PacientID
                JOIN Medici M ON C.MedicID = M.MedicID
            """
        },
        "Pacienți cu istoric de anulări": {
            "type": "static",
            "desc": "Pacienți care au cel puțin o programare cu statusul 'Anulat'.",
            "sql": """
                SELECT (Nume + ' ' + Prenume) AS Pacient, Telefon, CNP
                FROM Pacienti
                WHERE PacientID IN (
                    SELECT DISTINCT PacientID 
                    FROM Programari 
                    WHERE Status = 'Anulat'
                )
            """
        },
        "Pacienți după tipul afecțiunii": {
            "type": "param",
            "desc": "Filtrează pacienții în funcție de categoria bolii.",
            "sql": """
                SELECT (P.Nume + ' ' + P.Prenume) AS Pacient, A.Nume AS Afectiune, 
                       A.Tip, PA.DataDiagnostic
                FROM Pacienti P
                JOIN PacientiAfectiuni PA ON P.PacientID = PA.PacientID
                JOIN Afectiuni A ON PA.AfectiuneID = A.AfectiuneID
                WHERE A.Tip = ?
            """
        },
        "Registru general consultații": {
            "type": "static",
            "desc": "Istoricul tuturor consultațiilor din clinică.",
            "sql": """
                SELECT C.DataConsultatie, (P.Nume + ' ' + P.Prenume) AS Pacient, 
                       (M.Nume + ' ' + M.Prenume) AS Medic, C.Diagnostic
                FROM Consultatii C
                JOIN Pacienti P ON C.PacientID = P.PacientID
                JOIN Medici M ON C.MedicID = M.MedicID
                ORDER BY C.DataConsultatie DESC
            """
        },
        "Pacienți fără istoric medical (după asigurare)": {
            "type": "param",
            "desc": "Găsește pacienții care nu au venit niciodată, filtrând după tipul de asigurare.",
            "sql": """
                SELECT (Nume + ' ' + Prenume) AS Pacient, CNP, StatusAsigurare
                FROM Pacienti
                WHERE StatusAsigurare = ?
                AND PacientID NOT IN (SELECT DISTINCT PacientID FROM Consultatii)
            """
        },
        "Pacienți cu afecțiuni multiple": {
            "type": "param",
            "desc": "Găsește pacienții complecși care au un număr minim de boli diagnosticate.",
            "sql": """
                SELECT (P.Nume + ' ' + P.Prenume) AS Pacient, COUNT(PA.AfectiuneID) AS NumarBoli
                FROM Pacienti P
                JOIN PacientiAfectiuni PA ON P.PacientID = PA.PacientID
                GROUP BY P.Nume, P.Prenume
                HAVING COUNT(PA.AfectiuneID) >= ?
                ORDER BY NumarBoli DESC
            """
        }
    }

    QUERIES_ALTELE = {
        "Programările dintr-o anumită zi": {
            "type": "param",
            "desc": "Vezi fluxul de pacienți pentru o dată aleasă.",
            "sql": """
                SELECT PR.OraStart, PR.OraEnd, (P.Nume + ' ' + P.Prenume) AS Pacient, 
                       (M.Nume + ' ' + M.Prenume) AS Medic, PR.Status
                FROM Programari PR
                INNER JOIN Pacienti P ON PR.PacientID = P.PacientID
                INNER JOIN Medici M ON PR.MedicID = M.MedicID
                WHERE PR.Data = ?
                ORDER BY PR.OraStart
            """
        },
        "Situația programărilor": {
            "type": "param",
            "desc": "Vezi toate programările în funcție de starea lor.",
            "sql": """
                SELECT PR.Data, PR.OraStart, (P.Nume + ' ' + P.Prenume) AS Pacient, 
                       P.Telefon, PR.MotivProgramare, PR.Status
                FROM Programari PR
                JOIN Pacienti P ON PR.PacientID = P.PacientID
                WHERE PR.Status = ?
                ORDER BY PR.Data DESC
            """
        },
        "Zile cu activitate intensă (peste medie)": {
            "type": "static",
            "desc": "Zilele în care numărul de programări a depășit media zilnică a clinicii.",
            "sql": """
                SELECT Data, COUNT(ProgramareID) AS NumarProgramari
                FROM Programari
                GROUP BY Data
                HAVING COUNT(ProgramareID) > (
                    SELECT AVG(CAST(DailyCount AS FLOAT)) FROM (
                        SELECT COUNT(ProgramareID) AS DailyCount 
                        FROM Programari 
                        GROUP BY Data
                    ) AS SubQuery
                )
                ORDER BY NumarProgramari DESC
            """
        }
    }

    # --- TAB-URI ---
    tab_medici, tab_pacienti, tab_altele = st.tabs(["👨‍⚕️ Medici", "👤 Pacienți", "⚙️ Altele"])

    # TAB 1: MEDICI
    with tab_medici:
        st.subheader("📅 Statistici Săptămânale")
        
        # KPI: Programări Saptamana Asta (Azi -> Duminica)
        if conn:
            try:
                today = date.today()
                # Calculam duminica viitoare (weekday 6)
                # weekday(): Luni=0, Duminica=6
                days_until_sunday = 6 - today.weekday()
                sunday = today + timedelta(days=days_until_sunday)

                # 1. Total Programări Interval
                sql_week_count = "SELECT COUNT(*) FROM Programari WHERE Data BETWEEN ? AND ?"
                week_count = pd.read_sql(sql_week_count, conn, params=[today, sunday]).iloc[0, 0]
                
                # 2. Programări per Medic Interval
                sql_week_medici = """
                    SELECT (M.Nume + ' ' + M.Prenume) AS Medic, COUNT(*) as Programari
                    FROM Programari PR
                    JOIN Medici M ON PR.MedicID = M.MedicID
                    WHERE PR.Data BETWEEN ? AND ?
                    GROUP BY M.Nume, M.Prenume
                """
                df_week = pd.read_sql(sql_week_medici, conn, params=[today, sunday])

                col_kpi1, col_kpi2 = st.columns([1, 2])
                with col_kpi1:
                    st.metric("Total Programări (Azi-Dum)", week_count)
                with col_kpi2:
                    if not df_week.empty:
                        st.caption("Distribuție pe Medici:")
                        st.dataframe(df_week, hide_index=True)
                    else:
                        st.info("Nicio programare în acest interval.")
            except Exception as e:
                st.error(f"Eroare statistici: {e}")

        st.markdown("---")
        st.subheader("Rapoarte Detaliate")
        sel_medic = st.selectbox("Alege Raport Medic:", list(QUERIES_MEDICI.keys()))
        execute_report(QUERIES_MEDICI[sel_medic], sel_medic)

    # TAB 2: PACIENTI
    with tab_pacienti:
        st.subheader("Rapoarte Pacienți")
        sel_pacient = st.selectbox("Alege Raport Pacient:", list(QUERIES_PACIENTI.keys()))
        execute_report(QUERIES_PACIENTI[sel_pacient], sel_pacient)

    # TAB 3: ALTELE
    with tab_altele:
        st.subheader("Rapoarte Operaționale")
        sel_altele = st.selectbox("Alege Raport:", list(QUERIES_ALTELE.keys()))
        execute_report(QUERIES_ALTELE[sel_altele], sel_altele)

# ==============================================================================
# PAGINA 2: GESTIUNE PACIENȚI
# ==============================================================================
def page_pacienti():
    st.header("👤 Gestiune Pacienți")
    tab1, tab2, tab3 = st.tabs(["➕ Adaugă Pacient", "✏️ Modifică Pacient", "🗑️ Șterge Pacient"])
    medici_dict = get_medici_dict()

    # --- TAB 1: ADAUGARE ---
    with tab1:
        # --- CONTAINER PENTRU MESAJE (ERORI/SUCCES) - PLASAT SUS ---
        status_container = st.container()

        st.subheader("Adaugă un pacient nou")
        with st.form("add_pacient_form"):
            c1, c2 = st.columns(2)
            nume = c1.text_input("Nume")
            prenume = c2.text_input("Prenume")
            cnp = st.text_input("CNP", max_chars=13)
            medic_nume = st.selectbox("Medic de Familie", list(medici_dict.keys()))
            data_nasterii = st.date_input("Data Nașterii", min_value=date(1920, 1, 1))
            sex = st.selectbox("Sex", ["M", "F"])
            telefon = st.text_input("Telefon")
            adresa = st.text_input("Adresa")
            status = st.selectbox("Asigurare", ["Asigurat", "Neasigurat", "Coasigurat"])
            
            if st.form_submit_button("Salvează Pacient"):
                # --- VALIDARE DATE ---
                errors = []
                if not nume.strip():
                    errors.append("⚠️ Numele este obligatoriu.")
                if not prenume.strip():
                    errors.append("⚠️ Prenumele este obligatoriu.")
                if not cnp.strip() or len(cnp.strip()) != 13 or not cnp.strip().isdigit():
                    errors.append("⚠️ CNP-ul trebuie să conțină exact 13 cifre.")
                if not telefon.strip():
                    errors.append("⚠️ Numărul de telefon este obligatoriu.")
                
                if errors:
                    # Afișăm erorile în containerul de sus
                    with status_container:
                        for error in errors:
                            st.error(error)
                else:
                    conn = get_connection()
                    if conn:
                        try:
                            cursor = conn.cursor()
                            sql = """INSERT INTO Pacienti (MedicID, Nume, Prenume, CNP, DataNasterii, Sex, Telefon, Adresa, StatusAsigurare, DataInregistrare) 
                                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE())"""
                            cursor.execute(sql, (medici_dict[medic_nume], nume, prenume, cnp, data_nasterii, sex, telefon, adresa, status))
                            conn.commit()
                            # Afișăm succesul în containerul de sus
                            with status_container:
                                st.success("Pacient adăugat cu succes!")
                        except Exception as e:
                            with status_container:
                                st.error(f"Eroare: {e}")
                        finally:
                            conn.close()

    # --- TAB 2: MODIFICARE ---
    with tab2:
        st.subheader("Modifică datele unui pacient")
        pacienti_dict = get_pacienti_dict()
        if not pacienti_dict:
            st.warning("Nu există pacienți.")
        else:
            pacient_ales_nume = st.selectbox("Caută Pacient", list(pacienti_dict.keys()))
            pacient_id_ales = pacienti_dict[pacient_ales_nume]
            
            if st.button("Încarcă Datele"):
                conn = get_connection()
                if conn:
                    df = pd.read_sql("SELECT * FROM Pacienti WHERE PacientID = ?", conn, params=[pacient_id_ales])
                    conn.close()
                    if not df.empty:
                        row = df.iloc[0]
                        st.session_state['edit_nume'] = row['Nume']
                        st.session_state['edit_prenume'] = row['Prenume']
                        st.session_state['edit_telefon'] = row['Telefon']
                        st.success("Date încărcate.")
            
            if 'edit_nume' in st.session_state:
                with st.form("edit_pacient_form"):
                    new_nume = st.text_input("Nume", value=st.session_state['edit_nume'])
                    new_prenume = st.text_input("Prenume", value=st.session_state['edit_prenume'])
                    new_telefon = st.text_input("Telefon", value=st.session_state['edit_telefon'])
                    
                    if st.form_submit_button("Actualizează"):
                        conn = get_connection()
                        if conn:
                            try:
                                sql = "UPDATE Pacienti SET Nume=?, Prenume=?, Telefon=? WHERE PacientID=?"
                                conn.cursor().execute(sql, (new_nume, new_prenume, new_telefon, pacient_id_ales))
                                conn.commit()
                                st.success("Date actualizate!")
                            except Exception as e:
                                st.error(str(e))
                            finally:
                                conn.close()

    # --- TAB 3: STERGERE ---
    with tab3:
        st.subheader("Șterge un pacient")
        st.warning("Atenție: Ștergerea este definitivă!")
        pacienti_dict_del = get_pacienti_dict()
        if pacienti_dict_del:
            pacient_del_nume = st.selectbox("Selectează Pacientul", list(pacienti_dict_del.keys()))
            pacient_del_id = pacienti_dict_del[pacient_del_nume]
            
            if st.button("Șterge Pacient", type="primary"):
                conn = get_connection()
                if conn:
                    try:
                        conn.cursor().execute("DELETE FROM Programari WHERE PacientID=?", [pacient_del_id])
                        conn.cursor().execute("DELETE FROM Pacienti WHERE PacientID=?", [pacient_del_id])
                        conn.commit()
                        st.success(f"Pacientul {pacient_del_nume} a fost șters.")
                    except Exception as e:
                        st.error(f"Eroare: {e}")
                    finally:
                        conn.close()

# ==============================================================================
# PAGINA 3: GESTIUNE PROGRAMĂRI
# ==============================================================================
def page_programari():
    st.header("📅 Gestiune Programări")
    tab1, tab2, tab3 = st.tabs(["➕ Programare Nouă", "✏️ Modifică", "🗑️ Șterge"])
    medici_dict = get_medici_dict()
    pacienti_dict = get_pacienti_dict()

    # --- TAB 1: ADAUGARE ---
    with tab1:
        st.subheader("Creează o programare")
        with st.form("add_prog_form"):
            col1, col2 = st.columns(2)
            p_nume = col1.selectbox("Pacient", list(pacienti_dict.keys()))
            m_nume = col2.selectbox("Medic", list(medici_dict.keys()))
            data_prog = st.date_input("Data", value=date.today())
            ora_start = st.time_input("Ora Start", value=time(9, 00))
            ora_end = st.time_input("Ora Sfârșit", value=time(9, 30))
            motiv = st.text_input("Motiv Programare")
            status = st.selectbox("Status", ["Programat", "Finalizat", "Anulat"])
            
            if st.form_submit_button("Salvează Programarea"):
                conn = get_connection()
                if conn:
                    try:
                        str_start = ora_start.strftime("%H:%M")
                        str_end = ora_end.strftime("%H:%M")
                        sql = """INSERT INTO Programari (PacientID, MedicID, Data, OraStart, OraEnd, MotivProgramare, Status) 
                                 VALUES (?, ?, ?, ?, ?, ?, ?)"""
                        conn.cursor().execute(sql, (pacienti_dict[p_nume], medici_dict[m_nume], data_prog, str_start, str_end, motiv, status))
                        conn.commit()
                        st.success("Programare salvată!")
                    except Exception as e:
                        st.error(f"Eroare: {e}")
                    finally:
                        conn.close()

    # --- TAB 2: MODIFICARE ---
    with tab2:
        st.subheader("Modifică Status/Ora")
        prog_dict = get_programari_dict()
        if not prog_dict:
            st.info("Nu există programări.")
        else:
            prog_name = st.selectbox("Alege Programarea", list(prog_dict.keys()))
            prog_id = prog_dict[prog_name]
            new_status = st.selectbox("Noul Status", ["Programat", "Finalizat", "Anulat"], key="status_edit")
            new_motiv = st.text_input("Modifică Motivul", key="motiv_edit")
            
            if st.button("Actualizează Programare"):
                conn = get_connection()
                if conn:
                    try:
                        if new_motiv.strip():
                            sql = "UPDATE Programari SET Status=?, MotivProgramare=? WHERE ProgramareID=?"
                            params = (new_status, new_motiv, prog_id)
                        else:
                            sql = "UPDATE Programari SET Status=? WHERE ProgramareID=?"
                            params = (new_status, prog_id)
                        
                        conn.cursor().execute(sql, params)
                        conn.commit()
                        st.success("Actualizat!")
                    except Exception as e:
                        st.error(str(e))
                    finally:
                        conn.close()


    # --- TAB 3: STERGERE ---
    with tab3:
        st.subheader("Anulează/Șterge Programare")
        prog_dict_del = get_programari_dict()
        if prog_dict_del:
            del_name = st.selectbox("Selectează pentru ștergere", list(prog_dict_del.keys()), key="del_prog")
            del_id = prog_dict_del[del_name]
            if st.button("Șterge", type="primary"):
                conn = get_connection()
                if conn:
                    try:
                        conn.cursor().execute("DELETE FROM Programari WHERE ProgramareID=?", [del_id])
                        conn.commit()
                        st.success("Programarea a fost ștearsă.")
                    except Exception as e:
                        st.error(str(e))
                    finally:
                        conn.close()

# ==============================================================================
# PAGINA 4: ORAR MEDICI
# ==============================================================================
def page_orar_medici():
    st.header("🗓️ Orar și Activitate Medici")
    st.markdown("Vizualizează programul unui anumit medic.")

    medici_dict = get_medici_dict()
    if not medici_dict:
        st.error("Nu există medici în baza de date.")
        return

    # Select box pe toata latimea (fara coloane)
    nume_medic = st.selectbox("Selectează Medicul:", list(medici_dict.keys()))
    
    medic_id = medici_dict[nume_medic]

    # Interogare pentru orarul medicului
    sql = """
        SELECT PR.Data, PR.OraStart, PR.OraEnd,
               (P.Nume + ' ' + P.Prenume) AS Pacient,
               P.Telefon, PR.MotivProgramare, PR.Status
        FROM Programari PR
        JOIN Pacienti P ON PR.PacientID = P.PacientID
        WHERE PR.MedicID = ?
        ORDER BY PR.Data DESC, PR.OraStart ASC
    """
    
    conn = get_connection()
    if conn:
        try:
            df = pd.read_sql(sql, conn, params=[medic_id])
            st.markdown(f"### Programări pentru: **{nume_medic}**")
            
            if not df.empty:
                # Formatare tabel
                st.dataframe(df, width="stretch")
            else:
                st.info("Acest medic nu are programări înregistrate.")
        except Exception as e:
            st.error(f"Eroare la încărcarea datelor: {e}")
        finally:
            conn.close()

# ==============================================================================
# PAGINA 5: DOSAR PACIENT
# ==============================================================================
def page_dosar_pacient():
    st.header("📂 Dosar Electronic Pacient")
    st.markdown("Vizualizare completă a istoricului unui pacient.")

    pacienti_dict = get_pacienti_dict()
    if not pacienti_dict:
        st.error("Nu există pacienți înregistrați.")
        return

    # Selectare pacient
    nume_pacient_selectat = st.selectbox("Selectează Pacientul:", list(pacienti_dict.keys()))
    
    pacient_id = pacienti_dict[nume_pacient_selectat]
    conn = get_connection()

    if conn:
        try:
            # 1. Date Personale
            sql_detalii = """
                SELECT Nume, Prenume, CNP, DataNasterii, Sex, Telefon, Adresa, StatusAsigurare
                FROM Pacienti WHERE PacientID = ?
            """
            df_detalii = pd.read_sql(sql_detalii, conn, params=[pacient_id])

            if not df_detalii.empty:
                p = df_detalii.iloc[0]
                st.markdown("---")
                
                # Afisare Verticala (unul sub altul) pentru claritate
                st.markdown(f"### Date Personale")
                st.markdown(f"**Nume Complet:** {p['Nume']} {p['Prenume']}")
                st.markdown(f"**CNP:** {p['CNP']}")
                st.markdown(f"**Statut Asigurare:** {p['StatusAsigurare']}")
                st.markdown(f"**📞 Telefon:** {p['Telefon']}")
                st.markdown(f"**🏠 Adresa:** {p['Adresa']}")
                st.markdown(f"**🎂 Data Nașterii:** {p['DataNasterii']}")
            
            st.markdown("---")

            # 2. Tab-uri pentru Istoric
            tab_prog, tab_retete = st.tabs(["📅 Istoric Programări", "💊 Rețete Prescrise"])

            with tab_prog:
                sql_prog = """
                    SELECT PR.Data, PR.OraStart, 
                           (M.Nume + ' ' + M.Prenume) AS Medic,
                           PR.MotivProgramare, PR.Status
                    FROM Programari PR
                    JOIN Medici M ON PR.MedicID = M.MedicID
                    WHERE PR.PacientID = ?
                    ORDER BY PR.Data DESC
                """
                df_prog = pd.read_sql(sql_prog, conn, params=[pacient_id])
                if not df_prog.empty:
                    st.dataframe(df_prog, width="stretch")
                else:
                    st.info("Nu există programări în istoric.")

            with tab_retete:
                sql_retete = """
                    SELECT R.DataEmiterii, R.Medicamente, R.Valabilitate,
                           (M.Nume + ' ' + M.Prenume) AS Medic_Prescrip
                    FROM Retete R
                    JOIN Consultatii C ON R.ConsultatieID = C.ConsultatieID
                    JOIN Medici M ON C.MedicID = M.MedicID
                    WHERE C.PacientID = ?
                    ORDER BY R.DataEmiterii DESC
                """
                df_retete = pd.read_sql(sql_retete, conn, params=[pacient_id])
                if not df_retete.empty:
                    st.dataframe(df_retete, width="stretch")
                else:
                    st.info("Nu există rețete prescrise.")

        except Exception as e:
            st.error(f"Eroare la preluarea datelor: {e}")
        finally:
            conn.close()

# ==============================================================================
# MAIN APP - NAVIGARE
# ==============================================================================

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center;'>🔐 Login</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        if st.button("Login Admin (Demo)", type="primary"):
            st.session_state['logged_in'] = True
            st.rerun()
else:
    # --- SIDEBAR NAVIGATION ---
    st.sidebar.title("Meniu Principal")
    
    # Optiuni meniu
    meniu = [
        "📊 Dashboard",       
        "🗓️ Orar Medici",     
        "📂 Dosar Pacient",   
        "👤 Pacienți", 
        "📅 Programări"
    ]
    
    page = st.sidebar.radio("Navigare", meniu)
    
    st.sidebar.markdown("---")
    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.rerun()

    # --- ROUTING ---
    if page == "📊 Dashboard":
        page_dashboard(get_connection())
    elif page == "🗓️ Orar Medici":
        page_orar_medici()
    elif page == "📂 Dosar Pacient":
        page_dosar_pacient()
    elif page == "👤 Pacienți":
        page_pacienti()
    elif page == "📅 Programări":
        page_programari()