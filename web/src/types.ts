export type Relevance = "high" | "medium" | "low";

export interface EvidenceCase {
  id: number;
  title: string;
  source: string;
  year: string;
  journal: string;
  journal_tier: string;
  relevance: Relevance;
  reason: string;
  cross_point: string;
  suggestion: string;
}

export interface PromptMilestone {
  version: string;
  change: string;
  result: string;
}

export interface RunSummary {
  run_type: string;
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
  cases: EvidenceCase[];
}
