<!-- src/components/ConnectYouTubeButton.svelte -->
<script lang="ts">
  import { onMount, createEventDispatcher } from 'svelte';
  import Swal from 'sweetalert2';
  import { exchangeAuthCode } from '../lib/api';

  const dispatch = createEventDispatcher();
  let clientId: string | null = null;

  onMount(async () => {
    try {
      const res = await fetch('/api/config');
      if (!res.ok) throw new Error('Failed to fetch client config');
      const config = await res.json();
      clientId = config.google_client_id;
    } catch (err: any) {
      Swal.fire('Error', `Could not load Google Client ID: ${err.message}`, 'error');
    }
  });

  function connect() {
    if (!clientId) {
      Swal.fire('Error', 'Google Client ID not loaded.', 'error');
      return;
    }

    const client = google.accounts.oauth2.initCodeClient({
      client_id: clientId,
      scope: 'https://www.googleapis.com/auth/youtube.readonly openid https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile',
      callback: async (response) => {
        try {
          await exchangeAuthCode(response.code);
          Swal.fire('Connected!', 'Your YouTube account is now linked.', 'success');
          console.log('[YouTube ✅] Dispatching connected event');
          dispatch('connected');
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
