"""Tests for resume PDF validation and text extraction."""

import io
import os

import pytest

from services import resume_parser
from services.resume_parser import ResumeParseError


def test_allowed_file_accepts_pdf():
    assert resume_parser.allowed_file("resume.pdf") is True
    assert resume_parser.allowed_file("RESUME.PDF") is True


def test_allowed_file_rejects_other_types():
    assert resume_parser.allowed_file("resume.docx") is False
    assert resume_parser.allowed_file("resume.exe") is False
    assert resume_parser.allowed_file("noextension") is False
    assert resume_parser.allowed_file("") is False


def test_storage_filename_is_random_and_pdf():
    name = resume_parser.secure_filename_for_storage("../../etc/passwd.pdf")
    assert name.endswith(".pdf")
    assert "/" not in name
    assert "\\" not in name
    assert "passwd" not in name
    # 32 hex characters (uuid4) plus the ".pdf" extension.
    assert len(name) == 32 + len(".pdf")


def test_save_resume_rejects_non_pdf(tmp_path, monkeypatch):
    monkeypatch.setattr(resume_parser.Config, "UPLOAD_FOLDER", str(tmp_path))
    upload = io.BytesIO(b"plain text pretending to be a doc")
    upload.name = "resume.txt"
    with pytest.raises(ResumeParseError):
        resume_parser.save_resume(upload)


def test_save_resume_rejects_empty_file(tmp_path, monkeypatch):
    monkeypatch.setattr(resume_parser.Config, "UPLOAD_FOLDER", str(tmp_path))
    upload = io.BytesIO(b"")
    upload.name = "resume.pdf"
    with pytest.raises(ResumeParseError):
        resume_parser.save_resume(upload)


def test_extract_text_from_pdf(tmp_path, pdf_bytes):
    path = tmp_path / "resume.pdf"
    path.write_bytes(pdf_bytes)

    text = resume_parser.extract_text_from_pdf(str(path))

    assert isinstance(text, str)
    assert "Python" in text
    assert "AWS" in text


def test_extract_text_from_missing_file_raises():
    with pytest.raises(ResumeParseError):
        resume_parser.extract_text_from_pdf("/definitely/not/here.pdf")


def test_extract_text_from_corrupt_pdf_raises(tmp_path):
    path = tmp_path / "broken.pdf"
    path.write_bytes(b"this is definitely not a pdf file")
    with pytest.raises(ResumeParseError):
        resume_parser.extract_text_from_pdf(str(path))


def test_uploaded_file_is_deleted_after_extraction(tmp_path, monkeypatch, pdf_bytes):
    monkeypatch.setattr(resume_parser.Config, "UPLOAD_FOLDER", str(tmp_path))
    upload = io.BytesIO(pdf_bytes)
    upload.name = "my-resume.pdf"

    text = resume_parser.extract_text_from_upload(upload)

    assert "Python" in text
    # Nothing should remain in the upload folder after processing.
    assert os.listdir(str(tmp_path)) == []