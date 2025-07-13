# AI_Cab_Booking_Remainder
This Ai cab booking remainder can be used in company for giving remainder to employee who forgets to book cab for night shifts this system auto sends reminder through whatsapp to both employee and HR. It makes the use of ml model , Streamlit web app, GCP for google sheets .
Make .streamlit folder inside which make secrets.toml file in which place your credentials from twilo and GCP  : 
TWILIO_SID = "......."
TWILIO_AUTH_TOKEN = "...."

GOOGLE_CREDENTIALS = """
{
  "type": "service_account",
  "project_id": "Your Project Id",
  "private_key_id": "....",
  "private_key": "-----BEGIN PRIVATE KEY-----\\n ..Your Private key ..\\n-----END PRIVATE KEY-----\\n",
  "client_email": "......",
  "client_id": "",
  "auth_uri": ".......",
  "token_uri": "...",
  "auth_provider_x509_cert_url": ".....",
  "client_x509_cert_url": "...........",
  "universe_domain": "googleapis.com"
}
"""## 🖼️ Preview Screenshot

![App Preview](https://i.ibb.co/nqjJ6pbp/image.png)

---

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://cabbookingremainder.streamlit.app)

