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
    background-color: #f8fafc;
  }
</style>
