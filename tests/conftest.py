"""Shared pytest fixtures for AI Career Launchpad."""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Force the mock provider for tests so no AWS call is ever attempted.
os.environ["AI_PROVIDER"] = "mock"

import config  # noqa: E402
import app as app_module  # noqa: E402


SAMPLE_RESUME = (
    "Jordan Lee\n"
    "Data Science undergraduate, Class of 2026\n\n"
    "EDUCATION\n"
    "B.Tech Computer Science, XYZ University, CGPA 8.4\n\n"
    "SKILLS\n"
    "Python, SQL, Machine Learning, Pandas, NumPy, scikit-learn, Git, Linux\n\n"
    "PROJECTS\n"
    "Student attendance prediction system built with Python and scikit-learn.\n"
    "Built a Flask REST API for a campus event platform.\n\n"
    "INTERNSHIP\n"
    "Data analyst intern at a startup, built SQL dashboards.\n"
)

SAMPLE_JD = (
    "Machine Learning Engineer (Entry Level)\n"
    "We are hiring an entry level machine learning engineer to join our platform team.\n"
    "Responsibilities: build and deploy machine learning models, write Python code, "
    "design SQL data pipelines, collaborate with product teams, and improve model "
    "accuracy over time.\n"
    "Requirements: strong Python, SQL, machine learning fundamentals, experience with "
    "TensorFlow or scikit-learn, REST API development, Git, and strong communication "
    "skills. Exposure to AWS, Docker, and Kubernetes is a strong plus.\n"
)


@pytest.fixture
def client():
    """Flask test client with the configured upload size limit."""
    app_module.app.config["TESTING"] = True
    app_module.app.config["MAX_CONTENT_LENGTH"] = config.Config.MAX_CONTENT_LENGTH
    with app_module.app.test_client() as test_client:
        yield test_client


@pytest.fixture
def upload_folder():
    """Redirect uploads to a temporary directory during tests."""
    original = config.Config.UPLOAD_FOLDER
    with tempfile.TemporaryDirectory() as tmp:
        config.Config.UPLOAD_FOLDER = tmp
        app_module.app.config["UPLOAD_FOLDER"] = tmp
        yield tmp
    config.Config.UPLOAD_FOLDER = original


@pytest.fixture
def sample_resume_text():
    return SAMPLE_RESUME


@pytest.fixture
def sample_job_description():
    return SAMPLE_JD


@pytest.fixture
def pdf_bytes():
    """A minimal, valid single-page PDF with extractable text."""
    return build_minimal_pdf()


def build_minimal_pdf():
    """Construct a tiny PDF containing one line of real text."""
    text = (
        "Python SQL Machine Learning Flask Git Docker AWS React "
        "Pandas NumPy Scikit-learn PostgreSQL REST APIs CICD Testing Communication "
        "Leadership Data Analysis Project Management"
    )
    content_stream = (
        "BT /F1 10 Tf 40 760 Td ({}) Tj ET".format(text)
    ).encode("latin-1")

    objects = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objects.append(
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
    )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.append(
        b"<< /Length " + str(len(content_stream)).encode() + b" >>\nstream\n"
        + content_stream + b"\nendstream"
    )

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for index, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += str(index).encode() + b" 0 obj\n" + body + b"\nendobj\n"

    xref_pos = len(out)
    out += b"xref\n0 " + str(len(objects) + 1).encode() + b"\n"
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += ("{:010d} 00000 n \n".format(offset)).encode()
    out += b"trailer\n<< /Size " + str(len(objects) + 1).encode() + b" /Root 1 0 R >>\n"
    out += b"startxref\n" + str(xref_pos).encode() + b"\n%%EOF\n"
    return bytes(out)


@pytest.fixture
def make_pdf_upload(pdf_bytes):
    """Return a factory building an in-memory file-like PDF upload."""

    def _make(content=None, filename="resume.pdf", content_type="application/pdf"):
        import io

        raw = content if content is not None else pdf_bytes
        buffer = io.BytesIO(raw)
        buffer.name = filename
        return (buffer, filename, content_type)

    return _make