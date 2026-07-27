import pandas as pd
import json
io_supported = True

def parse_uploaded_document(uploaded_file):
    """Safely parses uploaded files (CSV, Excel, JSON, TXT) based on file extension."""
    if uploaded_file is None:
        return None, "No file uploaded."
    
    filename = uploaded_file.name.lower()
    try:
        if filename.endswith('.csv'):
            # Try UTF-8 first, fallback to latin-1
            try:
                df = pd.read_csv(uploaded_file, encoding='utf-8')
            except UnicodeDecodeError:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, encoding='latin-1')
            return df, "success"
            
        elif filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(uploaded_file)
            return df, "success"
            
        elif filename.endswith('.json'):
            data = json.load(uploaded_file)
            if isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                df = pd.DataFrame([data])
            return df, "success"
            
        elif filename.endswith(('.txt', '.md', '.fasta', '.fa')):
            content = uploaded_file.read().decode("utf-8", errors="ignore")
            return content, "success"
            
        else:
            return None, f"Unsupported file format: {filename}. Please upload CSV, Excel, JSON, or text/sequence files."
            
    except Exception as e:
        return None, f"Error parsing file: {str(e)}"
