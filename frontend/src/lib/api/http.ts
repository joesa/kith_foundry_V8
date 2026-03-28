import { apiPath } from './config';

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(message: string, status: number, detail?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

async function parseJson(res: Response): Promise<unknown> {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(apiPath(path), { credentials: 'include' });
  if (!res.ok) {
    const body = await parseJson(res);
    throw new ApiError(`GET ${path} failed`, res.status, body);
  }
  return (await res.json()) as T;
}

export async function apiPost<T, B = unknown>(path: string, body?: B): Promise<T> {
  const res = await fetch(apiPath(path), {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) {
    const parsed = await parseJson(res);
    throw new ApiError(`POST ${path} failed`, res.status, parsed);
  }
  return (await res.json()) as T;
}

export async function apiPatch<T, B = unknown>(path: string, body: B): Promise<T> {
  const res = await fetch(apiPath(path), {
    method: 'PATCH',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const parsed = await parseJson(res);
    throw new ApiError(`PATCH ${path} failed`, res.status, parsed);
  }
  return (await res.json()) as T;
}

export async function apiPut<T, B = unknown>(path: string, body: B): Promise<T> {
  const res = await fetch(apiPath(path), {
    method: 'PUT',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const parsed = await parseJson(res);
    throw new ApiError(`PUT ${path} failed`, res.status, parsed);
  }
  return (await res.json()) as T;
}

export async function apiDelete(path: string): Promise<void> {
  const res = await fetch(apiPath(path), {
    method: 'DELETE',
    credentials: 'include',
  });
  // 204 No Content is success; 404 is also treated as ok (already gone)
  if (!res.ok && res.status !== 404) {
    const parsed = await parseJson(res);
    throw new ApiError(`DELETE ${path} failed`, res.status, parsed);
  }
}
