"""Manual end-to-end smoke test against a running local server.

Usage:
    python tools/smoke_test.py
Requires the app to be running on http://127.0.0.1:5000
"""

import json
import os
import sys
import urllib.error
import urllib.request
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tests.conftest import build_minimal_pdf  # noqa: E402

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5000")

JOB_DESCRIPTION = """Machine Learning Engineer (Entry Level)

We are hiring an entry level machine learning engineer to join our platform team.

Responsibilities:
- Build, train and deploy machine learning models
- Write production Python code
- Design SQL data pipelines and reporting dashboards
- Build REST API services
- Collaborate with product and design teams

Requirements:
- Strong Python, SQL and machine learning fundamentals
- Experience with scikit-learn or TensorFlow
- REST API development
- Git, Linux and CI/CD
- Strong communication and teamwork skills

Nice to have: exposure to AWS, Docker, Kubernetes and Terraform.
"""


def post_multipart(fields, files):
    boundary = uuid.uuid4().hex
    chunks = []
    for name, value in fields.items():
        chunks.append(
            (
                "--{b}\r\nContent-Disposition: form-data; name=\"{n}\"\r\n\r\n".format(
                    b=boundary, n=name
                )
            ).encode()
            + value.encode()
            + b"\r\n"
        )
    for name, (filename, content, content_type) in files.items():
        chunks.append(
            (
                "--{b}\r\nContent-Disposition: form-data; name=\"{n}\"; "
                "filename=\"{f}\"\r\nContent-Type: {c}\r\n\r\n".format(
                    b=boundary, n=name, f=filename, c=content_type
                )
            ).encode()
            + content
            + b"\r\n"
        )
    chunks.append(("--{b}--\r\n".format(b=boundary)).encode())

    request = urllib.request.Request(
        BASE_URL + "/api/analyze",
        data=b"".join(chunks),
        headers={"Content-Type": "multipart/form-data; boundary=" + boundary},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.status, json.loads(response.read().decode())


def check(label, condition, detail=""):
    print("{0} {1}{2}".format("PASS" if condition else "FAIL", label,
                              "" if condition else " -> " + str(detail)))
    return condition


def main():
    ok = True

    # 1. Health
    with urllib.request.urlopen(BASE_URL + "/api/health", timeout=30) as response:
        health = json.loads(response.read().decode())
    ok &= check("health endpoint", health.get("status") == "ok", health)
    ok &= check("provider reported", "provider" in health.get("ai", {}), health)

    # 2. Landing page
    with urllib.request.urlopen(BASE_URL + "/", timeout=30) as response:
        html = response.read().decode()
    ok &= check("landing page renders", "AI Career Launchpad" in html)

    # 3. Missing job description -> 400
    try:
        post_multipart({}, {"resume": ("resume.pdf", build_minimal_pdf(),
                                       "application/pdf")})
        ok &= check("empty job description rejected", False, "no error raised")
    except urllib.error.HTTPError as exc:
        payload = json.loads(exc.read().decode())
        ok &= check("empty job description rejected",
                    exc.code == 400 and payload["success"] is False, payload)

    # 4. Missing resume -> 400
    try:
        post_multipart({"job_description": JOB_DESCRIPTION}, {})
        ok &= check("missing resume rejected", False, "no error raised")
    except urllib.error.HTTPError as exc:
        payload = json.loads(exc.read().decode())
        ok &= check("missing resume rejected",
                    exc.code == 400 and payload["success"] is False, payload)

    # 5. Wrong file type -> 400
    try:
        post_multipart(
            {"job_description": JOB_DESCRIPTION},
            {"resume": ("resume.txt", b"plain text", "text/plain")},
        )
        ok &= check("non-pdf rejected", False, "no error raised")
    except urllib.error.HTTPError as exc:
        payload = json.loads(exc.read().decode())
        ok &= check("non-pdf rejected", exc.code == 400, payload)

    # 6. Full happy path
    status, payload = post_multipart(
        {"job_description": JOB_DESCRIPTION},
        {"resume": ("resume.pdf", build_minimal_pdf(), "application/pdf")},
    )
    analysis = payload.get("analysis", {})
    required = ["fit_score", "matched_skills", "skill_gaps", "strengths",
                "improvement_areas", "action_plan", "next_steps"]
    ok &= check("analyze returns 200", status == 200, status)
    ok &= check("success flag true", payload.get("success") is True)
    for field in required:
        ok &= check("field present: " + field, field in analysis, analysis)
    ok &= check("fit score in range",
                isinstance(analysis.get("fit_score"), int)
                and 0 <= analysis["fit_score"] <= 100,
                analysis.get("fit_score"))

    print("\n--- Analysis ---")
    print(json.dumps(analysis, indent=2))

    print("\n--- Uploads folder ---")
    upload_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "uploads")
    leftovers = os.listdir(upload_dir) if os.path.isdir(upload_dir) else []
    print("contents:", leftovers)
    ok &= check("no resume files left on disk",
                not [f for f in leftovers if f.lower().endswith(".pdf")], leftovers)

    print("\nRESULT:", "ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())