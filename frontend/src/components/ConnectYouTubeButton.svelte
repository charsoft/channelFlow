<!-- src/components/ConnectYouTubeButton.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { get } from 'svelte/store';
  import Swal from 'sweetalert2';
  import { idToken } from '../lib/auth';
  import { exchangeAuthCode } from '../lib/api';

  export let onConnected: () => void;
  let clientId: string | null = null;

  onMount(async () => {
    try {
      const res = await fetch('/api/config');
      if (!res.ok) throw new Error('Failed to fetch client config');
      const config = await res.json();
      clientId = config.google_client_id;

      // ⚙️ Debug: show exactly which client ID we loaded
      console.log('🛠 Google OAuth2 Client ID loaded:', clientId);
    } catch (err: any) {
      Swal.fire('Error', `Could not load Google Client ID: ${err.message}`, 'error');
    }
  });

  function connect() {
    if (!clientId) {
      Swal.fire('Error', 'Google Client ID not loaded.', 'error');
      return;
    }

    console.log('🛠 Using Google Client ID:', clientId);

    const token = get(idToken);
    if (!token) {
      Swal.fire('Error', 'You must be signed in to connect your YouTube account.', 'error');
      return;
    }

    const client = google.accounts.oauth2.initCodeClient({
      client_id: clientId,
      scope: 'https://www.googleapis.com/auth/youtube.readonly',
      ux_mode: 'popup',
      callback: async (response) => {
        try {
          await exchangeAuthCode(response.code, token);
          Swal.fire('Connected!', 'Your YouTube account is now linked.', 'success');
          onConnected();
        } catch (err: any) {
          Swal.fire('Oops', err.message || 'Could not connect YouTube.', 'error');
        }
      },
    });

    client.requestCode();
  }
</script>

<button on:click={connect} class="button-secondary" disabled={!clientId}>
  Connect YouTube
</button>
