<script lang="ts">
  import Router, { link, location } from 'svelte-spa-router';

  import Header from './components/Header.svelte';
  import Home from './routes/Home.svelte';
  import Dashboard from './routes/Dashboard.svelte';
  import VideoDetail from './routes/VideoDetail.svelte';
  import SystemFlow from './routes/SystemFlow.svelte';
  import Maintenance from './routes/Maintenance.svelte';

  const routes = {
    '/': Home,
    '/dashboard': Dashboard,
    '/video/:id': VideoDetail,
    '/system-flow': SystemFlow,
    '/maintenance': Maintenance,

    // Catch-all
    '*': Home,
  };
</script>

<Header />

<main>
  <Router {routes}/>
</main>

<style>
  :global(:root) {
    --primary-color: #4F46E5;
    --primary-gradient: linear-gradient(90deg, #4F46E5, #818CF8);
    --background-color: #f8fafc;
    --card-background: #ffffff;
    --text-color: #1e293b;
    --subtle-text-color: #64748b;
    --border-color: #e2e8f0;
    --success-color: #16a34a;
    --danger-color: #dc2626;
    --warning-color: #f59e0b;
  }

  :global(*) {
    box-sizing: border-box;
  }

  :global(body) {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
      'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
      sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    background-color: var(--background-color);
  }

  :global(button), :global(.button-primary) {
    background: var(--primary-gradient);
    color: white;
    padding: 0.6rem 1.2rem;
    border: none;
    border-radius: 0.375rem;
    cursor: pointer;
    font-size: 0.95rem;
    font-weight: 600;
    transition: all 0.2s ease-in-out;
    text-decoration: none;
    display: inline-block;
  }

  :global(button:hover), :global(.button-primary:hover) {
    box-shadow: 0 4px 15px rgba(79, 70, 229, 0.2);
    transform: translateY(-2px);
  }

  :global(button:disabled) {
      opacity: 0.6;
      cursor: not-allowed;
      transform: none;
      box-shadow: none;
  }

  :global(.button-secondary) {
      background: #f1f5f9;
      border: 1px solid #e2e8f0;
      color: #475569;
  }
  :global(.button-secondary:hover) {
      background: #e2e8f0;
      border-color: #cbd5e1;
      box-shadow: none;
      transform: none;
  }

  :global(.button-outline) {
     background: transparent;
     border: 1px solid var(--primary-color);
     color: var(--primary-color);
     padding: 0.5rem 1rem;
  }

  :global(.button-outline:hover) {
     background: #f0f5ff; /* A very light shade of the primary color */
     box-shadow: none;
     transform: none;
  }

  :global(h1) {
    font-size: 2.25rem;
    font-weight: 800;
    color: var(--primary-color);
  }

  :global(h2) {
    font-size: 1.75rem;
    font-weight: 700;
    color: var(--text-color);
  }

  :global(p) {
    color: var(--subtle-text-color);
    line-height: 1.6;
  }
</style>
