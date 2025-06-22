<!-- src/components/AuthButton.svelte -->
<script lang="ts">
  import { onMount, tick } from 'svelte';
  import Swal from 'sweetalert2';
  import { accessToken, setAccessToken, clearAccessToken } from '../lib/auth';
  import { loginWithGoogle, getUserInfo } from '../lib/api';
  import { user } from '../lib/stores';
  import { push } from 'svelte-spa-router';

  export let clientId: string;

  // This whole subscription is for keeping the 'user' store in sync.
  accessToken.subscribe(async (token) => {
    if (token) {
      if (!$user) { // Only fetch if we don't have user info
        try {
          const userInfo = await getUserInfo();
          user.set(userInfo);
        } catch (error) {
          console.error('Failed to fetch user info:', error);
          clearAccessToken(); 
        }
      }
    } else {
      user.set(null);
    }
  });

  function loadGsiScript(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (window.google && window.google.accounts) {
        return resolve();
      }
      const script = document.createElement('script');
      script.src = 'https://accounts.google.com/gsi/client';
      script.onload = () => resolve();
      script.onerror = () => reject(new Error('Failed to load Google Identity Services'));
      document.head.appendChild(script);
    });
  }

  async function initializeGsi() {
    try {
      await loadGsiScript();
      
      google.accounts.id.initialize({
        client_id: clientId,
        callback: async (resp: { credential: any }) => {
          if (!resp.credential) {
              Swal.fire('Login failed', 'Received an invalid response from Google.', 'error');
              return;
          }
          try {
            const jwt = await loginWithGoogle(resp.credential);
            setAccessToken(jwt);
            Swal.fire('Success', 'Signed in!', 'success');
          } catch (e: any) {
            Swal.fire('Login failed', e.message, 'error');
          }
        },
        auto_select: false
      });

      renderGsiButton();

    } catch (err: any) {
      console.error('A critical error occurred during GSI setup.', err);
      Swal.fire('Error', err.message, 'error');
    }
  }

  async function renderGsiButton() {
    await tick(); // Wait for the DOM to update
    const buttonContainer = document.getElementById('gsi-button-container');
    if (buttonContainer) {
        if (buttonContainer.childElementCount === 0) {
            google.accounts.id.renderButton(
                buttonContainer,
                { theme: "outline", size: "large" } 
            );
        }
    }
  }
  
  // Reactive statement to re-initialize GSI or re-render the button if the user logs out.
  $: if (!$user && clientId && typeof window !== 'undefined') {
    if (window.google?.accounts?.id) {
        renderGsiButton();
    } else {
        initializeGsi();
    }
  }

  function handleLogout() {
    clearAccessToken();
    // user store is cleared via the subscription
    Swal.fire('Logged Out', 'You have been signed out.', 'info');
    push('/');
  }
</script>

<div class="auth-wrapper">
  {#if $user}
    <span class="user-name">Welcome, {$user.name}</span>
    <button on:click={handleLogout} class="button-secondary">Logout</button>
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
