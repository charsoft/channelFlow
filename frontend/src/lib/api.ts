// src/lib/api.ts
import { get } from 'svelte/store';
import { accessToken } from './auth';
import { videoStatus, statusHistory, resetStores } from './stores';

export async function getHeaders() {
    const token = get(accessToken);
    const headers: HeadersInit = {
        'Content-Type': 'application/json',
    };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
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
    if (!res.ok && res.status !== 202) { // Allow 202 to pass through
        const err = await res.json();
        const detail = err.detail || `Server error ${res.status}`;
        const finalErr = new Error(detail);
        if (err.code) finalErr.code = err.code;
        throw finalErr;
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

  // resetStores(); // This is now handled by the component.

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

export async function getVideoStatus(videoId: string): Promise<any> {
    const res = await fetch(`/api/status/${videoId}`, {
        headers: await getHeaders()
    });
    // This will not throw on 404, which is what we want.
    if (!res.ok) return null; 
    
    const payload = await res.json();
    return payload.data;
}

export async function retriggerStage(videoId: string, stage: string): Promise<void> {
  const res = await fetch('/api/re-trigger', {
    method: 'POST',
    headers: await getHeaders(),
    body: JSON.stringify({ video_id: videoId, stage: stage.toLowerCase() })
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || `Failed to re-trigger stage ${stage}`);
  }
}

export async function checkYouTubeConnection(): Promise<boolean> {
  try {
    const res = await fetch('/api/auth/youtube/status', {
      method: 'GET',
      headers: await getHeaders()
    });
    if (!res.ok) {
      // If we get a 401, it just means the user isn't logged in, which is fine.
      if (res.status === 401) return false;
      // For other errors, log them but treat as not connected.
      console.error(`API Error (${res.status}):`, await res.text());
      return false;
    }
    const data = await res.json();
    return data.isConnected === true;
  } catch (err) {
    console.error("Network or other error checking YouTube status:", err);
    return false;
  }
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

export async function disconnectYouTube(): Promise<void> {
    const res = await fetch('/api/auth/youtube/disconnect', {
        method: 'POST',
        headers: await getHeaders(),
    });

    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to disconnect YouTube account.');
    }
}
