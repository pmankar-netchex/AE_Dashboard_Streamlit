import { api } from "./client";

export interface SalesforceStatus {
  configured: boolean;
  has_token: boolean;
  instance_url: string | null;
  issued_at: number | null;
  age_seconds: number | null;
  last_error: string | null;
  last_success_at: number | null;
  token_origin: string | null;
  token_origin_is_generic: boolean;
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

export interface UserRoleSample {
  role_values: string[];
  total_active_users: number;
  error: string | null;
}

export function fetchUserRoles(): Promise<UserRoleSample> {
  return api<UserRoleSample>("/api/salesforce/user-roles");
}

export interface SalesforceUserInfoProbe {
  ok: boolean;
  status_code: number | null;
  user_id: string | null;
  username: string | null;
  email: string | null;
  display_name: string | null;
  organization_id: string | null;
  instance_url: string | null;
  latency_ms: number | null;
  error: string | null;
}

export function fetchUserInfoProbe(): Promise<SalesforceUserInfoProbe> {
  return api<SalesforceUserInfoProbe>("/api/salesforce/userinfo");
}
