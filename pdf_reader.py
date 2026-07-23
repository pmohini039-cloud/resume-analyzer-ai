from PyPDF2 import PdfReader


def extract_text(pdf_file) -> str:
    """Extract raw text content from uploaded PDF file."""
    reader = PdfReader(pdf_file)
    text = ""

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text

    return text