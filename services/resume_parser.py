"""Resume PDF validation and text extraction.

Uploads are stored under a private folder using a random filename and are
never served by Flask as static content.
"""

import os
import uuid

from config import Config


class ResumeParseError(Exception):
    """Raised when a resume cannot be validated or parsed."""


def allowed_file(filename):
    """Return True when the filename has an allowed extension."""
    if not filename or "." not in filename:
        return False
    extension = filename.rsplit(".", 1)[1].lower()
    return extension in Config.ALLOWED_EXTENSIONS


def secure_filename_for_storage(original_filename):
    """Return a safe, collision-free filename. Original name is not reused."""
    extension = "pdf"
    if original_filename and "." in original_filename:
        extension = original_filename.rsplit(".", 1)[1].lower()
    return "{}.{}".format(uuid.uuid4().hex, extension)


def _filename_of(file_storage):
    """Read the filename from a Werkzeug FileStorage or any upload-like object.

    Werkzeug exposes ``.filename``; plain BytesIO objects expose ``.name``.
    """
    if file_storage is None:
        return ""
    name = getattr(file_storage, "filename", None)
    if not name:
        name = getattr(file_storage, "name", "")
    return name or ""


def save_resume(file_storage):
    """Validate and persist an uploaded resume. Returns the stored path."""
    original_name = _filename_of(file_storage)
    if not original_name:
        raise ResumeParseError("No resume file was uploaded.")

    if not allowed_file(original_name):
        raise ResumeParseError("Only PDF resumes are supported.")

    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    stored_path = os.path.join(
        Config.UPLOAD_FOLDER, secure_filename_for_storage(original_name)
    )

    if hasattr(file_storage, "save"):
        file_storage.save(stored_path)
    else:
        # Fallback for plain file-like objects used in tests.
        with open(stored_path, "wb") as handle:
            handle.write(file_storage.getvalue())

    if os.path.getsize(stored_path) == 0:
        delete_resume(stored_path)
        raise ResumeParseError("The uploaded resume is empty.")

    return stored_path


def delete_resume(stored_path):
    """Best-effort deletion of a stored resume."""
    if stored_path and os.path.exists(stored_path):
        try:
            os.remove(stored_path)
        except OSError:
            pass


def extract_text_from_pdf(pdf_path):
    """Extract plain text from a PDF file."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ResumeParseError(
            "PDF support is not installed. Run: pip install -r requirements.txt"
        )

    if not os.path.exists(pdf_path):
        raise ResumeParseError("The uploaded resume could not be read.")

    try:
        reader = PdfReader(pdf_path)
        pages = reader.pages
        text = "\n".join((page.extract_text() or "") for page in pages)
    except ResumeParseError:
        raise
    except Exception:
        # Never leak internal library errors to the user.
        raise ResumeParseError("We could not read text from that PDF.")

    cleaned = _clean_text(text)
    if len(cleaned) < Config.MIN_RESUME_CHARS:
        raise ResumeParseError(
            "We could not find enough readable text in that PDF. "
            "Please upload a text-based resume (not a scanned image)."
        )
    return cleaned


def extract_text_from_upload(file_storage):
    """Validate, save, parse, then always delete the temporary file.

    Returns the cleaned resume text. The uploaded PDF is never retained.
    """
    stored_path = None
    try:
        stored_path = save_resume(file_storage)
        return extract_text_from_pdf(stored_path)
    except ResumeParseError:
        raise
    except Exception:
        raise ResumeParseError("We could not process that resume file.")
    finally:
        delete_resume(stored_path)


def _clean_text(text):
    """Normalise whitespace and drop null bytes from extracted text."""
    if not text:
        return ""
    text = text.replace("\x00", " ")
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()