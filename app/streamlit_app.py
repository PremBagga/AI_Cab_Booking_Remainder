import streamlit as st
from datetime import datetime, time, date
import pandas as pd
import os
import gspread
import json
from datetime import datetime, time, timedelta
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials

# ---- DARK THEME SETUP ----
st.set_page_config(page_title="AI Cab Booking Portal", layout="centered")

# ---- CUSTOM CSS FOR FIXING UI ISSUES ----
st.markdown("""
    <style>
    .stApp {
        background-color: #000000;
        color: #FFFFFF !important;
    }

    h1, h2, h3, h4, h5, h6, .stMarkdown, .stTextInput label,
    .stDateInput label, .stTimeInput label, .stTextArea label,
    .stSelectbox label {
        color: #FFFFFF !important;
    }

    input[type="text"], input[type="number"], input[type="time"],
    input[type="date"], textarea {
        background-color: #1c1c1c !important;
        color: #FFFFFF !important;
        border: 1px solid #555 !important;
        border-radius: 5px !important;
        caret-color: white !important;  /* Fixes black vertical caret */
    }

    .stTextInput > div > div > input,
    .stTextArea > div > textarea,
    .stDateInput > div > input,
    .stTimeInput > div > input,
    .stSelectbox > div > div > div > div,
    .stForm input,
    .stForm textarea {
        background-color: #1c1c1c !important;
        color: #FFFFFF !important;
        border: 1px solid #555 !important;
        border-radius: 5px !important;
        caret-color: white !important;
    }

    .stButton > button {
        background-color: #4CAF50 !important;
        color: white !important;
        font-weight: bold !important;
        font-size: 16px !important;
        border: none !important;
        padding: 0.5rem 1rem !important;
        border-radius: 5px !important;
        transition: background-color 0.3s ease;
        visibility: visible !important;  /* Fix: keep button always visible */
    }

    .stButton > button:hover {
        background-color: #45a049 !important;
        color: #ffffff !important;
    }

    .stForm {
        background-color: #111111 !important;
        padding: 2rem !important;
        border-radius: 10px !important;
    }
    </style>
""", unsafe_allow_html=True)

# ---- HEADER ----
st.title("🚖 AI Cab Booking Portal")
st.markdown("Book your cab for night shifts (10 PM to 6 AM) and auto-generate your booking message.")

# ---- GOOGLE SHEETS SETUP ----
# SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
# CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "..", "google_credentials.json")
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)


SHEET_NAME = "EmployeCabBookings"

# def log_to_google_sheets(row_data):
#     creds = ServiceAccountCredentials.from_json_keyfile_name(creds_dict, SCOPE)#CREDENTIALS_PATH
#     client = gspread.authorize(creds)
#     sheet = client.open(SHEET_NAME).sheet1
#     sheet.append_row(row_data)

# def log_to_google_sheets(row_data):
#     creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
#     creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
#     client = gspread.authorize(creds)
#     sheet = client.open(SHEET_NAME).sheet1
#     sheet.append_row(row_data)

def log_to_google_sheets(row_data):
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1
    sheet.append_row(row_data)


# Initialize session state
if "shift_start" not in st.session_state:
    st.session_state.shift_start = None
if "shift_end" not in st.session_state:
    st.session_state.shift_end = None

with st.form("booking_form"):
    st.subheader("📝 Enter Your Shift Details")

    name = st.text_input("Full Name")
    emp_id = st.text_input("Employee ID")
    mobile = st.text_input("Mobile Number")
    pickup_address = st.text_area("Home Address")
    shift_date = st.date_input("Shift Date")

    # Custom logic to simulate no default time
    shift_start_raw = st.text_input("Shift Start Time (HH:MM)", value=st.session_state.shift_start.strftime("%H:%M") if st.session_state.shift_start else "")

    # Parse valid time input
    try:
        if shift_start_raw:
            shift_start = datetime.strptime(shift_start_raw, "%H:%M").time()
            st.session_state.shift_start = shift_start
            # Suggest +9 hrs only once
            if not st.session_state.shift_end:
                st.session_state.shift_end = (datetime.combine(datetime.today(), shift_start) + timedelta(hours=9)).time()
        else:
            shift_start = None
    except ValueError:
        st.warning("Enter valid time in HH:MM format.")
        shift_start = None

    shift_end_raw = st.text_input("Shift End Time (Suggested: +9 hrs)", value=st.session_state.shift_end.strftime("%H:%M") if st.session_state.shift_end else "")
    try:
        shift_end = datetime.strptime(shift_end_raw, "%H:%M").time() if shift_end_raw else None
        st.session_state.shift_end = shift_end
    except ValueError:
        st.warning("Enter valid end time in HH:MM format.")
        shift_end = None

    submitted = st.form_submit_button("🚖 Generate Message & Book")


# ---- LOGIC + MESSAGE ----
def is_cab_required(start_time, end_time):
    return (
        start_time >= time(22, 0)
        or end_time <= time(6, 0)
        or (start_time <= time(6, 0) and end_time > time(6, 0))
        or (start_time < time(22, 0) and end_time >= time(22, 0))
    )


def get_direction(start_time, end_time):
    directions = []
    if start_time >= time(22, 0) or start_time <= time(6, 0):
        directions.append("Home to Office")
    if end_time >= time(22, 0) or end_time <= time(6, 0):
        directions.append("Office to Home")
    return directions

def format_message(direction, name, pickup, shift_time, date, mobile):
    drop = "Office Address" if direction == "Home to Office" else pickup
    pickup = pickup if direction == "Home to Office" else "Office Address"
    time_label = "Shift Start" if direction == "Home to Office" else "Shift End"

    return f"""
🚖 Cab Booking – {direction}

Name: {name}  
Pick Up: {pickup}  
Drop Off: {drop}  
{time_label}: {shift_time.strftime('%I:%M %p')}  
Date: {date.strftime('%d/%m/%Y')}  
Mobile: {mobile}
"""

if submitted:
    if not name or not emp_id or not mobile or not pickup_address:
        st.warning("Please fill all required fields.")
    elif len(emp_id) != 4 or not emp_id.isalnum():
        st.warning("Employee ID must be 4 characters long.")
    elif not mobile.isdigit() or len(mobile) != 10:
        st.warning("Mobile number must be exactly 10 digits.")
    else:
        if is_cab_required(shift_start, shift_end):
            directions = get_direction(shift_start, shift_end)
            for direction in directions:
                shift_time = shift_start if direction == "Home to Office" else shift_end
                msg = format_message(direction, name, pickup_address, shift_time, shift_date, mobile)
                st.success(f"✅ Cab Required: {direction}")
                st.code(msg)

                log_data = {
                    "Date": shift_date.strftime('%d/%m/%Y'),
                    "Name": name,
                    "Emp_ID": emp_id,
                    "Shift_Start": shift_start.strftime('%H:%M'),
                    "Shift_End": shift_end.strftime('%H:%M'),
                    "Direction": direction,
                    "Mobile": mobile,
                    "Pickup_Address": pickup_address,
                    "Booked_At": datetime.now().strftime('%d/%m/%Y %H:%M')
                }

                df = pd.DataFrame([log_data])
                os.makedirs("data", exist_ok=True)
                log_path = "data/cab_bookings.csv"
                if os.path.exists(log_path):
                    df.to_csv(log_path, mode='a', header=False, index=False)
                else:
                    df.to_csv(log_path, index=False)

                try:
                    log_to_google_sheets(list(log_data.values()))
                    st.success("Logged to Google Sheet ✅")
                except Exception as e:
                    st.warning(f"Google Sheets Error: {e}")
        else:
            st.info("❌ Based on your shift timings, cab is not required.")


# streamlit run app/streamlit_app.py

# import streamlit as st
# from datetime import datetime, time, date
# import pandas as pd
# import os
# import gspread
# import json
# from oauth2client.service_account import ServiceAccountCredentials

# # ---- DARK THEME SETUP ----
# st.set_page_config(page_title="AI Cab Booking Portal", layout="centered")

# # ---- CUSTOM CSS FOR BLACK BACKGROUND ----
# st.markdown("""
#     <style>
#     .stApp {
#         background-color: #000000;
#         color: #FFFFFF !important;
#     }
#     h1, h2, h3, h4, h5, h6, .stMarkdown, .stTextInput label,
#     .stDateInput label, .stTimeInput label, .stTextArea label,
#     .stSelectbox label {
#         color: #FFFFFF !important;
#     }
#     .stTextInput > div > div > input,
#     .stTextArea > div > textarea,
#     .stDateInput > div > input,
#     .stTimeInput > div > input,
#     .stSelectbox > div > div > div > div,
#     .stForm input,
#     .stForm textarea {
#         background-color: #1c1c1c !important;
#         color: #FFFFFF !important;
#         border: 1px solid #555 !important;
#         border-radius: 5px !important;
#     }
#     .stButton > button {
#         background-color: #4CAF50 !important;
#         color: white !important;
#         border: none !important;
#         padding: 0.5rem 1rem !important;
#         border-radius: 5px !important;
#     }
#     .stForm {
#         background-color: #111111 !important;
#         padding: 2rem !important;
#         border-radius: 10px !important;
#     }
#     </style>
# """, unsafe_allow_html=True)

# # ---- HEADER ----
# st.title("🚖 AI Cab Booking Portal")
# st.markdown("Book your cab for night shifts (10 PM to 6 AM) and auto-generate your booking message.")

# SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
# creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
# creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)

# SHEET_NAME = "EmployeCabBookings"

# def log_to_google_sheets(row_data):
#     creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
#     client = gspread.authorize(creds)
#     sheet = client.open(SHEET_NAME).sheet1
#     sheet.append_row(row_data)

# # ---- FORM ----
# # with st.form("booking_form"):
# #     st.subheader("📝 Enter Your Shift Details")

# #     name = st.text_input("Full Name")
# #     emp_id = st.text_input("Employee ID")
# #     mobile = st.text_input("Mobile Number")
# #     pickup_address = st.text_area("Home Address")
# #     shift_date = st.date_input("Shift Date", min_value=date.today())
# #     shift_start = st.time_input("Shift Start Time", value=time(22, 0))
# #     shift_end = st.time_input("Shift End Time", value=time(6, 0))
# #     Session state init

# # Initialize session state
# if "shift_start" not in st.session_state:
#     st.session_state.shift_start = None
# if "shift_end" not in st.session_state:
#     st.session_state.shift_end = None

# with st.form("booking_form"):
#     st.subheader("📝 Enter Your Shift Details")

#     name = st.text_input("Full Name")
#     emp_id = st.text_input("Employee ID")
#     mobile = st.text_input("Mobile Number")
#     pickup_address = st.text_area("Home Address")
#     shift_date = st.date_input("Shift Date")

#     # Custom logic to simulate no default time
#     shift_start_raw = st.text_input("Shift Start Time (HH:MM)", value=st.session_state.shift_start.strftime("%H:%M") if st.session_state.shift_start else "")

#     # Parse valid time input
#     try:
#         if shift_start_raw:
#             shift_start = datetime.strptime(shift_start_raw, "%H:%M").time()
#             st.session_state.shift_start = shift_start
#             # Suggest +9 hrs only once
#             if not st.session_state.shift_end:
#                 st.session_state.shift_end = (datetime.combine(datetime.today(), shift_start) + timedelta(hours=9)).time()
#         else:
#             shift_start = None
#     except ValueError:
#         st.warning("Enter valid time in HH:MM format.")
#         shift_start = None

#     shift_end_raw = st.text_input("Shift End Time (Suggested: +9 hrs)", value=st.session_state.shift_end.strftime("%H:%M") if st.session_state.shift_end else "")
#     try:
#         shift_end = datetime.strptime(shift_end_raw, "%H:%M").time() if shift_end_raw else None
#         st.session_state.shift_end = shift_end
#     except ValueError:
#         st.warning("Enter valid end time in HH:MM format.")
#         shift_end = None

#     submitted = st.form_submit_button("🚖 Generate Message & Book")



# # ---- LOGIC + MESSAGE ----
# def is_cab_required(start_time, end_time):
#     return (
#         start_time >= time(22, 0)
#         or end_time <= time(6, 0)
#         or (start_time <= time(6, 0) and end_time > time(6, 0))
#         or (start_time < time(22, 0) and end_time >= time(22, 0))
#     )

# def get_direction(start_time, end_time):
#     directions = []
#     if start_time >= time(22, 0) or start_time <= time(6, 0):
#         directions.append("Home to Office")
#     if end_time >= time(22, 0) or end_time <= time(6, 0):
#         directions.append("Office to Home")
#     return directions

# def format_message(direction, name, pickup, shift_time, date, mobile):
#     drop = "Office Address" if direction == "Home to Office" else pickup
#     pickup = pickup if direction == "Home to Office" else "Office Address"
#     time_label = "Shift Start" if direction == "Home to Office" else "Shift End"

#     return f"""
# 🚖 Cab Booking – {direction}

# Name: {name}  
# Pick Up: {pickup}  
# Drop Off: {drop}  
# {time_label}: {shift_time.strftime('%I:%M %p')}  
# Date: {date.strftime('%d/%m/%Y')}  
# Mobile: {mobile}
# """

# if submitted:
#     if not name or not emp_id or not mobile or not pickup_address:
#         st.warning("Please fill all required fields.")
#     elif len(emp_id) != 4 or not emp_id.isalnum():
#         st.warning("Employee ID must be 4 characters long.")
#     elif not mobile.isdigit() or len(mobile) != 10:
#         st.warning("Mobile number must be exactly 10 digits.")
#     else:
#         if is_cab_required(shift_start, shift_end):
#             directions = get_direction(shift_start, shift_end)
#             for direction in directions:
#                 shift_time = shift_start if direction == "Home to Office" else shift_end
#                 msg = format_message(direction, name, pickup_address, shift_time, shift_date, mobile)
#                 st.success(f"✅ Cab Required: {direction}")
#                 st.code(msg)

#                 # Save to CSV log
#                 log_data = {
#                     "Date": shift_date.strftime('%d/%m/%Y'),
#                     "Name": name,
#                     "Emp_ID": emp_id,
#                     "Shift_Start": shift_start.strftime('%H:%M'),
#                     "Shift_End": shift_end.strftime('%H:%M'),
#                     "Direction": direction,
#                     "Mobile": mobile,
#                     "Pickup_Address": pickup_address,
#                     "Booked_At": datetime.now().strftime('%d/%m/%Y %H:%M')
#                 }

#                 df = pd.DataFrame([log_data])
#                 if not os.path.exists("data"):
#                     os.makedirs("data")

#                 log_path = "data/cab_bookings.csv"
#                 if os.path.exists(log_path):
#                     df.to_csv(log_path, mode='a', header=False, index=False)
#                 else:
#                     df.to_csv(log_path, index=False)

#                 # Save to Google Sheets
#                 try:
#                     log_to_google_sheets(list(log_data.values()))
#                     st.success("Logged to Google Sheet ✅")
#                 except Exception as e:
#                     st.warning(f"Google Sheets Error: {e}")
#         else:
#             st.info("❌ Based on your shift timings, cab is not required.")


# streamlit run app/streamlit_app.py
