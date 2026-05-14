import { api } from "./client";

export interface SalesforceStatus {
  configured: boolean;
  has_token: boolean;
  instance_url: string | null;
  issued_at: number | null;
  age_seconds: number | null;
  last_error: string | null;
  last_success_at: number | null;
}

export interface SalesforceRefreshResult {
  ok: boolean;
  instance_url: string | null;
  latency_ms: number | null;
  error: string | null;
}

export function fetchSalesforceStatus(): Promise<SalesforceStatus> {
  return api<SalesforceStatus>("/api/salesforce/status");
}

export function refreshSalesforceToken(): Promise<SalesforceRefreshResult> {
  return api<SalesforceRefreshResult>("/api/salesforce/refresh", {
    method: "POST",
  });
}
