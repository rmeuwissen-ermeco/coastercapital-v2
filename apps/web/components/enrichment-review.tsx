"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import {
  adminApi,
  Coaster,
  EnrichmentJob,
  FieldProposal,
  Manufacturer,
  Page,
  Park,
} from "@/lib/api";

const FIELD_LABELS: Record<string, string> = {
  opened_on: "Opening date",
  height_m: "Height (m)",
  speed_kmh: "Speed (km/h)",
  length_m: "Track length (m)",
  summary: "Profile introduction",
  drop_m: "Drop (m)",
  inversions: "Inversions",
  capacity_pph: "Capacity (riders/hour)",
  city: "City",
  latitude: "Latitude",
  longitude: "Longitude",
  website_url: "Official website",
  founded_year: "Founded",
};

type EntityType = "coaster" | "park" | "manufacturer";
type EntityOption = { id: string; name: string; subtitle: string };
type ResearchCapabilities = {
  ai_available: boolean;
  ai_model: string | null;
  deterministic_research_available: boolean;
};

export function EnrichmentReview() {
  const [coasters, setCoasters] = useState<Coaster[]>([]);
  const [parks, setParks] = useState<Park[]>([]);
  const [manufacturers, setManufacturers] = useState<Manufacturer[]>([]);
  const [jobs, setJobs] = useState<EnrichmentJob[]>([]);
  const [entityType, setEntityType] = useState<EntityType>("coaster");
  const [entityId, setEntityId] = useState("");
  const [wikidataId, setWikidataId] = useState("");
  const [officialUrl, setOfficialUrl] = useState("");
  const [rcdbUrl, setRcdbUrl] = useState("");
  const [useAi, setUseAi] = useState(true);
  const [capabilities, setCapabilities] = useState<ResearchCapabilities | null>(null);
  const [message, setMessage] = useState("Loading enrichment workspace…");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [coasterPage, parkPage, manufacturerPage, jobList, researchCapabilities] =
        await Promise.all([
        adminApi<Page<Coaster>>("/v1/coasters?limit=100"),
        adminApi<Page<Park>>("/v1/parks?limit=100"),
        adminApi<Page<Manufacturer>>("/v1/manufacturers?limit=100"),
        adminApi<EnrichmentJob[]>("/v1/admin/enrichment/jobs"),
        adminApi<ResearchCapabilities>("/v1/admin/enrichment/capabilities"),
      ]);
      setCoasters(coasterPage.items);
      setParks(parkPage.items);
      setManufacturers(manufacturerPage.items);
      setEntityId((current) => current || coasterPage.items[0]?.id || "");
      setJobs(jobList);
      setCapabilities(researchCapabilities);
      if (!researchCapabilities.ai_available) setUseAi(false);
      setMessage("Ready · canonical data remains unchanged until approval");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not load enrichment data");
    }
  }, []);

  const entityOptions = useMemo<EntityOption[]>(() => {
    if (entityType === "park") {
      return parks.map((park) => ({
        id: park.id,
        name: park.name,
        subtitle: park.country?.name ?? park.city ?? "Park",
      }));
    }
    if (entityType === "manufacturer") {
      return manufacturers.map((manufacturer) => ({
        id: manufacturer.id,
        name: manufacturer.name,
        subtitle: manufacturer.country?.name ?? "Manufacturer",
      }));
    }
    return coasters.map((coaster) => ({
      id: coaster.id,
      name: coaster.name,
      subtitle: coaster.park.name,
    }));
  }, [coasters, entityType, manufacturers, parks]);

  useEffect(() => {
    const task = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(task);
  }, [load]);

  const pendingCount = useMemo(
    () =>
      jobs.reduce(
        (total, job) =>
          total + job.proposals.filter((item) => item.proposal_status === "pending").length,
        0,
      ),
    [jobs],
  );

  async function startJob(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("Collecting source assertions and calculating confidence…");
    try {
      await adminApi("/v1/admin/enrichment/jobs", {
        method: "POST",
        body: JSON.stringify({
          entity_type: entityType,
          entity_id: entityId,
          wikidata_id: wikidataId.trim() || null,
          official_url: officialUrl.trim() || null,
          rcdb_url: rcdbUrl.trim() || null,
          use_ai: useAi,
        }),
      });
      await load();
      setMessage("Source check complete · review each proposal below");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Enrichment failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <section className="data-toolbar">
        <div>
          <span>Pipeline status</span>
          <strong>{message}</strong>
        </div>
        <span className="proposal-counter">{pendingCount} pending</span>
      </section>

      <section className="record-creator enrichment-launcher">
        <div>
          <p className="label-large">SOURCE CHECK</p>
          <h2>Research canonical data</h2>
          <p>
            Sources provide assertions; the pipeline scores each proposed canonical value.
          </p>
        </div>
        <form onSubmit={startJob}>
          <label>
            Entity type
            <select
              value={entityType}
              onChange={(event) => {
                const nextType = event.target.value as EntityType;
                setEntityType(nextType);
                setEntityId(
                  nextType === "park"
                    ? parks[0]?.id ?? ""
                    : nextType === "manufacturer"
                      ? manufacturers[0]?.id ?? ""
                      : coasters[0]?.id ?? "",
                );
              }}
            >
              <option value="coaster">Coaster</option>
              <option value="park">Park</option>
              <option value="manufacturer">Manufacturer</option>
            </select>
          </label>
          <label>
            Entity
            <select
              required
              value={entityId}
              onChange={(event) => setEntityId(event.target.value)}
            >
              {entityOptions.map((entity) => (
                <option key={entity.id} value={entity.id}>
                  {entity.name} · {entity.subtitle}
                </option>
              ))}
            </select>
          </label>
          <label>
            Wikidata ID (optional)
            <input
              pattern="Q[1-9][0-9]*"
              placeholder="e.g. Q18285730"
              value={wikidataId}
              onChange={(event) => setWikidataId(event.target.value)}
            />
          </label>
          <label>
            Official source URL (optional)
            <input
              inputMode="url"
              placeholder="https://www.efteling.com/…"
              type="url"
              value={officialUrl}
              onChange={(event) => setOfficialUrl(event.target.value)}
            />
          </label>
          <label>
            RCDB record URL (optional)
            <input
              inputMode="url"
              pattern="https://(www\.)?rcdb\.com/.*"
              placeholder="https://rcdb.com/12083.htm"
              type="url"
              value={rcdbUrl}
              onChange={(event) => setRcdbUrl(event.target.value)}
            />
          </label>
          <label className="research-toggle">
            <input
              checked={useAi}
              disabled={!capabilities?.ai_available}
              type="checkbox"
              onChange={(event) => setUseAi(event.target.checked)}
            />
            Use AI to extract and compare source assertions
            {capabilities?.ai_model ? ` (${capabilities.ai_model})` : ""}
          </label>
          {capabilities && !capabilities.ai_available && (
            <p className="pipeline-warning">
              AI is unavailable until COASTER_OPENAI_API_KEY is configured. Deterministic
              Wikidata and RCDB research remains available.
            </p>
          )}
          <button className="filled-button" disabled={busy || !entityId} type="submit">
            {busy ? "Working…" : "Start source check"}
          </button>
        </form>
      </section>

      <section className="enrichment-jobs">
        {jobs.length === 0 ? (
          <div className="empty-review">
            <h2>No source checks yet</h2>
            <p>Start with Baron 1898 to test the complete review flow.</p>
          </div>
        ) : (
          jobs.map((job) => (
            <article className="enrichment-job" key={job.id}>
              <header>
                <div>
                  <span className={`status-chip status-${job.status}`}>{job.status}</span>
                  <h2>{job.entity.name}</h2>
                  <p>
                    {job.entity_type} · {job.wikidata_id ?? "No external identifier"}
                    {job.wikipedia_title ? ` · ${job.wikipedia_title}` : ""}
                    {job.ai_model ? ` · AI ${job.ai_model}` : " · AI not used"}
                  </p>
                </div>
                <time>{new Date(job.created_at).toLocaleString("nl-NL")}</time>
              </header>
              {job.error_message && <p className="pipeline-error">{job.error_message}</p>}
              {job.source_report && <SourceReport report={job.source_report} />}
              <div className="proposal-list">
                {job.proposals.map((proposal) => (
                  <ProposalCard
                    busy={busy}
                    key={proposal.id}
                    proposal={proposal}
                  />
                ))}
              </div>
            </article>
          ))
        )}
      </section>
    </>
  );
}

function SourceReport({ report }: { report: Record<string, unknown> }) {
  const sources = ["wikimedia", "official", "rcdb", "ai"];
  return (
    <div className="source-report">
      {sources.map((name) => {
        const detail = report[name] as Record<string, unknown> | undefined;
        if (!detail) return null;
        const url =
          typeof detail.final_url === "string"
            ? detail.final_url
            : typeof detail.url === "string"
              ? detail.url
              : null;
        const explanation =
          typeof detail.error === "string"
            ? detail.error
            : typeof detail.reason === "string"
              ? detail.reason
              : typeof detail.match_reason === "string"
                ? detail.match_reason
                : null;
        return (
          <div className={`source-state source-${String(detail.status)}`} key={name}>
            <strong>
              {name}: {String(detail.status)}
              {typeof detail.assertions === "number" ? ` · ${detail.assertions} facts` : ""}
            </strong>
            {url && (
              <a href={url} rel="noreferrer" target="_blank">
                {url} ↗
              </a>
            )}
            {typeof detail.http_status === "number" && (
              <small>
                HTTP {String(detail.http_status)}
                {typeof detail.title === "string" ? ` · ${detail.title}` : ""}
              </small>
            )}
            {explanation && <small>{explanation}</small>}
          </div>
        );
      })}
      {Array.isArray(report.warnings) && report.warnings.length > 0 && (
        <div className="source-warnings">
          {(report.warnings as string[]).map((warning) => (
            <small key={warning}>{warning}</small>
          ))}
        </div>
      )}
    </div>
  );
}

function ProposalCard({
  proposal,
  busy,
}: {
  proposal: FieldProposal;
  busy: boolean;
}) {
  const [value, setValue] = useState(formatEditableValue(proposal.proposed_value));
  const [reason, setReason] = useState("");
  const changed = value !== formatEditableValue(proposal.proposed_value);

  async function submit(decision: "accepted" | "rejected" | "insufficient_evidence" | "deferred") {
    const parsedValue = changed ? parseEditedValue(value, proposal.proposed_value) : undefined;
    await reviewProposal(proposal, decision, parsedValue, reason);
  }

  async function reviewProposal(
    item: FieldProposal,
    decision: "accepted" | "rejected" | "insufficient_evidence" | "deferred",
    editedValue?: unknown,
    overrideReason?: string,
  ) {
    await adminApi(`/v1/admin/enrichment/proposals/${item.id}`, {
      method: "PATCH",
      body: JSON.stringify({
        decision,
        value: editedValue,
        override_reason: overrideReason || null,
      }),
    });
    window.location.reload();
  }

  return (
    <article className="proposal-card">
      <div className="proposal-heading">
        <div>
          <span>{FIELD_LABELS[proposal.field_name] ?? proposal.field_name}</span>
          <strong>{formatValue(proposal.proposed_value)}</strong>
        </div>
        <span className={`status-chip status-${proposal.proposal_status}`}>
          {proposal.proposal_status}
        </span>
      </div>
      <dl>
        <div>
          <dt>Current</dt>
          <dd>{formatValue(proposal.current_value)}</dd>
        </div>
        <div>
          <dt>Confidence</dt>
          <dd>
            {Math.round(proposal.confidence * 100)}% ·{" "}
            {confidenceLabel(proposal.confidence_class)}
          </dd>
        </div>
        <div>
          <dt>Automation</dt>
          <dd>
            Class {proposal.automation_class} ·{" "}
            {proposal.auto_approval_eligible ? "eligible" : "manual review"}
          </dd>
        </div>
      </dl>
      {proposal.rationale && <p className="proposal-rationale">{proposal.rationale}</p>}
      <div className="source-links">
        {proposal.evidence.map((source) => (
          <a href={source.source_url} key={source.id} rel="noreferrer" target="_blank">
            {source.source_type} ↗
          </a>
        ))}
      </div>
      {proposal.proposal_status === "pending" && (
        <>
          <label className="proposal-editor">
            Final canonical value
            <input value={value} onChange={(event) => setValue(event.target.value)} />
          </label>
          {changed && (
            <label className="proposal-editor">
              Correction reason
              <textarea
                required
                value={reason}
                onChange={(event) => setReason(event.target.value)}
              />
            </label>
          )}
          <div className="review-actions">
          <button
            className="text-button"
            disabled={busy}
            onClick={() => void submit("deferred")}
            type="button"
          >
            Review later
          </button>
          <button
            className="text-button"
            disabled={busy}
            onClick={() => void submit("insufficient_evidence")}
            type="button"
          >
            Insufficient evidence
          </button>
          <button
            className="tonal-button"
            disabled={busy}
            onClick={() => void submit("rejected")}
            type="button"
          >
            Reject
          </button>
          <button
            className="filled-button"
            disabled={busy || (changed && !reason.trim())}
            onClick={() => void submit("accepted")}
            type="button"
          >
            {changed ? "Correct & accept" : "Accept"}
          </button>
        </div>
        </>
      )}
    </article>
  );
}

function formatEditableValue(value: unknown) {
  if (value === null || value === undefined) return "";
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}

function parseEditedValue(value: string, original: unknown): unknown {
  if (typeof original === "number") {
    const parsed = Number(value.replace(",", "."));
    return Number.isNaN(parsed) ? value : parsed;
  }
  return value;
}

function confidenceLabel(value: string) {
  return value.replaceAll("_", " ");
}

function formatValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "Not set";
  return typeof value === "string" || typeof value === "number"
    ? String(value)
    : JSON.stringify(value);
}
