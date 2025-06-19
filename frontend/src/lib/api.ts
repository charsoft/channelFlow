// src/lib/api.ts
import { get } from 'svelte/store';
import { accessToken } from './auth';
import { videoStatus, statusHistory, resetStores } from './stores';

async function getHeaders() {
    const token = get(accessToken);
    const headers: HeadersInit = {
        'Content-Type': 'application/json',
    };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
}

export async function checkVideo(
    url: string
): Promise<{ exists: boolean; video_id: string | null }> {
    const res = await fetch('/api/ingest-url', {
        method: 'POST',
        headers: await getHeaders(),
        body: JSON.stringify({ url, force: false })
    });

    if (res.status === 403) {
        const err = await res.json();
        const error: any = new Error(err.message || 'Authorization failed. Please connect your YouTube account.');
        error.code = err.code;
        throw error;
    }

    const json = await res.json();
    if (res.ok && json.status === 'exists') {
        return { exists: true, video_id: json.data.video_id };
    }
    
    return { exists: false, video_id: null };
}

export async function sendIngest(
    url: string,
    force: boolean
): Promise<string> {
    const res = await fetch('/api/ingest-url', {
        method: 'POST',
        headers: await getHeaders(),
        body: JSON.stringify({ url, force })
    });
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || `Server error ${res.status}`);
    }
    const json = await res.json();
    return json.video_id;
}

let eventSource: EventSource | null = null;

export function listenForUpdates(videoId: string) {
  // Close any existing connection
  if (eventSource) {
    eventSource.close();
  }

  // Clear old data from the stores
  resetStores();
  
  const es = new EventSource(`/api/stream-status/${videoId}`);
  
  es.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      videoStatus.set(data);
      statusHistory.update(currentHistory => [...currentHistory, data]);
    } catch (err) {
      console.error('Failed to parse SSE message', err);
    }
  };

  es.onerror = (err) => {
    console.error('EventSource failed:', err);
    es.close();
    // Here you could set an error state in a store if needed
  };
  
  eventSource = es;
  return es;
}

export async function exchangeAuthCode(code: string): Promise<void> {
    const res = await fetch('/api/oauth/exchange-code', {
        method: 'POST',
        headers: await getHeaders(), // This endpoint must be called *after* login
        body: JSON.stringify({ code })
    });
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to exchange authorization code.');
    }
}

export async function loginWithGoogle(idTokenFromGoogle: string): Promise<string> {
    const res = await fetch('/api/auth/google/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: idTokenFromGoogle })
    });

    const payload = await res.json();
    if (!res.ok) {
        // include status for extra context
        throw new Error(payload.detail || `Google login failed (${res.status})`);
    }

    return payload.access_token;
}

