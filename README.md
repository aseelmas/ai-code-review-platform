# AI Code Review Platform

An automated code review platform that analyzes Python GitHub repositories and detects potential code-quality and security issues.

The project provides a FastAPI backend that clones a repository, analyzes its Python source files using Python's Abstract Syntax Tree (AST), and returns structured information about the code and detected issues.

## Features

- Clone and analyze public GitHub repositories
- Automatically discover Python files
- Parse Python source code using AST
- Extract functions, classes, and imports
- Detect code-quality issues
- Classify detected issues by severity
- Detect bare `except` blocks
- Detect silent exception handling
- Detect debugging `print()` statements
- Detect hardcoded secrets
- Analyze an entire repository through a REST API
- Automated unit testing with Pytest

## Tech Stack

- **Python 3.12**
- **FastAPI**
- **Python AST**
- **Pytest**
- **Git**
- **Uvicorn**

## Project Structure

```text
ai-code-review-platform/
├── backend/
│   ├── analyzer.py
│   ├── main.py
│   └── models.py
├── tests/
│   └── test_analyzer.py
├── .gitignore
├── requirements.txt
└── README.md
```

## API

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

### Analyze Repository

```http
POST /analyze
```

Example request:

```json
{
  "repo_url": "https://github.com/psf/requests"
}
```

The API clones the repository, analyzes its Python files, and returns information about the repository structure and detected code issues.

## Installation

Clone the repository:

```bash
git clone https://github.com/aseelmas/ai-code-review-platform.git
cd ai-code-review-platform
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the API:

```bash
uvicorn backend.main:app --reload
```

Open the interactive API documentation at:

```text
http://127.0.0.1:8000/docs
```

## Running Tests

Run the automated test suite with:

```bash
pytest
```

## Example Analysis

The platform has been tested on real-world open-source Python repositories, including the Requests library, to analyze repository structure and detect potential code issues.

## Roadmap

This project is actively being developed. Planned improvements include:

- Additional static-analysis rules
- More detailed repository-level reports
- Improved issue explanations
- AI-assisted code review suggestions
- GitHub integration
- Web-based user interface

## Author

**Aseel Masarwa**

Computer Science Graduate, Ben-Gurion University of the Negev
