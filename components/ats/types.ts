export type ViewState = "form" | "loading" | "result";

export type RequirementMatch = {
  requirement: string;
  category: string;
  importance: string;
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

export type WeakBullet = {
  id: string;
  text: string;
  section: string;
  reasons: string[];
};

export type Suggestion = {
  id: string;
  section: string;
  original_text: string;
  proposed_text: string;
  reason: string;
  estimated_score_impact: number;
  confidence: number;
};

export type ParsedProjectEntry = {
  title: string;
  metadata?: string | null;
  tech_stack?: string | null;
  bullets: string[];
};

export type ParsedExperienceEntry = {
  organization?: string | null;
  role: string;
  dates?: string | null;
  bullets: string[];
};

export type ParsedResumeSummary = {
  summary_text: string;
  skills: string[];
  sections_found: string[];
  projects: ParsedProjectEntry[];
  experience: ParsedExperienceEntry[];
  education_text: string;
  certifications_text: string;
  project_count: number;
  experience_count: number;
  parser_notes: string[];
};

export type AnalyzeResponse = {
  score_breakdown: ScoreBreakdown;
  missing_keywords: string[];
  weak_bullets: string[];
  weak_bullet_details: WeakBullet[];
  suggestions: Suggestion[];
  parsed_resume?: ParsedResumeSummary | null;
  debug?: {
    resume_skills: string[];
    jd_required_skills: string[];
    jd_preferred_skills: string[];
    jd_all_skills: string[];
  } | null;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export type PlanModeResponse = {
  mode: "question" | "options";
  reply: string;
  question?: string | null;
  options: string[];
  current_bullet: string;
};