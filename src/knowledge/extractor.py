import os
from pathlib import Path
from typing import Tuple

import httpx


async def extract_text_from_bytes(
    data: bytes, filename: str, mime_type: str
) -> Tuple[str, str, str | None]:
    """Extract searchable text from file bytes.

    Returns:
        (text, status, error)
    """
    ext = Path(filename).suffix.lower()

    if mime_type.startswith("text/") or ext in (".txt", ".md", ".py", ".js", ".json", ".csv"):
        try:
            return data.decode("utf-8"), "success", None
        except UnicodeDecodeError:
            return "", "failed", "UTF-8 decode failed"

    if mime_type == "application/pdf" or ext == ".pdf":
        return _extract_pdf(data)

    if (
        mime_type
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        or ext == ".docx"
    ):
        return _extract_docx(data)

    if (
        mime_type
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        or ext == ".xlsx"
    ):
        return _extract_xlsx(data)

    if mime_type.startswith("image/"):
        return _extract_image(data)

    # For unsupported types, fallback to empty text
    return "", "not_applicable", None


def _extract_pdf(data: bytes) -> Tuple[str, str, str | None]:
    try:
        import pypdf

        reader = pypdf.PdfReader(io.BytesIO(data))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return text, "success", None
    except Exception as e:
        return "", "failed", str(e)


def _extract_docx(data: bytes) -> Tuple[str, str, str | None]:
    try:
        import docx

        document = docx.Document(io.BytesIO(data))
        text = "\n".join(p.text for p in document.paragraphs)
        return text, "success", None
    except Exception as e:
        return "", "failed", str(e)


def _extract_xlsx(data: bytes) -> Tuple[str, str, str | None]:
    try:
        import openpyxl

        wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
        parts = []
        for sheet in wb.worksheets:
            rows = []
            for row in sheet.iter_rows(values_only=True):
                rows.append("\t".join(str(cell) if cell is not None else "" for cell in row))
            parts.append("\n".join(rows))
        return "\n\n".join(parts), "success", None
    except Exception as e:
        return "", "failed", str(e)


def _extract_image(data: bytes) -> Tuple[str, str, str | None]:
    try:
        import pytesseract
        from PIL import Image

        image = Image.open(io.BytesIO(data))
        text = pytesseract.image_to_string(image)
        return text, "success", None
    except ImportError:
        return "", "failed", "OCR not available (pytesseract + Pillow required)"
    except Exception as e:
        return "", "failed", str(e)


async def extract_text_from_url(url: str) -> Tuple[str, str, str | None]:
    """Fetch URL and extract article text."""
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text

        try:
            import trafilatura

            text = trafilatura.extract(html, include_comments=False)
            if text:
                return text, "success", None
        except Exception:
            pass

        # Fallback to plain text if trafilatura fails
        return html, "success", None
    except Exception as e:
        return "", "failed", str(e)


import io
