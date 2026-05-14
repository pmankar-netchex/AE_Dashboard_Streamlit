import { api } from "./client";

export type Role = "admin" | "user";

export interface UserRow {
  email: string;
  role: Role;
  is_active: boolean;
  added_by: string;
  added_at: string;
}

export function listUsers(): Promise<UserRow[]> {
  return api<UserRow[]>("/api/users");
}

export function createUser(body: {
  email: string;
  role: Role;
  is_active?: boolean;
}): Promise<UserRow> {
  return api<UserRow>("/api/users", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateUser(
  email: string,
  body: { role?: Role; is_active?: boolean },
): Promise<UserRow> {
  return api<UserRow>(`/api/users/${encodeURIComponent(email)}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export function deleteUser(email: string): Promise<void> {
  return api<void>(`/api/users/${encodeURIComponent(email)}`, {
    method: "DELETE",
  });
}
