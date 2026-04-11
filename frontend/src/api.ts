import type { Application, ImportMessage } from './types';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';

type ParsePayload = {
  raw_email: string;
  vendor?: string;
  subject?: string;
  job_title?: string | null;
  company?: string | null;
  location?: string | null;
  status?: string | null;
  requisition_id?: string | null;
  applied_at?: string | null;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json'
    },
    ...init
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }

  return (await response.json()) as T;
}

export async function getApplications(): Promise<Application[]> {
  return request<Application[]>('/applications');
}

export async function parseEmail(rawEmail: string): Promise<Application> {
  const payload: ParsePayload = {
    raw_email: rawEmail,
    vendor: 'workday',
    subject: '',
    job_title: null,
    company: null,
    location: null,
    status: null,
    requisition_id: null,
    applied_at: null
  };

  return request<Application>('/parse', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function importGmail(params: {
  limit: number;
  lookback_days: number;
  sender_filter?: string;
}): Promise<ImportMessage[]> {
  const searchParams = new URLSearchParams({
    limit: String(params.limit),
    lookback_days: String(params.lookback_days)
  });

  if (params.sender_filter?.trim()) {
    searchParams.set('sender_filter', params.sender_filter.trim());
  }

  return request<ImportMessage[]>(`/gmail/import?${searchParams.toString()}`, {
    method: 'POST'
  });
}
