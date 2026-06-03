"use client";

import { useState } from "react";
import LoadingState from "@/components/ats/LoadingState";
import ResultsContent from "@/components/ats/ResultsContent";
import ResultsHeader from "@/components/ats/ResultsHeader";
import ScoreSidebar from "@/components/ats/ScoreSidebar";
import UploadForm from "@/components/ats/UploadForm";
import { AnalyzeResponse, ViewState } from "@/components/ats/types";

export default function HomePage() {
  const [file, setFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState<string>("");
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [view, setView] = useState<ViewState>("form");
  const [error, setError] = useState("");
  const [scoringModeAI, setScoringMode] = useState<boolean>(true);
  const [weakBulletModeAI, setWeakBulletMode] = useState<boolean>(true);

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
      formData.append("scoring_mode_ai", String(scoringModeAI));
      formData.append("weak_bullet_mode_ai", String(weakBulletModeAI));

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
              scoringMode={scoringModeAI}
              weakBulletMode={weakBulletModeAI}
              onFileChange={setFile}
              onJobDescriptionChange={setJobDescription}
              onScoringModeChange={setScoringMode}
              onWeakBulletModeChange={setWeakBulletMode}
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
                <ResultsContent result={result} />
              </div>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
