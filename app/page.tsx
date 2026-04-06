"use client";

import { useState } from "react";
import LoadingState from "@/components/ats/LoadingState";
import ResultsContent from "@/components/ats/ResultsContent";
import ResultsHeader from "@/components/ats/ResultsHeader";
import ScoreSidebar from "@/components/ats/ScoreSidebar";
import UploadForm from "@/components/ats/UploadForm";
import { AnalyzeResponse, ViewState } from "@/components/ats/types";

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

export default function HomePage() {
  const [file, setFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState(temp);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [view, setView] = useState<ViewState>("form");
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

    setView("loading");

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
        } catch {
          // ignore JSON parse failures
        }
        throw new Error(message);
      }

      const data: AnalyzeResponse = await res.json();
      setResult(data);
      setView("result");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
      setView("form");
    }
  }

  function handleEditInputs() {
    setError("");
    setView("form");
  }

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-50 via-white to-slate-100 text-slate-900">
      <div className="mx-auto flex min-h-screen max-w-6xl items-center justify-center px-4 py-10">
        <div className="w-full">
          {view === "form" && (
            <UploadForm
              file={file}
              jobDescription={jobDescription}
              error={error}
              onFileChange={setFile}
              onJobDescriptionChange={setJobDescription}
              onSubmit={handleSubmit}
            />
          )}

          {view === "loading" && (
            <LoadingState onEditInputs={handleEditInputs} />
          )}

          {view === "result" && result && (
            <div className="mx-auto max-w-6xl space-y-6">
              <ResultsHeader
                fileName={file?.name ?? "Uploaded resume"}
                onEditInputs={handleEditInputs}
              />

              <div className="grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
                <ScoreSidebar result={result} />
                <ResultsContent
                  result={result}
                  jobDescription={jobDescription}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
