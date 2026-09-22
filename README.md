# AI Code Review Platform

An AI-powered code review platform that analyzes Python GitHub repositories, detects code-quality and security issues, and generates contextual AI explanations and suggested fixes.

The platform combines **AST-based static analysis**, a **FastAPI backend**, an interactive **React dashboard**, automated testing, and **AI-powered code review**.

---

## Overview

AI Code Review Platform allows developers to submit the URL of a public GitHub repository and automatically analyze its Python codebase.

The platform clones the repository, discovers Python files, parses the source code using Python's Abstract Syntax Tree (AST), detects potential code-quality and security issues, assigns severity levels, calculates a repository health score, and displays the results through an interactive web dashboard.

For individual findings, developers can request an AI-powered review that uses the relevant source-code context to explain the issue, describe its risk, recommend an improvement, and suggest a possible code fix.

---

## Demo

### Live Demo

Try the deployed application:

https://ai-code-review-platform-hvhx.onrender.com

The live demo includes repository analysis and code diff review. The backend is hosted on Render's free tier, so the first request after a period of inactivity may take a few seconds while the service starts.

### API Documentation

https://ai-code-review-platform-rpg9.onrender.com/docs

### Repository Analysis Dashboard

![Repository Analysis Dashboard](screenshots/dashboard.png)

### File & Issue Explorer

![File and Issue Explorer](screenshots/issue-explorer.png)

### AI-Powered Code Review

![AI Code Review](screenshots/ai-review.png)

---

## Features

### Repository Analysis

- Clone and analyze public GitHub repositories
- Automatically discover Python source files
- Parse Python code using the built-in AST module
- Extract functions, classes, methods, and imports
- Analyze an entire repository through a REST API
- Remove temporary cloned repositories after analysis

### Static Code Analysis

The analyzer currently detects:

- Bare `except` blocks
- Silent exception handling
- Debugging `print()` statements
- Dangerous `eval()` usage
- Dangerous `exec()` usage
- `subprocess` calls using `shell=True`
- Potential hard-coded secrets

Each detected issue includes:

- Rule name
- Severity
- Severity score
- Line number
- Description
- Relevant source-code context

### Code Diff Review

Select **Code Diff Review** in the dashboard, enter a Python filename, and paste
the complete **Before** and **After** source. Click **Review Code Diff** to inspect
findings with the same severity filters, source context, and optional AI reviews.
The UI reviews one file at a time; the API accepts up to 20 files.

- An empty Before represents a new file; an empty After represents a deletion.
- Added and replaced lines use one-based line numbers in the updated file.
- Unchanged findings are excluded, including when insertions shift their lines.
- Deleted lines, unchanged files, and non-Python files are skipped with a reason.
- Invalid updated Python is reported per file; other files can still be reviewed.
- The changed-code score uses the existing penalties on the filtered findings.
  It is `null` if nothing was analyzed or any Python file failed to parse.

**Scope:** this is a line-scoped review, not a comparison of before/after findings.
A finding is included only when its AST start line was added or replaced. Editing
an existing problematic line can report it again. Changes later in a multiline
call, or inside an exception handler whose header is unchanged, can be missed.
Moved code can be reported as added. Line-ending and final-newline-only changes
are ignored. No claims are made about resolved issues or whole-repository health.

The implementation uses `difflib.SequenceMatcher` to identify changed lines,
parses the complete updated source through the existing AST rules, then filters
the findings. Source stays in memory and is never executed or written to a path
supplied by the client. Static review needs neither GitHub access nor an AI key.
Future GitHub PR integration can fetch base/head file contents and pass them to
this same service; authentication, patch ingestion, and PR comments are deferred.

### Repository Health Score

The platform calculates a repository health score from **0 to 100** based on detected issues and their severity.

This provides a quick repository-level indication of code quality and potential risk.

> The health score is a heuristic designed to summarize analyzer findings and should not be interpreted as a formal security rating.

### AI-Powered Code Review

Each detected issue can be reviewed individually using AI.

The AI receives the issue metadata together with a small section of relevant source code and generates:

- **Explanation** — why the issue matters
- **Risk** — the potential impact
- **Recommendation** — how the code can be improved
- **Suggested Fix** — an example of corrected code

AI reviews are generated only when explicitly requested by the user.

Use the **Include AI review** checkbox to enhance up to three high/medium
findings during repository analysis, or use an issue's **AI Review** button.
Static analysis remains the default and works without an API key. Enrichment
never changes rule results, severities, or health scores. If OpenAI is unavailable,
the repository response still succeeds with static findings and a visible warning.
The batch stops after the first failure; individual findings can be retried later.

The backend uses the Responses API with a strict JSON schema and validates the
result with Pydantic. Malformed, refused, or incomplete output is not displayed.
Each SDK request has a 20-second timeout, no automatic retries, a 2,000-token
output limit, and at most 12,000 characters of source context. Responses are
requested with `store=False`. See the official
[Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs).

### Interactive Dashboard

The React frontend provides:

- GitHub repository analysis form
- Repository health score
- Python file count
- Total detected issue count
- High, medium, and low severity summaries
- Top 10 issues ranked by severity, with shortcuts to the file explorer
- File and issue explorer
- Severity filtering
- Source-code context display
- On-demand AI reviews
- AI-generated fix suggestions
- Loading and error states

---

## Tech Stack

### Backend

- **Python 3.12**
- **FastAPI**
- **Python AST**
- **Pydantic**
- **OpenAI API**
- **Pytest**
- **Git**
- **Uvicorn**

### Frontend

- **React**
- **Vite**
- **JavaScript**
- **CSS**

---

## Architecture

```text
                 GitHub Repository
                        |
                        v
                 Repository Clone
                        |
                        v
              Python File Discovery
                        |
                        v
                AST Static Analysis
                        |
             +----------+----------+
             |                     |
             v                     v
      Structure Extraction    Issue Detection
             |                     |
             |              Severity Classification
             |                     |
             |              Code Context Extraction
             |                     |
             +----------+----------+
                        |
                        v
                 FastAPI Backend
                        |
              +---------+---------+
              |                   |
              v                   v
       Health Score        React Dashboard
                                  |
                                  v
                         File / Issue Explorer
                                  |
                                  v
                           AI Review Request
                                  |
                                  v
                            OpenAI API
                                  |
                                  v
                     Explanation + Risk +
                  Recommendation + Suggested Fix
```

---

## Project Structure

```text
ai-code-review-platform/
├── backend/
│   ├── __init__.py
│   ├── ai_reviewer.py
│   ├── analyzer.py
│   ├── diff_analyzer.py
│   ├── main.py
│   ├── models.py
│   └── repository.py
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── assets/
│   │   ├── App.css
│   │   ├── App.jsx
│   │   ├── api.js
│   │   ├── api.test.js
│   │   ├── index.css
│   │   └── main.jsx
│   ├── .env.example
│   ├── package.json
│   └── vite.config.js
│
├── tests/
│   ├── test_api.py
│   ├── conftest.py
│   ├── test_ai_reviewer.py
│   ├── test_repository.py
│   ├── test_diff_analyzer.py
│   └── test_analyzer.py
│
├── screenshots/
│   ├── dashboard.png
│   ├── issue-explorer.png
│   └── ai-review.png
│
├── .gitignore
├── .env.example
├── requirements.txt
└── README.md
```

---

## API

FastAPI automatically provides interactive API documentation through Swagger UI.

When the backend is running:

```text
http://127.0.0.1:8000/docs
```

### Health Check

```http
GET /
```

Example response:

```json
{
  "message": "AI Code Review Platform is running"
}
```

---

### Analyze Repository

```http
POST /analyze
```

Example request:

```json
{
  "repo_url": "https://github.com/psf/requests",
  "include_ai_review": false
}
```

The endpoint:

1. Clones the repository
2. Discovers Python files
3. Parses the files using AST
4. Extracts code structure
5. Detects potential issues
6. Assigns severity and scores
7. Extracts relevant code context
8. Calculates the repository health score
9. Returns structured analysis results
10. Removes the temporary repository

Set `include_ai_review` to `true` to request AI enhancement of up to three
high/medium findings. Enriched findings include `ai_review` in both `files`
and `top_issues`; failures include a safe `ai_error` and a response-level warning.
Responses also include `warnings` and `skipped_files`. No Python files, or
unparseable Python files that make a review incomplete, produce a `null` health
score rather than a misleading healthy score.

Repository URLs must be `https://github.com/owner/repository` (an optional `.git`
suffix or trailing slash is accepted). Credentials, query strings, fragments,
custom ports, subpaths, other hosts, and non-HTTPS schemes are rejected.

Expected errors: **422** invalid input, **413** repository/source size limit,
**502** clone failure (including private/nonexistent repositories), **504** clone
timeout. Git cannot reliably distinguish a nonexistent repository from a private
one without authentication, so both receive the same safe explanation.
Unexpected failures return **500** with a generic message; Git stderr, local
paths, API keys, and stack traces are not sent to the frontend. `/ai-review`
returns **503** when AI is unavailable; existing static results remain usable.

Example response structure:

```json
{
  "repository": "https://github.com/psf/requests",
  "python_files_count": 37,
  "analyzed_files_count": 37,
  "health_score": 35,
  "summary": {
    "total_issues": 15,
    "severity_counts": {
      "high": 1,
      "medium": 9,
      "low": 5
    }
  },
  "top_issues": [],
  "files": []
}
```

---

### Analyze Code Diff

```http
POST /analyze-diff
```

Example request:

```json
{
  "files": [
    {
      "file": "app.py",
      "before": "x = 1\n",
      "after": "x = 1\nprint(x)\n"
    }
  ]
}
```

The response includes `analysis_type: "diff"`, `python_files_count`,
`analyzed_files_count`, `health_score`, `summary`, `top_issues`, and `files`.
Each file contains `file`, `changed_lines`, `issues`, and a `status` of
`analyzed`, `skipped`, or `error`; skipped/error files include a `reason`.
In this example, `changed_lines` is `[2]`, the print finding is at line 2,
and the changed-code score is 98.

Both source strings are required, but may be empty. Limits: 20 files,
100,000 characters per source snapshot, and 500 characters per filename.
Blank or duplicate filenames and invalid payloads return HTTP 422.
Per-file syntax errors return HTTP 200 with an explicit error status so that
valid files in the same request still produce results. Filenames are labels,
not server filesystem paths. Full snapshots are required; unified patches and
GitHub PR URLs are not accepted by this endpoint yet.

### AI Review

```http
POST /ai-review
```

Example request:

```json
{
  "rule": "silent-exception",
  "severity": "medium",
  "line": 43,
  "message": "Exception is silently ignored. Verify that this behavior is intentional.",
  "code_context": "try:\n    load_module()\nexcept ImportError:\n    pass"
}
```

Example response structure:

```json
{
  "issue": {
    "rule": "silent-exception",
    "severity": "medium",
    "line": 43
  },
  "ai_review": {
    "explanation": "Explanation of why the issue matters.",
    "risk": "Description of the potential risk.",
    "recommendation": "Recommended improvement.",
    "suggested_fix": "Example corrected Python code."
  }
}
```

---

## Installation

For hosted deployment, see [DEPLOYMENT.md](DEPLOYMENT.md): Docker backend,
static frontend, environment settings, and exact Render deployment steps.

### 1. Clone the Repository

```bash
git clone https://github.com/aseelmas/ai-code-review-platform.git
cd ai-code-review-platform
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

On macOS/Linux:

```bash
source venv/bin/activate
```

### 3. Install Backend Dependencies

```bash
pip install -r requirements-dev.txt
```

### 4. Configure the OpenAI API Key

Copy `.env.example` to `.env` in the project root and configure it locally.
If `.env` already exists, edit it instead of overwriting it:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-5.4
```

The `.env` file should never be committed to Git.
The key is optional for static analysis; it is required only when requesting AI
review. `OPENAI_MODEL` is optional and defaults to the existing `gpt-5.4` model.
Use a Responses API model that supports structured output and is available to
your account. Keep the key on the backend; never put it in a `VITE_` variable.

### 5. Run the Backend

```bash
uvicorn backend.main:app --reload
```

The backend will run at:

```text
http://127.0.0.1:8000
```

Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

---

## Frontend Setup

Open another terminal:

```bash
cd frontend
npm install
```

The frontend supports configuration through:

```text
frontend/.env
```

Example:

```env
VITE_API_URL=http://127.0.0.1:8000
```

A configuration example is available in:

```text
frontend/.env.example
```

Run the development server:

```bash
npm run dev
```

Open the application at:

```text
http://localhost:5173
```

---

## Running Tests

Run the backend test suite from the project root:

```bash
python -m pytest -v
```

The automated tests cover:

- Issue detection rules
- Severity classification
- Issue scores
- Correct line-number detection
- False-positive edge cases
- Hard-coded secret detection
- Dangerous subprocess detection
- Repository health-score calculation
- Source-code context extraction
- Diff line mapping, additions, replacements, deletions, and repeated lines
- Exclusion of unchanged findings and explicit issue-start-line scope
- Per-file errors, request validation, and multi-file diff results
- Repository API regression checks and compatibility with AI review (mocked)
- GitHub URL validation, clone failures/timeouts, source limits, and cleanup
- AI success, invalid output, missing key, and provider failure fallbacks

Tests replace the OpenAI SDK with mocks and block real calls by default. Git
cloning is mocked in automated tests, so the suite needs neither network access
nor API credits. The frontend request-helper tests use Node's built-in test
runner; no additional packages are required.

Frontend validation:

```bash
cd frontend
npm test
npm run lint
npm run build
```

Production builds require `VITE_API_URL` to be set to the public HTTPS backend
URL before running `npm run build` (PowerShell: `$env:VITE_API_URL = 'https://YOUR-BACKEND-HOST'`).
Local `npm run dev` keeps its localhost default. Runtime-only backend installs
use `requirements.txt`; tests require `requirements-dev.txt`.

---

## Example Analysis

The platform has been tested on the open-source Requests repository:

```text
https://github.com/psf/requests
```

An example analysis detected findings across multiple severity levels and displayed them through the repository dashboard and file explorer.

Users can inspect the source-code context of each finding and optionally request an AI-powered explanation and suggested fix.

> Static-analysis findings are heuristic. A detected issue does not necessarily represent a confirmed bug or security vulnerability and should be reviewed by a developer.

---

## Security and Privacy

The platform follows several practices to reduce unnecessary exposure of source code and credentials:

- API keys are stored using environment variables.
- `.env` files are excluded from Git.
- Temporary repository clones are removed after analysis.
- AI review is performed only when explicitly requested.
- The entire repository is not sent to the AI service.
- AI review requests contain only issue metadata and the relevant source-code context.

Cloning is shallow, single-branch, and excludes tags. Git credential prompts,
credential helpers, user/system configuration, hooks, and HTTP redirects are
disabled for these clones; submodules are not fetched and LFS files are not
downloaded. Python discovery excludes `.git` and symbolic links. Temporary
clones are cleaned up on success and failure, including read-only Windows Git
objects. An OS-level cleanup failure is logged without sensitive details.

Limits are readable constants in `backend/repository.py`:

| Limit | Value |
| --- | --- |
| Clone duration | 60 seconds |
| Clone disk usage, including `.git` | 100 MiB |
| Total repository files | 20,000 |
| Python files | 500 |
| Single Python file | 512 KiB |
| Total Python source | 5 MiB |

Disk/file limits are checked while Git is running and after it finishes; the
clone process tree is stopped on timeout or excess size. Polling may briefly
overshoot a limit. These are local-app safeguards, not OS-enforced quotas.

When analyzing proprietary or sensitive source code, users should review their organization's policies before sending code snippets to external AI services.

---

## Current Limitations

The static analyzer is intentionally lightweight and rule-based.

Current limitations include:

- Python repositories only
- Public GitHub repositories only
- Heuristic secret detection may produce false positives
- The health score is not normalized by repository size
- Static analysis cannot determine every runtime behavior
- AI-generated fixes should be reviewed before being applied
- Public deployment still needs authentication, rate limiting, and isolated
  workers with hard CPU/memory/disk quotas; the production entry point adds a
  basic server concurrency cap

---

## Future Improvements

Potential future improvements include:

- Support for additional programming languages
- GitHub authentication for private repositories
- GitHub pull-request integration
- Automated pull-request review comments
- Configurable analysis rules
- Improved false-positive detection
- Repository-size-normalized health scoring
- Additional security rules
- Persistent analysis history
- User authentication
- Deployment and CI/CD integration

---

## Author

**Aseel Masarwa**

Computer Science Graduate from Ben-Gurion University of the Negev.

Interested in software engineering, backend development, and AI-powered developer tools.
