import { useMemo, useState } from "react";
import "./App.css";

function App() {
  const [repoUrl, setRepoUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [selectedFile, setSelectedFile] = useState("all");
  const [severityFilter, setSeverityFilter] = useState("all");

  const [aiReviews, setAiReviews] = useState({});
  const [aiLoading, setAiLoading] = useState({});
  const [aiErrors, setAiErrors] = useState({});

  const analyzeRepository = async () => {
    if (!repoUrl.trim()) {
      setError("Please enter a GitHub repository URL.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);
    setSelectedFile("all");
    setSeverityFilter("all");

    setAiReviews({});
    setAiLoading({});
    setAiErrors({});

    try {
      const response = await fetch("http://127.0.0.1:8000/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          repo_url: repoUrl,
        }),
      });

      if (!response.ok) {
        throw new Error("Repository analysis failed.");
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getHealthClass = (score) => {
    if (score >= 80) {
      return "health-good";
    }

    if (score >= 50) {
      return "health-medium";
    }

    return "health-bad";
  };

  const getIssueId = (issue) => {
    return `${issue.file}-${issue.line}-${issue.rule}`;
  };

  const requestAiReview = async (issue) => {
    const issueId = getIssueId(issue);

    setAiLoading((previous) => ({
      ...previous,
      [issueId]: true,
    }));

    setAiErrors((previous) => ({
      ...previous,
      [issueId]: "",
    }));

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/ai-review",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            rule: issue.rule,
            severity: issue.severity,
            line: issue.line,
            message: issue.message,
            code_context: issue.code_context || "",
          }),
        }
      );

      if (!response.ok) {
        throw new Error("AI review failed.");
      }

      const data = await response.json();

      setAiReviews((previous) => ({
        ...previous,
        [issueId]: data.ai_review,
      }));
    } catch (err) {
      setAiErrors((previous) => ({
        ...previous,
        [issueId]: err.message,
      }));
    } finally {
      setAiLoading((previous) => ({
        ...previous,
        [issueId]: false,
      }));
    }
  };

  const filesWithIssues = useMemo(() => {
    if (!result) {
      return [];
    }

    return result.files.filter((file) => file.issues.length > 0);
  }, [result]);

  const filteredIssues = useMemo(() => {
    if (!result) {
      return [];
    }

    let issues = result.files.flatMap((file) =>
      file.issues.map((issue) => ({
        ...issue,
        file: file.file,
      }))
    );

    if (selectedFile !== "all") {
      issues = issues.filter(
        (issue) => issue.file === selectedFile
      );
    }

    if (severityFilter !== "all") {
      issues = issues.filter(
        (issue) => issue.severity === severityFilter
      );
    }

    return issues.sort((a, b) => b.score - a.score);
  }, [result, selectedFile, severityFilter]);

  return (
    <div className="app">
      <div className="container">
        <header className="header">
          <h1>AI Code Review Platform</h1>

          <p className="subtitle">
            Analyze Python GitHub repositories for code quality and security
            issues.
          </p>
        </header>

        <section className="analyze-section">
          <div className="analyze-form">
            <input
              type="text"
              placeholder="https://github.com/owner/repository"
              value={repoUrl}
              onChange={(event) => setRepoUrl(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  analyzeRepository();
                }
              }}
            />

            <button
              onClick={analyzeRepository}
              disabled={loading}
            >
              {loading
                ? "Analyzing..."
                : "Analyze Repository"}
            </button>
          </div>

          {error && <p className="error">{error}</p>}
        </section>

        {loading && (
          <div className="loading-card">
            <div className="spinner"></div>
            <p>Analyzing repository...</p>
          </div>
        )}

        {result && (
          <main className="dashboard">
            <div className="repository-header">
              <p className="section-label">
                ANALYSIS RESULT
              </p>

              <h2>{result.repository}</h2>
            </div>

            <div className="stats-grid">
              <div
                className={`stat-card health-card ${getHealthClass(
                  result.health_score
                )}`}
              >
                <span className="stat-label">
                  Health Score
                </span>

                <div className="health-score">
                  {result.health_score}
                  <span>/100</span>
                </div>
              </div>

              <div className="stat-card">
                <span className="stat-label">
                  Python Files
                </span>

                <span className="stat-value">
                  {result.python_files_count}
                </span>
              </div>

              <div className="stat-card">
                <span className="stat-label">
                  Total Issues
                </span>

                <span className="stat-value">
                  {result.summary.total_issues}
                </span>
              </div>
            </div>

            <section className="severity-section">
              <h2>Issue Severity</h2>

              <div className="severity-grid">
                <div className="severity-card severity-high">
                  <span className="severity-name">
                    High
                  </span>

                  <span className="severity-number">
                    {
                      result.summary.severity_counts
                        .high
                    }
                  </span>
                </div>

                <div className="severity-card severity-medium">
                  <span className="severity-name">
                    Medium
                  </span>

                  <span className="severity-number">
                    {
                      result.summary.severity_counts
                        .medium
                    }
                  </span>
                </div>

                <div className="severity-card severity-low">
                  <span className="severity-name">
                    Low
                  </span>

                  <span className="severity-number">
                    {
                      result.summary.severity_counts
                        .low
                    }
                  </span>
                </div>
              </div>
            </section>

            <section className="explorer-section">
              <div className="explorer-header">
                <div>
                  <p className="section-label">
                    REPOSITORY EXPLORER
                  </p>

                  <h2>Files & Issues</h2>
                </div>

                <span className="issue-count">
                  {filteredIssues.length} issues
                </span>
              </div>

              <div className="explorer-layout">
                <aside className="file-panel">
                  <button
                    className={`file-item ${
                      selectedFile === "all"
                        ? "active-file"
                        : ""
                    }`}
                    onClick={() =>
                      setSelectedFile("all")
                    }
                  >
                    <span>All Files</span>
                    <span>
                      {result.summary.total_issues}
                    </span>
                  </button>

                  {filesWithIssues.map((file) => (
                    <button
                      className={`file-item ${
                        selectedFile === file.file
                          ? "active-file"
                          : ""
                      }`}
                      key={file.file}
                      onClick={() =>
                        setSelectedFile(file.file)
                      }
                    >
                      <span className="file-name">
                        {file.file}
                      </span>

                      <span className="file-count">
                        {file.issues.length}
                      </span>
                    </button>
                  ))}
                </aside>

                <div className="issues-panel">
                  <div className="filter-row">
                    {[
                      "all",
                      "high",
                      "medium",
                      "low",
                    ].map((filter) => (
                      <button
                        key={filter}
                        className={`filter-button ${
                          severityFilter === filter
                            ? "active-filter"
                            : ""
                        }`}
                        onClick={() =>
                          setSeverityFilter(filter)
                        }
                      >
                        {filter.charAt(0).toUpperCase() +
                          filter.slice(1)}
                      </button>
                    ))}
                  </div>

                  {filteredIssues.length === 0 ? (
                    <div className="no-issues">
                      No issues match the selected
                      filters.
                    </div>
                  ) : (
                    <div className="issues-list">
                      {filteredIssues.map(
                        (issue, index) => {
                          const issueId =
                            getIssueId(issue);

                          const aiReview =
                            aiReviews[issueId];

                          const isAiLoading =
                            aiLoading[issueId];

                          const aiError =
                            aiErrors[issueId];

                          return (
                            <article
                              className="issue-card"
                              key={`${issue.file}-${issue.line}-${index}`}
                            >
                              <div className="issue-top">
                                <div className="issue-title">
                                  <span
                                    className={`severity-badge badge-${issue.severity}`}
                                  >
                                    {issue.severity}
                                  </span>

                                  <span className="rule-name">
                                    {issue.rule}
                                  </span>
                                </div>

                                <button
                                  className="ai-review-button"
                                  onClick={() =>
                                    requestAiReview(
                                      issue
                                    )
                                  }
                                  disabled={
                                    isAiLoading
                                  }
                                >
                                  {isAiLoading
                                    ? "Reviewing..."
                                    : aiReview
                                    ? "Review Again"
                                    : "AI Review"}
                                </button>
                              </div>

                              <p className="issue-message">
                                {issue.message}
                              </p>

                              <div className="issue-location">
                                <span>
                                  {issue.file}
                                </span>

                                <span>
                                  Line {issue.line}
                                </span>
                              </div>

                              {issue.code_context && (
                                <pre className="code-context">
                                  <code>
                                    {
                                      issue.code_context
                                    }
                                  </code>
                                </pre>
                              )}

                              {aiError && (
                                <p className="ai-error">
                                  {aiError}
                                </p>
                              )}

                              {aiReview && (
                                <div className="ai-review">
                                  <div className="ai-review-header">
                                    <div>
                                      <p className="section-label">
                                        AI CODE
                                        REVIEW
                                      </p>

                                      <h3>
                                        Review Result
                                      </h3>
                                    </div>
                                  </div>

                                  <div className="ai-review-grid">
                                    <div className="ai-review-block">
                                      <span className="ai-review-label">
                                        Explanation
                                      </span>

                                      <p>
                                        {
                                          aiReview.explanation
                                        }
                                      </p>
                                    </div>

                                    <div className="ai-review-block">
                                      <span className="ai-review-label">
                                        Risk
                                      </span>

                                      <p>
                                        {
                                          aiReview.risk
                                        }
                                      </p>
                                    </div>

                                    <div className="ai-review-block">
                                      <span className="ai-review-label">
                                        Recommendation
                                      </span>

                                      <p>
                                        {
                                          aiReview.recommendation
                                        }
                                      </p>
                                    </div>
                                  </div>

                                  {aiReview.suggested_fix && (
                                    <div className="suggested-fix">
                                      <span className="ai-review-label">
                                        Suggested Fix
                                      </span>

                                      <pre>
                                        <code>
                                          {
                                            aiReview.suggested_fix
                                          }
                                        </code>
                                      </pre>
                                    </div>
                                  )}
                                </div>
                              )}
                            </article>
                          );
                        }
                      )}
                    </div>
                  )}
                </div>
              </div>
            </section>
          </main>
        )}
      </div>
    </div>
  );
}

export default App;