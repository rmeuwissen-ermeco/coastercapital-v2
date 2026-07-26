"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import {
  api,
  Coaster,
  Manufacturer,
  Page,
  Park,
} from "@/lib/api";

type Kind = "park" | "manufacturer" | "coaster";

export function CatalogueManager() {
  const [parks, setParks] = useState<Park[]>([]);
  const [manufacturers, setManufacturers] = useState<Manufacturer[]>([]);
  const [coasters, setCoasters] = useState<Coaster[]>([]);
  const [kind, setKind] = useState<Kind>("park");
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [parkId, setParkId] = useState("");
  const [manufacturerId, setManufacturerId] = useState("");
  const [message, setMessage] = useState("Loading live catalogue…");

  const load = useCallback(async () => {
    try {
      const [parkPage, manufacturerPage, coasterPage] = await Promise.all([
        api<Page<Park>>("/v1/parks?limit=100"),
        api<Page<Manufacturer>>("/v1/manufacturers?limit=100"),
        api<Page<Coaster>>("/v1/coasters?limit=100"),
      ]);
      setParks(parkPage.items);
      setManufacturers(manufacturerPage.items);
      setCoasters(coasterPage.items);
      setParkId((current) => current || parkPage.items[0]?.id || "");
      setMessage("Live catalogue connected");
    } catch {
      setMessage("API not connected · configure NEXT_PUBLIC_API_URL in Vercel");
    }
  }, []);

  useEffect(() => {
    const task = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(task);
  }, [load]);

  async function createRecord(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("Saving…");
    try {
      if (kind === "park") {
        await api("/v1/parks", {
          method: "POST",
          body: JSON.stringify({ name, slug }),
        });
      } else if (kind === "manufacturer") {
        await api("/v1/manufacturers", {
          method: "POST",
          body: JSON.stringify({ name, slug }),
        });
      } else {
        await api("/v1/coasters", {
          method: "POST",
          body: JSON.stringify({
            name,
            slug,
            park_id: parkId,
            manufacturer_id: manufacturerId || null,
          }),
        });
      }
      setName("");
      setSlug("");
      await load();
      setMessage(`${name} saved`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not save record");
    }
  }

  return (
    <>
      <section className="data-toolbar" aria-label="Catalogue status">
        <div>
          <span>API connection</span>
          <strong>{message}</strong>
        </div>
        <button className="tonal-button" onClick={() => void load()} type="button">
          Refresh data
        </button>
      </section>

      <section className="record-creator">
        <div>
          <p className="label-large">CREATE CANONICAL RECORD</p>
          <h2>Add catalogue data</h2>
          <p>Create a park or manufacturer first, then connect a coaster.</p>
        </div>
        <form onSubmit={createRecord}>
          <label>
            Record type
            <select value={kind} onChange={(event) => setKind(event.target.value as Kind)}>
              <option value="park">Park</option>
              <option value="manufacturer">Manufacturer</option>
              <option value="coaster">Coaster</option>
            </select>
          </label>
          <label>
            Name
            <input
              minLength={kind === "coaster" ? 1 : 2}
              onChange={(event) => setName(event.target.value)}
              required
              value={name}
            />
          </label>
          <label>
            Slug
            <input
              onChange={(event) => setSlug(event.target.value)}
              pattern="[a-z0-9]+(?:-[a-z0-9]+)*"
              placeholder="lowercase-with-dashes"
              required
              value={slug}
            />
          </label>
          {kind === "coaster" && (
            <>
              <label>
                Park
                <select
                  onChange={(event) => setParkId(event.target.value)}
                  required
                  value={parkId}
                >
                  <option value="">Select park</option>
                  {parks.map((park) => (
                    <option key={park.id} value={park.id}>
                      {park.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Manufacturer
                <select
                  onChange={(event) => setManufacturerId(event.target.value)}
                  value={manufacturerId}
                >
                  <option value="">Unknown / not set</option>
                  {manufacturers.map((manufacturer) => (
                    <option key={manufacturer.id} value={manufacturer.id}>
                      {manufacturer.name}
                    </option>
                  ))}
                </select>
              </label>
            </>
          )}
          <button className="filled-button" type="submit">
            Save record
          </button>
        </form>
      </section>

      <section className="catalogue-columns">
        <RecordList title="Parks" records={parks.map((item) => [item.name, item.city])} />
        <RecordList
          title="Manufacturers"
          records={manufacturers.map((item) => [
            item.name,
            item.founded_year?.toString() ?? null,
          ])}
        />
        <RecordList
          title="Coasters"
          records={coasters.map((item) => [item.name, item.park.name])}
        />
      </section>
    </>
  );
}

function RecordList({
  title,
  records,
}: {
  title: string;
  records: [string, string | null][];
}) {
  return (
    <article className="record-list">
      <header>
        <h2>{title}</h2>
        <span>{records.length}</span>
      </header>
      {records.length === 0 ? (
        <p>No records yet</p>
      ) : (
        <ul>
          {records.map(([name, context]) => (
            <li key={`${name}-${context}`}>
              <strong>{name}</strong>
              <small>{context ?? "Canonical record"}</small>
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}
