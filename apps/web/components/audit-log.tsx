"use client";

import { useEffect, useState } from "react";

import { adminApi } from "@/lib/api";

type AuditEvent = {
  id: string;
  action: string;
  entity_type: string;
  entity_id: string;
  changes: Record<string, unknown> | null;
  created_at: string;
  actor: { email: string };
};

export function AuditLog() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [message, setMessage] = useState("Loading audit history…");

  useEffect(() => {
    const task = window.setTimeout(() => {
      adminApi<AuditEvent[]>("/v1/admin/audit-events")
        .then((data) => {
          setEvents(data);
          setMessage(data.length ? "" : "No changes recorded yet");
        })
        .catch((error) =>
          setMessage(error instanceof Error ? error.message : "Could not load audit history"),
        );
    }, 0);
    return () => window.clearTimeout(task);
  }, []);

  if (message) return <p className="audit-message">{message}</p>;

  return (
    <div className="audit-list">
      {events.map((event) => (
        <article key={event.id}>
          <div>
            <strong>
              {event.action} · {event.entity_type}
            </strong>
            <span>{event.actor.email}</span>
          </div>
          <time dateTime={event.created_at}>
            {new Date(event.created_at).toLocaleString()}
          </time>
          <code>{event.entity_id}</code>
        </article>
      ))}
    </div>
  );
}
