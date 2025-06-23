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
  console.log('[Watcher 🔁] token changed:', token);
  if (token) {
    if (!$user) {
      console.log('[Watcher 🤔] No user info, fetching...');
      try {
        const userInfo = await getUserInfo();
        console.log('[Watcher ✅] Got user info:', userInfo);
        user.set(userInfo);
      } catch (error) {
        console.error('[Watcher ❌] Failed to fetch user info:', error);
        clearAccessToken();
      }
    } else {
      console.log('[Watcher 🧍] User info already present:', $user);
    }
  } else {
    console.log('[Watcher ⚠️] Token was cleared');
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
    console.log('Initializing Google Sign-In...');

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
            console.log('[AuthButton ✅] Set token:', jwt);
            console.log('[AuthButton ✅] LocalStorage:', localStorage.getItem('accessToken'));

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
    console.log('Rendering GSI button...');

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
 onMount(async () => {
  if (!$user && clientId) {
    await initializeGsi();
  }
});


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
