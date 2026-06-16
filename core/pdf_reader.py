import io
from PyPDF2 import PdfReader

def extract_text_from_pdf(uploaded_file) -> str:
    """Extracts full text from an uploaded PDF file."""
    try:
        # Seek to the beginning of the BytesIO object
        uploaded_file.seek(0)
        reader = PdfReader(uploaded_file)
        full_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
        return full_text
    except Exception as e:
        raise Exception(f"Failed to read PDF: {str(e)}")