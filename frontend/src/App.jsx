import { useState } from "react";
import "./App.css";

function App() {
  const [repoUrl, setRepoUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const analyzeRepository = async () => {
    if (!repoUrl.trim()) {
      setError("Please enter a GitHub repository URL.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

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

  return (
    <div className="app">
      <div className="container">
        <header className="header">
          <div>
            <h1>AI Code Review Platform</h1>

            <p className="subtitle">
              Analyze Python GitHub repositories for code quality and security
              issues.
            </p>
          </div>
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

            <button onClick={analyzeRepository} disabled={loading}>
              {loading ? "Analyzing..." : "Analyze Repository"}
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
              <div>
                <p className="section-label">ANALYSIS RESULT</p>
                <h2>{result.repository}</h2>
              </div>
            </div>

            <div className="stats-grid">
              <div
                className={`stat-card health-card ${getHealthClass(
                  result.health_score
                )}`}
              >
                <span className="stat-label">Health Score</span>

                <div className="health-score">
                  {result.health_score}
                  <span>/100</span>
                </div>
              </div>

              <div className="stat-card">
                <span className="stat-label">Python Files</span>
                <span className="stat-value">
                  {result.python_files_count}
                </span>
              </div>

              <div className="stat-card">
                <span className="stat-label">Total Issues</span>
                <span className="stat-value">
                  {result.summary.total_issues}
                </span>
              </div>
            </div>

            <section className="severity-section">
              <h2>Issue Severity</h2>

              <div className="severity-grid">
                <div className="severity-card severity-high">
                  <span className="severity-name">High</span>
                  <span className="severity-number">
                    {result.summary.severity_counts.high}
                  </span>
                </div>

                <div className="severity-card severity-medium">
                  <span className="severity-name">Medium</span>
                  <span className="severity-number">
                    {result.summary.severity_counts.medium}
                  </span>
                </div>

                <div className="severity-card severity-low">
                  <span className="severity-name">Low</span>
                  <span className="severity-number">
                    {result.summary.severity_counts.low}
                  </span>
                </div>
              </div>
            </section>

            <section className="issues-section">
              <div className="issues-header">
                <div>
                  <p className="section-label">PRIORITY FINDINGS</p>
                  <h2>Top Issues</h2>
                </div>

                <span className="issue-count">
                  {result.top_issues.length} shown
                </span>
              </div>

              {result.top_issues.length === 0 ? (
                <div className="no-issues">
                  No issues detected in this repository.
                </div>
              ) : (
                <div className="issues-list">
                  {result.top_issues.map((issue, index) => (
                    <article
                      className="issue-card"
                      key={`${issue.file}-${issue.line}-${index}`}
                    >
                      <div className="issue-top">
                        <span
                          className={`severity-badge badge-${issue.severity}`}
                        >
                          {issue.severity}
                        </span>

                        <span className="rule-name">{issue.rule}</span>
                      </div>

                      <p className="issue-message">{issue.message}</p>

                      <div className="issue-location">
                        <span>{issue.file}</span>
                        <span>Line {issue.line}</span>
                      </div>

                      {issue.code_context && (
                        <pre className="code-context">
                          <code>{issue.code_context}</code>
                        </pre>
                      )}
                    </article>
                  ))}
                </div>
              )}
            </section>
          </main>
        )}
      </div>
    </div>
  );
}

export default App;