import Link from "next/link";

import { EnrichmentReview } from "@/components/enrichment-review";
import { LogoutButton } from "@/components/logout-button";

export default function AdminEnrichmentPage() {
  return (
    <main className="admin-shell">
      <aside className="navigation-rail">
        <Link className="brand" href="/" aria-label="Back to Coaster Capital">
          <span className="brand-mark">C</span>
        </Link>
        <nav aria-label="Admin navigation">
          <Link href="/admin">Overview</Link>
          <Link href="/admin/data">Data</Link>
          <Link className="active" href="/admin/enrichment">Enrichment</Link>
          <Link href="/admin/audit">Audit</Link>
        </nav>
      </aside>
      <section className="admin-content">
        <header className="admin-header">
          <div>
            <p className="label-large">AI DATA ENRICHMENT PIPELINE</p>
            <h1>Source-backed proposals</h1>
            <p>Collect facts, inspect provenance and approve changes field by field.</p>
          </div>
          <div className="admin-actions">
            <Link className="tonal-button" href="/admin/data">Open catalogue</Link>
            <LogoutButton />
          </div>
        </header>
        <EnrichmentReview />
      </section>
    </main>
  );
}
