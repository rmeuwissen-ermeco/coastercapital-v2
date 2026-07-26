"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import {
  adminApi,
  Coaster,
  EnrichmentJob,
  FieldProposal,
  Page,
} from "@/lib/api";

const FIELD_LABELS: Record<string, string> = {
  opened_on: "Opening date",
  height_m: "Height (m)",
  speed_kmh: "Speed (km/h)",
  length_m: "Track length (m)",
  summary: "Profile introduction",
};

export function EnrichmentReview() {
  const [coasters, setCoasters] = useState<Coaster[]>([]);
  const [jobs, setJobs] = useState<EnrichmentJob[]>([]);
  const [coasterId, setCoasterId] = useState("");
  const [wikidataId, setWikidataId] = useState("");
  const [message, setMessage] = useState("Loading enrichment workspace…");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [coasterPage, jobList] = await Promise.all([
        adminApi<Page<Coaster>>("/v1/coasters?limit=100"),
        adminApi<EnrichmentJob[]>("/v1/admin/enrichment/jobs"),
      ]);
      setCoasters(coasterPage.items);
      setCoasterId((current) => current || coasterPage.items[0]?.id || "");
      setJobs(jobList);
      setMessage("Ready · canonical data remains unchanged until approval");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not load enrichment data");
    }
  }, []);

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
    setMessage("Checking Wikidata and Wikipedia…");
    try {
      await adminApi("/v1/admin/enrichment/jobs", {
        method: "POST",
        body: JSON.stringify({
          coaster_id: coasterId,
          wikidata_id: wikidataId.trim() || null,
        }),
      });
      setWikidataId("");
      await load();
      setMessage("Source check complete · review each proposal below");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Enrichment failed");
    } finally {
      setBusy(false);
    }
  }

  async function review(proposal: FieldProposal, decision: "accepted" | "rejected") {
    setBusy(true);
    try {
      await adminApi(`/v1/admin/enrichment/proposals/${proposal.id}`, {
        method: "PATCH",
        body: JSON.stringify({ decision }),
      });
      await load();
      setMessage(
        decision === "accepted"
          ? "Proposal accepted and applied to the canonical record"
          : "Proposal rejected; the canonical record was not changed",
      );
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Review failed");
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
          <h2>Enrich a coaster</h2>
          <p>
            Search automatically, or enter a Wikidata Q-ID to prevent an ambiguous match.
          </p>
        </div>
        <form onSubmit={startJob}>
          <label>
            Coaster
            <select
              required
              value={coasterId}
              onChange={(event) => setCoasterId(event.target.value)}
            >
              {coasters.map((coaster) => (
                <option key={coaster.id} value={coaster.id}>
                  {coaster.name} · {coaster.park.name}
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
          <button className="filled-button" disabled={busy || !coasterId} type="submit">
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
                  <h2>{job.coaster.name}</h2>
                  <p>
                    {job.wikidata_id ?? "No Wikidata match"}
                    {job.wikipedia_title ? ` · ${job.wikipedia_title}` : ""}
                  </p>
                </div>
                <time>{new Date(job.created_at).toLocaleString("nl-NL")}</time>
              </header>
              {job.error_message && <p className="pipeline-error">{job.error_message}</p>}
              <div className="proposal-list">
                {job.proposals.map((proposal) => (
                  <ProposalCard
                    busy={busy}
                    key={proposal.id}
                    proposal={proposal}
                    review={review}
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

function ProposalCard({
  proposal,
  busy,
  review,
}: {
  proposal: FieldProposal;
  busy: boolean;
  review: (proposal: FieldProposal, decision: "accepted" | "rejected") => void;
}) {
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
          <dd>{Math.round(proposal.confidence * 100)}% · {proposal.evidence_status}</dd>
        </div>
      </dl>
      <div className="source-links">
        {proposal.evidence.map((source) => (
          <a href={source.source_url} key={source.id} rel="noreferrer" target="_blank">
            {source.source_type} ↗
          </a>
        ))}
      </div>
      {proposal.proposal_status === "pending" && (
        <div className="review-actions">
          <button
            className="tonal-button"
            disabled={busy}
            onClick={() => review(proposal, "rejected")}
            type="button"
          >
            Reject
          </button>
          <button
            className="filled-button"
            disabled={busy}
            onClick={() => review(proposal, "accepted")}
            type="button"
          >
            Accept
          </button>
        </div>
      )}
    </article>
  );
}

function formatValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "Not set";
  return typeof value === "string" || typeof value === "number"
    ? String(value)
    : JSON.stringify(value);
}
