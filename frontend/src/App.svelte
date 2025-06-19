<script lang="ts">
  import AuthButton      from './components/AuthButton.svelte';
  import IngestForm      from './components/IngestForm.svelte';
  import StatusLog       from './components/StatusLog.svelte';
  import Workflow        from './components/Workflow.svelte';
  import PreviousVideos  from './components/PreviousVideos.svelte';
  import ConnectYouTubeButton from './components/ConnectYouTubeButton.svelte';
  import { accessToken } from './lib/auth';
  import { videoStatus } from './lib/stores';
  import { listenForUpdates } from './lib/api';
  import logoUrl from './assets/channel-flow-logo.png';

  let isYouTubeConnected = false; 

  function handleNewIngestion(e: CustomEvent) {
    const videoId = e.detail.videoId;
    if (videoId) {
      listenForUpdates(videoId);
    }
  }

  function handleView(e: CustomEvent) {
    window.location.href = `/video/${e.detail.videoId}`;
  }

  function onYouTubeConnected() {
    isYouTubeConnected = true;
  }
</script>

<div class="main-container">
  <!-- Back to workflow -->
  <div id="back-to-workflow" class="mb-4 cursor-pointer">
    ← Back to Workflow
  </div>

  <!-- Header navigation -->
  <div class="header-nav">
    <div class="header-left">
      <button class="hamburger-menu" aria-label="Open navigation menu">
        <span class="hamburger-line"></span>
        <span class="hamburger-line"></span>
        <span class="hamburger-line"></span>
      </button>
      <a href="/" class="logo-link">
        <img src={logoUrl} alt="ChannelFlow Logo" class="logo-icon" />
      </a>
    </div>
    <nav class="nav-links">
      <a href="/management" class="nav-link button-cta">Content Dashboard</a>
      <a href="/management" class="nav-link button-cta">Maintenance</a>
      <div class="user-auth">
        <AuthButton />
      </div>
    </nav>
  </div>

  <!-- Main and sidebar columns directly under main-container -->
  <div class="content-column">
    <h1 class="mb-4">Amplify your message.</h1>
    <p class="mb-6">
      Paste a YouTube link to transform a single video into a complete,
      multi-platform marketing campaign, orchestrated by autonomous AI agents.
    </p>

    {#if $accessToken && !isYouTubeConnected}
      <div class="youtube-connect-prompt">
        <p>To get started, connect your YouTube account.</p>
        <ConnectYouTubeButton onConnected={onYouTubeConnected} />
      </div>
    {/if}

    <IngestForm on:new-ingestion={handleNewIngestion} on:view={handleView} />

    {#if $videoStatus}
      <StatusLog />
    {/if}
  </div>

  <div class="workflow-column">
    <h2 class="mb-4">Agentic Workflow</h2>
    <Workflow />
  </div>

  <!-- Previously processed videos -->
  {#if $accessToken}
    <PreviousVideos />
  {/if}
</div>
