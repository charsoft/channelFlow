// src/lib/api.ts
export async function checkVideo(
    url: string,
    token: string
): Promise<{ exists: boolean; video_id: string | null }> {
    const res = await fetch('/api/ingest-url', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ url, force: false })
    });

    // If backend 403s because of an auth issue, throw a structured error.
    if (res.status === 403) {
        const err = await res.json();
        const error: any = new Error(err.message || 'Authorization failed. Please connect your YouTube account.');
        error.code = err.code; // Pass the code along for the UI to handle
        throw error;
    }

    const json = await res.json();
    if (res.ok && json.status === 'exists') {
        return { exists: true, video_id: json.data.video_id };
    }

    // New video
    return { exists: false, video_id: null };
}
export async function sendIngest(
    url: string,
    force: boolean,
    token: string
): Promise<string> {
    const res = await fetch('/api/ingest-url', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ url, force })
    });
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || `Server error ${res.status}`);
    }
    const json = await res.json();
    return json.video_id;
}
// Listen for SSE updates for a given videoId
export function listenForUpdates(
    videoId: string,
    token: string,
    onMessage: (data: any) => void,
    onError: () => void
): EventSource {
    const es = new EventSource(`/api/events/${videoId}?token=${encodeURIComponent(token)}`);
    es.onmessage = e => {
        try {
            onMessage(JSON.parse(e.data));
        } catch (err) {
            console.error('Failed to parse SSE message', err);
        }
    };
    es.onerror = () => {
        es.close();
        onError();
    };
    return es;
}
export async function exchangeAuthCode(code: string, token: string) {
    const res = await fetch('/api/oauth/exchange-code', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ code })
    });
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to exchange authorization code.');
    }
}
