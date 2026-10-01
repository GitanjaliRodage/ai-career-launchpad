"""Isolated AI layer for AI Career Launchpad.

Two providers are supported:

* ``bedrock`` - Amazon Bedrock (Claude) using the default AWS credential chain.
* ``mock``    - deterministic local analysis so the whole UI flow can be tested
  without any AWS access. This is the default for local development.

The provider is chosen with the ``AI_PROVIDER`` environment variable.
Credentials are never hard-coded and never sent to the browser.
"""

import json
import os
import re

from config import Config


class AIProviderError(Exception):
    """Raised when the configured AI provider cannot produce an analysis."""


# --------------------------------------------------------------------------
# Provider selection
# --------------------------------------------------------------------------
def get_provider():
    """Return an AI provider instance based on configuration."""
    provider = Config.AI_PROVIDER
    if provider == "bedrock":
        return BedrockProvider()
    return MockProvider()


def provider_status():
    """Describe the active provider for the UI / health endpoint."""
    if Config.AI_PROVIDER == "bedrock":
        return {
            "provider": "bedrock",
            "model_id": Config.BEDROCK_MODEL_ID,
            "region": Config.AWS_REGION,
        }
    return {"provider": "mock", "model_id": "local-mock", "region": None}


# --------------------------------------------------------------------------
# Prompt
# --------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are a senior technical recruiter and career coach helping students "
    "and fresh graduates. You are precise, practical, and encouraging."
)

INSTRUCTION = """Analyse the candidate resume and the job description below.

Return ONLY valid JSON, no markdown fences and no extra commentary, using
exactly these keys:

{
  "fit_score": <integer 0-100>,
  "matched_skills": [<string>, ...],
  "skill_gaps": [<string>, ...],
  "strengths": [<string>, ...],
  "improvement_areas": [<string>, ...],
  "action_plan": [<string>, ...],
  "next_steps": [<string>, ...]
}

Rules:
- fit_score must be a realistic whole number between 0 and 100.
- matched_skills: skills the candidate demonstrably has that the job needs.
- skill_gaps: skills the job needs that the resume does not show.
- strengths: 3 to 5 short, specific professional observations.
- improvement_areas: 3 to 5 short, actionable observations.
- action_plan: 5 to 7 numbered-as-text practical steps, most impactful first.
- next_steps: 3 to 5 concrete actions the candidate can take this week.
- Keep every item under 160 characters. Write for a student audience.

JOB DESCRIPTION:
<<<JOB_DESCRIPTION>>>

RESUME:
<<<RESUME>>>
"""


def build_prompt(resume_text, job_description, max_chars=6000):
    """Build the user prompt, trimming long inputs to stay within limits.

    Uses explicit placeholder replacement rather than str.format() because the
    instruction template contains literal JSON braces.
    """
    prompt = INSTRUCTION.replace(
        "<<<RESUME>>>", _trim(resume_text, max_chars)
    )
    return prompt.replace(
        "<<<JOB_DESCRIPTION>>>", _trim(job_description, max_chars)
    )


def _trim(text, max_chars):
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n[...truncated...]"


# --------------------------------------------------------------------------
# Amazon Bedrock provider
# --------------------------------------------------------------------------
class BedrockProvider:
    """Calls Amazon Bedrock via the AWS SDK default credential chain."""

    def analyze(self, resume_text, job_description):
        try:
            import boto3
        except ImportError:
            raise AIProviderError(
                "boto3 is not installed. Run: pip install -r requirements.txt"
            )

        client = self._client(boto3)
        prompt = build_prompt(resume_text, job_description)

        try:
            response = client.converse(
                modelId=Config.BEDROCK_MODEL_ID,
                system=[{"text": SYSTEM_PROMPT}],
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={
                    "maxTokens": Config.BEDROCK_MAX_TOKENS,
                    "temperature": Config.BEDROCK_TEMPERATURE,
                },
            )
            raw_text = response["output"]["message"]["content"][0]["text"]
        except AIProviderError:
            raise
        except Exception as exc:
            raise AIProviderError(_friendly_bedrock_error(exc))

        return parse_analysis(raw_text)

    def _client(self, boto3):
        """Build a Bedrock Runtime client using the default credential chain."""
        session_kwargs = {"region_name": Config.AWS_REGION}
        # Only pass static keys when explicitly provided; otherwise the SDK
        # falls back to environment, profile, or instance/task credentials.
        if Config.AWS_ACCESS_KEY_ID and Config.AWS_SECRET_ACCESS_KEY:
            session_kwargs["aws_access_key_id"] = Config.AWS_ACCESS_KEY_ID
            session_kwargs["aws_secret_access_key"] = Config.AWS_SECRET_ACCESS_KEY
            if Config.AWS_SESSION_TOKEN:
                session_kwargs["aws_session_token"] = Config.AWS_SESSION_TOKEN

        try:
            return boto3.session.Session().client("bedrock-runtime", **session_kwargs)
        except Exception as exc:
            raise AIProviderError(_friendly_bedrock_error(exc))


def _friendly_bedrock_error(exc):
    """Map SDK errors to a message that is safe to show a user."""
    name = type(exc).__name__
    text = str(exc)
    if "AccessDenied" in text or name == "AccessDeniedException":
        return (
            "Amazon Bedrock denied access to this model. Check that model access "
            "is enabled in the Bedrock console for this region."
        )
    if "ValidationException" in text or name == "ValidationException":
        return "Amazon Bedrock rejected the request. Check the model ID."
    if "ThrottlingException" in text or name == "ThrottlingException":
        return "The AI service is busy right now. Please try again in a moment."
    if "credentials" in text.lower() or "CredentialRetrievalError" in text:
        return (
            "No valid AWS credentials were found. Configure the AWS credential "
            "chain or set AI_PROVIDER=mock for local development."
        )
    if os.environ.get("FLASK_DEBUG"):
        return "{}: {}".format(name, text)
    return "The AI service is temporarily unavailable. Please try again."


# --------------------------------------------------------------------------
# Mock provider (local development / offline demos)
# --------------------------------------------------------------------------
class MockProvider:
    """Deterministic local analysis used when Bedrock is not configured."""

    SKILL_LIBRARY = {
        "python": "Python",
        "java": "Java",
        "javascript": "JavaScript",
        "typescript": "TypeScript",
        "sql": "SQL",
        "nosql": "NoSQL",
        "mongodb": "MongoDB",
        "react": "React",
        "angular": "Angular",
        "vue": "Vue",
        "node": "Node.js",
        "nodejs": "Node.js",
        "express": "Express",
        "flask": "Flask",
        "django": "Django",
        "html": "HTML",
        "css": "CSS",
        "tailwind": "Tailwind CSS",
        "machine learning": "Machine Learning",
        "ml": "Machine Learning",
        "deep learning": "Deep Learning",
        "tensorflow": "TensorFlow",
        "pytorch": "PyTorch",
        "pandas": "Pandas",
        "numpy": "NumPy",
        "scikit-learn": "scikit-learn",
        "nlp": "NLP",
        "computer vision": "Computer Vision",
        "aws": "AWS",
        "lambda": "AWS Lambda",
        "s3": "Amazon S3",
        "dynamodb": "DynamoDB",
        "ec2": "Amazon EC2",
        "bedrock": "Amazon Bedrock",
        "sagemaker": "Amazon SageMaker",
        "docker": "Docker",
        "kubernetes": "Kubernetes",
        "terraform": "Terraform",
        "ci/cd": "CI/CD",
        "cicd": "CI/CD",
        "git": "Git",
        "github": "GitHub",
        "linux": "Linux",
        "rest": "REST APIs",
        "graphql": "GraphQL",
        "redis": "Redis",
        "postgres": "PostgreSQL",
        "postgresql": "PostgreSQL",
        "mysql": "MySQL",
        "spark": "Apache Spark",
        "hadoop": "Hadoop",
        "etl": "ETL",
        "power bi": "Power BI",
        "tableau": "Tableau",
        "excel": "Excel",
        "communication": "Communication",
        "leadership": "Leadership",
        "teamwork": "Teamwork",
        "testing": "Testing",
        "pytest": "Testing",
    }

    def analyze(self, resume_text, job_description):
        resume_skills = self._extract_skills(resume_text)
        job_skills = self._extract_skills(job_description)

        matched = [s for s in resume_skills if s in job_skills]
        gaps = [s for s in job_skills if s not in resume_skills]

        if job_skills:
            skill_ratio = len(matched) / float(len(job_skills))
        else:
            skill_ratio = 0.0

        keywords = self._keywords(job_description)
        keyword_hits = sum(1 for k in keywords if k in (resume_text or "").lower())
        keyword_ratio = (keyword_hits / float(len(keywords))) if keywords else 0.0

        resume_size = min(len(resume_text or "") / 1500.0, 1.0)

        score = int(
            round(
                max(
                    0,
                    min(
                        100,
                        (0.60 * skill_ratio + 0.25 * keyword_ratio + 0.15 * resume_size)
                        * 100,
                    ),
                )
            )
        )

        strengths = self._strengths(matched, keyword_hits, score)
        improvement_areas = self._improvement_areas(gaps, score)
        action_plan = self._action_plan(gaps, matched)
        next_steps = self._next_steps(gaps, matched, keyword_hits)

        return {
            "fit_score": score,
            "matched_skills": matched[:12],
            "skill_gaps": gaps[:12],
            "strengths": strengths,
            "improvement_areas": improvement_areas,
            "action_plan": action_plan,
            "next_steps": next_steps,
            "provider": "mock",
        }

    def _extract_skills(self, text):
        lowered = (text or "").lower()
        found = []
        for needle, label in self.SKILL_LIBRARY.items():
            if re.search(r"(?<![a-z0-9])" + re.escape(needle) + r"(?![a-z0-9])", lowered):
                if label not in found:
                    found.append(label)
        return found

    def _keywords(self, job_description):
        stopwords = {
            "and", "the", "with", "for", "our", "you", "your", "will", "have", "has",
            "are", "who", "that", "this", "from", "work", "team", "teams", "role",
            "job", "position", "candidate", "candidates", "experience", "workforce",
            "years", "year", "including", "such", "other", "ability", "strong",
            "excellent", "good", "great", "new", "using", "use", "used", "help",
            "helps", "helpping", "across", "within", "etc", "plus", "must", "should",
            "required", "requirements", "responsibilities", "about", "we", "us",
        }
        words = re.findall(r"[a-z][a-z+#]{2,}", (job_description or "").lower())
        seen = []
        for word in words:
            if word in stopwords or word in seen:
                continue
            seen.append(word)
            if len(seen) >= 25:
                break
        return seen

    def _strengths(self, matched, keyword_hits, score):
        items = []
        if matched:
            items.append(
                "Strong overlap with the role on {} of the required skills.".format(
                    ", ".join(matched[:4])
                )
            )
        if keyword_hits >= 3:
            items.append(
                "Your resume already references {} key terms from this job "
                "description, which helps with keyword screening.".format(keyword_hits)
            )
        if score >= 60:
            items.append(
                "You meet the core technical baseline for this role and can be "
                "credible in a screening conversation."
            )
        if not items:
            items.append(
                "You have relevant education or project experience that can be "
                "reframed toward this role."
            )
        items.append(
            "Showing initiative through projects or internships is your fastest "
            "way to stand out among early-career applicants."
        )
        return items[:4]

    def _improvement_areas(self, gaps, score):
        items = []
        if gaps:
            items.append(
                "Add hands-on evidence for the missing skills: {}, among others."
                .format(", ".join(gaps[:4]))
            )
        else:
            items.append(
                "Deepen the skills you already have by building one project that "
                "shows real-world depth."
            )
        if score < 50:
            items.append(
                "Your resume currently reads broadly. Tailor the summary and "
                "bullet points to mirror the exact language in this job description."
            )
        items.append(
            "Quantify results (numbers, scale, users, time saved) instead of only "
            "listing responsibilities."
        )
        items.append(
            "Your action plan should be time-boxed so recruiters can see "
            "consistency, not just intent."
        )
        return items[:4]

    def _action_plan(self, gaps, matched):
        plan = []
        if gaps:
            plan.append(
                "Week 1 - Close the highest-demand gap: {}.".format(gaps[0])
            )
        elif matched:
            plan.append(
                "Week 1 - Go deeper on {} and document the impact you created."
                .format(matched[0])
            )
        else:
            plan.append(
                "Week 1 - Build a small, complete project that matches the core "
                "requirements in this job description."
            )
        if len(gaps) > 1:
            plan.append(
                "Week 2 - Start learning {} with a tutorial plus one hands-on "
                "exercise.".format(gaps[1])
            )
        if len(gaps) > 2:
            plan.append("Week 3 - Practise {} in a deployed mini-project.".format(gaps[2]))
        plan.append(
            "Week 4 - Rewrite your resume so the top third mirrors the job "
            "description keywords."
        )
        plan.append(
            "Week 5 - Publish the project on GitHub with a clear README so "
            "recruiters can run it."
        )
        plan.append(
            "Week 6 - Prepare and mock three technical interviews using this "
            "job description as the prompt."
        )
        return plan[:7]

    def _next_steps(self, gaps, matched, keyword_hits):
        steps = [
            "Apply to 5 targeted roles this week using the tailored resume.",
            "Ask a mentor or classmate to review your resume in 10 minutes.",
            "Track every application and follow up after 5 business days.",
        ]
        if gaps:
            steps.append(
                "Enrol in one free course for {} and set a completion date."
                .format(gaps[0])
            )
        if matched:
            steps.append(
                "Turn your strongest {} experience into a 60-second interview "
                "story.".format(matched[0])
            )
        return steps[:5]


# --------------------------------------------------------------------------
# Response normalisation
# --------------------------------------------------------------------------
def parse_analysis(raw_text):
    """Turn a model response into the validated analysis structure."""
    payload = _extract_json(raw_text)
    if not isinstance(payload, dict):
        raise AIProviderError("The AI response could not be understood.")

    analysis = {
        "fit_score": _coerce_score(payload.get("fit_score")),
        "matched_skills": _coerce_list(payload.get("matched_skills")),
        "skill_gaps": _coerce_list(payload.get("skill_gaps")),
        "strengths": _coerce_list(payload.get("strengths")),
        "improvement_areas": _coerce_list(payload.get("improvement_areas")),
        "action_plan": _coerce_list(payload.get("action_plan")),
        "next_steps": _coerce_list(payload.get("next_steps")),
        "provider": Config.AI_PROVIDER,
    }
    return normalise_analysis(analysis)


def _extract_json(raw_text):
    if not raw_text:
        raise AIProviderError("The AI returned an empty response.")
    text = raw_text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except ValueError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise AIProviderError("The AI response was not valid JSON.")
    try:
        return json.loads(text[start : end + 1])
    except ValueError:
        raise AIProviderError("The AI response was not valid JSON.")


def _coerce_score(value):
    try:
        score = int(round(float(value)))
    except (TypeError, ValueError):
        score = 0
    return max(0, min(100, score))


def _coerce_list(value):
    if isinstance(value, str):
        parts = [p.strip(" -\u2022\t") for p in value.splitlines()]
        return [p for p in parts if p]
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def normalise_analysis(analysis):
    """Guarantee every documented field exists with the right type."""
    if not isinstance(analysis, dict):
        raise AIProviderError("The AI response could not be understood.")

    result = {
        "fit_score": _coerce_score(analysis.get("fit_score")),
        "matched_skills": _coerce_list(analysis.get("matched_skills")),
        "skill_gaps": _coerce_list(analysis.get("skill_gaps")),
        "strengths": _coerce_list(analysis.get("strengths")),
        "improvement_areas": _coerce_list(analysis.get("improvement_areas")),
        "action_plan": _coerce_list(analysis.get("action_plan")),
        "next_steps": _coerce_list(analysis.get("next_steps")),
        "provider": analysis.get("provider", Config.AI_PROVIDER),
    }
    return result