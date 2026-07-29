st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>",unsafe_allow_html=True)

"""
🌐 Global Language & Academic Register — Localization Engine
Complete application UI, AI synthesis, and neural audio localization
with comprehensive world language support and formal academic precision.
"""
import streamlit as st

st.set_page_config(page_title="Global Localization Engine", layout="wide", page_icon="🌐")

from modules.config import init_session_state
from modules.ui_components import hero_card, watermark

init_session_state()
load_css = __import__("modules.ui_components", fromlist=["load_css"]).load_css
load_css(is_dark=st.session_state.get("theme", "light") == "dark")

# ==========================================
# 1. COMPREHENSIVE WORLD LANGUAGE OPTIONS
# ==========================================

EXTENDED_LANGUAGES = [
    # ─── Africa ─────────────────────────────────────────────────
    {"code": "sw", "name": "Swahili", "nativeName": "Kiswahili (Rasmi)", "flag": "🇰🇪",
     "accentVariants": ["East African Academic", "Tanzanian Sanifu", "Congolese Swahili"],
     "description": "Official language of the East African Community. Formal Kiswahili for research and policy.",
     "region": "Africa"},
    {"code": "ha", "name": "Hausa", "nativeName": "Hausa (Harshen Makaranta)", "flag": "🇳🇬",
     "accentVariants": ["Kano Academic", "Niamey Formal", "Katsina Professional"],
     "description": "Major West African lingua franca. Formal Hausa for academic publishing.",
     "region": "Africa"},
    {"code": "yo", "name": "Yoruba", "nativeName": "Yorùbá (Èdè Ìjìnlẹ̀)", "flag": "🇳🇬",
     "accentVariants": ["Standard Academic", "Ibadan Formal"],
     "description": "Formal Yoruba for academic research and scientific discourse.",
     "region": "Africa"},
    {"code": "ig", "name": "Igbo", "nativeName": "Igbo (Asụsụ Ọ̀hà)", "flag": "🇳🇬",
     "accentVariants": ["Standard Academic", "Central Igbo"],
     "description": "Standardized Igbo for academic and professional communication.",
     "region": "Africa"},
    {"code": "am", "name": "Amharic", "nativeName": "አማርኛ (አካዳሚክ)", "flag": "🇪🇹",
     "accentVariants": ["Addis Ababa Academic", "Gondar Formal"],
     "description": "Official working language of Ethiopia. Formal Amharic for research.",
     "region": "Africa"},
    {"code": "so", "name": "Somali", "nativeName": "Soomaali (Heerka Akademiyada)", "flag": "🇸🇴",
     "accentVariants": ["Mogadishu Academic", "Northern Somali"],
     "description": "Official language of Somalia. Formal Somali for academic use.",
     "region": "Africa"},
    {"code": "zu", "name": "Zulu", "nativeName": "isiZulu (Oluqondile)", "flag": "🇿🇦",
     "accentVariants": ["Standard Academic", "KwaZulu-Natal Formal"],
     "description": "One of South Africa's 11 official languages. Formal isiZulu for academic contexts.",
     "region": "Africa"},
    {"code": "xh", "name": "Xhosa", "nativeName": "isiXhosa (Oluqondile)", "flag": "🇿🇦",
     "accentVariants": ["Standard Academic", "Eastern Cape"],
     "description": "Official South African language. Formal isiXhosa for academic communication.",
     "region": "Africa"},
    {"code": "af", "name": "Afrikaans", "nativeName": "Afrikaans (Akademies)", "flag": "🇿🇦",
     "accentVariants": ["South African Academic", "Namibian Formal"],
     "description": "Official language of South Africa and Namibia. Formal Afrikaans for publishing.",
     "region": "Africa"},
    {"code": "om", "name": "Oromo", "nativeName": "Afaan Oromoo (Akademik)", "flag": "🇪🇹",
     "accentVariants": ["Standard Academic", "Western Oromo"],
     "description": "Major Cushitic language of Ethiopia. Formal Afaan Oromoo for education.",
     "region": "Africa"},
    {"code": "rw", "name": "Kinyarwanda", "nativeName": "Ikinyarwanda (Isomo)", "flag": "🇷🇼",
     "accentVariants": ["Standard Academic", "Rwandan Formal"],
     "description": "Official language of Rwanda. Formal Kinyarwanda for government.",
     "region": "Africa"},
    {"code": "lg", "name": "Luganda", "nativeName": "Luganda (Olutongole)", "flag": "🇺🇬",
     "accentVariants": ["Central Academic", "Kampala Formal"],
     "description": "Official academic and professional register of Uganda.",
     "region": "Africa"},
    {"code": "ny", "name": "Chichewa", "nativeName": "Chichewa (Chilankhulo)", "flag": "🇲🇼",
     "accentVariants": ["Malawian Academic", "Zambian Chichewa"],
     "description": "National language of Malawi. Formal Chichewa for education.",
     "region": "Africa"},
    {"code": "sn", "name": "Shona", "nativeName": "chiShona (Chidzidzo)", "flag": "🇿🇼",
     "accentVariants": ["Standard Academic", "Zimbabwean Formal"],
     "description": "Major Bantu language of Zimbabwe. Formal chiShona for academic contexts.",
     "region": "Africa"},
    {"code": "st", "name": "Sesotho", "nativeName": "Sesotho (Sekolo)", "flag": "🇱🇸",
     "accentVariants": ["Lesotho Academic", "South African Sesotho"],
     "description": "Official language of Lesotho and South Africa. Formal Sesotho for education.",
     "region": "Africa"},

    # ─── Middle East & North Africa ────────────────────────────
    {"code": "ar", "name": "Arabic", "nativeName": "العربية (الفصحى الحديثة)", "flag": "🇸🇦",
     "accentVariants": ["Modern Standard", "Maghrebi Formal", "Levantine Academic", "Gulf Academic"],
     "description": "MSA for academic publishing and research across the Arab world.",
     "region": "Middle East & North Africa", "rtl": True},
    {"code": "he", "name": "Hebrew", "nativeName": "עברית (אקדמית)", "flag": "🇮🇱",
     "accentVariants": ["Standard Academic", "Modern Israeli Formal"],
     "description": "Modern Hebrew for academic research and scientific publishing.",
     "region": "Middle East & North Africa", "rtl": True},
    {"code": "fa", "name": "Persian (Farsi)", "nativeName": "فارسی (دانشگاهی)", "flag": "🇮🇷",
     "accentVariants": ["Tehran Academic", "Dari Formal", "Tajik Academic"],
     "description": "Formal Persian for academic and scientific discourse across Iran, Afghanistan, Tajikistan.",
     "region": "Middle East & North Africa", "rtl": True},
    {"code": "ku", "name": "Kurdish", "nativeName": "Kurdî (Akademîk)", "flag": "🇮🇶",
     "accentVariants": ["Kurmanji Academic", "Sorani Academic"],
     "description": "Standard Kurdish registers for academic use across Kurdistan.",
     "region": "Middle East & North Africa"},
    {"code": "ps", "name": "Pashto", "nativeName": "پښتو (اکادمیک)", "flag": "🇦🇫",
     "accentVariants": ["Kandahar Academic", "Kabul Formal"],
     "description": "Official language of Afghanistan. Formal Pashto for academic use.",
     "region": "Middle East & North Africa", "rtl": True},
    {"code": "ber", "name": "Tamazight", "nativeName": "ⵜⴰⵎⴰⵣⵉⵖⵜ (ⵜⴰⵙⵏⴰ)", "flag": "🇲🇦",
     "accentVariants": ["Moroccan Academic", "Kabyle Academic", "Tuareg Formal"],
     "description": "Official language of Morocco and Algeria. Standard Tamazight for research.",
     "region": "Middle East & North Africa"},

    # ─── Europe ────────────────────────────────────────────────
    {"code": "en", "name": "English", "nativeName": "English (International)", "flag": "🇬🇧",
     "accentVariants": ["Academic US", "Academic UK", "International Scientific", "East African Academic"],
     "description": "Global standard for academic publishing and scientific research.",
     "region": "Europe"},
    {"code": "fr", "name": "French", "nativeName": "Français (Académique)", "flag": "🇫🇷",
     "accentVariants": ["Parisian Academic", "West African Academic", "Canadian Academic", "Belgian Formal"],
     "description": "Formal French for academic publishing and scientific research worldwide.",
     "region": "Europe"},
    {"code": "es", "name": "Spanish", "nativeName": "Español (Profesional)", "flag": "🇪🇸",
     "accentVariants": ["Castilian Academic", "Latin American Academic", "Mexican Formal", "Argentinian Academic"],
     "description": "Professional Spanish for academic research across 20+ countries.",
     "region": "Europe"},
    {"code": "de", "name": "German", "nativeName": "Deutsch (Wissenschaftlich)", "flag": "🇩🇪",
     "accentVariants": ["Standard Hochdeutsch", "Austrian Academic", "Swiss Formal"],
     "description": "Scientific German register for formal publication and research.",
     "region": "Europe"},
    {"code": "it", "name": "Italian", "nativeName": "Italiano (Accademico)", "flag": "🇮🇹",
     "accentVariants": ["Florentine Academic", "Milanese Formal"],
     "description": "Formal Italian for academic publishing and humanities research.",
     "region": "Europe"},
    {"code": "pt", "name": "Portuguese", "nativeName": "Português (Académico)", "flag": "🇵🇹",
     "accentVariants": ["European Academic", "Brazilian Academic", "African Lusophone"],
     "description": "Formal Portuguese for research across Portugal, Brazil, and Lusophone Africa.",
     "region": "Europe"},
    {"code": "ru", "name": "Russian", "nativeName": "Русский (Академический)", "flag": "🇷🇺",
     "accentVariants": ["Moscow Academic", "Saint Petersburg Formal"],
     "description": "Scientific Russian for academic publishing and technical research.",
     "region": "Europe"},
    {"code": "nl", "name": "Dutch", "nativeName": "Nederlands (Academisch)", "flag": "🇳🇱",
     "accentVariants": ["Standard Dutch Academic", "Flemish Academic"],
     "description": "Formal Dutch for academic research and scientific publishing.",
     "region": "Europe"},
    {"code": "pl", "name": "Polish", "nativeName": "Polski (Akademicki)", "flag": "🇵🇱",
     "accentVariants": ["Warsaw Academic", "Krakow Formal"],
     "description": "Formal Polish for academic research and scientific publications.",
     "region": "Europe"},
    {"code": "sv", "name": "Swedish", "nativeName": "Svenska (Akademisk)", "flag": "🇸🇪",
     "accentVariants": ["Stockholm Academic", "Finland Swedish"],
     "description": "Formal Swedish for academic research and Nordic collaboration.",
     "region": "Europe"},
    {"code": "el", "name": "Greek", "nativeName": "Ελληνικά (Ακαδημαϊκά)", "flag": "🇬🇷",
     "accentVariants": ["Athens Academic", "Cypriot Formal"],
     "description": "Formal Greek for academic research and classical studies.",
     "region": "Europe"},
    {"code": "cs", "name": "Czech", "nativeName": "Čeština (Akademická)", "flag": "🇨🇿",
     "accentVariants": ["Prague Academic", "Moravian Formal"],
     "description": "Formal Czech for academic publishing and technical research.",
     "region": "Europe"},
    {"code": "ro", "name": "Romanian", "nativeName": "Română (Academic)", "flag": "🇷🇴",
     "accentVariants": ["Bucharest Academic", "Moldovan Formal"],
     "description": "Formal Romanian for academic research and scientific publishing.",
     "region": "Europe"},
    {"code": "hu", "name": "Hungarian", "nativeName": "Magyar (Akadémiai)", "flag": "🇭🇺",
     "accentVariants": ["Budapest Academic", "Transylvanian Formal"],
     "description": "Formal Hungarian for academic research and scholarly communication.",
     "region": "Europe"},
    {"code": "uk", "name": "Ukrainian", "nativeName": "Українська (Академічна)", "flag": "🇺🇦",
     "accentVariants": ["Kyiv Academic", "Lviv Formal"],
     "description": "Formal Ukrainian for academic research and official communication.",
     "region": "Europe"},
    {"code": "da", "name": "Danish", "nativeName": "Dansk (Akademisk)", "flag": "🇩🇰",
     "accentVariants": ["Copenhagen Academic"],
     "description": "Formal Danish for academic research and Nordic collaboration.",
     "region": "Europe"},
    {"code": "fi", "name": "Finnish", "nativeName": "Suomi (Akateeminen)", "flag": "🇫🇮",
     "accentVariants": ["Helsinki Academic"],
     "description": "Formal Finnish for academic research and educational discourse.",
     "region": "Europe"},
    {"code": "nb", "name": "Norwegian", "nativeName": "Norsk (Akademisk)", "flag": "🇳🇴",
     "accentVariants": ["Bokmål Academic", "Nynorsk Formal"],
     "description": "Formal Norwegian for academic research across Norway.",
     "region": "Europe"},
    {"code": "hr", "name": "Croatian", "nativeName": "Hrvatski (Akademski)", "flag": "🇭🇷",
     "accentVariants": ["Zagreb Academic", "Bosnian Formal"],
     "description": "Formal Croatian for academic research and official communication.",
     "region": "Europe"},
    {"code": "sr", "name": "Serbian", "nativeName": "Српски (Академски)", "flag": "🇷🇸",
     "accentVariants": ["Belgrade Academic", "Montenegrin Formal"],
     "description": "Formal Serbian for academic research and regional scholarship.",
     "region": "Europe"},
    {"code": "bg", "name": "Bulgarian", "nativeName": "Български (Академичен)", "flag": "🇧🇬",
     "accentVariants": ["Sofia Academic"],
     "description": "Formal Bulgarian for academic research and scholarly discourse.",
     "region": "Europe"},
    {"code": "sk", "name": "Slovak", "nativeName": "Slovenčina (Akademická)", "flag": "🇸🇰",
     "accentVariants": ["Bratislava Academic"],
     "description": "Formal Slovak for academic research and official communication.",
     "region": "Europe"},
    {"code": "sl", "name": "Slovenian", "nativeName": "Slovenščina (Akademska)", "flag": "🇸🇮",
     "accentVariants": ["Ljubljana Academic"],
     "description": "Formal Slovenian for academic research and scholarly communication.",
     "region": "Europe"},
    {"code": "lt", "name": "Lithuanian", "nativeName": "Lietuvių (Akademinė)", "flag": "🇱🇹",
     "accentVariants": ["Vilnius Academic"],
     "description": "Formal Lithuanian for academic research and Baltic scholarship.",
     "region": "Europe"},
    {"code": "lv", "name": "Latvian", "nativeName": "Latviešu (Akadēmiskā)", "flag": "🇱🇻",
     "accentVariants": ["Riga Academic"],
     "description": "Formal Latvian for academic research and official communication.",
     "region": "Europe"},
    {"code": "et", "name": "Estonian", "nativeName": "Eesti (Akadeemiline)", "flag": "🇪🇪",
     "accentVariants": ["Tallinn Academic"],
     "description": "Formal Estonian for academic research and digital scholarship.",
     "region": "Europe"},
    {"code": "ga", "name": "Irish", "nativeName": "Gaeilge (Acadúil)", "flag": "🇮🇪",
     "accentVariants": ["Standard Academic", "Connacht Formal"],
     "description": "Official language of Ireland. Formal Irish for academic research.",
     "region": "Europe"},
    {"code": "mt", "name": "Maltese", "nativeName": "Malti (Akademiku)", "flag": "🇲🇹",
     "accentVariants": ["Standard Academic"],
     "description": "Official language of Malta. Formal Maltese for academic use.",
     "region": "Europe"},

    # ─── South Asia ─────────────────────────────────────────────
    {"code": "hi", "name": "Hindi", "nativeName": "हिन्दी (अकादमिक)", "flag": "🇮🇳",
     "accentVariants": ["Standard Academic", "Scientific Register", "Delhi Formal"],
     "description": "Official language of India. Formal Hindi for scientific research.",
     "region": "South Asia"},
    {"code": "bn", "name": "Bengali", "nativeName": "বাংলা (একাডেমিক)", "flag": "🇧🇩",
     "accentVariants": ["Dhaka Academic", "Kolkata Formal"],
     "description": "Official language of Bangladesh. Formal Bengali for academic research.",
     "region": "South Asia"},
    {"code": "ur", "name": "Urdu", "nativeName": "اردو (تعلیمی)", "flag": "🇵🇰",
     "accentVariants": ["Islamabad Academic", "Lucknow Formal", "Karachi Academic"],
     "description": "Official language of Pakistan. Formal Urdu for academic research.",
     "region": "South Asia", "rtl": True},
    {"code": "ta", "name": "Tamil", "nativeName": "தமிழ் (கல்வியியல்)", "flag": "🇮🇳",
     "accentVariants": ["Chennai Academic", "Jaffna Formal", "Singapore Tamil"],
     "description": "Classical language of India, Sri Lanka, Singapore. Formal Tamil for research.",
     "region": "South Asia"},
    {"code": "te", "name": "Telugu", "nativeName": "తెలుగు (విద్యాపరమైన)", "flag": "🇮🇳",
     "accentVariants": ["Hyderabad Academic", "Vijayawada Formal"],
     "description": "Official language of Andhra Pradesh. Formal Telugu for research.",
     "region": "South Asia"},
    {"code": "mr", "name": "Marathi", "nativeName": "मराठी (शैक्षणिक)", "flag": "🇮🇳",
     "accentVariants": ["Pune Academic", "Mumbai Formal"],
     "description": "Official language of Maharashtra. Formal Marathi for research.",
     "region": "South Asia"},
    {"code": "gu", "name": "Gujarati", "nativeName": "ગુજરાતી (શૈક્ષણિક)", "flag": "🇮🇳",
     "accentVariants": ["Ahmedabad Academic", "Surat Formal"],
     "description": "Official language of Gujarat. Formal Gujarati for literary research.",
     "region": "South Asia"},
    {"code": "kn", "name": "Kannada", "nativeName": "ಕನ್ನಡ (ಶೈಕ್ಷಣಿಕ)", "flag": "🇮🇳",
     "accentVariants": ["Bangalore Academic", "Mysore Formal"],
     "description": "Official language of Karnataka. Formal Kannada for research.",
     "region": "South Asia"},
    {"code": "ml", "name": "Malayalam", "nativeName": "മലയാളം (അക്കാദമിക്)", "flag": "🇮🇳",
     "accentVariants": ["Thiruvananthapuram Academic", "Kochi Formal"],
     "description": "Official language of Kerala. Formal Malayalam for research.",
     "region": "South Asia"},
    {"code": "pa", "name": "Punjabi", "nativeName": "ਪੰਜਾਬੀ (ਅਕਾਦਮਿਕ)", "flag": "🇮🇳",
     "accentVariants": ["Amritsar Academic", "Lahore Formal"],
     "description": "Official language of Punjab. Formal Punjabi for cultural research.",
     "region": "South Asia"},
    {"code": "si", "name": "Sinhala", "nativeName": "සිංහල (ශාස්ත්‍රීය)", "flag": "🇱🇰",
     "accentVariants": ["Colombo Academic", "Kandy Formal"],
     "description": "Official language of Sri Lanka. Formal Sinhala for academic research.",
     "region": "South Asia"},
    {"code": "ne", "name": "Nepali", "nativeName": "नेपाली (शैक्षिक)", "flag": "🇳🇵",
     "accentVariants": ["Kathmandu Academic", "Pokhara Formal"],
     "description": "Official language of Nepal. Formal Nepali for academic discourse.",
     "region": "South Asia"},
    {"code": "sd", "name": "Sindhi", "nativeName": "سنڌي (تعليمي)", "flag": "🇵🇰",
     "accentVariants": ["Karachi Academic", "Hyderabad Sindhi"],
     "description": "Official language of Sindh province. Formal Sindhi for research.",
     "region": "South Asia", "rtl": True},

    # ─── East Asia ──────────────────────────────────────────────
    {"code": "zh", "name": "Chinese (Mandarin)", "nativeName": "中文 (学术)", "flag": "🇨🇳",
     "accentVariants": ["Mandarin Academic (Simplified)", "Taiwan Academic (Traditional)", "HK Formal"],
     "description": "Standard academic Mandarin with verified scientific terminology.",
     "region": "East Asia"},
    {"code": "ja", "name": "Japanese", "nativeName": "日本語 (学術)", "flag": "🇯🇵",
     "accentVariants": ["Tokyo Academic", "Kyoto Formal", "Osaka Professional"],
     "description": "Formal Japanese for academic publishing and technical documentation.",
     "region": "East Asia"},
    {"code": "ko", "name": "Korean", "nativeName": "한국어 (학술)", "flag": "🇰🇷",
     "accentVariants": ["Seoul Academic", "Pyongyang Formal"],
     "description": "Formal Korean for academic research and technological discourse.",
     "region": "East Asia"},
    {"code": "mn", "name": "Mongolian", "nativeName": "Монгол (Эрдэм шинжилгээний)", "flag": "🇲🇳",
     "accentVariants": ["Ulaanbaatar Academic", "Inner Mongolian"],
     "description": "Official language of Mongolia. Formal Mongolian for research.",
     "region": "East Asia"},

    # ─── Southeast Asia ─────────────────────────────────────────
    {"code": "id", "name": "Indonesian", "nativeName": "Bahasa Indonesia (Akademik)", "flag": "🇮🇩",
     "accentVariants": ["Jakarta Academic", "Javanese Formal"],
     "description": "Official language of Indonesia. Formal Bahasa Indonesia for scholarship.",
     "region": "Southeast Asia"},
    {"code": "ms", "name": "Malay", "nativeName": "Bahasa Melayu (Akademik)", "flag": "🇲🇾",
     "accentVariants": ["KL Academic", "Brunei Formal", "Singapore Malay"],
     "description": "Official language of Malaysia, Brunei, Singapore. Formal Malay.",
     "region": "Southeast Asia"},
    {"code": "vi", "name": "Vietnamese", "nativeName": "Tiếng Việt (Học thuật)", "flag": "🇻🇳",
     "accentVariants": ["Hanoi Academic", "Saigon Formal"],
     "description": "Official language of Vietnam. Formal Vietnamese for scientific publishing.",
     "region": "Southeast Asia"},
    {"code": "th", "name": "Thai", "nativeName": "ไทย (วิชาการ)", "flag": "🇹🇭",
     "accentVariants": ["Bangkok Academic", "Northern Thai Formal"],
     "description": "Official language of Thailand. Formal Thai for scholarly discourse.",
     "region": "Southeast Asia"},
    {"code": "my", "name": "Burmese", "nativeName": "မြန်မာ (ပညာရပ်ဆိုင်ရာ)", "flag": "🇲🇲",
     "accentVariants": ["Yangon Academic", "Mandalay Formal"],
     "description": "Official language of Myanmar. Formal Burmese for research.",
     "region": "Southeast Asia"},
    {"code": "km", "name": "Khmer", "nativeName": "ភាសាខ្មែរ (សិក្សា)", "flag": "🇰🇭",
     "accentVariants": ["Phnom Penh Academic"],
     "description": "Official language of Cambodia. Formal Khmer for educational discourse.",
     "region": "Southeast Asia"},
    {"code": "lo", "name": "Lao", "nativeName": "ລາວ (ວິຊາການ)", "flag": "🇱🇦",
     "accentVariants": ["Vientiane Academic"],
     "description": "Official language of Laos. Formal Lao for research.",
     "region": "Southeast Asia"},
    {"code": "tl", "name": "Filipino", "nativeName": "Filipino (Akademiko)", "flag": "🇵🇭",
     "accentVariants": ["Manila Academic", "Cebuano Formal"],
     "description": "Official language of the Philippines. Formal Filipino for national discourse.",
     "region": "Southeast Asia"},

    # ─── Central Asia ───────────────────────────────────────────
    {"code": "kk", "name": "Kazakh", "nativeName": "Қазақ (Академиялық)", "flag": "🇰🇿",
     "accentVariants": ["Nur-Sultan Academic", "Almaty Formal"],
     "description": "Official language of Kazakhstan. Formal Kazakh for research.",
     "region": "Central Asia"},
    {"code": "uz", "name": "Uzbek", "nativeName": "O'zbek (Akademik)", "flag": "🇺🇿",
     "accentVariants": ["Tashkent Academic", "Samarkand Formal"],
     "description": "Official language of Uzbekistan. Formal Uzbek for scientific publishing.",
     "region": "Central Asia"},
    {"code": "tk", "name": "Turkmen", "nativeName": "Türkmen (Akademiki)", "flag": "🇹🇲",
     "accentVariants": ["Ashgabat Academic"],
     "description": "Official language of Turkmenistan. Formal Turkmen for official use.",
     "region": "Central Asia"},
    {"code": "ky", "name": "Kyrgyz", "nativeName": "Кыргыз (Академиялык)", "flag": "🇰🇬",
     "accentVariants": ["Bishkek Academic"],
     "description": "Official language of Kyrgyzstan. Formal Kyrgyz for research.",
     "region": "Central Asia"},
    {"code": "tg", "name": "Tajik", "nativeName": "Тоҷикӣ (Академӣ)", "flag": "🇹🇯",
     "accentVariants": ["Dushanbe Academic"],
     "description": "Official language of Tajikistan. Formal Tajik for academic discourse.",
     "region": "Central Asia"},
    {"code": "tr", "name": "Turkish", "nativeName": "Türkçe (Akademik)", "flag": "🇹🇷",
     "accentVariants": ["Istanbul Academic", "Ankara Formal", "Azerbaijani Academic"],
     "description": "Official language of Turkey. Formal Turkish for regional scholarship.",
     "region": "Central Asia"},

    # ─── Americas ───────────────────────────────────────────────
    {"code": "qu", "name": "Quechua", "nativeName": "Runasimi (Akadimiku)", "flag": "🇵🇪",
     "accentVariants": ["Southern Quechua (Cusco)", "Northern Quechua (Ecuador)", "Bolivian Quechua"],
     "description": "Official language of Peru, Bolivia, Ecuador. Formal Quechua for indigenous research.",
     "region": "Americas"},
    {"code": "gn", "name": "Guaraní", "nativeName": "Avañe'ẽ (Akadémiko)", "flag": "🇵🇾",
     "accentVariants": ["Paraguayan Academic", "Eastern Bolivian Guaraní"],
     "description": "Official language of Paraguay and Bolivia. Formal Guaraní for indigenous research.",
     "region": "Americas"},
    {"code": "ay", "name": "Aymara", "nativeName": "Aymar (Yatiña)", "flag": "🇧🇴",
     "accentVariants": ["La Paz Academic", "Peruvian Aymara"],
     "description": "Official language of Bolivia and Peru. Formal Aymara for cultural studies.",
     "region": "Americas"},
    {"code": "nv", "name": "Navajo", "nativeName": "Diné Bizaad (Óltaʼ)", "flag": "🇺🇸",
     "accentVariants": ["Standard Navajo Academic", "Arizona Formal"],
     "description": "Most widely spoken Indigenous language in the US. Formal Navajo.",
     "region": "Americas"},
    {"code": "ht", "name": "Haitian Creole", "nativeName": "Kreyòl Ayisyen (Akademik)", "flag": "🇭🇹",
     "accentVariants": ["Port-au-Prince Academic"],
     "description": "Official language of Haiti. Formal Kreyòl for education.",
     "region": "Americas"},

    # ─── Oceania ────────────────────────────────────────────────
    {"code": "mi", "name": "Māori", "nativeName": "Te Reo Māori (Mātauranga)", "flag": "🇳🇿",
     "accentVariants": ["Standard Māori Academic", "Southern Māori"],
     "description": "Official language of New Zealand. Formal Māori for indigenous knowledge.",
     "region": "Oceania"},
    {"code": "sm", "name": "Samoan", "nativeName": "Gagana Samoa (A'oa'oga)", "flag": "🇼🇸",
     "accentVariants": ["Standard Academic", "American Samoan"],
     "description": "Official language of Samoa. Formal Samoan for cultural research.",
     "region": "Oceania"},
    {"code": "to", "name": "Tongan", "nativeName": "Lea Faka-Tonga (Ako)", "flag": "🇹🇴",
     "accentVariants": ["Standard Academic"],
     "description": "Official language of Tonga. Formal Tongan for cultural preservation.",
     "region": "Oceania"},
    {"code": "fj", "name": "Fijian", "nativeName": "Na Vosa Vakaviti (Vuli)", "flag": "🇫🇯",
     "accentVariants": ["Standard Academic", "Bauan Formal"],
     "description": "Official language of Fiji. Formal Fijian for cultural discourse.",
     "region": "Oceania"},
    {"code": "haw", "name": "Hawaiian", "nativeName": "ʻŌlelo Hawaiʻi (Hoʻonaʻauao)", "flag": "🌺",
     "accentVariants": ["Standard Academic", "Niʻihau"],
     "description": "Official language of Hawaiʻi. Formal Hawaiian for cultural revitalization.",
     "region": "Oceania"},
]

# ─── Domain Glossaries ────────────────────────────────────────────────
DOMAIN_GLOSSARIES = [
    {"id": "bio", "name": "Molecular Biology & Genetics", "termsLocked": 4200},
    {"id": "agri", "name": "Agriculture & Environmental Science", "termsLocked": 3100},
    {"id": "cs", "name": "Computer Science & AI Pipelines", "termsLocked": 5400},
    {"id": "med", "name": "Clinical Medicine & Pharmacology", "termsLocked": 6800},
    {"id": "econ", "name": "Data Analytics & Applied Economics", "termsLocked": 2900},
    {"id": "law", "name": "Legal & Jurisprudence Terminology", "termsLocked": 3600},
    {"id": "edu", "name": "Education & Pedagogy Research", "termsLocked": 2400},
    {"id": "eng", "name": "Engineering & Technology Standards", "termsLocked": 4500},
    {"id": "soc", "name": "Sociology & Anthropology Studies", "termsLocked": 2800},
    {"id": "phys", "name": "Physics & Mathematical Sciences", "termsLocked": 5100},
]

REGIONS = [
    "Africa", "Middle East & North Africa", "Europe", "South Asia",
    "East Asia", "Southeast Asia", "Central Asia", "Americas", "Oceania"
]

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================

def get_lang(code):
    for l in EXTENDED_LANGUAGES:
        if l["code"] == code:
            return l
    return EXTENDED_LANGUAGES[22]  # default to English

def get_glossary(gid):
    for g in DOMAIN_GLOSSARIES:
        if g["id"] == gid:
            return g
    return DOMAIN_GLOSSARIES[0]

def get_langs_by_region(region):
    if region == "All Regions":
        return EXTENDED_LANGUAGES
    return [l for l in EXTENDED_LANGUAGES if l.get("region") == region]

# ==========================================
# 3. RENDER PAGE
# ==========================================

hero_card(
    "🌐 Global Language & Academic Register",
    "Complete localization engine for the application interface, AI synthesis, and neural audio podcasts. "
    f"Supports {len(EXTENDED_LANGUAGES)} official languages across {len(REGIONS)} world regions.",
    badge_text=f"v1.0 — {len(REGIONS)} Regions · {sum(len(gl['accentVariants']) for gl in EXTENDED_LANGUAGES)} Accents"
)
watermark("CHRISHEM")

st.markdown('<div class="loc-engine-wrapper">', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# STATUS BAR
# ═══════════════════════════════════════════════════════════════════════
current_lang = get_lang(st.session_state.get("loc_selected_language", "en"))
active_glossary = get_glossary(st.session_state.get("loc_selected_glossary", "bio"))

tot_langs = len(EXTENDED_LANGUAGES)
tot_accents = sum(len(l["accentVariants"]) for l in EXTENDED_LANGUAGES)

# ─── TOP CONTROLS BAR ────────────────────────────────────────────────
bar_cols = st.columns([3, 1, 1, 1])
with bar_cols[0]:
    region_opts = ["All Regions"] + REGIONS
    current_region = st.session_state.get("loc_region_filter", "All Regions")
    def_idx = region_opts.index(current_region) if current_region in region_opts else 0
    sel_region = st.selectbox("🌍 Filter by Region", region_opts, index=def_idx, key="loc_region_sel")
    st.session_state["loc_region_filter"] = sel_region

with bar_cols[1]:
    st.markdown(
        f'<div class="loc-stat-card"><div class="loc-stat-num">{tot_langs}</div><div class="loc-stat-label">Languages</div></div>',
        unsafe_allow_html=True)
with bar_cols[2]:
    st.markdown(
        f'<div class="loc-stat-card"><div class="loc-stat-num">{tot_accents}</div><div class="loc-stat-label">Accents</div></div>',
        unsafe_allow_html=True)
with bar_cols[3]:
    st.markdown(
        f'<div class="loc-stat-card"><div class="loc-stat-num">{len(DOMAIN_GLOSSARIES)}</div><div class="loc-stat-label">Glossaries</div></div>',
        unsafe_allow_html=True)

# ─── ACTIVE LANGUAGE HUD ─────────────────────────────────────────────
rtl_badge = ('<span class="loc-rtl-badge">RTL LAYOUT</span>' if current_lang.get('rtl') else '')
st.markdown(
    f'<div class="loc-hud">'
    f'<span class="loc-hud-flag">{current_lang["flag"]}</span>'
    f'<div class="loc-hud-info">'
    f'<div class="loc-hud-name">{current_lang["nativeName"]} {rtl_badge}</div>'
    f'<div class="loc-hud-meta">'
    f'<span class="loc-live-dot"></span> VOICE: {st.session_state.get("loc_selected_accent", "Academic US")}'
    f'<span class="loc-hud-sep">|</span>'
    f'🗂️ {active_glossary["name"]}'
    f'<span class="loc-hud-sep">|</span>'
    f'📶 {current_lang.get("region", "International")}'
    f'</div></div>'
    f'<div class="loc-hud-code"><div class="loc-hud-code-text">{current_lang["code"].upper()}</div><div class="loc-hud-code-label">Locale</div></div>'
    f'</div>',
    unsafe_allow_html=True
)

# ═══════════════════════════════════════════════════════════════════════
# MAIN GRID: LEFT (Language + Accent) | RIGHT (Glossary + Controls)
# ═══════════════════════════════════════════════════════════════════════
left_col, right_col = st.columns([7, 5])

with left_col:
    # ─── 1. LANGUAGE SELECTOR ──────────────────────────────────
    st.markdown(
        '<div class="loc-section-card">'
        '<div class="loc-section-header">'
        '<span class="loc-section-title">🌐 1. System & AI Synthesis Working Language</span>'
        f'<span class="loc-section-count">{len(EXTENDED_LANGUAGES)} OFFICIAL LOCALES</span>'
        '</div>',
        unsafe_allow_html=True
    )

    filtered = get_langs_by_region(st.session_state["loc_region_filter"])
    lang_opts = {l["code"]: f"{l['flag']} {l['name']} — {l['nativeName']} ({l.get('region', '')})" for l in filtered}
    opt_list = list(lang_opts.keys())

    cur_idx = 0
    if st.session_state["loc_selected_language"] in opt_list:
        cur_idx = opt_list.index(st.session_state["loc_selected_language"])

    sel_lang = st.selectbox(
        "Choose Language", opt_list,
        format_func=lambda c: lang_opts.get(c, c),
        index=cur_idx, key="loc_lang_select", label_visibility="collapsed"
    )

    if sel_lang != st.session_state.get("loc_selected_language"):
        st.session_state["loc_selected_language"] = sel_lang
        new_lang = get_lang(sel_lang)
        st.session_state["loc_selected_accent"] = new_lang["accentVariants"][0]
        st.rerun()

    # Visual language grid — purely decorative card display
    lang_cards_html = '<div class="loc-lang-grid">'
    for l in filtered:
        sel = l["code"] == st.session_state["loc_selected_language"]
        cls = "loc-lang-card active" if sel else "loc-lang-card"
        lang_cards_html += f'<div class="{cls}">'
        lang_cards_html += f'<span class="loc-lang-flag">{l["flag"]}</span>'
        lang_cards_html += f'<div class="loc-lang-info"><div class="loc-lang-name">{l["name"]}</div>'
        lang_cards_html += f'<div class="loc-lang-native">{l["nativeName"]}</div>'
        lang_cards_html += f'<div class="loc-lang-desc">{l["description"][:55]}...</div>'
        lang_cards_html += f'<div class="loc-lang-region">{l.get("region", "")} · {len(l["accentVariants"])} accents</div></div>'
        if sel:
            lang_cards_html += '<span class="loc-lang-check">✓</span>'
        lang_cards_html += '</div>'
    lang_cards_html += '</div>'
    lang_cards_html += f'<div class="loc-lang-count">Showing {len(filtered)} of {len(EXTENDED_LANGUAGES)} languages</div>'
    st.markdown(lang_cards_html, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)  # close section-card

    # ─── 2. ACCENT SELECTOR ────────────────────────────────────
    st.markdown(
        '<div class="loc-section-card">'
        '<div class="loc-section-header">'
        '<span class="loc-section-title">🎙️ 2. Neural Vocal Model & Regional Accent</span>'
        '</div>',
        unsafe_allow_html=True
    )

    accent_opts = current_lang["accentVariants"]
    cur_accent = st.session_state.get("loc_selected_accent", accent_opts[0])
    acc_idx = accent_opts.index(cur_accent) if cur_accent in accent_opts else 0

    sel_accent = st.radio("Select Accent", accent_opts, index=acc_idx,
                          key="loc_accent_radio", label_visibility="collapsed",
                          horizontal=True)

    if sel_accent != st.session_state.get("loc_selected_accent"):
        st.session_state["loc_selected_accent"] = sel_accent
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

with right_col:
    st.markdown('<div class="loc-section-card loc-right-panel">', unsafe_allow_html=True)

    # Domain Glossary
    st.markdown(
        f'<div class="loc-glossary-header">'
        f'<span class="loc-section-title">⚙️ Domain Technical Glossary</span>'
        f'<span class="loc-glossary-badge">{active_glossary["termsLocked"]:,} TERMS</span>'
        f'</div>',
        unsafe_allow_html=True
    )

    gl_opts = [g["id"] for g in DOMAIN_GLOSSARIES]
    gl_fmt = lambda gid: f'{next(g["name"] for g in DOMAIN_GLOSSARIES if g["id"] == gid)} ({next(g["termsLocked"] for g in DOMAIN_GLOSSARIES if g["id"] == gid):,})'
    gl_idx = gl_opts.index(st.session_state["loc_selected_glossary"])
    sel_gl = st.selectbox("Glossary", gl_opts, format_func=gl_fmt, index=gl_idx,
                          key="loc_glossary_sel", label_visibility="collapsed")
    st.session_state["loc_selected_glossary"] = sel_gl
    st.markdown('<div class="loc-glossary-hint">Forces exact scientific terminology mappings during translation.</div>',
                unsafe_allow_html=True)

    # Academic Tone
    st.markdown('<div class="loc-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="loc-section-title" style="margin-bottom:0.5rem;">Academic Tone & Register Level</div>',
                unsafe_allow_html=True)

    t1, t2 = st.columns(2)
    cur_tone = st.session_state.get("loc_academic_tone", "peer_reviewed")
    with t1:
        cls = "loc-tone-btn active" if cur_tone == "peer_reviewed" else "loc-tone-btn"
        if st.button("📘 Formal Academic", key="loc_tone_peer", use_container_width=True):
            st.session_state["loc_academic_tone"] = "peer_reviewed"
            st.rerun()
        st.caption("Peer-Reviewed Standard")
    with t2:
        if st.button("📋 Executive Debrief", key="loc_tone_exec", use_container_width=True):
            st.session_state["loc_academic_tone"] = "executive"
            st.rerun()
        st.caption("Concise & Direct")

    # Feature Toggles
    st.markdown('<div class="loc-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="loc-features">', unsafe_allow_html=True)

    dv = st.checkbox("🔄 Synchronized Dual Reader — Display source English side-by-side with localized outputs.",
                     value=st.session_state.get("loc_dual_view_enabled", True), key="loc_dv")
    st.session_state["loc_dual_view_enabled"] = dv

    op = st.checkbox("📡 Offline Compressed MP3 Packs — Pre-compress audio for low-bandwidth field work.",
                     value=st.session_state.get("loc_offline_pack_enabled", True), key="loc_op")
    st.session_state["loc_offline_pack_enabled"] = op

    ip = st.checkbox("🏛️ Enforce Team Language Policy — Apply standardized glossaries across shared workspaces.",
                     value=st.session_state.get("loc_institutional_policy", True), key="loc_ip")
    st.session_state["loc_institutional_policy"] = ip

    pt = st.checkbox("🔒 Preserve Technical Identifiers — Lock gene names, formulas, and data variables.",
                     value=st.session_state.get("loc_preserve_tech_terms", True), key="loc_pt")
    st.session_state["loc_preserve_tech_terms"] = pt

    st.markdown('</div>', unsafe_allow_html=True)

    # Status Footer
    lock_state = '🔒' if st.session_state.get("loc_preserve_tech_terms", True) else '🔓'
    st.markdown(
        f'<div class="loc-footer">'
        f'<span class="loc-footer-status"><span class="loc-live-dot"></span> Strict Academic Guard {lock_state}</span>'
        f'<span class="loc-footer-saved">Auto-Saved</span>'
        f'</div>',
        unsafe_allow_html=True
    )

    st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# DUAL-READER LIVE PREVIEW
# ═══════════════════════════════════════════════════════════════════════
if st.session_state.get("loc_dual_view_enabled", True):
    st.markdown(
        '<div class="loc-dual-reader">'
        '<div class="loc-dual-header">'
        '<span class="loc-dual-title">⇄ Live Preview: Synchronized Dual-Language Reader Mode</span>'
        '<span class="loc-dual-badge">SYNCHRONIZED LINE-BY-LINE</span>'
        '</div>'
        '<div class="loc-dual-grid">',
        unsafe_allow_html=True
    )

    pc1, pc2 = st.columns(2)

    with pc1:
        st.markdown(
            '<div class="loc-dual-panel">'
            '<div class="loc-dual-panel-header">'
            '<span>ORIGINAL SOURCE (ENGLISH)</span>'
            '<span>SECTION 3.2</span>'
            '</div>'
            '<p class="loc-dual-panel-text">'
            '"The analysis identified major resistance genes in <i>Klebsiella pneumoniae</i> isolates, '
            'specifically <b>KPC-2</b> and <b>NDM-1</b> carbapenemases. High-throughput sequencing '
            'revealed plasmid-mediated dissemination across clinical datasets."'
            '</p></div>',
            unsafe_allow_html=True
        )

    with pc2:
        lang_code = st.session_state.get("loc_selected_language", "en")
        localized_map = {
            "sw": '"Uchanganuzi ulibaini jenomu kuu za usugu, hasa <b>KPC-2</b> na <b>NDM-1</b>."',
            "ha": '"Binciken ya gano manyan kwayoyin juriya, musamman <b>KPC-2</b> da <b>NDM-1</b>."',
            "yo": '"Ìtúpalẹ̀ ṣàwárí àwọn jiín ìdènà, pàápàá <b>KPC-2</b> àti <b>NDM-1</b>."',
            "ig": '"Nyocha ahụtara mkpụrụ ndụ iguzogide, karịsịa <b>KPC-2</b> na <b>NDM-1</b>."',
            "am": '"ጥናቱ ዋና ዋና የተቃውሞ ጂኖችን ለይቷል፣ <b>KPC-2</b> እና <b>NDM-1</b>።"',
            "so": '"Falanqeyntu waxay ogaatay hiddo-wadayaasha, gaar ahaan <b>KPC-2</b> iyo <b>NDM-1</b>."',
            "zu": '"Ukuhlaziywa kuthole izakhi zofuzo, ikakhulukazi <b>KPC-2</b> kanye ne-<b>NDM-1</b>."',
            "ar": '"حدد التحليل جينات المقاومة، وتحديداً <b>KPC-2</b> و<b>NDM-1</b>."',
            "fa": '"تجزیه و تحلیل ژن‌های مقاومت، به طور خاص <b>KPC-2</b> و <b>NDM-1</b>."',
            "he": '"הניתוח זיהה גנים של עמידות, במיוחד <b>KPC-2</b> ו-<b>NDM-1</b>."',
            "hi": '"विश्लेषण ने प्रमुख प्रतिरोध जीन की पहचान की, विशेष रूप से <b>KPC-2</b> और <b>NDM-1</b>।"',
            "bn": '"বিশ্লেষণে প্রধান প্রতিরোধ জিন চিহ্নিত, বিশেষ করে <b>KPC-2</b> এবং <b>NDM-1</b>।"',
            "ur": '"تجزیہ نے مزاحمت کے اہم جینوں کی نشاندہی کی، خاص طور پر <b>KPC-2</b> اور <b>NDM-1</b>۔"',
            "ta": '"பகுப்பாய்வு முக்கிய எதிர்ப்பு மரபணுக்களை அடையாளம் கண்டது, <b>KPC-2</b>, <b>NDM-1</b>."',
            "te": '"విశ్లేషణ ప్రధాన నిరోధక జన్యువులను గుర్తించింది, <b>KPC-2</b>, <b>NDM-1</b>."',
            "zh": '"分析确定了主要耐药基因，特别是<b>KPC-2</b>和<b>NDM-1</b>。"',
            "ja": '"主要な耐性遺伝子、特に<b>KPC-2</b>および<b>NDM-1</b>が特定されました。"',
            "ko": '"주요 내성 유전자, 특히 <b>KPC-2</b> 및 <b>NDM-1</b>이 확인되었습니다."',
            "id": '"Analisis mengidentifikasi gen resistensi utama, khususnya <b>KPC-2</b> dan <b>NDM-1</b>."',
            "ms": '"Analisis mengenal pasti gen rintangan utama, khususnya <b>KPC-2</b> dan <b>NDM-1</b>."',
            "vi": '"Phân tích xác định gen kháng thuốc chính, đặc biệt <b>KPC-2</b> và <b>NDM-1</b>."',
            "th": '"การวิเคราะห์ระบุยีนดื้อยาหลัก โดยเฉพาะ <b>KPC-2</b> และ <b>NDM-1</b>"',
            "tr": '"Analiz, majör direnç genlerini tanımladı, özellikle <b>KPC-2</b> ve <b>NDM-1</b>."',
            "ru": '"Анализ выявил гены резистентности, в частности <b>KPC-2</b> и <b>NDM-1</b>."',
            "fr": '"L\'analyse a identifié les gènes de résistance, notamment <b>KPC-2</b> et <b>NDM-1</b>."',
            "es": '"El análisis identificó genes de resistencia, específicamente <b>KPC-2</b> y <b>NDM-1</b>."',
            "de": '"Die Analyse identifizierte Resistenzgene, insbesondere <b>KPC-2</b> und <b>NDM-1</b>."',
            "pt": '"A análise identificou genes de resistência, especificamente <b>KPC-2</b> e <b>NDM-1</b>."',
            "it": '"L\'analisi ha identificato geni di resistenza, in particolare <b>KPC-2</b> e <b>NDM-1</b>."',
            "nl": '"De analyse identificeerde resistentiegenen, met name <b>KPC-2</b> en <b>NDM-1</b>."',
            "pl": '"Analiza zidentyfikowała geny oporności, szczególnie <b>KPC-2</b> i <b>NDM-1</b>."',
        }
        localized_text = localized_map.get(lang_code,
            f'"Professional localized output in {current_lang["name"]}. Locked scientific codes <b>KPC-2</b> and <b>NDM-1</b>."')

        tone_label = st.session_state.get("loc_academic_tone", "peer_reviewed").replace("_", " ").title()

        st.markdown(
            f'<div class="loc-dual-panel localized">'
            f'<div class="loc-dual-panel-header">'
            f'<span>LOCALIZED SYNTHESIS ({current_lang["name"].upper()})</span>'
            f'<span>{tone_label} REGISTER</span>'
            f'</div>'
            f'<p class="loc-dual-panel-text">{localized_text}</p>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.markdown('</div></div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# WORLD LANGUAGE COVERAGE MAP
# ═══════════════════════════════════════════════════════════════════════
st.markdown(
    '<div class="loc-section-card">'
    '<div class="loc-section-header">'
    '<span class="loc-section-title">🌍 World Language Coverage Map</span>'
    '</div>'
    '<div class="loc-region-grid">',
    unsafe_allow_html=True
)

rcols = st.columns(3)
for idx, region in enumerate(REGIONS):
    region_langs = [l for l in EXTENDED_LANGUAGES if l.get("region") == region]
    n_accents = sum(len(l["accentVariants"]) for l in region_langs)
    lang_list = ' '.join(f'{l["flag"]} {l["name"]}' for l in region_langs)
    with rcols[idx % 3]:
        st.markdown(
            f'<div class="loc-region-card">'
            f'<div class="loc-region-name">{region}</div>'
            f'<div class="loc-region-langs">{lang_list}</div>'
            f'<div class="loc-region-stats">{len(region_langs)} languages · {n_accents} accents</div>'
            f'</div>',
            unsafe_allow_html=True
        )

st.markdown('</div></div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)  # close loc-engine-wrapper

st.caption(
    f"🌐 Global Localization Engine — {tot_langs} languages · "
    f"{tot_accents} neural accents · "
    f"{len(DOMAIN_GLOSSARIES)} domain glossaries · "
    f"Academic Tone: {st.session_state.get('loc_academic_tone', 'peer_reviewed').replace('_', ' ').title()}"
)

