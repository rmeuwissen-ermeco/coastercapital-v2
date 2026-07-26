import { CatalogueDiscovery } from "@/components/catalogue-discovery";

const highlights = [
  {
    eyebrow: "Source-driven",
    title: "Every fact keeps its provenance",
    body: "See where a specification came from, when it was retrieved and how it was reviewed.",
  },
  {
    eyebrow: "Community-reviewed",
    title: "Proposals before publication",
    body: "AI and editors suggest changes. Canonical data changes only after an accountable review.",
  },
  {
    eyebrow: "API-first",
    title: "Structured for reuse",
    body: "A stable data contract powers the website, research exports and future commercial APIs.",
  },
];

export default function Home() {
  return (
    <div className="site-shell">
      <header className="top-app-bar">
        <a className="brand" href="#" aria-label="Coaster Capital home">
          <span className="brand-mark" aria-hidden="true">
            C
          </span>
          <span>Coaster Capital</span>
        </a>
        <nav className="primary-nav" aria-label="Primary navigation">
          <a href="#discover">Discover</a>
          <a href="#database">Database</a>
          <a href="#about">About</a>
        </nav>
        <a className="tonal-button" href="/admin">
          Open admin
        </a>
      </header>

      <main>
        <section className="hero" id="discover">
          <div className="hero-copy">
            <p className="label-large">THE KNOWLEDGE BASE FOR ROLLER COASTERS</p>
            <h1>Coaster facts you can trace and trust.</h1>
            <p className="hero-intro">
              Explore structured roller coaster data with transparent sources,
              human review and AI-assisted discovery.
            </p>

            <CatalogueDiscovery />
          </div>

          <div className="hero-visual" aria-label="Illustrated coaster data card">
            <div className="track track-one" />
            <div className="track track-two" />
            <article className="coaster-card">
              <div className="card-image">
                <span className="status-chip">Verified</span>
              </div>
              <div className="card-content">
                <p className="label-medium">FEATURED COASTER</p>
                <h2>Baron 1898</h2>
                <p>Efteling · B&amp;M Dive Coaster</p>
                <dl>
                  <div>
                    <dt>Height</dt>
                    <dd>37.5 m</dd>
                  </div>
                  <div>
                    <dt>Speed</dt>
                    <dd>90 km/h</dd>
                  </div>
                  <div>
                    <dt>Opened</dt>
                    <dd>2015</dd>
                  </div>
                </dl>
              </div>
            </article>
          </div>
        </section>

        <section className="principles-section" id="database">
          <div className="section-heading">
            <p className="label-large">BUILT DIFFERENTLY</p>
            <h2>One coherent data platform</h2>
            <p>
              The public site, administration and external API share the same
              definitions and review rules.
            </p>
          </div>
          <div className="feature-grid">
            {highlights.map((item, index) => (
              <article className="feature-card" key={item.title}>
                <span className="feature-number">0{index + 1}</span>
                <p className="label-medium">{item.eyebrow}</p>
                <h3>{item.title}</h3>
                <p>{item.body}</p>
              </article>
            ))}
          </div>
        </section>
      </main>

      <footer id="about">
        <a className="brand footer-brand" href="#">
          <span className="brand-mark" aria-hidden="true">
            C
          </span>
          <span>Coaster Capital</span>
        </a>
        <p>Run 2 data core · Source-driven by design.</p>
      </footer>
    </div>
  );
}
