
"""African Student Verification  Automated ID Verification Pipeline."""
import io
import hashlib
import logging
import re
import os
import time
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List

import streamlit as st
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# ELIGIBLE AFRICAN DOMAINS & COUNTRIES
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

ELIGIBLE_ACADEMIC_DOMAINS = {
    # Top-level African university domains
    ".ac.za", ".ac.zw", ".ac.ug", ".ac.ke", ".ac.tz", ".ac.bw", ".ac.zm",
    ".ac.rw", ".ac.na", ".ac.gh", ".ac.et", ".ac.mu", ".ac.mw", ".ac.ls",
    ".edu.ng", ".edu.gh", ".edu.ke", ".edu.za", ".edu.tz", ".edu.ug",
    ".edu.et", ".edu.rw", ".edu.zm", ".edu.na", ".edu.bw", ".edu.mw",
    ".edu.ls", ".edu.mu", ".å­¦æ ¡.cn",  # Chinese students (developing)
    ".edu.in",  # India (developing)
    # Country code TLDs for developing nations
    ".ug", ".ke", ".tz", ".bw", ".zm", ".rw", ".na", ".gh", ".et", 
    ".mw", ".ls", ".mu", ".zw", ".ng", ".cd", ".ao", ".mz", ".zm",
}

ELIGIBLE_COUNTRIES = {
    "AFG", "BGD", "BEN", "BFA", "BDI", "CAF", "TCD", "COM", "COD",
    "DJI", "ERI", "ETH", "GMB", "GIN", "GNB", "KEN", "LBR", "LSO",
    "MDG", "MLI", "MOZ", "MMR", "NER", "RWA", "SEN", "SLE", "SOM",
    "SSD", "SDN", "TZA", "TGO", "UGA", "ZMB", "ZWE", "AGO", "BDI",
    "BWA", "CMR", "EGY", "GAB", "GHA", "IND", "MAR", "NGA", "PAK",
    "ZAF", "THA", "VNM", "IDN", "PHL", "CHN", "PER", "BOL", "PRY",
}

# GeoIP fallback countries when IP detection unavailable
DEVELOPING_REGION_CODES = ["AF", "AM", "AO", "BD", "BF", "BI", "BJ", "BT", "BW", 
    "CD", "CF", "CG", "CI", "CM", "CN", "CO", "CV", "DJ", "DZ", "EG",
    "ER", "ET", "GA", "GE", "GH", "GN", "GW", "HN", "ID", "IN", "IQ",
    "KE", "KH", "KM", "LA", "LK", "LR", "LS", "MG", "ML", "MM", "MR",
    "MU", "MW", "MZ", "NA", "NE", "NG", "NI", "NP", "OM", "PK", "PS",
    "PW", "PY", "RW", "SA", "SD", "SN", "SO", "SR", "SS", "SD", "SZ",
    "TD", "TG", "TL", "TN", "TZ", "UG", "VN", "VU", "WS", "YE", "ZA",
    "ZM", "ZW"]

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# ID VERIFICATION CONFIG
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

# Supported ID types
ID_TYPES = [
    "National ID",
    "Passport",
    "Student ID Card",
    "University Admission Letter",
    "National Student ID",
]

# Max file sizes (5MB)
MAX_FILE_SIZE = 5 * 1024 * 1024

# Supported formats
SUPPORTED_FORMATS = ["jpg", "jpeg", "png", "pdf", "webp"]

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# GEOLOCATION & IP DETECTION
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def get_client_ip() -> str:
    """Extract client IP from request headers."""
    # Check X-Forwarded-For header (for proxied requests)
    forwarded = st.context.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    # Check X-Real-IP header
    real_ip = st.context.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback (won't work in Streamlit Cloud but harmless)
    return "127.0.0.1"

def get_country_from_ip(ip: str) -> Optional[str]:
    """Get country code from IP using free GeoIP service."""
    if not ip or ip.startswith("127.") or ip.startswith("localhost"):
        return None
    
    try:
        # Use ip-api.com (free tier: 45 requests/minute)
        response = requests.get(
            f"http://ip-api.com/json/{ip}",
            params={"fields": "countryCode,status"},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                return data.get("countryCode")
    except Exception as e:
        logger.debug(f"GeoIP lookup failed: {e}")
    
    return None

def check_domain_eligibility(email: str) -> Tuple[bool, Optional[str]]:
    """Check if email domain is from eligible African institution."""
    if not email or "@" not in email:
        return False, None
    
    domain = email.split("@")[-1].lower()
    
    for eligible in ELIGIBLE_ACADEMIC_DOMAINS:
        if domain.endswith(eligible) or domain == eligible.lstrip("."):
            return True, domain
    
    return False, domain

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# OCR PROCESSING (Tesseract / EasyOCR)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def extract_text_from_image(file_bytes: bytes, filename: str) -> Tuple[str, float]:
    """
    Extract text from image using OCR.
    Returns (extracted_text, confidence_score).
    Falls back gracefully if no OCR library available.
    """
    # First try Tesseract
    try:
        import pytesseract
        from PIL import Image
        
        image = Image.open(io.BytesIO(file_bytes))
        text = pytesseract.image_to_string(image)
        confidence = pytesseract.get_image_dimensions(image)
        
        if text and len(text.strip()) > 10:
            return text, 0.85
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"Tesseract OCR failed: {e}")
    
    # Fallback to EasyOCR
    try:
        import easyocr
        reader = easyocr.Reader(['en'], gpu=False)
        results = reader.readtext(file_bytes)
        
        text_parts = []
        for detection in results:
            text_parts.append(detection[1])
        
        if text_parts:
            return " ".join(text_parts), 0.80
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"EasyOCR failed: {e}")
    
    # Last resort: return placeholder (user must manually verify)
    return "[OCR Unavailable - Please manually verify your documents]", 0.0

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF for verification."""
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text = "\n".join(page.extract_text() for page in reader.pages)
        return text if text else ""
    except Exception as e:
        logger.debug(f"PDF extraction failed: {e}")
    
    # Try pdfplumber
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            text = "\n".join(page.extract_text() for page in pdf.pages)
            return text if text else ""
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"pdfplumber OCR failed: {e}")
    
    return ""

def process_document(file, doc_type: str) -> Tuple[str, float]:
    """Process uploaded document and extract text."""
    file_bytes = file.read()
    
    if len(file_bytes) > MAX_FILE_SIZE:
        return "", 0.0
    
    ext = file.name.split(".")[-1].lower()
    
    if ext == "pdf":
        return extract_text_from_pdf(file_bytes), 0.90
    elif ext in ("jpg", "jpeg", "png", "webp"):
        return extract_text_from_image(file_bytes, file.name), 0.85
    else:
        return "", 0.0

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# DOCUMENT VERIFICATION LOGIC
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def extract_name_from_text(text: str) -> List[str]:
    """Extract potential names from OCR text using pattern matching."""
    # Common name patterns (2-4 capitalized words)
    name_pattern = r'\b[A-Z][a-z] (?:\w )?[A-Z][a-z]\b'
    names = re.findall(name_pattern, text)
    
    # Also look for "Name:" patterns
    name_label_pattern = r'(?:Name|Student|Name\s*[:\-])\s*([A-Za-z\s])'
    labeled_names = re.findall(name_label_pattern, text, re.IGNORECASE)
    
    return names  [n.strip() for n in labeled_names]

def extract_university_from_text(text: str) -> List[str]:
    """Extract potential university names from text."""
    # Common patterns for universities
    uni_patterns = [
        r'(?:University|College|Institute|Academy)\sof\s[A-Za-z\s]',
        r'[A-Z][a-z](?:University|College|Institute)',
        r'(?:University|Univ\.?)\s[A-Z][a-z]',
    ]
    
    universities = []
    for pattern in uni_patterns:
        matches = re.findall(pattern, text)
        universities.extend(matches)
    
    return list(set(universities))

def extract_date_from_text(text: str) -> List[str]:
    """Extract potential dates (for expiry verification)."""
    date_patterns = [
        r'\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}',
        r'\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}',
        r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s\d{1,2},?\s\d{4}',
    ]
    
    dates = []
    for pattern in date_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        dates.extend(matches)
    
    return dates

def verify_student_id(
    id_text: str,
    student_id_text: str,
    email: str,
    ip_country: Optional[str],
) -> Dict[str, Any]:
    """
    Verify student identity from extracted document text.
    Returns verification result with score and details.
    """
    results = {
        "verified": False,
        "score": 0.0,
        "checks": {},
        "details": {},
    }
    
    score = 0
    total_checks = 0
    
    # Check 1: Domain eligibility (strong signal)
    if email:
        domain_eligible, domain = check_domain_eligibility(email)
        results["checks"]["domain_eligible"] = domain_eligible
        results["details"]["domain"] = domain
        if domain_eligible:
            score = 40
        total_checks = 1
    
    # Check 2: GeoIP country eligibility
    if ip_country and ip_country in DEVELOPING_REGION_CODES:
        results["checks"]["geoip_eligible"] = True
        results["details"]["country"] = ip_country
        score = 30
    elif ip_country:
        results["checks"]["geoip_eligible"] = False
        results["details"]["country"] = ip_country
    else:
        results["checks"]["geoip_eligible"] = None
    total_checks = 1
    
    # Check 3: Name extraction from ID document
    id_names = extract_name_from_text(id_text)
    results["details"]["extracted_names"] = id_names[:3]  # Limit for display
    
    if id_names and len(id_text) > 50:
        score = 15
        results["checks"]["name_found"] = True
    else:
        results["checks"]["name_found"] = bool(id_names)
    total_checks = 1
    
    # Check 4: University name from student ID
    uni_names = extract_university_from_text(student_id_text)
    results["details"]["extracted_universities"] = uni_names[:3]
    
    # Check against email domain
    if email and uni_names:
        email_domain = email.split("@")[-1].lower()
        for uni in uni_names:
            if any(part.lower() in email_domain for part in uni.split()):
                score = 10
                results["checks"]["university_match"] = True
                break
    
    if uni_names:
        score = 10
    total_checks = 1
    
    # Check 5: Expiry date (if present)
    id_dates = extract_date_from_text(id_text)
    student_dates = extract_date_from_text(student_id_text)
    results["details"]["extracted_dates"] = id_dates + student_dates
    
    if id_dates or student_dates:
        # Parse dates and check if expired
        all_dates = id_dates + student_dates
        try:
            for date_str in all_dates:
                # Simple year extraction
                years = re.findall(r'20\d{2}', date_str)
                if years:
                    year = int(years[0])
                    if year >= datetime.now().year:
                        score = 5
                        results["checks"]["document_valid"] = True
                        break
        except Exception:
            pass
    total_checks = 1
    
    # Calculate final score
    results["score"] = min(100, round(score, 1))
    
    # Verification threshold: 50 for auto-approve, 30-49 for manual review
    if results["score"] >= 50:
        results["verified"] = True
        results["status"] = "auto_approved"
    elif results["score"] >= 30:
        results["status"] = "manual_review"
    else:
        results["status"] = "rejected"
    
    return results

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# STREAMLIT UI
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def render_verification_ui():
    """Render the African Student Verification UI."""
    st.subheader("ðŸŽ“ African Student Verification")
    st.markdown("""
    Verify your student status to unlock **Free Standard Tier** access.
    
    **Eligibility:** Students from African universities and developing nations.
    """)
    
    # Quick check: email domain
    col1, col2 = st.columns(2)
    with col1:
        email = st.text_input(
            "ðŸ“§ Student Email",
            help="Use your university email (.ac.za, .edu.ng, etc.)",
            placeholder="student@university.edu.ug"
        )
    with col2:
        st.markdown("#####")
        if email:
            eligible, domain = check_domain_eligibility(email)
            if eligible:
                st.success(f"âœ… Eligible domain: {domain}")
            else:
                st.warning(f"âš ï¸ Domain not recognized: {domain}")
    
    st.divider()
    
    # Document upload section
    st.markdown("#### ðŸ“„ Upload Verification Documents")
    
    col1, col2 = st.columns(2)
    with col1:
        id_type = st.selectbox("ID Document Type", ID_TYPES)
        id_file = st.file_uploader(
            "National ID or Passport",
            type=SUPPORTED_FORMATS,
            help="Upload a clear image or PDF of your national ID/passport"
        )
    with col2:
        student_id = st.file_uploader(
            "Student ID or Admission Letter",
            type=SUPPORTED_FORMATS,
            help="Upload your student ID card or university admission letter"
        )
    
    # Process on button click
    if st.button("ðŸ” Verify Documents", type="primary", disabled=not (id_file and student_id and email)):
        if not id_file or not student_id:
            st.error("Please upload both documents")
            return
        
        with st.spinner("Processing documents..."):
            # Get client IP and country
            client_ip = get_client_ip()
            country = get_country_from_ip(client_ip)
            
            # Extract text from documents
            id_text, id_confidence = process_document(id_file, id_type)
            student_text, student_confidence = process_document(student_id, "Student ID")
            
            if not id_text or id_confidence == 0:
                st.error("Could not process ID document. Please upload clearer images.")
                return
            
            # Run verification
            result = verify_student_id(
                id_text=id_text,
                student_id_text=student_text,
                email=email,
                ip_country=country,
            )
            
            # Display results
            st.divider()
            
            if result["verified"]:
                st.success("ðŸŽ‰ **Verification Successful!**")
                st.balloons()
                
                # Auto-upgrade to Standard tier
                update_user_tier(Tier.STANDARD)
                st.session_state["african_verified"] = True
                st.session_state["subscription_status"] = "verified"
                
                # Update database
                try:
                    from modules.subscription import SUPABASE_URL, _get_service_headers
                    import requests as req
                    if SUPABASE_URL and st.session_state.get("user_id"):
                        req.patch(
                            f"{SUPABASE_URL}/rest/v1/users?id=eq.{st.session_state['user_id']}",
                            headers=_get_service_headers(),
                            json={
                                "tier": Tier.STANDARD.value,
                                "african_verified": True,
                                "subscription_status": "verified",
                                "verification_date": datetime.utcnow().isoformat(),
                            },
                        )
                except Exception as e:
                    logger.error(f"DB update failed: {e}")
                
                st.markdown(f"""
                ### âœ… You now have STANDARD Tier Access!
                
                - **Verification Score:** {result['score']}%
                - **Status:** Auto-approved
                
                Your account has been upgraded. Enjoy full literature search, 
                file exports, and standard automation tools!
                """)
            else:
                if result["status"] == "manual_review":
                    st.warning("â³ **Manual Review Required**")
                    st.markdown(f"""
                    Your documents require manual verification.
                    
                    **Score:** {result['score']}%  
                    **Status:** Pending Review
                    
                    Our team will review your submission within 24-48 hours.
                    You'll receive an email once verified.
                    """)
                else:
                    st.error("âŒ **Verification Failed**")
                    st.markdown(f"""
                    We couldn't verify your student status.
                    
                    **Score:** {result['score']}%  
                    **Reason:** Insufficient documentation
                    
                    Please ensure:
                    - Your documents are clear and readable
                    - Your university email matches your institution
                    - Both documents show your name clearly
                    """)
            
            # Debug: Show extracted text (collapsible)
            with st.expander("ðŸ”§ Verification Details (Debug)"):
                st.write("**ID Document Text:**")
                st.text(id_text[:500] + "..." if len(id_text) > 500 else id_text)
                st.write(f"Confidence: {id_confidence}")
                
                st.write("**Student ID Text:**")
                st.text(student_text[:500] + "..." if len(student_text) > 500 else student_text)
                st.write(f"Confidence: {student_confidence}")
                
                st.write("**Checks:**", result["checks"])
                st.write("**Details:**", result["details"])
    
    st.divider()
    
    # Alternative: Manual review request
    with st.expander("ðŸ“§ Request Manual Review"):
        st.markdown("""
        If automatic verification fails, you can request manual review.
        Our team will verify your documents within 2-3 business days.
        """)
        manual_email = st.text_input("Contact Email", email or "")
        manual_message = st.text_area("Additional Information", 
            placeholder="University name, Student ID number, etc.")
        
        if st.button("Submit Manual Review Request"):
            # In production: send email to admin
            st.success("Review request submitted! We'll contact you soon.")

def render_tier_selector():
    """Render tier selection UI with African verification."""
    from modules.subscription import get_current_tier, Tier, check_feature_access
    
    current = get_current_tier()
    
    st.markdown("### ðŸ’³ Subscription Tier")
    
    # Current tier display
    tier_colors = {
        Tier.FREE: "#6b7280",
        Tier.STANDARD: "#3b82f6", 
        Tier.PREMIUM: "#8b5cf6",
    }
    
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, {tier_colors.get(current, '#6b7280')}20, {tier_colors.get(current, '#6b7280')}10);
        border: 1px solid {tier_colors.get(current, '#6b7280')};
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 1rem;
    ">
        <strong>Current Tier:</strong> <span style="color: {tier_colors.get(current, '#6b7280')}; font-weight: bold;">{current.name.title()}</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Tier cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        **ðŸ†“ Free**
        - Basic Literature Search
        - Limited Tools
        """)
        if current != Tier.FREE:
            if st.button("Downgrade to Free", key="downgrade_free"):
                update_user_tier(Tier.FREE)
                st.rerun()
    
    with col2:
        st.markdown("""
        **ðŸ“˜ Standard**
        - Full Literature Engine
        - File Exports
        - Standard Automation
        - **15-Day Free Trial**
        """)
        if current != Tier.STANDARD and not st.session_state.get("african_verified"):
            if st.button("Start Trial", key="start_trial"):
                from modules.subscription import start_trial
                start_trial(Tier.STANDARD)
                st.rerun()
    
    with col3:
        st.markdown("""
        ** Premium**
        - Everything in Standard
        - Deep Research Synthesis
        - Email Reports
        - Notion Workspace Access
        """)
        if current == Tier.FREE:
            if st.button("Upgrade to Premium", key="upgrade_premium"):
                # Redirect to Stripe checkout
                from modules.subscription import create_stripe_checkout_session
                import streamlit as st
                url = create_stripe_checkout_session(
                    Tier.PREMIUM,
                    success_url=st.query_params.get("url", "") + "?success=true",
                    cancel_url=st.query_params.get("url", "") + "?canceled=true",
                )
                if url:
                    st.markdown(f'<script>window.location.href = "{url}"</script>', unsafe_allow_html=True)
                else:
                    st.error("Payment system not configured")
    
    # African verification section
    st.divider()
    render_verification_ui()
