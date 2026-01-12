"""Protocol PDF parsing utilities."""
from pathlib import Path
import pdfplumber


def extract_text_from_pdf(pdf_path):
    """
    Extract text from PDF file.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        String containing all text from PDF
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    text_parts = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
    except Exception as e:
        raise RuntimeError(f"Failed to extract text from PDF: {e}")
    
    return "\n\n".join(text_parts)


def merge_protocols(pdf_paths):
    """
    Merge multiple protocol PDFs into a single text string.
    
    Args:
        pdf_paths: List of paths to PDF files
        
    Returns:
        Merged text string
    """
    all_text = []
    
    for pdf_path in pdf_paths:
        text = extract_text_from_pdf(pdf_path)
        all_text.append(text)
    
    return "\n\n---\n\n".join(all_text)

