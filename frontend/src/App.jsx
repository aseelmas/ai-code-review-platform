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

  return (
    <div className="app">
      <div className="container">
        <h1>AI Code Review Platform</h1>

        <p className="subtitle">
          Analyze Python GitHub repositories for code quality and security issues.
        </p>

        <div className="analyze-form">
          <input
            type="text"
            placeholder="https://github.com/owner/repository"
            value={repoUrl}
            onChange={(event) => setRepoUrl(event.target.value)}
          />

          <button onClick={analyzeRepository} disabled={loading}>
            {loading ? "Analyzing..." : "Analyze Repository"}
          </button>
        </div>

        {error && <p className="error">{error}</p>}

        {result && (
          <div className="result">
            <h2>Analysis Complete</h2>

            <p>
              <strong>Repository:</strong> {result.repository}
            </p>

            <p>
              <strong>Python Files:</strong> {result.python_files_count}
            </p>

            <p>
              <strong>Total Issues:</strong> {result.summary.total_issues}
            </p>

            <p>
              <strong>Health Score:</strong> {result.health_score}/100
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;