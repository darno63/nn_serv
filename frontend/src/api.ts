import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';
const API_PREFIX = import.meta.env.VITE_API_PREFIX ?? '/api';

const client = axios.create({
  baseURL: API_BASE_URL || undefined,
  headers: {
    'Content-Type': 'application/json'
  }
});

export type GeneratePayload = {
  prompt: string;
  negativePrompt?: string;
  seed?: number | null;
  numFrames?: number;
};

export async function fetchHealth(): Promise<string> {
  const response = await client.get(`${API_PREFIX}/health`);
  if (typeof response.data === 'string') {
    return response.data;
  }
  return JSON.stringify(response.data);
}

export async function submitGeneration(payload: GeneratePayload): Promise<unknown> {
  const response = await client.post(`${API_PREFIX}/generate`, payload);
  return response.data;
}
