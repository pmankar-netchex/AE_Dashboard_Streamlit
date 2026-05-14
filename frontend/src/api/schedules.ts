import { api } from "./client";

export interface Schedule {
  id: string;
  name: string;
  cron: string;
  recipients: string[];
  subject: string;
  filters: Record<string, unknown>;
  is_active: boolean;
  created_by: string;
  created_at: string;
  last_run_at: string | null;
  last_run_status: string | null;
}

export interface ScheduleCreateIn {
  name: string;
  cron: string;
  recipients: string[];
  subject?: string;
  filters?: Record<string, unknown>;
  is_active?: boolean;
}

export interface ScheduleUpdateIn {
  name?: string;
  cron?: string;
  recipients?: string[];
  subject?: string;
  filters?: Record<string, unknown>;
  is_active?: boolean;
}

export interface SendNowResult {
  ok: boolean;
  message_id: string;
  error: string | null;
}

export function listSchedules(): Promise<Schedule[]> {
  return api<Schedule[]>("/api/schedules");
}

export function createSchedule(body: ScheduleCreateIn): Promise<Schedule> {
  return api<Schedule>("/api/schedules", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateSchedule(id: string, body: ScheduleUpdateIn): Promise<Schedule> {
  return api<Schedule>(`/api/schedules/${encodeURIComponent(id)}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export function deleteSchedule(id: string): Promise<void> {
  return api<void>(`/api/schedules/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

export function sendNow(id: string): Promise<SendNowResult> {
  return api<SendNowResult>(`/api/schedules/${encodeURIComponent(id)}/send-now`, {
    method: "POST",
  });
}
