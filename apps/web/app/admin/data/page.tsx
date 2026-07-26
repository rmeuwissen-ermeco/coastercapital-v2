import Link from "next/link";

import { CatalogueManager } from "@/components/catalogue-manager";

export default function AdminDataPage() {
  return (
    <main className="admin-shell">
      <aside className="navigation-rail">
        <Link className="brand" href="/" aria-label="Back to Coaster Capital">
          <span className="brand-mark">C</span>
        </Link>
        <nav aria-label="Admin navigation">
          <Link href="/admin">Overview</Link>
          <Link className="active" href="/admin/data">
            Data
          </Link>
          <a href="#">Review</a>
          <a href="#">Sources</a>
        </nav>
      </aside>
      <section className="admin-content">
        <header className="admin-header">
          <div>
            <p className="label-large">CATALOGUE MANAGEMENT</p>
            <h1>Data core</h1>
            <p>Create and inspect records through the live API.</p>
          </div>
          <Link className="tonal-button" href="/">
            View public site
          </Link>
        </header>
        <CatalogueManager />
      </section>
    </main>
  );
}
