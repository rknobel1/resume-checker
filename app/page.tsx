"use client";

import { useState } from "react";

const temp = `Full job description
Qualifications:
Education:
Master’s degree in Electrical Engineering, Computer Science, Mathematics, Statistic, Physics, Data Science, Machine Learning, Music Technology or field related to research science
PhD in Electrical Engineering, Computer Science, Mathematics, Statistic, Physics, Data Science, Machine Learning, Music Technology or field related to research science
Technical Skills:
Proficiency in programming languages: Python required; C/C++ or Matlab also preferred
Proficiency in leveraging frameworks and libraries including: PyTorch, Tensorflow, scikit-learn, NumPy, Matplotlib, etc.
Proficiency in tools and technologies including: Git/GitHub, Docker, Jupyter Lab, AWS, OnPrem GPU training tools
Preferred Experience:
Knowledge or experience with Speech enhancement algorithms
Knowledge or experience with classical Digital Signal Processing
Proficiency in developing low latency, embedded-friendly solutions
Experience in Audio engineering, DAWs, recording, or other audio production.`;

type RequirementMatch = {
  requirement: string;
  category: string;
  importance: "required" | "preferred";
  matched: boolean;
  score: number;
  evidence_score: number;
  best_evidence?: string | null;
  notes?: string | null;
};

type ScoreBreakdown = {
  overall_score: number;
  required_coverage: number;
  preferred_coverage: number;
  semantic_alignment: number;
  evidence_strength: number;
  bullet_quality: number;
  formatting: number;
  title_alignment: number;
  matched_requirements: RequirementMatch[];
  missing_required: string[];
  missing_preferred: string[];
  strengths: string[];
  improvement_priorities: string[];
};

type AnalyzeResponse = {
  score_breakdown: ScoreBreakdown;
  missing_keywords: string[];
  weak_bullets: string[];
  weak_bullet_details: {
    text: string;
    section: string;
    reasons: string[];
  }[];
  suggestions: {
    id?: string;
    section?: string;
    original_text?: string;
    proposed_text?: string;
    reason?: string;
    estimated_score_impact?: number;
    confidence?: number;
    type?: string;
    target_requirement?: string;
    original?: string;
    suggested?: string;
  }[];
  debug?: unknown;
};

export default function HomePage() {
  const [file, setFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState(temp);
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
        let message = `Request failed: ${res.status}`;
        try {
          const errData = await res.json();
          message = errData.detail || message;
        } catch {}
        throw new Error(message);
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
          <label className="block font-medium">
            Required/Preferred Qualifications
          </label>
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
                Required coverage: {result.score_breakdown.required_coverage}
              </p>
              <p>
                Preferred coverage: {result.score_breakdown.preferred_coverage}
              </p>
              <p>
                Semantic alignment: {result.score_breakdown.semantic_alignment}
              </p>
              <p>
                Evidence strength: {result.score_breakdown.evidence_strength}
              </p>
              <p>Bullet quality: {result.score_breakdown.bullet_quality}</p>
              <p>Formatting: {result.score_breakdown.formatting}</p>
              <p>Title alignment: {result.score_breakdown.title_alignment}</p>
            </div>
          </div>

          <div className="border rounded-xl p-4">
            <h2 className="text-xl font-semibold mb-3">Strengths</h2>
            {result.score_breakdown.strengths.length > 0 ? (
              <ul className="list-disc pl-5">
                {result.score_breakdown.strengths.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : (
              <p>No standout strengths detected yet.</p>
            )}
          </div>

          <div className="border rounded-xl p-4">
            <h2 className="text-xl font-semibold mb-3">
              Missing Required Requirements
            </h2>
            {result.score_breakdown.missing_required.length > 0 ? (
              <ul className="list-disc pl-5">
                {result.score_breakdown.missing_required.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : (
              <p>No major required gaps found.</p>
            )}
          </div>

          <div className="border rounded-xl p-4">
            <h2 className="text-xl font-semibold mb-3">
              Missing Preferred Requirements
            </h2>
            {result.score_breakdown.missing_preferred.length > 0 ? (
              <ul className="list-disc pl-5">
                {result.score_breakdown.missing_preferred.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : (
              <p>No major preferred gaps found.</p>
            )}
          </div>

          <div className="border rounded-xl p-4">
            <h2 className="text-xl font-semibold mb-3">
              Top Improvement Priorities
            </h2>
            {result.score_breakdown.improvement_priorities.length > 0 ? (
              <ul className="list-disc pl-5">
                {result.score_breakdown.improvement_priorities.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : (
              <p>No improvement priorities generated.</p>
            )}
          </div>

          <div className="border rounded-xl p-4">
            <h2 className="text-xl font-semibold mb-3">Requirement Matches</h2>
            {result.score_breakdown.matched_requirements.length > 0 ? (
              <div className="space-y-3">
                {result.score_breakdown.matched_requirements.map((req, idx) => (
                  <div
                    key={`${req.requirement}-${idx}`}
                    className="border rounded-md p-3"
                  >
                    <div className="flex justify-between gap-4">
                      <p className="font-medium">{req.requirement}</p>
                      <p className="text-sm text-gray-600">
                        {req.importance} • {req.category}
                      </p>
                    </div>
                    <p className="text-sm mt-1">
                      Matched: {req.matched ? "Yes" : "No"}
                    </p>
                    <p className="text-sm">Score: {req.score}</p>
                    <p className="text-sm">
                      Evidence strength: {req.evidence_score}/5
                    </p>
                    {req.best_evidence && (
                      <p className="text-sm mt-2">
                        <span className="font-medium">Best evidence:</span>{" "}
                        {req.best_evidence}
                      </p>
                    )}
                    {req.notes && (
                      <p className="text-sm text-gray-600 mt-1">{req.notes}</p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p>No requirement matches available.</p>
            )}
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
            {result.weak_bullet_details.length > 0 ? (
              <ul className="space-y-3">
                {result.weak_bullet_details.map((item, idx) => (
                  <li
                    key={`${item.text}-${idx}`}
                    className="border rounded-md p-3"
                  >
                    <p className="font-medium">{item.text}</p>
                    <p className="text-sm text-gray-600 mt-1">
                      Reasons: {item.reasons.join(", ")}
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <p>No obviously weak bullets found.</p>
            )}
          </div>

          {/* <div className="border rounded-xl p-4">
            <h2 className="text-xl font-semibold mb-3">
              Suggested Improvements
            </h2>
            {result.suggestions.length > 0 ? (
              <div className="space-y-4">
                {result.suggestions.map((s) => (
                  <div key={s.id} className="border rounded-md p-3 space-y-2">
                    <div>
                      <p className="text-sm font-medium text-gray-500">
                        Original
                      </p>
                      <p>{s.original_text}</p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-500">
                        Suggested Rewrite
                      </p>
                      <p>{s.proposed_text}</p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-500">Why</p>
                      <p>{s.reason}</p>
                    </div>
                    <div className="text-sm text-gray-600">
                      Estimated score impact: +{s.estimated_score_impact} |
                      Confidence: {s.confidence}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p>No suggestions generated yet.</p>
            )}
          </div> */}
        </section>
      )}
    </main>
  );
}
