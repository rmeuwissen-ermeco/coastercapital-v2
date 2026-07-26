export const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ??
  "http://127.0.0.1:8000";

export type Stats = {
  parks: number;
  manufacturers: number;
  coasters: number;
};

export type SearchResult = {
  id: string;
  entity_type: "coaster" | "park" | "manufacturer";
  name: string;
  slug: string;
  subtitle: string | null;
};

export type Country = {
  id: string;
  code: string;
  name: string;
};

export type Park = {
  id: string;
  name: string;
  slug: string;
  city: string | null;
  country: Country | null;
  is_active: boolean;
};

export type Manufacturer = {
  id: string;
  name: string;
  slug: string;
  founded_year: number | null;
  country: Country | null;
  is_active: boolean;
};

export type Coaster = {
  id: string;
  name: string;
  slug: string;
  status: string;
  park: Park;
  manufacturer: Manufacturer | null;
  is_active: boolean;
};

export type SourceEvidence = {
  id: string;
  source_type: string;
  source_url: string;
  source_label: string | null;
  retrieved_at: string;
  asserted_value: unknown;
  source_confidence: number | null;
  is_primary: boolean;
};

export type FieldProposal = {
  id: string;
  field_name: string;
  proposed_value: unknown;
  reviewed_value: unknown;
  current_value: unknown;
  evidence_status: string;
  proposal_status:
    | "pending"
    | "accepted"
    | "auto_accepted"
    | "rejected"
    | "insufficient_evidence"
    | "deferred"
    | "disputed";
  confidence: number;
  confidence_class: string;
  automation_class: "A" | "B" | "C";
  score_breakdown: Record<string, number> | null;
  has_conflict: boolean;
  auto_approval_eligible: boolean;
  is_manual_override: boolean;
  rationale: string | null;
  evidence: SourceEvidence[];
};

export type EnrichmentJob = {
  id: string;
  status: "pending" | "running" | "review" | "completed" | "failed";
  wikidata_id: string | null;
  wikipedia_title: string | null;
  source_report: Record<string, unknown> | null;
  ai_model: string | null;
  error_message: string | null;
  created_at: string;
  entity_type: "coaster" | "park" | "manufacturer";
  entity_id: string;
  entity_match_confidence: number | null;
  entity: { id: string; name: string; slug: string };
  coaster: Pick<Coaster, "id" | "name" | "slug"> | null;
  proposals: FieldProposal[];
};

export type Page<T> = {
  items: T[];
  meta: { total: number; limit: number; offset: number };
};

export async function api<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `API request failed (${response.status})`);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export async function adminApi<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(`/api/backend${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(body?.detail ?? `Admin request failed (${response.status})`);
  }
  return body as T;
}
