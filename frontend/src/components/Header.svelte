<script lang="ts">
    import { link } from 'svelte-spa-router';
    import logoUrl from '../assets/channel-flow-logo.png';
    import AuthButton from './AuthButton.svelte';

    let isMenuOpen = false;

    function toggleMenu() {
        isMenuOpen = !isMenuOpen;
    }
</script>

<header class="app-header">
    <div class="header-content">
        <a href="/" use:link class="logo-link">
            <img src={logoUrl} alt="ChannelFlow Logo" class="logo-icon">
            <span class="logo-text">ChannelFlow</span>
        </a>
        <button class="hamburger" on:click={toggleMenu} aria-label="Open menu">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M4 6H20M4 12H20M4 18H20" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
        </button>
        <nav class="main-nav" class:is-open={isMenuOpen}>
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
        gap: 2rem;
        width: 100%;
        padding: 0 2rem;
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
        justify-content: space-around;
        flex-grow: 1;
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

    .hamburger {
        display: none;
        background: none;
        border: none;
        cursor: pointer;
        padding: 0;
        color: #1e293b;
    }

    @media (max-width: 820px) {
        .header-content {
            justify-content: space-between;
            flex-wrap: wrap;
        }

        .main-nav {
            display: none;
            flex-direction: column;
            width: 100%;
            order: 3;
            gap: 0.5rem;
            margin-top: 1rem;
            background-color: white;
            padding: 1rem;
            border-radius: 0.375rem;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        }

        .main-nav.is-open {
            display: flex;
        }

        .hamburger {
            display: block;
        }

        .header-right {
           position: static;
           order: 2;
        }

        .logo-text {
            /* Optionally hide on very small screens if needed, but let's keep it for now */
        }
    }
</style> 