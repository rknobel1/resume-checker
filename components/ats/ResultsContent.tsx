"use client";

import { useMemo, useState } from "react";
import SectionCard from "./SectionCard";
import PlanModeModal from "./PlanModeModal";
import {
  AnalyzeResponse,
  ChatMessage,
  ParsedExperienceEntry,
  ParsedProjectEntry,
  WeakBullet,
} from "./types";

type BulletUiState = {
  currentText: string;
  improved: boolean;
  messages: ChatMessage[];
  options: string[];
};

type ResultsTab = "resume" | "analysis";

function ParsedProjectList({
  projects,
  weakBulletLookup,
  bulletState,
  onImprove,
}: {
  projects: ParsedProjectEntry[];
  weakBulletLookup: Map<string, WeakBullet>;
  bulletState: Record<string, BulletUiState>;
  onImprove: (bullet: WeakBullet) => void;
}) {
  if (!projects.length) {
    return <p className="text-slate-600">No projects detected.</p>;
  }

  return (
    <div className="space-y-4">
      {projects.map((project, idx) => (
        <div
          key={`${project.title}-${idx}`}
          className="rounded-2xl border border-slate-200 p-4"
        >
          <p className="font-semibold text-slate-900">{project.title}</p>

          {project.metadata && (
            <p className="mt-1 text-sm text-slate-600">{project.metadata}</p>
          )}

          {project.tech_stack && (
            <p className="mt-1 text-sm italic text-slate-500">
              {project.tech_stack}
            </p>
          )}

          {project.bullets.length > 0 ? (
            <ul className="mt-3 space-y-2">
              {project.bullets.map((bullet, bulletIdx) => {
                const weakBullet = weakBulletLookup.get(bullet.trim());
                const state = weakBullet
                  ? bulletState[weakBullet.id]
                  : undefined;

                return (
                  <ResumeBullet
                    key={`${project.title}-${bulletIdx}`}
                    text={bullet}
                    weakBullet={weakBullet}
                    state={state}
                    onImprove={onImprove}
                  />
                );
              })}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-slate-500">No bullets found.</p>
          )}
        </div>
      ))}
    </div>
  );
}

function ParsedExperienceList({
  experience,
  weakBulletLookup,
  bulletState,
  onImprove,
}: {
  experience: ParsedExperienceEntry[];
  weakBulletLookup: Map<string, WeakBullet>;
  bulletState: Record<string, BulletUiState>;
  onImprove: (bullet: WeakBullet) => void;
}) {
  if (!experience.length) {
    return <p className="text-slate-600">No experience entries detected.</p>;
  }

  return (
    <div className="space-y-4">
      {experience.map((entry, idx) => (
        <div
          key={`${entry.role}-${idx}`}
          className="rounded-2xl border border-slate-200 p-4"
        >
          <p className="font-semibold text-slate-900">{entry.role}</p>

          {(entry.organization || entry.dates) && (
            <p className="mt-1 text-sm text-slate-600">
              {[entry.organization, entry.dates].filter(Boolean).join(" • ")}
            </p>
          )}

          {entry.bullets.length > 0 ? (
            <ul className="mt-3 space-y-2">
              {entry.bullets.map((bullet, bulletIdx) => {
                const weakBullet = weakBulletLookup.get(bullet.trim());
                const state = weakBullet
                  ? bulletState[weakBullet.id]
                  : undefined;

                return (
                  <ResumeBullet
                    key={`${entry.role}-${bulletIdx}`}
                    text={bullet}
                    weakBullet={weakBullet}
                    state={state}
                    onImprove={onImprove}
                  />
                );
              })}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-slate-500">No bullets found.</p>
          )}
        </div>
      ))}
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-2xl px-4 py-2 text-sm font-medium transition ${
        active
          ? "bg-slate-900 text-white"
          : "bg-slate-100 text-slate-700 hover:bg-slate-200"
      }`}
    >
      {children}
    </button>
  );
}

function ResumeBullet({
  text,
  weakBullet,
  state,
  onImprove,
}: {
  text: string;
  weakBullet?: WeakBullet;
  state?: BulletUiState;
  onImprove?: (bullet: WeakBullet) => void;
}) {
  const isWeak = !!weakBullet;
  const isImproved = !!state?.improved;

  return (
    <li
      className={`rounded-xl px-4 py-3 text-sm transition ${
        isImproved
          ? "border border-emerald-200 bg-emerald-50/70"
          : isWeak
            ? "border border-red-200 bg-red-50/70 hover:bg-red-100/70"
            : "bg-slate-50 text-slate-700"
      }`}
    >
      <div className="space-y-2">
        <p className="text-slate-800">
          {isImproved ? (state?.currentText ?? text) : text}
        </p>

        {isWeak && weakBullet && (
          <div className="flex flex-wrap items-center gap-2">
            {!isImproved && (
              <p className="text-xs text-red-700">
                Needs improvement: {weakBullet.reasons.join(", ")}
              </p>
            )}

            <button
              type="button"
              onClick={() => onImprove?.(weakBullet)}
              className={`rounded-2xl px-3 py-1.5 text-xs font-medium ${
                isImproved
                  ? "bg-emerald-700 text-white hover:bg-emerald-800"
                  : "bg-slate-900 text-white hover:bg-slate-800"
              }`}
            >
              {state?.messages?.length ? "Continue plan mode" : "Improve"}
            </button>
          </div>
        )}
      </div>
    </li>
  );
}

export default function ResultsContent({
  result,
}: {
  result: AnalyzeResponse;
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

  const weakBulletLookup = useMemo(() => {
    const map = new Map<string, WeakBullet>();
    for (const bullet of result.weak_bullet_details) {
      map.set(bullet.text.trim(), bullet);
    }
    return map;
  }, [result.weak_bullet_details]);

  const [bulletState, setBulletState] =
    useState<Record<string, BulletUiState>>(initialBulletState);

  const [selectedBullet, setSelectedBullet] = useState<WeakBullet | null>(null);
  const [modalLoading, setModalLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<ResultsTab>("resume");

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
        <div className="flex flex-wrap gap-3">
          <TabButton
            active={activeTab === "resume"}
            onClick={() => setActiveTab("resume")}
          >
            Resume View
          </TabButton>

          <TabButton
            active={activeTab === "analysis"}
            onClick={() => setActiveTab("analysis")}
          >
            Analysis
          </TabButton>
        </div>

        {activeTab === "resume" && (
          <>
            {result.parsed_resume ? (
              <SectionCard title="What we read from your resume">
                <div className="space-y-6">
                  <div className="grid gap-4 md:grid-cols-3">
                    <div className="rounded-2xl bg-slate-50 p-4">
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Sections found
                      </p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {result.parsed_resume.sections_found.length > 0 ? (
                          result.parsed_resume.sections_found.map((section) => (
                            <span
                              key={section}
                              className="rounded-full border border-slate-200 bg-white px-3 py-1 text-sm text-slate-700"
                            >
                              {section}
                            </span>
                          ))
                        ) : (
                          <p className="text-sm text-slate-600">
                            None detected
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="rounded-2xl bg-slate-50 p-4">
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Experience entries
                      </p>
                      <p className="mt-3 text-2xl font-bold text-slate-900">
                        {result.parsed_resume.experience_count}
                      </p>
                    </div>

                    <div className="rounded-2xl bg-slate-50 p-4">
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Project entries
                      </p>
                      <p className="mt-3 text-2xl font-bold text-slate-900">
                        {result.parsed_resume.project_count}
                      </p>
                    </div>
                  </div>

                  {result.parsed_resume.summary_text && (
                    <div>
                      <p className="text-sm font-semibold text-slate-900">
                        Summary
                      </p>
                      <p className="mt-2 rounded-2xl bg-slate-50 p-4 text-sm leading-6 text-slate-700">
                        {result.parsed_resume.summary_text}
                      </p>
                    </div>
                  )}

                  <div>
                    <p className="text-sm font-semibold text-slate-900">
                      Detected skills
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {result.parsed_resume.skills.length > 0 ? (
                        result.parsed_resume.skills.map((skill) => (
                          <span
                            key={skill}
                            className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm text-slate-700"
                          >
                            {skill}
                          </span>
                        ))
                      ) : (
                        <p className="text-slate-600">No skills detected.</p>
                      )}
                    </div>
                  </div>

                  <div className="space-y-6">
                    <div>
                      <p className="mb-3 text-sm font-semibold text-slate-900">
                        Experience
                      </p>
                      <ParsedExperienceList
                        experience={result.parsed_resume.experience}
                        weakBulletLookup={weakBulletLookup}
                        bulletState={bulletState}
                        onImprove={openPlanMode}
                      />
                    </div>

                    <div>
                      <p className="mb-3 text-sm font-semibold text-slate-900">
                        Projects
                      </p>
                      <ParsedProjectList
                        projects={result.parsed_resume.projects}
                        weakBulletLookup={weakBulletLookup}
                        bulletState={bulletState}
                        onImprove={openPlanMode}
                      />
                    </div>
                  </div>

                  {result.parsed_resume.education_text && (
                    <div>
                      <p className="text-sm font-semibold text-slate-900">
                        Education
                      </p>
                      <p className="mt-2 whitespace-pre-wrap rounded-2xl bg-slate-50 p-4 text-sm leading-6 text-slate-700">
                        {result.parsed_resume.education_text}
                      </p>
                    </div>
                  )}

                  {result.parsed_resume.certifications_text && (
                    <div>
                      <p className="text-sm font-semibold text-slate-900">
                        Certifications
                      </p>
                      <p className="mt-2 whitespace-pre-wrap rounded-2xl bg-slate-50 p-4 text-sm leading-6 text-slate-700">
                        {result.parsed_resume.certifications_text}
                      </p>
                    </div>
                  )}

                  {result.parsed_resume.parser_notes.length > 0 && (
                    <div>
                      <p className="text-sm font-semibold text-slate-900">
                        Parser notes
                      </p>
                      <ul className="mt-2 space-y-2">
                        {result.parsed_resume.parser_notes.map((note) => (
                          <li
                            key={note}
                            className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700"
                          >
                            {note}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </SectionCard>
            ) : (
              <SectionCard title="What we read from your resume">
                <p className="text-slate-600">
                  No parsed resume data available.
                </p>
              </SectionCard>
            )}
          </>
        )}

        {activeTab === "analysis" && (
          <>
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

            <div className="space-y-6">
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
                  <p className="text-slate-600">
                    No major required gaps found.
                  </p>
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
                  <p className="text-slate-600">
                    No major preferred gaps found.
                  </p>
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

            <div className="space-y-6">
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
                  <p className="text-slate-600">
                    No major missing keywords found.
                  </p>
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
                  <p className="text-slate-600">
                    No obviously weak bullets found.
                  </p>
                )}
              </SectionCard>
            </div>
          </>
        )}
      </div>

      <PlanModeModal
        isOpen={!!selectedBullet}
        bullet={selectedBullet}
        currentBullet={selectedState?.currentText ?? selectedBullet?.text ?? ""}
        jdJsonSummary={result.jd_json_summary}
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
