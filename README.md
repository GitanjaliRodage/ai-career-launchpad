AI Career Launchpad

An AI-powered career assistant for students and fresh graduates. Upload a resume,
paste a job description, and get a structured career-fit analysis: a score, matched
skills, skill gaps, strengths, improvement areas, and a personalised action plan.

Built for the **AWS Zero to Shipped Hackathon 2026**.

---

## Table of contents

1. [Project overview](#1-project-overview)
2. [Features](#2-features)
3. [Architecture](#3-architecture)
4. [Folder structure](#4-folder-structure)
5. [Local setup](#5-local-setup)
6. [Environment variables](#6-environment-variables)
7. [Running the application](#7-running-the-application)
8. [Testing](#8-testing)
9. [Amazon Bedrock configuration](#9-amazon-bedrock-configuration)
10. [AWS deployment plan](#10-aws-deployment-plan)
11. [How a coding agent assisted](#11-how-a-coding-agent-assisted)
12. [Development record](#12-development-record)
13. [Security notes](#13-security-notes)

---

## 1. Project overview

Most career advice tools are built for experienced professionals. This one is built
for students and freshers who need a fast, honest read on whether they are ready for
a specific role and, if not, exactly what to do next.

The core flow is:

```
Landing page -> Upload resume (PDF) -> Paste job description
             -> Analyse My Career Fit -> Results dashboard
```

The backend always returns a **structured** analysis object, never free-form prose,
so the dashboard can render each section predictably:

```json
{
  "fit_score": 72,
  "matched_skills": ["Python", "SQL", "Machine Learning"],
  "skill_gaps": ["AWS", "Docker", "React"],
  "strengths": ["..."],
  "improvement_areas": ["..."],
  "action_plan": ["..."],
  "next_steps": ["..."],
  "provider": "bedrock",
  "summary": "..."
}
```

---

## 2. Features

- **Resume upload (PDF)** with file-type and size validation. Files are stored under a
  random name and deleted immediately after extraction.
- **Job description input** with a minimum-length check and a live character counter.
- **Career fit score** from 0-100 rendered as a visual ring.
- **Matched skills** and **skill gaps** as clear, colour-coded chips.
- **Strengths** and **improvement areas** as short AI-written explanations.
- **Personalised action plan** as an ordered, week-by-week list.
- **Next steps** the student can take immediately.
- **Loading state** with rotating progress messages while analysis runs.
- **Client-side and server-side validation** with readable error messages.
- **Two AI providers**: Amazon Bedrock for production, a deterministic mock for local
  development and demos.
- **Responsive, accessible UI** that works on phone, tablet, and desktop.
- **Health endpoint** (`/api/health`) for smoke tests and load balancers.

---

## 3. Architecture

```
Browser
  |  GET  /                  -> landing page + form
  |  POST /api/analyze       -> resume (PDF) + job_description
  v
Flask app (app.py)
  |  validates input
  |  never exposes internal errors
  v
services/
  resume_parser.py   -> validate + extract text from PDF (pypdf)
  career_analyzer.py -> validate job description, orchestrate, normalise
  ai_service.py      -> BedrockProvider | MockProvider + JSON parsing
  v
Amazon Bedrock (Claude)   OR   MockProvider (offline)
```

Design decisions worth knowing:

- **The AI layer is isolated.** Swapping or replacing the model means editing only
  `services/ai_service.py`. Nothing else in the app imports `boto3`.
- **Credentials are never in code or in the frontend.** The app uses the standard AWS
  credential chain (env vars, shared profile, or IAM role on the compute resource).
- **Resumes are never retained.** Text is extracted in memory and the temp file is
  deleted in a `finally` block.
- **Two providers, one contract.** Both return the same normalised structure, so the
  frontend does not change between local and production.

---

## 4. Folder structure

```
.
├── app.py                     # Flask app and routes
├── config.py                  # Environment-based configuration
├── requirements.txt           # Python dependencies
├── .env.example               # Template for local environment variables
├── .gitignore                 # Keeps secrets and local files out of Git
├── README.md
├── templates/
│   └── index.html             # Landing page + form + dashboard
├── static/
│   ├── style.css              # Design system and responsive layout
│   └── script.js              # Form handling, API call, result rendering
├── services/
│   ├── __init__.py
│   ├── ai_service.py          # Bedrock + mock providers, JSON parsing
│   ├── resume_parser.py       # PDF validation and text extraction
│   └── career_analyzer.py     # Validation and orchestration
├── tests/
│   ├── conftest.py            # Fixtures, sample PDF generator
│   ├── test_resume_parser.py  # Extraction and upload security
│   ├── test_career_analyzer.py# Validation and response structure
│   └── test_app.py            # Routes and error handling
├── tools/
│   └── smoke_test.py          # End-to-end check against a running server
└── uploads/                   # Private temp folder, never served, git-ignored
```

---

## 5. Local setup

Prerequisites: **Python 3.10 or newer** and **Git**.

```bash
git clone <your-github-repo-url>
cd ai-career-launchpad

python -m venv .venv
```

Activate the virtual environment:

```bash
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create your local config:

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

No changes are needed to run locally. `AI_PROVIDER=mock` is the default.

---

## 6. Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `SECRET_KEY` | dev placeholder | Flask session signing. Set a random value in production. |
| `FLASK_DEBUG` | `0` | Set to `1` locally only. Never in production. |
| `MAX_UPLOAD_MB` | `5` | Maximum resume size in megabytes. |
| `AI_PROVIDER` | `mock` | `mock` or `bedrock`. |
| `AWS_REGION` | `us-east-1` | Region for Bedrock. |
| `BEDROCK_MODEL_ID` | `anthropic.claude-3-5-sonnet-20240620-v1:0` | Model to call. |
| `BEDROCK_MAX_TOKENS` | `2000` | Max tokens for the response. |
| `BEDROCK_TEMPERATURE` | `0.2` | Lower is more consistent. |
| `AWS_ACCESS_KEY_ID` | empty | Leave blank. Use an IAM role in AWS. |
| `AWS_SECRET_ACCESS_KEY` | empty | Leave blank. Use an IAM role in AWS. |
| `AWS_SESSION_TOKEN` | empty | Only for temporary credentials. |

Generate a strong secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 7. Running the application

```bash
python app.py
```

Then open <http://127.0.0.1:5000>.

To try the analysis flow without AWS access, keep `AI_PROVIDER=mock` and paste any
real job description along with a text-based PDF resume.

Verify a running server end to end:

```bash
python tools/smoke_test.py
```

---

## 8. Testing

```bash
pytest -q
```

Current result: **36 tests passing**.

Coverage areas:

| Area | What is tested |
| --- | --- |
| Resume extraction | Valid PDF text extraction, corrupt files, missing files, too-short text |
| Upload security | Non-PDF rejected, empty file rejected, random filenames, files deleted after use |
| Job description validation | Empty input, whitespace-only input, too-short input, trimming |
| Analysis structure | All required fields present, correct types, score range, matched vs. gap separation |
| Model response parsing | JSON fences, surrounding prose, malformed JSON, truncation |
| Routes | Home page, health, robots.txt, analyze happy path |
| Error handling | Missing resume, missing job description, wrong file type, oversized upload, 404, 405 |

---

## 9. Amazon Bedrock configuration

### Step 1 - Enable model access

1. Open the **Amazon Bedrock** console in the region you plan to use.
2. In **Model access**, request access for the model in your `BEDROCK_MODEL_ID`.
3. Confirm the status is **Granted**. Access is granted per account per region.

### Step 2 - Point the app at Bedrock

```bash
AI_PROVIDER=bedrock
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20240620-v1:0
```

### Step 3 - Provide credentials

For local testing, the simplest approach is the AWS CLI credential chain:

```bash
aws configure
```

Or export temporary credentials in your shell. Do not put keys in `.env` if you can
avoid it. For AWS deployments, do not set keys at all: attach an IAM role instead.

### Step 4 - Required IAM permissions

The role only needs model invocation. A minimal policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "bedrock:InvokeModel",
      "Resource": "arn:aws:bedrock:*:*:inference-profile/*"
    }
  ]
}
```

### Step 5 - Verify

```bash
curl http://127.0.0.1:5000/api/health
```

`ai.provider` should read `bedrock` and `ai.region` should show your region.

### Switching back to local development

```bash
AI_PROVIDER=mock
```

---

## 10. AWS deployment plan

**Recommended: AWS App Runner + Amazon Bedrock.** It is the shortest path from this
repository to a public HTTPS URL.

| AWS service | Role |
| --- | --- |
| **AWS App Runner** | Runs the containerised Flask app behind an HTTPS endpoint. |
| **Amazon Bedrock** | Generates the career analysis. |
| **Amazon ECR** | Stores the container image built from GitHub. |
| **AWS IAM** | Supplies credentials to the running service. No static keys. |
| **Amazon CloudWatch** | Application logs and basic metrics. |
| **AWS Secrets Manager** *(optional)* | Stores `SECRET_KEY` and other config. |

### Step-by-step

**1. Enable Bedrock model access** as described in section 9.

**2. Create an ECR repository**

```bash
aws ecr create-repository --repository-name ai-career-launchpad
```

**3. Build and push the image**

```bash
aws ecr get-login-password --region us-east-1 \
  | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com

docker build -t ai-career-launchpad .
docker push ai-career-launchpad:latest
```

**4. Create an App Runner service**

```bash
aws apprunner create-service \
  --service-name ai-career-launchpad \
  --source-configuration \
    "ImageRepository={ImageRepository=<account>.dkr.ecr.<region>.amazonaws.com/ai-career-launchpad,ImageConfigurationType=PORT},Port=8080" \
  --instance-configuration "Cpu=1,Memory=2G" \
  --auto-deployment-configuration "AutoDeploymentsEnabled=false"
```

**5. Set environment variables on the service**

| Key | Value |
| --- | --- |
| `AI_PROVIDER` | `bedrock` |
| `AWS_REGION` | your region |
| `BEDROCK_MODEL_ID` | your model |
| `SECRET_KEY` | a random 64-character hex string |
| `FLASK_DEBUG` | `0` |

**6. Attach the IAM role** that allows `bedrock:InvokeModel`.

**7. Wait for the deployment URL**, then confirm it works:

```bash
curl -fsSL <your-url>/api/health
```

Expected response:

```json
{"status":"ok","service":"ai-career-launchpad","ai":{"provider":"bedrock", ...}}
```

### Alternative and manual options

- **AWS Elastic Beanstalk** - more control, more configuration, same Bedrock backend.
- **Amazon ECS on Fargate** - best if you want autoscaling and VPC placement.
- **AWS Lambda + AWS Lambda Web Adapter** - lowest running cost, cold starts are the
  main tradeoff for an interactive analysis tool.

### Testing the deployed application

```bash
# Health
curl -fsSL https://<your-url>/api/health

# Full flow against production
BASE_URL=https://<your-url> python tools/smoke_test.py
```

Record the live URL below once deployed.

**Public application URL:** _not deployed yet_

---

## 11. How a coding agent assisted

An AI coding agent (OpenCode) was used throughout. Documented honestly, the work
split into these phases:

| Phase | Agent contribution |
| --- | --- |
| Repository inspection | Confirmed the target folder was empty and unlinked from any existing project, so no legacy code was carried over. |
| Architecture | Chose a flat Flask structure with an isolated `services/` layer so the AI provider could be swapped without touching routes or UI. |
| Implementation | Wrote `app.py`, `config.py`, the three service modules, the full frontend (HTML/CSS/JS), and the test suite. |
| Debugging | Ran the suite, read the tracebacks, and found two genuine bugs: `str.format()` choking on the literal JSON braces in the Bedrock prompt template, and Flask error handlers whose parameter names shadowed the module-level `_error()` helper, causing infinite recursion. Also fixed filename handling for non-Werkzeug upload objects and PDF fixture text length. |
| Documentation | Generated this README, `.env.example`, and `.gitignore`. |
| Deployment prep | Wrote `tools/smoke_test.py` for verifying the live endpoint after deploy. |

The agent did not deploy to AWS and did not push to GitHub. Those steps require
your credentials and were left for you.

---

## 12. Development record

Only steps actually performed are recorded.

### Project idea

Give students and freshers a fast, honest answer to one question: *am I ready for
this job, and if not, what do I do about it this week?*

### Development stages

| Stage | Status | Notes |
| --- | --- | --- |
| 1. Environment check | Done | Confirmed empty folder, Python 3.14, no Git repo. |
| 2. Project scaffold | Done | Structure, `requirements.txt`, `.env.example`, `.gitignore`. |
| 3. Backend | Done | Flask app, config, resume parser, analyzer, dual AI providers. |
| 4. Frontend | Done | Landing page, upload area, job description input, dashboard, responsive CSS. |
| 5. Tests | Done | 36 tests passing across parser, analyzer, routes, error handling. |
| 6. Local verification | Done | Server started, health checked, full flow verified, smoke test passed. |
| 7. Git init and commit | Done | Initial commit created in this folder. |
| 8. GitHub remote | **Needs you** | Repository must be created and pushed manually. See below. |
| 9. AWS deployment | Not started | Requires Bedrock model access and an AWS account. |
| 10. Public URL | Not started | Recorded once deployed. |

### AWS services used

Locally: none. The app runs fully offline in mock mode.

Planned for deployment: **Amazon Bedrock**, **AWS App Runner**, **Amazon ECR**,
**AWS IAM**, **Amazon CloudWatch**.

### GitHub repository

- **Name:** `ai-career-launchpad`
- **Remote:** not yet connected (needs your GitHub account)

### Deployment process

1. Enable model access in the Bedrock console.
2. Build the container image and push it to ECR.
3. Create the App Runner service from that image.
4. Set `AI_PROVIDER=bedrock` and the AWS settings as environment variables.
5. Attach an IAM role permitting `bedrock:InvokeModel`.
6. Verify with `curl <url>/api/health`, then `BASE_URL=<url> python tools/smoke_test.py`.
7. Paste the live URL into the two placeholders in this README.

### Final public application URL

_To be added after deployment._

---

## 13. Security notes

- **No secrets in code.** All configuration comes from environment variables.
- **No secrets in the browser.** The frontend only calls `/api/analyze`. AWS
  credentials never leave the server.
- **`.env` is git-ignored.** `.env.example` contains only blank placeholders.
- **Uploads are private.** `uploads/` sits outside `static/` and is never served. Files
  are renamed with a UUID and deleted right after extraction.
- **Uploads are validated.** PDF extension only, size capped by `MAX_UPLOAD_MB`, empty
  files rejected.
- **Internal errors are never shown.** SDK and parser failures are converted into
  user-friendly messages; details stay in server logs.
- **The AI response is parsed defensively.** Malformed JSON or out-of-range scores are
  normalised rather than passed through to the UI.