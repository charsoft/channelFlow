<!-- src/components/AuthButton.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import Swal from 'sweetalert2';
  import { accessToken, setAccessToken, clearAccessToken } from '../lib/auth';
  import { loginWithGoogle, getUserInfo } from '../lib/api';
  import { user } from '../lib/stores';
  import { link, push } from 'svelte-spa-router';

  let clientId: string;

  accessToken.subscribe(async (token) => {
    if (token) {
      try {
        const userInfo = await getUserInfo();
        user.set(userInfo);
      } catch (error) {
        console.error('Failed to fetch user info:', error);
        user.set(null);
      }
    } else {
      user.set(null);
    }
  });

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
        auto_select: false
      });
      
      const buttonContainer = document.getElementById('gsi-button-container');
      if (buttonContainer) {
        google.accounts.id.renderButton(
          buttonContainer,
          { theme: "outline", size: "large" } 
        );
      }

      console.info('[AuthButton DBG]: GSI initialization complete.');

    } catch (err: any) {
      console.error('[AuthButton DBG]: A critical error occurred during onMount setup.', err);
      Swal.fire('Error', err.message, 'error');
    }
  });

  function handleLogout() {
    console.log('[AuthButton DBG]: handleLogout() called.');
    clearAccessToken();
    user.set(null);
    Swal.fire('Logged Out', 'You have been signed out.', 'info');
    push('/');
  }
</script>

<div class="auth-wrapper">
  {#if $user}
    <span class="user-name">Welcome, {$user.name}</span>
    <button on:click={handleLogout} class="button-secondary">Logout</button>
  {:else if $accessToken}
    <!-- Still authenticating -->
    <span>Loading...</span>
  {:else}
    <div id="gsi-button-container"></div>
  {/if}
</div>

<style>
  .auth-wrapper {
    display: flex;
    align-items: center;
    gap: 1rem;
  }
  .user-name {
    font-weight: 600;
    color: var(--text-color);
  }
</style>
