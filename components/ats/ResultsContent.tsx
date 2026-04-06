"use client";

import { useMemo, useState } from "react";
import SectionCard from "./SectionCard";
import PlanModeModal from "./PlanModeModal";
import { AnalyzeResponse, ChatMessage, WeakBullet } from "./types";

type BulletUiState = {
  currentText: string;
  improved: boolean;
  messages: ChatMessage[];
  options: string[];
};

export default function ResultsContent({
  result,
  jobDescription,
}: {
  result: AnalyzeResponse;
  jobDescription: string;
}) {
  const initialBulletState = useMemo(() => {
    const entries: Record<string, BulletUiState> = {};
    for (const bullet of result.weak_bullet_details) {
      entries[bullet.id] = {
        currentText: bullet.text,
        improved: false,
        messages: [],
        options: [],
      };
    }
    return entries;
  }, [result]);

  const [bulletState, setBulletState] =
    useState<Record<string, BulletUiState>>(initialBulletState);

  const [selectedBullet, setSelectedBullet] = useState<WeakBullet | null>(null);
  const [modalLoading, setModalLoading] = useState(false);

  function openPlanMode(bullet: WeakBullet) {
    setSelectedBullet(bullet);
  }

  function closePlanMode() {
    setSelectedBullet(null);
    setModalLoading(false);
  }

  function updateSelectedMessages(messages: ChatMessage[]) {
    if (!selectedBullet) return;
    setBulletState((prev) => ({
      ...prev,
      [selectedBullet.id]: {
        ...prev[selectedBullet.id],
        messages,
      },
    }));
  }

  function updateSelectedOptions(options: string[]) {
    if (!selectedBullet) return;
    setBulletState((prev) => ({
      ...prev,
      [selectedBullet.id]: {
        ...prev[selectedBullet.id],
        options,
      },
    }));
  }

  function updateSelectedCurrentBullet(value: string) {
    if (!selectedBullet) return;
    setBulletState((prev) => ({
      ...prev,
      [selectedBullet.id]: {
        ...prev[selectedBullet.id],
        currentText: value,
      },
    }));
  }

  function applyOption(value: string) {
    if (!selectedBullet) return;
    setBulletState((prev) => ({
      ...prev,
      [selectedBullet.id]: {
        ...prev[selectedBullet.id],
        currentText: value,
        improved: true,
        options: [],
        messages: [
          ...prev[selectedBullet.id].messages,
          {
            role: "assistant",
            content: "Applied selected version to the page.",
          },
        ],
      },
    }));
    setSelectedBullet(null);
  }

  const selectedState = selectedBullet ? bulletState[selectedBullet.id] : null;

  return (
    <>
      <div className="space-y-6">
        <SectionCard title="Strengths">
          {result.score_breakdown.strengths.length > 0 ? (
            <ul className="space-y-2">
              {result.score_breakdown.strengths.map((item) => (
                <li
                  key={item}
                  className="rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-700"
                >
                  {item}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-slate-600">
              No standout strengths detected yet.
            </p>
          )}
        </SectionCard>

        <div className="grid gap-6 xl:grid-cols-2">
          <SectionCard title="Missing Required Requirements">
            {result.score_breakdown.missing_required.length > 0 ? (
              <ul className="space-y-2">
                {result.score_breakdown.missing_required.map((item) => (
                  <li
                    key={item}
                    className="rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-800"
                  >
                    {item}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-slate-600">No major required gaps found.</p>
            )}
          </SectionCard>

          <SectionCard title="Missing Preferred Requirements">
            {result.score_breakdown.missing_preferred.length > 0 ? (
              <ul className="space-y-2">
                {result.score_breakdown.missing_preferred.map((item) => (
                  <li
                    key={item}
                    className="rounded-xl border border-amber-100 bg-amber-50 px-4 py-3 text-sm text-amber-800"
                  >
                    {item}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-slate-600">No major preferred gaps found.</p>
            )}
          </SectionCard>
        </div>

        <SectionCard title="Top Improvement Priorities">
          {result.score_breakdown.improvement_priorities.length > 0 ? (
            <ul className="space-y-2">
              {result.score_breakdown.improvement_priorities.map((item) => (
                <li
                  key={item}
                  className="rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-700"
                >
                  {item}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-slate-600">
              No improvement priorities generated.
            </p>
          )}
        </SectionCard>

        <SectionCard title="Requirement Matches">
          {result.score_breakdown.matched_requirements.length > 0 ? (
            <div className="space-y-4">
              {result.score_breakdown.matched_requirements.map((req, idx) => (
                <div
                  key={`${req.requirement}-${idx}`}
                  className="rounded-2xl border border-slate-200 p-4"
                >
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <p className="font-semibold text-slate-900">
                      {req.requirement}
                    </p>
                    <span className="w-fit rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
                      {req.importance} • {req.category}
                    </span>
                  </div>

                  <div className="mt-3 grid gap-2 text-sm text-slate-600 sm:grid-cols-3">
                    <p>Matched: {req.matched ? "Yes" : "No"}</p>
                    <p>Score: {req.score}</p>
                    <p>Evidence: {req.evidence_score}/5</p>
                  </div>

                  {req.best_evidence && (
                    <div className="mt-3 rounded-xl bg-slate-50 p-3 text-sm text-slate-700">
                      <span className="font-medium">Best evidence:</span>{" "}
                      {req.best_evidence}
                    </div>
                  )}

                  {req.notes && (
                    <p className="mt-2 text-sm text-slate-500">{req.notes}</p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-slate-600">No requirement matches available.</p>
          )}
        </SectionCard>

        <div className="grid gap-6 xl:grid-cols-2">
          <SectionCard title="Missing Keywords">
            {result.missing_keywords.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {result.missing_keywords.map((kw) => (
                  <span
                    key={kw}
                    className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm text-slate-700"
                  >
                    {kw}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-slate-600">No major missing keywords found.</p>
            )}
          </SectionCard>

          <SectionCard title="Weak Bullets">
            {result.weak_bullet_details.length > 0 ? (
              <ul className="space-y-3">
                {result.weak_bullet_details.map((item) => {
                  const state = bulletState[item.id];

                  return (
                    <li
                      key={item.id}
                      className={`rounded-2xl border p-4 ${
                        state?.improved
                          ? "border-emerald-200 bg-emerald-50/50"
                          : "border-slate-200"
                      }`}
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="space-y-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="font-medium text-slate-900">
                              {state?.currentText ?? item.text}
                            </p>
                          </div>

                          {state?.improved &&
                            state.currentText !== item.text && (
                              <p className="text-xs text-slate-500">
                                Original: {item.text}
                              </p>
                            )}
                          <p className="mt-3 text-sm text-slate-600">
                            Reasons: {item.reasons.join(", ")}
                          </p>
                          <button
                            type="button"
                            onClick={() => openPlanMode(item)}
                            className="rounded-2xl bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
                          >
                            {state?.messages?.length
                              ? "Continue plan mode"
                              : "Improve in plan mode"}
                          </button>
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="text-slate-600">No obviously weak bullets found.</p>
            )}
          </SectionCard>
        </div>
      </div>

      <PlanModeModal
        isOpen={!!selectedBullet}
        bullet={selectedBullet}
        currentBullet={selectedState?.currentText ?? selectedBullet?.text ?? ""}
        jobDescription={jobDescription}
        messages={selectedState?.messages ?? []}
        options={selectedState?.options ?? []}
        loading={modalLoading}
        onClose={closePlanMode}
        onMessagesChange={updateSelectedMessages}
        onOptionsChange={updateSelectedOptions}
        onCurrentBulletChange={updateSelectedCurrentBullet}
        onApplyOption={applyOption}
      />
    </>
  );
}
