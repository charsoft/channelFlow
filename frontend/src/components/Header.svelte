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

<style>
    .app-header {
        background-color: #ffffff;
        border-bottom: 1px solid #e5e7eb;
        padding: 0 2rem;
        position: sticky;
        top: 0;
        z-index: 50;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    .header-content {
        display: flex;
        justify-content: space-between;
        align-items: center;
        height: 64px;
        max-width: 1400px;
        margin: 0 auto;
    }
    
    .logo-link {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        text-decoration: none;
        color: inherit;
    }

    .logo-icon {
        height: 40px;
    }

    .logo-text {
        font-size: 1.25rem;
        font-weight: 700;
        color: #1e293b;
    }

    .main-nav {
        display: flex;
        gap: 1.5rem;
    }

    .nav-link {
        text-decoration: none;
        font-weight: 600;
        color: #4b5563;
        transition: color 0.2s;
    }
    .nav-link:hover {
        color: #4F46E5;
    }
</style> 