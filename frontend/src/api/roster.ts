import { api } from "./client";

export interface RosterEntry {
  sf_id: string;
  name: string;
  email: string;
  manager_name: string;
  manager_id: string;
  sdr_id: string;
  sdr_name: string;
  sdr_email: string;
  added_by: string;
  added_at: string;
}

export interface SfUserResult {
  id: string;
  name: string;
  email: string;
  manager_name: string;
  manager_id: string;
  sdr_id: string;
  sdr_name: string;
  sdr_email: string;
}

export interface RosterImportResult {
  imported: number;
}

export function fetchRoster(): Promise<RosterEntry[]> {
  return api<RosterEntry[]>("/api/roster");
}

export function searchSfUsers(q: string): Promise<SfUserResult[]> {
  return api<SfUserResult[]>(`/api/roster/search?q=${encodeURIComponent(q)}`);
}

export function importFromSf(): Promise<RosterImportResult> {
  return api<RosterImportResult>("/api/roster/import", { method: "POST" });
}

export function addToRoster(sfId: string): Promise<RosterEntry> {
  return api<RosterEntry>(`/api/roster/${encodeURIComponent(sfId)}`, { method: "POST" });
}

export function removeFromRoster(sfId: string): Promise<void> {
  return api<void>(`/api/roster/${encodeURIComponent(sfId)}`, { method: "DELETE" });
}
