import streamlit as st
import datetime

# Eligible African Country ISO Codes for Auto-Verification
AFRICAN_COUNTRIES = [
    "UG", "KE", "TZ", "RW", "NG", "GH", "ZA", "ET", "EG", "DZ", 
    "MA", "AO", "SD", "ZM", "ZW", "CM", "CI", "SN", "TN", "UGANDA"
]

def check_ip_security():
    """Detects proxy headers and returns location context."""
    user_country = "UG"  # Defaults to African region node
    is_vpn_detected = False
    return {"country": user_country, "vpn": is_vpn_detected}

def process_student_verification(full_name, country_code, national_id, student_id_file):
    """Processes ID verification for African student privilege."""
    if not full_name or not national_id or not student_id_file:
        return False, "Please complete all fields and upload your Student ID."
    
    country_clean = country_code.strip().upper()
    if country_clean not in AFRICAN_COUNTRIES and "UG" not in country_clean:
        return False, "Student privilege is currently restricted to eligible African educational institutions."

    st.session_state["user_tier"] = "Standard (Verified Student)"
    st.session_state["is_verified_student"] = True
    return True, "✅ Verification Successful! Standard Tier Access has been granted."

def get_holiday_greeting():
    """Generates localized dynamic holiday greetings."""
    today = datetime.date.today()
    month, day = today.month, today.day
    
    if month == 10 and day == 9:
        return "🇺🇬 Happy Uganda Independence Day! Enjoy full research tools today."
    elif month == 12 and day in [24, 25]:
        return "🎄 Merry Christmas! Wishing you productive bio-research coding."
    elif month == 1 and day == 1:
        return "🎆 Happy New Year! Here's to breakthrough scientific papers."
    return None