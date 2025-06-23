<script lang="ts">
    import { onMount } from 'svelte';
    import { link } from 'svelte-spa-router';
    import logoUrl from '../assets/channel-flow-logo.png';
    import AuthButton from './AuthButton.svelte';
    import { watchAccessToken } from '../lib/authUtils';
    import { refreshConnection } from '../lib/api';


    let googleClientId: string | null = null;

    onMount(async () => {
        try {
            const res = await fetch('/api/config');
            if (!res.ok) throw new Error('Failed to fetch API config');
            const config = await res.json();
            googleClientId = config.google_client_id;
               // 🧠 Start watching the token once the header loads
      watchAccessToken(refreshConnection);
        } catch (error) {
            console.error('Error fetching config in Header:', error);
        }
    });
</script>

<header class="app-header">
    <div class="header-content">
        <a href="/" use:link class="logo-link">
            <img src={logoUrl} alt="ChannelFlow Logo" class="logo-icon">
            <span class="logo-text">ChannelFlow</span>
        </a>
        <nav class="main-nav">
            <a href="/" use:link class="nav-link">Home</a>
            <a href="/dashboard" use:link class="nav-link">Dashboard</a>
            <a href="/system-flow" use:link class="nav-link">System Flow</a>
            <a href="/maintenance" use:link class="nav-link">Maintenance</a>
        </nav>
        <div class="auth-container">
            {#if googleClientId}
                <AuthButton clientId={googleClientId} />
            {:else}
                <div>Loading...</div>
            {/if}
        </div>
    </div>
</header>

<style>
  .header-content {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: center;
    width: 100%;
  }

  :global(.logo-link) {
    justify-self: start;
  }

  .main-nav {
    justify-self: center;
  }

  .auth-container {
    justify-self: end;
  }

  .nav-link {
  display: inline-block;
  padding: 0.5rem 1rem;
  margin-left: 0.5rem;
  border-radius: 0.375rem;
  font-weight: 600;
  text-decoration: none;
  color: var(--primary-color-dark);
  background-color: transparent;
  border: 2px solid var(--primary-color-light); /* ✅ new border */
  transition: all 0.2s ease;
}


.nav-link:hover,
.nav-link:focus {
  background-color: var(--primary-color-light);
  color: var(--primary-color-dark);
  border-color: var(--primary-color); /* darker border on hover */
}


.nav-link.active {
  background-color: var(--primary-color);
  color: white;
  border-color: var(--primary-color-dark);
}


</style>