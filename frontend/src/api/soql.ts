import { api } from "./client";

export interface SoqlEntry {
  col_id: string;
  display_name: string;
  section: string;
  description: string;
  aggregation: string;
  template_default: string;
  template_active: string;
  has_override: boolean;
  time_filter: boolean;
  computed: boolean;
  blocked: boolean;
}

export interface SoqlTestRequest {
  template: string;
  ae_user_id?: string | null;
  period?: string | null;
}

export interface SoqlTestResult {
  ok: boolean;
  value: number | null;
  total_size: number;
  soql: string;
  error: string | null;
}

export interface SoqlHistoryRow {
  version: string;
  template: string;
  saved_by: string;
  saved_at: string;
}

export function listSoql(): Promise<SoqlEntry[]> {
  return api<SoqlEntry[]>("/api/soql");
}

export function getSoql(colId: string): Promise<SoqlEntry> {
  return api<SoqlEntry>(`/api/soql/${encodeURIComponent(colId)}`);
}

export function updateSoql(colId: string, template: string): Promise<SoqlEntry> {
  return api<SoqlEntry>(`/api/soql/${encodeURIComponent(colId)}`, {
    method: "PUT",
    body: JSON.stringify({ template }),
  });
}

export function testSoql(
  colId: string,
  body: SoqlTestRequest,
): Promise<SoqlTestResult> {
  return api<SoqlTestResult>(`/api/soql/${encodeURIComponent(colId)}/test`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getSoqlHistory(colId: string): Promise<SoqlHistoryRow[]> {
  return api<SoqlHistoryRow[]>(`/api/soql/${encodeURIComponent(colId)}/history`);
}
