def extract_text(uploaded):
 name=getattr(uploaded,"name","").lower(); data=uploaded.getvalue()
 if name.endswith(".txt"):return data.decode("utf-8",errors="ignore")
 if name.endswith(".pdf"):
  from pypdf import PdfReader
  import io
  return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
 if name.endswith(".docx"):
  from docx import Document
  import io
  return "\n".join(p.text for p in Document(io.BytesIO(data)).paragraphs)
 raise ValueError("Supported formats: PDF, DOCX, TXT")
