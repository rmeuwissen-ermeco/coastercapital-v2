"use client";

import { FormEvent, useEffect, useState } from "react";

import { api, SearchResult, Stats } from "@/lib/api";

const fallbackStats: Stats = { coasters: 0, parks: 0, manufacturers: 0 };

function SearchIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="m21 20-5.2-5.2a7 7 0 1 0-1 1L20 21l1-1ZM5 10.5a5.5 5.5 0 1 1 11 0 5.5 5.5 0 0 1-11 0Z" />
    </svg>
  );
}

export function CatalogueDiscovery() {
  const [stats, setStats] = useState(fallbackStats);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [message, setMessage] = useState("Connecting to the live catalogue…");

  useEffect(() => {
    api<Stats>("/v1/stats")
      .then((data) => {
        setStats(data);
        setMessage("Live catalogue connected");
      })
      .catch(() => setMessage("Demo mode · connect the catalogue API to search"));
  }, []);

  async function search(event: FormEvent) {
    event.preventDefault();
    if (query.trim().length < 2) return;

    setMessage("Searching…");
    try {
      const data = await api<SearchResult[]>(
        `/v1/search?query=${encodeURIComponent(query.trim())}`,
      );
      setResults(data);
      setMessage(data.length ? `${data.length} result(s)` : "No results found");
    } catch {
      setResults([]);
      setMessage("The catalogue API is not connected yet");
    }
  }

  const statItems = [
    { value: stats.coasters, label: "Coasters" },
    { value: stats.parks, label: "Parks" },
    { value: stats.manufacturers, label: "Manufacturers" },
  ];

  return (
    <>
      <form className="search-bar" role="search" onSubmit={search}>
        <SearchIcon />
        <label className="sr-only" htmlFor="coaster-search">
          Search coasters, parks or manufacturers
        </label>
        <input
          id="coaster-search"
          name="query"
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search coasters, parks or manufacturers"
          value={query}
        />
        <button type="submit">Search</button>
      </form>
      <p className="connection-state" aria-live="polite">
        {message}
      </p>
      {results.length > 0 && (
        <div className="search-results">
          {results.map((result) => (
            <article key={`${result.entity_type}-${result.id}`}>
              <span>{result.entity_type}</span>
              <strong>{result.name}</strong>
              <small>{result.subtitle ?? "Canonical record"}</small>
            </article>
          ))}
        </div>
      )}
      <div className="stat-row" aria-label="Live database statistics">
        {statItems.map((stat) => (
          <div className="stat" key={stat.label}>
            <strong>{stat.value.toLocaleString()}</strong>
            <span>{stat.label}</span>
          </div>
        ))}
      </div>
    </>
  );
}
