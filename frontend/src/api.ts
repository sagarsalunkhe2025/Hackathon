// API types matching the backend models

export interface ChatRequest {
  prompt: string;
  category?: string;
}

export interface ChatResponse {
  summary: string;
  sqlQuery?: string;
  data?: Record<string, unknown>[];
  analysisType?: string;
  insights?: AnalysisInsight[];
  success: boolean;
  error?: string;
}

export interface AnalysisInsight {
  title: string;
  description: string;
  severity: 'info' | 'warning' | 'critical';
  relatedData?: Record<string, unknown>[];
}

export interface QuickAnalysisRequest {
  analysisType: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  response?: ChatResponse;
  loading?: boolean;
}

const API_BASE = '/api';

export async function sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  return res.json();
}

export async function getAnalysisTypes(): Promise<Record<string, string>> {
  const res = await fetch(`${API_BASE}/analysis/types`);
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  return res.json();
}

export async function runAnalysis(request: QuickAnalysisRequest): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/analysis/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  return res.json();
}
