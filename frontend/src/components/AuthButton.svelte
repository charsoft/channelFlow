<!-- src/components/AuthButton.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import Swal from 'sweetalert2';
  import { accessToken, setAccessToken, clearAccessToken } from '../lib/auth';
  import { loginWithGoogle } from '../lib/api';

  let gsiReady = false;
  let clientId: string;

  function loadGsiScript(): Promise<void> {
    console.log('[AuthButton DBG]: loadGsiScript() called.');
    return new Promise((resolve, reject) => {
      if (window.google && window.google.accounts) {
        console.log('[AuthButton DBG]: GSI script already exists.');
        return resolve();
      }
      const script = document.createElement('script');
      script.src = 'https://accounts.google.com/gsi/client';
      script.onload = () => {
        console.info('[AuthButton DBG]: GSI script loaded successfully via script tag.');
        resolve();
      };
      script.onerror = () => {
        console.error('[AuthButton DBG]: Failed to load GSI script.');
        reject(new Error('Failed to load Google Identity Services'));
      };
      document.head.appendChild(script);
    });
  }

  onMount(async () => {
    console.log('[AuthButton DBG]: Component mounted.');
    try {
      console.log('[AuthButton DBG]: Attempting to load GSI script...');
      await loadGsiScript();
      console.info('[AuthButton DBG]: GSI script is loaded.');

      console.log('[AuthButton DBG]: Fetching /api/config...');
      const res = await fetch('/api/config');
      if (!res.ok) {
          throw new Error(`Failed to fetch config: ${res.statusText}`);
      }
      const cfg = await res.json();  
      clientId = cfg.google_client_id;
      console.info(`[AuthButton DBG]: Received Client ID: ${clientId}`);
      if (!clientId) {
          throw new Error('Client ID received from backend is empty.');
      }

      console.log('[AuthButton DBG]: Initializing google.accounts.id...');
      google.accounts.id.initialize({
        client_id: clientId,
        callback: async (resp: { credential: any }) => {
          console.info('[AuthButton DBG]: Google Sign-In callback triggered.');
          console.log('[AuthButton DBG]: Received credential object from Google:', resp);
          if (!resp.credential) {
              console.error('[AuthButton DBG]: Credential response from Google is missing the credential property.');
              Swal.fire('Login failed', 'Received an invalid response from Google.', 'error');
              return;
          }
          try {
            console.log('[AuthButton DBG]: Exchanging Google credential for internal JWT...');
            const jwt = await loginWithGoogle(resp.credential);
            console.info('[AuthButton DBG]: Successfully exchanged for internal JWT.');
            setAccessToken(jwt);
            Swal.fire('Success', 'Signed in!', 'success');
          } catch (e: any) {
            console.error('[AuthButton DBG]: Failed during JWT exchange.', e);
            Swal.fire('Login failed', e.message, 'error');
          }
        },
        ux_mode: 'popup',
        auto_select: false
      });
      
      // Render the button, but it will be disabled until gsiReady is true
      google.accounts.id.renderButton(
        document.createElement('div'), // Create a dummy element
        { theme: "outline", size: "large" } 
      );

      console.info('[AuthButton DBG]: GSI initialization complete.');

      gsiReady = true;
      console.log('[AuthButton DBG]: gsiReady is now true.');
    } catch (err: any) {
      console.error('[AuthButton DBG]: A critical error occurred during onMount setup.', err);
      Swal.fire('Error', err.message, 'error');
    }
  });

  function handleLogin() {
    console.log('[AuthButton DBG]: handleLogin() called.');
    if (!gsiReady || !window.google || !window.google.accounts || !window.google.accounts.id) {
      console.warn('[AuthButton DBG]: Login clicked, but GSI is not ready.');
      Swal.fire('Error', 'Google Sign-In is not ready. Please wait a moment.', 'error');
      return;
    }
    console.info('[AuthButton DBG]: Calling google.accounts.id.prompt().');
    google.accounts.id.prompt();
  }

  function handleLogout() {
    console.log('[AuthButton DBG]: handleLogout() called.');
    clearAccessToken();
    Swal.fire('Logged Out', 'You have been signed out.', 'info');
  }
</script>

{#if $accessToken}
    <button on:click={handleLogout} class="button-secondary">Logout</button>
{:else}
    <button on:click={handleLogin} class="button-primary" disabled={!gsiReady}>
        {#if !gsiReady}Initializing...{:else}Sign in with Google{/if}
    </button>
{/if}
