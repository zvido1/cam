"""
CAM Lease Review — Document Text Extraction

Accepts a file path and returns plain text content.
Supports TXT, DOCX, and PDF formats.
"""

from pathlib import Path


def parse_document(file_path: str) -> str:
    """Extract plain text from PDF, DOCX, or TXT file.

    Args:
        file_path: Path to the document file.

    Returns:
        Plain text content of the document.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file format is not supported.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    suffix = path.suffix.lower()

    if suffix == ".txt":
        return _parse_txt(path)
    elif suffix == ".docx":
        return _parse_docx(path)
    elif suffix == ".pdf":
        return _parse_pdf(path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Supported: .txt, .docx, .pdf")


def _parse_txt(path: Path) -> str:
    """Read plain text file (UTF-8)."""
    return path.read_text(encoding="utf-8")


def _parse_docx(path: Path) -> str:
    """Extract text from DOCX using python-docx. Preserves paragraph structure."""
    import docx

    doc = docx.Document(str(path))
    paragraphs = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            paragraphs.append(text)
    return "\n\n".join(paragraphs)


def _parse_pdf(path: Path) -> str:
    """Extract text from PDF using PyMuPDF (fitz). Preserves page structure."""
    import fitz

    doc = fitz.open(str(path))
    pages = []
    for page in doc:
        text = page.get_text().strip()
        if text:
            pages.append(text)
    doc.close()
    return "\n\n".join(pages)
