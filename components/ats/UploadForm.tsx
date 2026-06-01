"use client";

import { useState } from "react";

type UploadFormProps = {
  file: File | null;
  jobDescription: string;
  error: string;
  scoringMode: boolean;
  weakBulletMode: boolean;
  onFileChange: (file: File | null) => void;
  onJobDescriptionChange: (value: string) => void;
  onScoringModeChange: (value: boolean) => void;
  onWeakBulletModeChange: (value: boolean) => void;
  onSubmit: (e: React.FormEvent) => void;
};

export default function UploadForm({
  file,
  jobDescription,
  error,
  scoringMode,
  weakBulletMode,
  onFileChange,
  onJobDescriptionChange,
  onScoringModeChange,
  onWeakBulletModeChange,
  onSubmit,
}: UploadFormProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isInvalidDrag, setIsInvalidDrag] = useState(false);

  function isPdfDrag(e: React.DragEvent<HTMLElement>) {
    const item = e.dataTransfer.items?.[0];

    if (!item) return false;

    return item.kind === "file" && item.type === "application/pdf";
  }

  const selectedFileName = file?.name ?? "No file selected";

  return (
    <div className="mx-auto grid max-w-6xl gap-8 lg:grid-cols-[1.05fr_0.95fr]">
      <div className="flex flex-col justify-center">
        <div className="mb-6 inline-flex w-fit items-center rounded-full border border-slate-200 bg-white px-3 py-1 text-sm text-slate-600 shadow-sm">
          ATS Resume Checker
        </div>

        <h1 className="max-w-xl text-4xl font-bold tracking-tight sm:text-5xl">
          Upload your resume and compare it to the job description.
        </h1>

        <p className="mt-4 max-w-xl text-base leading-7 text-slate-600 sm:text-lg">
          Get a score, missing keywords, requirement matches, and the
          highest-impact improvements in one clean view.
        </p>

        <div className="mt-8 grid gap-4 sm:grid-cols-3">
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-sm font-medium text-slate-900">1. Upload</p>
            <p className="mt-1 text-sm text-slate-600">Add your resume PDF.</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-sm font-medium text-slate-900">2. Analyze</p>
            <p className="mt-1 text-sm text-slate-600">
              Match against the role.
            </p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-sm font-medium text-slate-900">3. Improve</p>
            <p className="mt-1 text-sm text-slate-600">
              Review gaps and strengths.
            </p>
          </div>
        </div>
      </div>

      <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-xl">
        <form onSubmit={onSubmit} className="space-y-6">
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-800">
              Resume PDF
            </label>

            <label
              onDragEnter={(e) => {
                e.preventDefault();

                const valid = isPdfDrag(e);

                setIsDragging(true);
                setIsInvalidDrag(!valid);
              }}
              onDragOver={(e) => {
                e.preventDefault();

                const valid = isPdfDrag(e);

                e.dataTransfer.dropEffect = valid ? "copy" : "none";

                setIsDragging(true);
                setIsInvalidDrag(!valid);
              }}
              onDragLeave={(e) => {
                e.preventDefault();

                setIsDragging(false);
                setIsInvalidDrag(false);
              }}
              onDrop={(e) => {
                e.preventDefault();

                setIsDragging(false);

                const droppedFile = e.dataTransfer.files?.[0];

                if (!droppedFile || droppedFile.type !== "application/pdf") {
                  setIsInvalidDrag(false);
                  onFileChange(null);
                  return;
                }

                setIsInvalidDrag(false);
                onFileChange(droppedFile);
              }}
              className={`flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-8 text-center transition ${
                isInvalidDrag
                  ? "cursor-not-allowed border-red-400 bg-red-50"
                  : isDragging
                    ? "cursor-copy border-blue-500 bg-blue-50"
                    : "border-slate-300 bg-slate-50 hover:border-slate-500 hover:bg-slate-100"
              }`}
            >
              <span className="text-sm font-medium text-slate-900">
                Click to upload or drag and drop
              </span>

              <span className="mt-1 text-sm text-slate-500">PDF only</span>

              <span className="mt-3 rounded-full bg-white px-3 py-1 text-xs text-slate-600 shadow-sm">
                {selectedFileName}
              </span>

              <input
                type="file"
                accept="application/pdf"
                className="hidden"
                onChange={(e) => onFileChange(e.target.files?.[0] ?? null)}
              />
            </label>
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-800">
              Job Description
            </label>
            <textarea
              className="min-h-[220px] w-full rounded-2xl border border-slate-300 bg-white p-4 text-sm outline-none transition placeholder:text-slate-400 focus:border-slate-500 focus:ring-4 focus:ring-slate-200"
              value={jobDescription}
              onChange={(e) => onJobDescriptionChange(e.target.value)}
              placeholder="Paste the job description here..."
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-800">
              Type of Analysis
            </label>

            <label className="mt-2 flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={scoringMode === true}
                onChange={(e) =>
                  onScoringModeChange(e.target.checked ? true : false)
                }
                className="h-4 w-4 rounded border-slate-300"
              />
              AI Scoring
            </label>

            <label className="mt-2 flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={weakBulletMode === true}
                onChange={(e) =>
                  onWeakBulletModeChange(e.target.checked ? true : false)
                }
                className="h-4 w-4 rounded border-slate-300"
              />
              AI Weak Bullet Analysis
            </label>
          </div>

          {error && (
            <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <button
            type="submit"
            className="w-full rounded-2xl bg-slate-900 px-4 py-3 font-medium text-white transition hover:cursor-pointer hover:bg-slate-800"
          >
            Analyze Resume
          </button>
        </form>
      </div>
    </div>
  );
}
