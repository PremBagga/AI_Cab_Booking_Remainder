import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime, timedelta, time
import os
import pickle
import numpy as np
import random
from twilio.rest import Client

# --- Load environment variables ---
from dotenv import load_dotenv
load_dotenv()


# --- Twilio WhatsApp Setup ---
TWILIO_SID = os.getenv("TWILIO_SID")  # You can also hardcode for testing
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = "whatsapp:+14155238886"  # Twilio Sandbox number

twilio_client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)


# --- Google Sheets Setup ---
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "..", "google_credentials.json")

MASTER_SHEET = "MasterShiftList"
BOOKING_SHEET = "EmployeCabBookings"
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "model", "xgb_model.pkl")

# --- Authenticate ---
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, SCOPE)
client = gspread.authorize(creds)

# --- Load Sheets into DataFrames ---
try:
    master_sheet = client.open(MASTER_SHEET).sheet1
    master_df = pd.DataFrame(master_sheet.get_all_records())

    booking_sheet = client.open(BOOKING_SHEET).sheet1
    booking_df = pd.DataFrame(booking_sheet.get_all_records())
except Exception as e:
    print(f"❌ Error loading Google Sheets: {e}")
    exit(1)

# --- Format date columns ---
master_df['Shift_Date'] = pd.to_datetime(master_df['Shift_Date'], format="%d/%m/%Y", errors='coerce')
booking_df['Date'] = pd.to_datetime(booking_df['Date'], format="%d/%m/%Y", errors='coerce')

# --- Define time boundaries for night shift ---
today = datetime.now().date()
tomorrow = today + timedelta(days=1)

print(f"🔍 Checking night shifts for: {today.strftime('%d/%m/%Y')} night to {tomorrow.strftime('%d/%m/%Y')} morning")

# Filter shifts that are today or tomorrow
night_df = master_df[
    (master_df['Shift_Date'].dt.date == today) |
    (master_df['Shift_Date'].dt.date == tomorrow)
].copy()

# Drop rows with missing times
night_df = night_df.dropna(subset=['Shift_Start', 'Shift_End'])

# --- Define night cab requirement logic ---
def is_cab_required(row):
    try:
        emp_id = row.get('Emp_ID', 'Unknown')

        start_str = str(row['Shift_Start']).strip()
        end_str = str(row['Shift_End']).strip()

        start = datetime.strptime(start_str, "%H:%M:%S").time() if ":" in start_str and len(start_str.split(":")) == 3 else datetime.strptime(start_str, "%H:%M").time()
        end = datetime.strptime(end_str, "%H:%M:%S").time() if ":" in end_str and len(end_str.split(":")) == 3 else datetime.strptime(end_str, "%H:%M").time()

        return (
            start >= time(22, 0)
            or end <= time(6, 0)
            or (start <= time(6, 0) and end > time(6, 0))
            or (start < time(22, 0) and end >= time(22, 0))
        )
    except Exception as e:
        print(f"⚠️ Error parsing time for Emp ID {emp_id}: {e}")
        return False

# --- Apply cab requirement logic ---
night_df['Cab_Required'] = night_df.apply(is_cab_required, axis=1)
required_df = night_df[night_df['Cab_Required'] == True]

# --- Get booked Emp_IDs for today or tomorrow ---
booked_df = booking_df[
    (booking_df['Date'].dt.date == today) | (booking_df['Date'].dt.date == tomorrow)
].copy()

booked_ids = booked_df['Emp_ID'].astype(str).unique()

# --- Detect unbooked employees ---
unbooked_df = required_df[~required_df['Emp_ID'].astype(str).isin(booked_ids)].copy()

if unbooked_df.empty:
    print("✅ All required employees have booked.")
    exit()

# --- ML Feature Engineering ---
features = []
for _, row in unbooked_df.iterrows():
    emp_id = row['Emp_ID']
    shift_date = row['Shift_Date']
    day_of_week = shift_date.weekday()

    emp_history = booking_df[booking_df['Emp_ID'] == emp_id].copy()

    past_count = emp_history.shape[0]
    late_count = sum(pd.to_datetime(emp_history['Booked_At'], format="%d/%m/%Y %H:%M", dayfirst=True, errors='coerce').dt.time > time(16, 0))
    reminders = random.randint(0, 5)

    if past_count == 0:
        avg_min = 360
    else:
        emp_history.loc[:, 'Shift_Start'] = pd.to_datetime(emp_history['Shift_Start'], format="%H:%M", errors='coerce').dt.time
        emp_history.loc[:, 'Booked_At'] = pd.to_datetime(emp_history['Booked_At'], format="%d/%m/%Y %H:%M", errors='coerce')
        emp_history = emp_history.dropna(subset=['Booked_At', 'Shift_Start'])
        emp_history.loc[:, 'BookingMin'] = emp_history.apply(lambda r: (datetime.combine(datetime.today(), r['Shift_Start']) - r['Booked_At']).total_seconds() // 60, axis=1)
        avg_min = int(emp_history['BookingMin'].mean()) if not emp_history['BookingMin'].empty else 360

    features.append({
        'Emp_ID': emp_id,
        'DayOfWeek': day_of_week,
        'BookingTimeMin': 0,
        'AvgBookingTimeMin': avg_min,
        'MissedDeadline': 1,
        'PastBookingCount': past_count,
        'PastLateBooking': late_count,
        'PreviousRemainders': reminders
    })

feature_df = pd.DataFrame(features)
X = feature_df[['DayOfWeek', 'BookingTimeMin', 'AvgBookingTimeMin', 'MissedDeadline', 'PastBookingCount', 'PastLateBooking', 'PreviousRemainders']]

# --- Load model and predict risk ---
with open(MODEL_PATH, 'rb') as f:
    model = pickle.load(f)

feature_df['Risk'] = model.predict(X)

# --- Final alerts ---
risky_unbooked = unbooked_df[unbooked_df['Emp_ID'].isin(feature_df[feature_df['Risk'] == 1]['Emp_ID'])]

for _, row in risky_unbooked.iterrows():
    print(f"🚨 HIGH RISK: {row['Name']} (Emp ID: {row['Emp_ID']}) has not booked cab for {row['Shift_Date'].strftime('%d/%m/%Y')}")
    print(f"📨 HR ALERT: [High Risk] {row['Name']} has not booked. Mobile: {row['Mobile_No']} | Shift: {row['Shift_Start']} to {row['Shift_End']}")
    # print(f"📩 WhatsApp to {row['Mobile_No']} → [URGENT] Please book your cab for night shift starting at {row['Shift_Start']}. You are marked high risk for missing the booking deadline.")
    emp_mobile = f"whatsapp:+91{str(row['Mobile_No']).strip()}"  # Assuming Indian numbers
    message_body = (
        f"🚨 URGENT: Dear {row['Name']}, you have not booked a cab for your night shift starting at "
        f"{row['Shift_Start']}. Please book immediately. You are marked HIGH RISK for missing the deadline."
    )
    
    try:
        twilio_client.messages.create(
            from_=TWILIO_NUMBER,
            to=emp_mobile,
            body=message_body
        )
        print(f"✅ WhatsApp sent to {row['Name']} ({emp_mobile})")
    except Exception as e:
        print(f"❌ Failed to send WhatsApp to {row['Name']}: {e}")

# --- End of script ---


