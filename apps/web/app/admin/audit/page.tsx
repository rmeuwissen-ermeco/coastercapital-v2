import Link from "next/link";

import { AuditLog } from "@/components/audit-log";
import { LogoutButton } from "@/components/logout-button";

export default function AuditPage() {
  return (
    <main className="admin-shell">
      <aside className="navigation-rail">
        <Link className="brand" href="/">
          <span className="brand-mark">C</span>
        </Link>
        <nav aria-label="Admin navigation">
          <Link href="/admin">Overview</Link>
          <Link href="/admin/data">Data</Link>
          <Link className="active" href="/admin/audit">
            Audit
          </Link>
          <a href="#">Sources</a>
        </nav>
      </aside>
      <section className="admin-content">
        <header className="admin-header">
          <div>
            <p className="label-large">ACCOUNTABLE CHANGES</p>
            <h1>Audit history</h1>
            <p>Who changed which canonical record and when.</p>
          </div>
          <LogoutButton />
        </header>
        <AuditLog />
      </section>
    </main>
  );
}
