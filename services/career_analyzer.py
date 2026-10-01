"""Career analysis orchestration.

Validates inputs, calls the configured AI provider, and guarantees a
structured response shape for the dashboard.
"""

from config import Config
from services import ai_service
from services.ai_service import AIProviderError
from services.resume_parser import ResumeParseError

MIN_JD_CHARS = Config.MIN_JD_CHARS


class AnalysisError(Exception):
    """Raised for user-correctable problems with the analysis request."""


def validate_job_description(job_description):
    """Return the trimmed job description or raise AnalysisError."""
    if not job_description or not job_description.strip():
        raise AnalysisError("Please paste a job description before analysing.")

    cleaned = job_description.strip()
    if len(cleaned) < MIN_JD_CHARS:
        raise AnalysisError(
            "The job description looks too short. Paste the full description "
            "(at least {} characters).".format(MIN_JD_CHARS)
        )
    return cleaned


def validate_resume_text(resume_text):
    """Return the trimmed resume text or raise AnalysisError."""
    if not resume_text or not resume_text.strip():
        raise AnalysisError("We could not read any text from your resume.")
    return resume_text.strip()


def analyze(resume_text, job_description):
    """Run the full analysis and return a validated analysis dict.

    Raises AnalysisError for input problems and AIProviderError when the
    AI provider itself fails.
    """
    resume_text = validate_resume_text(resume_text)
    job_description = validate_job_description(job_description)

    provider = ai_service.get_provider()
    raw_result = provider.analyze(resume_text, job_description)

    if not isinstance(raw_result, dict):
        raise AIProviderError("The AI service returned an unexpected response.")

    return ai_service.normalise_analysis(raw_result)


def run_analysis_from_request(file_storage, job_description):
    """Convenience wrapper used by the Flask route.

    Raises AnalysisError (user-facing) or ResumeParseError (user-facing).
    """
    from services.resume_parser import extract_text_from_upload

    resume_text = extract_text_from_upload(file_storage)
    return analyze(resume_text, job_description)


__all__ = [
    "AnalysisError",
    "AIProviderError",
    "ResumeParseError",
    "analyze",
    "run_analysis_from_request",
    "validate_job_description",
    "validate_resume_text",
]