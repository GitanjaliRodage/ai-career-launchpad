"""AI Career Launchpad - Flask application entry point.

Routes:
    GET  /                       Landing page + resume upload + job description
    POST /api/analyze            Run the career fit analysis (JSON response)
    GET  /api/health             Simple health / provider check
    GET  /robots.txt             Allow indexing for the public deployment
"""

import utils.http_session
import utils.transport
import utils.session
import logging
import os

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import RequestEntityTooLarge

from config import Config
from services import ai_service
from services.career_analyzer import (
    AnalysisError,
    AIProviderError,
    ResumeParseError,
    run_analysis_from_request,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai-career-launchpad")

app = Flask(__name__)
app.config.from_object(Config)

# Ensure the private upload folder exists.
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)


@app.route("/")
def index():
    """Render the landing page and analysis form."""
    return render_template("index.html", limits=page_limits())


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    """Validate inputs, run analysis, return structured JSON."""
    if not request.files or "resume" not in request.files:
        return _error("Please upload your resume as a PDF file.", 400)

    job_description = request.form.get("job_description", "")

    try:
        analysis = run_analysis_from_request(request.files["resume"], job_description)
    except (AnalysisError, ResumeParseError) as exc:
        return _error(str(exc), 400)
    except AIProviderError as exc:
        logger.warning("AI provider error: %s", exc)
        return _error(str(exc), 502)
    except Exception:
        logger.exception("Unexpected error during analysis")
        return _error("Something went wrong while analysing your profile.", 500)

    analysis["summary"] = _build_summary(analysis)
    logger.info("Analysis completed, fit score %s", analysis["fit_score"])
    return jsonify({"success": True, "analysis": analysis}), 200


@app.route("/api/health")
def health():
    """Health check used by the load balancer / smoke tests."""
    return jsonify({
        "status": "ok",
        "service": "ai-career-launchpad",
        "ai": ai_service.provider_status(),
    }), 200


@app.route("/robots.txt")
def robots():
    return "User-agent: *\nAllow: /\n", 200, {"Content-Type": "text/plain"}


@app.errorhandler(RequestEntityTooLarge)
def handle_too_large(exc):
    limit_mb = Config.MAX_CONTENT_LENGTH // (1024 * 1024)
    return _error(
        "That file is too large. Please upload a PDF under {} MB.".format(limit_mb),
        413,
    )


@app.errorhandler(404)
def handle_404(exc):
    if request.path.startswith("/api/"):
        return _error("Endpoint not found.", 404)
    return render_template("index.html", limits=page_limits()), 404


@app.errorhandler(405)
def handle_405(exc):
    return _error("Method not allowed.", 405)


@app.errorhandler(500)
def handle_500(exc):
    return _error("An internal error occurred.", 500)


def page_limits():
    """Template limits derived from configuration."""
    return {
        "max_upload_mb": Config.MAX_CONTENT_LENGTH // (1024 * 1024),
        "min_jd_chars": Config.MIN_JD_CHARS,
    }


def _error(message, status):
    """Return a consistent JSON error envelope."""
    return jsonify({"success": False, "error": message}), status


def _build_summary(analysis):
    """One-line plain-English headline for the dashboard."""
    score = analysis["fit_score"]
    matched = len(analysis["matched_skills"])
    gaps = len(analysis["skill_gaps"])

    if score >= 80:
        headline = "Strong fit - you are close to interview ready."
    elif score >= 60:
        headline = "Good fit - a focused gap-closing plan should get you there."
    elif score >= 40:
        headline = "Partial fit - targeted upskilling can move you into range."
    else:
        headline = "Early fit - start with the foundations listed in your plan."

    return "{} You match {} of the job's key skills and have {} skill gap(s) to close.".format(
        headline, matched, gaps
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)