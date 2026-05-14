import { api } from "./client";

export interface AuditEvent {
  timestamp: string;
  actor: string;
  entity: string;
  action: string;
  target: string;
  details: Record<string, unknown>;
}

export interface AuditPage {
  events: AuditEvent[];
  next_cursor: string | null;
}

export interface AuditQuery {
  cursor?: string | null;
  page_size?: number;
  entity?: string | null;
  actor?: string | null;
}

export function fetchAudit(q: AuditQuery = {}): Promise<AuditPage> {
  const sp = new URLSearchParams();
  if (q.cursor) sp.set("cursor", q.cursor);
  if (q.page_size) sp.set("page_size", String(q.page_size));
  if (q.entity) sp.set("entity", q.entity);
  if (q.actor) sp.set("actor", q.actor);
  const qs = sp.toString();
  return api<AuditPage>(`/api/audit${qs ? `?${qs}` : ""}`);
}
