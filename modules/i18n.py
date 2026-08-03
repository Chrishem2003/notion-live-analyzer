import security_guard

import streamlit as st

LOCALES = {
    "English": {
        "title": "Enterprise Intelligence Engine",
        "subtitle": "Autonomous Analytics & Secure Research Workspace",
        "select_lang": "Select Display Language",
        "export": "Export Localized Data"
    },
    "Swahili": {
        "title": "Injini ya Ujasusi wa Biashara",
        "subtitle": "Uchambuzi wa Kujitegemea na Nafasi Salama ya Utafiti",
        "select_lang": "Chagua Lugha ya Kuonyesha",
        "export": "Hamisha Data Iliyotafsiriwa"
    },
    "French": {
        "title": "Moteur d'Intelligence d'Entreprise",
        "subtitle": "Analytique Autonome et Espace de Recherche SðŸ” curisðŸ” ",
        "select_lang": "SðŸ” lectionner la Langue d'Affichage",
        "export": "Exporter les DonnðŸ” es LocalisðŸ” es"
    },
    "Arabic": {
        "title": "  ",
        "subtitle": "?   ? ",
        "select_lang": "? ? ?",
        "export": "?  ?"
    },
    "Mandarin": {
        "title": "",
        "subtitle": "",
        "select_lang": "",
        "export": "?"
    }
}

def get_locale_strings():
    selected_lang = st.sidebar.selectbox(" Language / Lugha", list(LOCALES.keys()), key="global_lang_select")
    return LOCALES.get(selected_lang, LOCALES["English"])
