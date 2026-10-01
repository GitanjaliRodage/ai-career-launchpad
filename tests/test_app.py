"""Tests for the Flask application (routes, health, errors)."""

from io import BytesIO

SAMPLE_JD = "Machine Learning Engineer. Requires Python, SQL, Machine Learning, AWS, Docker, scikit-learn, Git. Responsibilities include model training, deployment, and API development to help users get real value from data."


def test_home_page_returns_200(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "AI Career Launchpad" in body
    assert "Analyse my career fit" in body
    assert "Career Fit Score" in body


def test_robots_txt(client):
    response = client.get("/robots.txt")
    assert response.status_code == 200
    assert b"Allow: /" in response.data


def test_health_endpoint_returns_provider_info(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["service"] == "ai-career-launchpad"
    assert "ai" in payload
    assert payload["ai"]["provider"] == "mock"


def test_analyze_requires_resume(client):
    response = client.post("/api/analyze", data={"job_description": SAMPLE_JD})
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["success"] is False
    assert "resume" in payload["error"].lower()


def test_analyze_requires_job_description(client, make_pdf_upload):
    pdf_buf, _, _ = make_pdf_upload()
    response = client.post("/api/analyze", data={"resume": (pdf_buf, "resume.pdf")})
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["success"] is False
    assert "job description" in payload["error"].lower()


def test_analyze_accepts_pdf_and_returns_analysis(client, make_pdf_upload):
    pdf_buf, _, _ = make_pdf_upload()
    response = client.post(
        "/api/analyze",
        data={
            "resume": (pdf_buf, "resume.pdf"),
            "job_description": SAMPLE_JD,
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert "analysis" in payload

    analysis = payload["analysis"]
    required = [
        "fit_score",
        "matched_skills",
        "skill_gaps",
        "strengths",
        "improvement_areas",
        "action_plan",
        "next_steps",
        "provider",
        "summary",
    ]
    for field in required:
        assert field in analysis

    assert isinstance(analysis["fit_score"], int)
    assert 0 <= analysis["fit_score"] <= 100
    assert len(analysis["summary"]) > 0


def test_analyze_rejects_non_pdf(client):
    fake = BytesIO(b"hello world")
    response = client.post(
        "/api/analyze",
        data={
            "resume": (fake, "resume.txt"),
            "job_description": SAMPLE_JD,
        },
    )
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["success"] is False


def test_analyze_rejects_too_large_file(client, monkeypatch):
    from config import Config
    import app as app_module

    app_module.app.config["MAX_CONTENT_LENGTH"] = 1024  # 1 KB

    large_pdf = b"%PDF-1.4\n" + b"x" * 2048
    big = BytesIO(large_pdf)
    response = client.post(
        "/api/analyze",
        data={
            "resume": (big, "huge.pdf"),
            "job_description": SAMPLE_JD,
        },
    )
    assert response.status_code == 413
    payload = response.get_json()
    assert payload["success"] is False
    assert "large" in payload["error"].lower()


def test_api_404_returns_json(client):
    response = client.get("/api/non-existent")
    assert response.status_code == 404
    assert response.is_json
    payload = response.get_json()
    assert payload["success"] is False
    assert "not found" in payload["error"].lower()


def test_short_job_description_returns_400(client, make_pdf_upload):
    pdf_buf, _, _ = make_pdf_upload()
    response = client.post(
        "/api/analyze",
        data={
            "resume": (pdf_buf, "resume.pdf"),
            "job_description": "AWS",
        },
    )
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["success"] is False


def test_uploaded_files_are_not_left_on_disk(client, make_pdf_upload, upload_folder):
    pdf_buf, _, _ = make_pdf_upload()
    response = client.post(
        "/api/analyze",
        data={
            "resume": (pdf_buf, "resume.pdf"),
            "job_description": SAMPLE_JD,
        },
    )
    assert response.status_code == 200
    # Upload folder must be empty after successful analysis.
    assert len(upload_folder) == 0 or all(
        not f.endswith(".pdf") for f in __import__("os").listdir(upload_folder)
    )