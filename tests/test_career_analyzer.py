"""Tests for the career analyzer: validation and analysis structure."""

import pytest

from services import ai_service
from services.career_analyzer import (
    AnalysisError,
    analyze,
    validate_job_description,
    validate_resume_text,
)

REQUIRED_FIELDS = [
    "fit_score",
    "matched_skills",
    "skill_gaps",
    "strengths",
    "improvement_areas",
    "action_plan",
    "next_steps",
]


# ------------------------------------------------------------------
# Job description validation
# ------------------------------------------------------------------
def test_empty_job_description_raises():
    with pytest.raises(AnalysisError):
        validate_job_description("")
    with pytest.raises(AnalysisError):
        validate_job_description("    \n  ")


def test_short_job_description_raises():
    with pytest.raises(AnalysisError):
        validate_job_description("machine learning")


def test_valid_job_description_is_trimmed(sample_job_description):
    result = validate_job_description("   " + sample_job_description + "  \n")
    assert result == sample_job_description.strip()


def test_empty_resume_text_raises():
    with pytest.raises(AnalysisError):
        validate_resume_text("  ")


# ------------------------------------------------------------------
# Analysis structure
# ------------------------------------------------------------------
def test_analysis_has_all_required_fields(sample_resume_text, sample_job_description):
    result = analyze(sample_resume_text, sample_job_description)

    for field in REQUIRED_FIELDS:
        assert field in result, "missing field: {}".format(field)

    assert isinstance(result["fit_score"], int)
    assert 0 <= result["fit_score"] <= 100

    for field in REQUIRED_FIELDS[1:]:
        assert isinstance(result[field], list)
        assert len(result[field]) > 0, "{} should not be empty".format(field)
        assert all(isinstance(item, str) for item in result[field])


def test_analysis_detects_matched_and_missing_skills(
    sample_resume_text, sample_job_description
):
    result = analyze(sample_resume_text, sample_job_description)

    matched_lower = [s.lower() for s in result["matched_skills"]]
    gaps_lower = [s.lower() for s in result["skill_gaps"]]

    assert "python" in matched_lower
    assert "sql" in matched_lower
    # Mentioned in the job description, absent from the resume.
    assert "aws" in gaps_lower
    assert "docker" in gaps_lower

    # No skill can be both matched and a gap.
    assert not (set(matched_lower) & set(gaps_lower))


def test_poor_match_scores_lower_than_strong_match():
    jd = "Kubernetes Terraform Docker AWS S3 DynamoDB " * 8
    strong = "Python SQL Machine Learning Pandas NumPy Flask " * 12

    strong_result = analyze(strong, jd)
    weak_result = analyze("Basketball player. Hobbies: football and music.", jd)

    assert strong_result["fit_score"] > weak_result["fit_score"]


def test_action_plan_is_ordered_and_practical(sample_resume_text, sample_job_description):
    result = analyze(sample_resume_text, sample_job_description)
    assert len(result["action_plan"]) >= 4
    assert len(result["next_steps"]) >= 3


# ------------------------------------------------------------------
# Response normalisation
# ------------------------------------------------------------------
def test_normalise_analysis_fills_defaults():
    normalised = ai_service.normalise_analysis({})
    assert normalised["fit_score"] == 0
    assert normalised["matched_skills"] == []
    assert normalised["strengths"] == []
    for field in REQUIRED_FIELDS:
        assert field in normalised


def test_normalise_analysis_clamps_score():
    assert ai_service.normalise_analysis({"fit_score": 999})["fit_score"] == 100
    assert ai_service.normalise_analysis({"fit_score": -20})["fit_score"] == 0
    assert ai_service.normalise_analysis({"fit_score": "72"})["fit_score"] == 72
    assert ai_service.normalise_analysis({"fit_score": "bad"})["fit_score"] == 0


def test_normalise_analysis_accepts_string_lists():
    normalised = ai_service.normalise_analysis(
        {"matched_skills": "Python\n- SQL\n- AWS", "next_steps": "Apply online"}
    )
    assert normalised["matched_skills"] == ["Python", "SQL", "AWS"]
    assert normalised["next_steps"] == ["Apply online"]


# ------------------------------------------------------------------
# Model response parsing
# ------------------------------------------------------------------
def test_parse_analysis_handles_json_fence():
    raw = '```json\n{"fit_score": 80, "matched_skills": ["Python"]}\n```'
    parsed = ai_service.parse_analysis(raw)
    assert parsed["fit_score"] == 80
    assert parsed["matched_skills"] == ["Python"]


def test_parse_analysis_handles_surrounding_prose():
    raw = 'Sure! Here is the analysis:\n{"fit_score": 55, "next_steps": ["Apply"]}\nHope this helps.'
    parsed = ai_service.parse_analysis(raw)
    assert parsed["fit_score"] == 55


def test_parse_analysis_rejects_non_json():
    with pytest.raises(ai_service.AIProviderError):
        ai_service.parse_analysis("I could not do that.")


def test_prompt_truncates_long_input():
    prompt = ai_service.build_prompt("a" * 10000, "b" * 10000, max_chars=100)
    assert "truncated" in prompt


def test_mock_provider_is_default_in_tests():
    assert ai_service.get_provider().__class__.__name__ == "MockProvider"