export type RequirementMatch = {
  requirement: string;
  category: string;
  importance: "required" | "preferred";
  matched: boolean;
  score: number;
  evidence_score: number;
  best_evidence?: string | null;
  notes?: string | null;
};

export type ScoreBreakdown = {
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

export type AnalyzeResponse = {
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

export type ViewState = "form" | "loading" | "result";