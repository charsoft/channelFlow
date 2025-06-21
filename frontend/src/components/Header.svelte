<script lang="ts">
    import { link } from 'svelte-spa-router';
    import logoUrl from '../assets/channel-flow-logo.png';
    import AuthButton from './AuthButton.svelte';
</script>

<header class="app-header">
    <div class="header-content">
        <a href="/" use:link class="logo-link">
            <img src={logoUrl} alt="ChannelFlow Logo" class="logo-icon">
            <span class="logo-text">ChannelFlow</span>
        </a>
        <nav class="main-nav">
            <a href="/" use:link class="nav-link button-outline">Home</a>
            <a href="/dashboard" use:link class="nav-link button-outline">Dashboard</a>
            <a href="/system-flow" use:link class="nav-link button-outline">System Flow</a>
            <a href="/maintenance" use:link class="nav-link button-outline">Maintenance</a>
        </nav>
        <div class="header-right">
            <AuthButton />
        </div>
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
        width: 100%;
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
        color: #1e293b;
    }

    .logo-icon {
        height: 40px;
    }

    .logo-text {
        font-size: 1.25rem;
        font-weight: 700;
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
        padding: 0.5rem 1rem;
        border-radius: 0.375rem;
    }
    .nav-link:hover {
        color: #4F46E5;
        background-color: #f0f5ff;
    }

    .header-right {
        /* This will push the auth button to the far right */
    }

    @media (max-width: 820px) {
        .header-content {
            flex-direction: column;
            height: auto;
            padding: 1rem 0;
            position: relative;
        }

        .main-nav {
            order: 3; /* Render nav after logo and auth button */
            flex-direction: column;
            align-items: center;
            width: 100%;
            margin-top: 1rem;
            gap: 0.5rem;
        }

        .header-right {
           position: absolute;
           top: 1rem;
           right: 0;
        }

        .logo-text {
            display: none; /* Hide text on small screens to save space */
        }
    }
</style> 