import { AnalyzeResponse } from "./types";
import ScoreBar from "./ScoreBar";

export default function ScoreSidebar({ result }: { result: AnalyzeResponse }) {
  return (
    <aside className="space-y-6">
      <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-sm font-medium text-slate-500">Overall Score</p>
        <p className="mt-2 text-6xl font-bold tracking-tight">
          {result.score_breakdown.overall_score}
        </p>
        <p className="mt-1 text-slate-500">out of 100</p>

        <div className="mt-6 space-y-4">
          <ScoreBar
            label="Required Coverage"
            value={result.score_breakdown.required_coverage}
          />
          <ScoreBar
            label="Preferred Coverage"
            value={result.score_breakdown.preferred_coverage}
          />
          <ScoreBar
            label="Semantic Alignment"
            value={result.score_breakdown.semantic_alignment}
          />
          <ScoreBar
            label="Evidence Strength"
            value={result.score_breakdown.evidence_strength}
          />
          <ScoreBar
            label="Bullet Quality"
            value={result.score_breakdown.bullet_quality}
          />
          <ScoreBar
            label="Formatting"
            value={result.score_breakdown.formatting}
          />
          <ScoreBar
            label="Title Alignment"
            value={result.score_breakdown.title_alignment}
          />
        </div>
      </div>
    </aside>
  );
}
