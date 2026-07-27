import pandas as pd
import json

def parse_uploaded_document(uploaded_file):
    """Safely parses uploaded files (CSV, Excel, JSON, TXT, PDF) based on file extension."""
    if uploaded_file is None:
        return None, "No file uploaded."
    
    filename = uploaded_file.name.lower()
    try:
        if filename.endswith('.csv'):
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
            
        elif filename.endswith('.pdf'):
            try:
                from pypdf import PdfReader
                reader = PdfReader(uploaded_file)
                text = ""
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
                if not text.strip():
                    return None, "PDF appears to be scanned or contains no selectable text."
                return text, "success"
            except Exception as pdf_err:
                return None, f"Error reading PDF: {str(pdf_err)}"
            
        elif filename.endswith(('.txt', '.md', '.fasta', '.fa')):
            content = uploaded_file.read().decode("utf-8", errors="ignore")
            return content, "success"
            
        else:
            return None, f"Unsupported file format: {filename}. Please upload CSV, Excel, JSON, PDF, or text files."
            
    except Exception as e:
        return None, f"Error parsing file: {str(e)}"
