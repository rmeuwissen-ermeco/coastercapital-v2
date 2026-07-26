import Link from "next/link";
import { LogoutButton } from "@/components/logout-button";

const modules = [
  ["Parks", "Canonical park records, locations and source coverage"],
  ["Coasters", "Specifications, status history and relationships"],
  ["Manufacturers", "Companies, models and production history"],
  ["Proposals", "Source-backed facts waiting for review"],
];

export default function AdminPage() {
  return (
    <main className="admin-shell">
      <aside className="navigation-rail">
        <Link className="brand" href="/" aria-label="Back to Coaster Capital">
          <span className="brand-mark">C</span>
        </Link>
        <nav aria-label="Admin navigation">
          <a className="active" href="/admin">
            Overview
          </a>
          <Link href="/admin/data">Data</Link>
          <Link href="/admin/audit">Audit</Link>
          <a href="#">Sources</a>
        </nav>
      </aside>
      <section className="admin-content">
        <header className="admin-header">
          <div>
            <p className="label-large">COASTER CAPITAL ADMIN</p>
            <h1>Good morning</h1>
            <p>Manage canonical data and review source-backed proposals.</p>
          </div>
          <div className="admin-actions">
            <Link className="filled-button" href="/admin/data">
              Add record
            </Link>
            <LogoutButton />
          </div>
        </header>
        <div className="admin-summary">
          <article>
            <span>Pending proposals</span>
            <strong>0</strong>
            <Link href="/admin/audit">Open audit history</Link>
          </article>
          <article>
            <span>Source health</span>
            <strong>—</strong>
            <a href="#">Connect first source</a>
          </article>
          <article>
            <span>API status</span>
            <strong className="success-text">Healthy</strong>
            <a href="/admin/data">Open live catalogue</a>
          </article>
        </div>
        <div className="module-grid">
          {modules.map(([title, description]) => (
            <article key={title}>
              <div className="module-icon">{title.charAt(0)}</div>
              <div>
                <h2>{title}</h2>
                <p>{description}</p>
              </div>
              <Link aria-label={`Open ${title}`} href="/admin/data">
                →
              </Link>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
