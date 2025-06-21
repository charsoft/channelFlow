<script lang="ts">
    import { link } from 'svelte-spa-router';
    import logoUrl from '../assets/channel-flow-logo.png';
</script>

<header class="app-header">
    <div class="header-content">
        <a href="/" use:link class="logo-link">
            <img src={logoUrl} alt="ChannelFlow Logo" class="logo-icon">
            <span class="logo-text">ChannelFlow</span>
        </a>
        <nav class="main-nav">
            <a href="/dashboard" use:link class="nav-link">Dashboard</a>
            <a href="/system-flow" use:link class="nav-link">System Flow</a>
            <a href="/maintenance" use:link class="nav-link">Maintenance</a>
        </nav>
    </div>
</header>
