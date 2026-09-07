export type Relevance = "high" | "medium" | "low";

export interface EvidenceCase {
  id: number;
  dedup_key: string;
  title: string;
  source: string;
  year: string;
  journal: string;
  journal_tier: string;
  relevance: Relevance;
  reason: string;
  cross_point: string;
  suggestion: string;
  has_direct_link: boolean;
  has_doi_fallback: boolean;
}

export interface DuplicateGroup {
  dedup_key: string;
  title: string;
  occurrences: number;
  files: string[];
}

export interface PromptMilestone {
  version: string;
  change: string;
  result: string;
}

export interface RunSummary {
  run_type: string;
  problem_context: {
    manual_screening_minutes_per_week: number;
    evidence_type: string;
    note: string;
  };
  scope: {
    input_boundary: string;
    automated_steps: string[];
    accuracy_evaluated: boolean;
    cross_domain_migration_validated: boolean;
  };
  model: {
    provider: string;
    name: string;
    prompt_version: string;
  };
  summary: {
    input_files: number;
    raw_records: number;
    unique_papers: number;
    duplicate_records_removed: number;
    sources: { CNKI: number; WOS: number };
    relevance: Record<Relevance, number>;
    links: {
      direct: number;
      doi_fallback: number;
      reachable_total: number;
      without_link: number;
    };
    recorded_at: string;
  };
  prompt_milestones: PromptMilestone[];
  duplicate_groups: DuplicateGroup[];
  cases: EvidenceCase[];
  records: EvidenceCase[];
}
