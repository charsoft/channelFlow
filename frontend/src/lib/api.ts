// src/lib/api.ts
import { get } from 'svelte/store';
import { accessToken } from './auth';
import { videoStatus, statusHistory, resetStores } from './stores';

async function getHeaders() {
    const token = typeof window !== 'undefined' ? localStorage.getItem('accessToken') : null;
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

  // resetStores(); // This is now handled by the component.
  
  const token = get(accessToken);
  if (!token) {
      console.error("No access token found. Cannot connect to status stream.");
      // Optionally, set an error state in a store
      return null;
  }

  const es = new EventSource(`/api/stream-status/${videoId}?token=${encodeURIComponent(token)}`);
  
  es.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      videoStatus.set(data);
      statusHistory.update(currentHistory => [...currentHistory, data]);
    } catch (err) {
      console.error('Failed to parse SSE message', err);
    }
  };

  es.addEventListener('error', (e) => {
    // This listener handles custom 'error' events from the server, not connection errors.
    console.error('Received error from server:', e);
    try {
        const data = JSON.parse((e as MessageEvent).data);
        // Here you could set an error state in a store to display to the user
        // e.g., sseError.set(data.message);
    } catch (err) {
        // e.g., sseError.set('An unknown error occurred on the stream.');
    }
    es.close();
  });

  es.onerror = (err) => {
    // This listener handles network-level errors, like the connection dropping.
    console.error('EventSource failed:', err);
    es.close();
    // Here you could set an error state in a store if needed
  };
  
  eventSource = es;
  return es;
}

export async function retriggerStage(videoId: string, stage: string): Promise<void> {
  const res = await fetch('/api/re-trigger', {
    method: 'POST',
    headers: await getHeaders(),
    body: JSON.stringify({ video_id: videoId, stage: stage.toLowerCase() })
  });
  
  const responseBody = await res.json().catch(() => ({})); // Gracefully handle non-JSON responses

  if (!res.ok) {
    // Use the specific 'detail' or 'message' from the backend, or fall back to a generic message
    const errorMessage = responseBody.detail || responseBody.message || `Failed to re-trigger stage '${stage}'. (Status: ${res.status})`;
    throw new Error(errorMessage);
  }
}

export async function checkYouTubeConnection(): Promise<{ isConnected: boolean; email?: string }> {
    const token = localStorage.getItem('accessToken');
    if (!token) throw new Error("Not authenticated");

    const response = await fetch('/api/auth/youtube/status', {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(errorData.detail);
    }
    return await response.json();
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

export async function getUserInfo() {
    const token = localStorage.getItem('accessToken');
    if (!token) {
        throw new Error("No access token found");
    }

    const response = await fetch('/api/user/me', {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });

    if (!response.ok) {
        throw new Error(`Failed to fetch user info: ${response.statusText}`);
    }
    return await response.json();
}

export async function generateNewPrompts(videoId: string): Promise<string[]> {
    const res = await fetch(`/api/video/${videoId}/generate-prompts`, {
        method: 'POST',
        headers: await getHeaders(),
        body: JSON.stringify({}) // Backend doesn't require a body, just the videoId from the URL
    });

    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Failed to generate prompts' }));
        throw new Error(err.detail);
    }
    const data = await res.json();
    return data.prompts || [];
}

export async function generateOnDemandImage(videoId: string, prompt: string, modelName: string | null): Promise<any> {
    const res = await fetch(`/api/video/${videoId}/generate-image`, {
        method: 'POST',
        headers: await getHeaders(),
        body: JSON.stringify({ prompt, model_name: modelName })
    });

    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Failed to generate image' }));
        throw new Error(err.detail);
    }
    return await res.json();
}

