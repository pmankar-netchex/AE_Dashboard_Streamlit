const BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export interface SalesforceErrorPayload {
  error_code: "sf_session_expired" | "sf_auth_failed";
  instance_url: string | null;
  last_success_at: number | null;
}

export class ApiError extends Error {
  status: number;
  code?: number;
  errorCode?: string;
  salesforce?: SalesforceErrorPayload;
  constructor(
    message: string,
    status: number,
    extras: {
      code?: number;
      errorCode?: string;
      salesforce?: SalesforceErrorPayload;
    } = {},
  ) {
    super(message);
    this.status = status;
    this.code = extras.code;
    this.errorCode = extras.errorCode;
    this.salesforce = extras.salesforce;
  }
}

export function isSalesforceSessionError(err: unknown): err is ApiError {
  return (
    err instanceof ApiError &&
    (err.errorCode === "sf_session_expired" ||
      err.errorCode === "sf_auth_failed")
  );
}

interface ErrorBody {
  error?: string;
  detail?: string;
  error_code?: string;
  instance_url?: string | null;
  last_success_at?: number | null;
}

export async function api<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const url = `${BASE}${path}`;
  const res = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
  });
  if (!res.ok) {
    let body: ErrorBody = {};
    try {
      body = (await res.json()) as ErrorBody;
    } catch {
      // ignore
    }
    const detail = body.error ?? body.detail ?? res.statusText;
    const sf: SalesforceErrorPayload | undefined =
      body.error_code === "sf_session_expired" ||
      body.error_code === "sf_auth_failed"
        ? {
            error_code: body.error_code,
            instance_url: body.instance_url ?? null,
            last_success_at: body.last_success_at ?? null,
          }
        : undefined;
    throw new ApiError(detail, res.status, {
      errorCode: body.error_code,
      salesforce: sf,
    });
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}
