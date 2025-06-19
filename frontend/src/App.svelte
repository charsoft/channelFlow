<script lang="ts">
  import Router, { push } from 'svelte-spa-router';
  import AuthButton from './components/AuthButton.svelte';
  import logoUrl from './assets/channel-flow-logo.png';
  import Home from './routes/Home.svelte';
  import VideoDetail from './routes/VideoDetail.svelte';
  import Dashboard from './routes/Dashboard.svelte';

  const routes = {
    '/': Home,
    '/video/:id': VideoDetail,
    '/dashboard': Dashboard,
    '*': Home, // Fallback for any other route
  };

</script>

<div class="main-container">
  <!-- Header navigation -->
  <div class="header-nav">
    <div class="header-left">
      <button class="hamburger-menu" aria-label="Open navigation menu">
        <span class="hamburger-line"></span>
        <span class="hamburger-line"></span>
        <span class="hamburger-line"></span>
      </button>
      <a href="/" on:click|preventDefault={() => push('/')} class="logo-link">
        <img src={logoUrl} alt="ChannelFlow Logo" class="logo-icon" />
      </a>
    </div>
    <nav class="nav-links">
      <a href="#/dashboard" class="nav-link button-secondary">Content Dashboard</a>
      <a href="/management" class="nav-link button-secondary">Maintenance</a>
      <div class="user-auth">
        <AuthButton />
      </div>
    </nav>
  </div>

  <main>
    <Router {routes} />
  </main>
</div>

<style>
  .main-container {
    display: block;
  }
  main {
    padding: 1rem;
  }
</style>
