"use client";

import { useState } from "react";

type ScoreBreakdown = {
  keyword_relevance: number;
  skills_match: number;
  experience_alignment: number;
  achievement_strength: number;
  section_completeness: number;
  ats_formatting: number;
  overall_score: number;
};

type AnalyzeResponse = {
  resume_text: string;
  score_breakdown: ScoreBreakdown;
  missing_keywords: string[];
  weak_bullets: string[];
};

export default function HomePage() {
  const [file, setFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState("");
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setResult(null);

    if (!file) {
      setError("Please upload a resume PDF.");
      return;
    }

    if (!jobDescription.trim()) {
      setError("Please paste a job description.");
      return;
    }

    setLoading(true);

    try {
      const formData = new FormData();
      formData.append("resume_pdf", file);
      formData.append("job_description", jobDescription);

      const res = await fetch("http://127.0.0.1:8000/analyze-pdf", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        throw new Error(`Request failed: ${res.status}`);
      }

      const data: AnalyzeResponse = await res.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="max-w-3xl mx-auto p-6 space-y-6">
      <h1 className="text-3xl font-bold">ATS Resume Checker MVP</h1>

      <form onSubmit={handleSubmit} className="space-y-4 border rounded-xl p-4">
        <div className="space-y-2">
          <label className="block font-medium">Resume PDF</label>
          <input
            type="file"
            accept="application/pdf"
            className="border border-black/30 rounded-md py-2 px-1.5 hover:cursor-pointer"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </div>

        <div className="space-y-2">
          <label className="block font-medium">Job Description</label>
          <textarea
            className="w-full min-h-[180px] border rounded-md p-3"
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            placeholder="Paste the job description here..."
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="px-4 py-2 rounded-md border hover:cursor-pointer"
        >
          {loading ? "Analyzing..." : "Analyze Resume"}
        </button>
      </form>

      {error && (
        <div className="border border-red-500 rounded-md p-3 text-red-700">
          {error}
        </div>
      )}

      {result && (
        <section className="space-y-6">
          <div className="border rounded-xl p-4">
            <h2 className="text-xl font-semibold mb-3">Overall Score</h2>
            <p className="text-4xl font-bold">
              {result.score_breakdown.overall_score}/100
            </p>
          </div>

          <div className="border rounded-xl p-4">
            <h2 className="text-xl font-semibold mb-3">Score Breakdown</h2>
            <div className="space-y-1">
              <p>
                Keyword relevance: {result.score_breakdown.keyword_relevance}
              </p>
              <p>Skills match: {result.score_breakdown.skills_match}</p>
              <p>
                Experience alignment:{" "}
                {result.score_breakdown.experience_alignment}
              </p>
              <p>
                Achievement strength:{" "}
                {result.score_breakdown.achievement_strength}
              </p>
              <p>
                Section completeness:{" "}
                {result.score_breakdown.section_completeness}
              </p>
              <p>ATS formatting: {result.score_breakdown.ats_formatting}</p>
            </div>
          </div>

          <div className="border rounded-xl p-4">
            <h2 className="text-xl font-semibold mb-3">Missing Keywords</h2>
            {result.missing_keywords.length > 0 ? (
              <ul className="list-disc pl-5">
                {result.missing_keywords.map((kw) => (
                  <li key={kw}>{kw}</li>
                ))}
              </ul>
            ) : (
              <p>No major missing keywords found.</p>
            )}
          </div>

          <div className="border rounded-xl p-4">
            <h2 className="text-xl font-semibold mb-3">Weak Bullets</h2>
            {result.weak_bullets.length > 0 ? (
              <ul className="list-disc pl-5">
                {result.weak_bullets.map((bullet, idx) => (
                  <li key={`${bullet}-${idx}`}>{bullet}</li>
                ))}
              </ul>
            ) : (
              <p>No obviously weak bullets found.</p>
            )}
          </div>
        </section>
      )}
    </main>
  );
}
