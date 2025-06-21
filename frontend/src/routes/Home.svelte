<script lang="ts">
  import IngestForm from '../components/IngestForm.svelte';
  import StatusLog from '../components/StatusLog.svelte';
  import Workflow from '../components/Workflow.svelte';
  import ConnectYouTubeButton from '../components/ConnectYouTubeButton.svelte';
  import SystemFlow from './SystemFlow.svelte';
  import { accessToken } from '../lib/auth';
  import { videoStatus, resetStores } from '../lib/stores';
  import { listenForUpdates, checkYouTubeConnection, disconnectYouTube, retriggerStage } from '../lib/api';
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import Swal from 'sweetalert2';

  let isYouTubeConnected = false;
  let isRestartMode = false;
  let currentVideoId: string | null = null;
  let hasHandledFirstStatus = false;
  $: currentVideoId = $videoStatus?.video_id ?? null;

   // 1) Check once on page load (if the user is already logged in)
  onMount(() => {
    if ($accessToken) {
      refreshConnection();
    }
  });

  // 2) Helper to (re)validate connection state
  async function refreshConnection() {
    try {
      isYouTubeConnected = await checkYouTubeConnection();
    } catch {
      isYouTubeConnected = false;
    }
  }

  // 3) Fired when your ConnectYouTubeButton emits `on:connected`
  function onYouTubeConnected() {
    isYouTubeConnected = true;
  }

  // 4) Your existing disconnect flow
  async function handleDisconnect() {
    try {
      await disconnectYouTube();
      isYouTubeConnected = false;
      Swal.fire('Success', 'Your YouTube account has been disconnected.', 'success');
    } catch (err: any) {
      Swal.fire('Error', err.message, 'error');
    }
  }

  $: if ($videoStatus?.video_id) {
    currentVideoId = $videoStatus.video_id;
  }

  function handleNewIngestion(e: CustomEvent) {
    const videoId = e.detail.videoId;
    if (!videoId) return;

    // Always reset the UI and attach the listener for a new user submission.
    resetStores();
    listenForUpdates(videoId);
  }

  function handleView(e: CustomEvent) {
    push(`/video/${e.detail.videoId}`);
  }

  async function handleRetrigger(event: { detail: { stage: string }}) {
    const stage = event.detail.stage;
    
    Swal.fire({
      title: 'Are you sure?',
      text: `This will re-run the process from the '${stage}' stage.`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#3085d6',
      cancelButtonColor: '#d33',
      confirmButtonText: 'Yes, re-run it!'
    }).then(async (result) => {
      if (result.isConfirmed) {
        if (!currentVideoId) {
          Swal.fire('Error!', 'No video is currently being processed.', 'error');
          return;
        }
        try {
          await retriggerStage(currentVideoId, stage);
          Swal.fire(
            'Restarted!',
            `The process will now re-run from the ${stage} stage.`,
            'success'
          );
        } catch (err: any) {
          Swal.fire(
            'Error!',
            err.message || 'Failed to re-trigger the process.',
            'error'
          );
        }
      }

      // De-select restart mode regardless of the outcome
      isRestartMode = false;
    });
  }

  // This reactive block is removed as it's causing unpredictable UI behavior.
  // The user will now explicitly control restart mode via the UI button.
  /*
  $: if ($videoStatus?.status && !hasHandledFirstStatus) {
    if ($videoStatus.status !== 'ingesting') {
        isRestartMode = true;
    }
    hasHandledFirstStatus = true;
  }
  */

   const agents = [
    'Ingestion',
    'Transcription',
    'Analysis',
    'Copywriting',
    'Visuals',
    'Publisher'
  ];

   const statusMap: Record<string, { agent: string; state: 'active' | 'completed' | 'failed' }> = {
    'ingesting':         { agent: 'Ingestion',     state: 'active'    },
    'ingested':          { agent: 'Ingestion',     state: 'completed' },
    'ingestion_failed':  { agent: 'Ingestion',     state: 'failed'    },

    'pending_transcription_rerun': { agent: 'Transcription', state: 'active' },
    'transcribing':      { agent: 'Transcription', state: 'active'    },
    'transcribed':       { agent: 'Transcription', state: 'completed' },
    'transcribing_failed': { agent: 'Transcription', state: 'failed' },
    'transcription_failed': { agent: 'Transcription', state: 'failed' },
    'auth_failed':       { agent: 'Transcription', state: 'failed'    },

    'pending_analysis_rerun': { agent: 'Analysis', state: 'active' },
    'analyzing':         { agent: 'Analysis',      state: 'active'    },
    'analyzed':          { agent: 'Analysis',      state: 'completed' },
    'analyzing_failed':   { agent: 'Analysis',      state: 'failed'    },
    'analysis_failed':   { agent: 'Analysis',      state: 'failed'    },

    'pending_copywriting_rerun': { agent: 'Copywriting', state: 'active' },
    'generating_copy':   { agent: 'Copywriting',   state: 'active'    },
    'copy_generated':    { agent: 'Copywriting',   state: 'completed' },
    'generating_copy_failed': { agent: 'Copywriting',   state: 'failed'    },
    'copy_failed':       { agent: 'Copywriting',   state: 'failed'    },

    'pending_visuals_rerun': { agent: 'Visuals', state: 'active' },
    'generating_visuals':{ agent: 'Visuals',       state: 'active'    },
    'visuals_generated': { agent: 'Visuals',       state: 'completed' },
    'generating_visuals_failed': { agent: 'Visuals',       state: 'failed'    },
    'visuals_failed':    { agent: 'Visuals',       state: 'failed'    },
    'visuals_skipped':   { agent: 'Visuals',       state: 'completed' }, // Treat skipped as completed

    'publishing':        { agent: 'Publisher',     state: 'active'    },
    'published':         { agent: 'Publisher',     state: 'completed' },
    'publishing_failed': { agent: 'Publisher',     state: 'failed'    },
  };
// 2) Derive `stages` reactively from your store + constants:
  $: if ($videoStatus) {
    console.log('Received video status from backend:', $videoStatus);
  }

  $: stages = agents.map((agent) => {
    // default to "pending"
    let state: 'pending' | 'active' | 'completed' | 'failed' = 'pending';

    if ($videoStatus?.status) {
      const entry = statusMap[$videoStatus.status];
      if (entry) {
        const currentAgent = entry.agent;
        const currentState = entry.state;
        const currentIndex = agents.indexOf(currentAgent);
        const thisIndex    = agents.indexOf(agent);

        if (agent === currentAgent) {
          // the one that's running or just finished
          state = currentState;
        } else if (thisIndex < currentIndex) {
          // any agent before it must have completed already
          state = 'completed';
        }
        // otherwise leave it as "pending"
      }
    }

    return { name: agent, status: state };
  });
</script>

<div class="home-container">
  <div class="content-column">
  
    {#if $accessToken}
      <h1 class="mb-2">Amplify your message.</h1>
      <p class="mb-4">
        Paste a YouTube link to transform a single video into a complete,
        multi-platform marketing campaign, orchestrated by autonomous AI agents.
      </p>

      {#if isYouTubeConnected}
        <div class="ingestion-container">
          <div class="youtube-connected-status">
            <span class="icon">✅</span>
            <span class="status-text">YouTube Connected</span>
            <button on:click={handleDisconnect} class="disconnect-button" title="Disconnect YouTube Account">×</button>
          </div>
          <IngestForm on:new-ingestion={handleNewIngestion} on:view={handleNewIngestion} />
        </div>
      {:else}
        <div class="youtube-connect-prompt">
          <p>To get started, connect your YouTube account.</p>
          <ConnectYouTubeButton on:connected={onYouTubeConnected} />
        </div>
      {/if}
    {:else}
      <div class="welcome-header">
        <h2>Sign in to get started... you'll turn your YouTube Channel into multiple channels of creativity, using this amazing Agent Development Kit Google hackathon contender!</h2>
      </div>
      <SystemFlow />
    {/if}

    {#if $accessToken && $videoStatus}
      <div class="processing-section">
        <div class="workflow-controls">
          <h3 class="text-lg font-semibold text-gray-700">Live Workflow</h3>
          <button class="button-secondary" on:click={() => { isRestartMode = !isRestartMode; }}>
            {#if isRestartMode}
              Cancel
            {:else}
              Restart From Stage...
            {/if}
          </button>
        </div>
         {#if isRestartMode}
          <p class="restart-prompt">Select a completed stage to restart from.</p>
        {/if}
        <Workflow 
          bind:isRestartMode 
          {stages}
          on:retrigger={handleRetrigger} 
        />
        <StatusLog />
      </div>
    {/if}
  </div>
</div>

<style>
  .home-container {
    display: flex;
    justify-content: center;
    padding: 2rem;
    width: 100%;
  }

  .content-column {
    max-width: 800px;
    width: 100%;
    background-color: #ffffff;
    padding: 2.5rem;
    border-radius: 0.75rem;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1);
  }

  .ingestion-container {
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 0.75rem;
    padding: 1.5rem;
    margin-bottom: 2rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .youtube-connected-status {
    display: flex;
    align-items: center;
    background-color: #f0fdf4;
    color: #166534;
    padding: 0.75rem 1rem;
    border-radius: 0.5rem;
    font-size: 0.9rem;
    font-weight: 500;
  }
  
  .youtube-connect-prompt {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    gap: 1rem;
    padding: 2rem;
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 0.75rem;
  }

  .icon {
    margin-right: 0.5rem;
  }

  .status-text {
     margin-right: 0.75rem;
  }

  .disconnect-button {
    margin-left: auto;
    background: none;
    border: none;
    color: #9ca3af;
    cursor: pointer;
    font-size: 1.25rem;
    line-height: 1;
    padding: 0.25rem;
  }
  .disconnect-button:hover {
    color: #374151;
  }
  
  .welcome-header {
    text-align: center;
    margin-bottom: 2rem;
  }

  .processing-section {
    margin-top: 3rem;
    padding-top: 2rem;
    border-top: 1px solid #e2e8f0;
  }

  .workflow-controls {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }

  .restart-prompt {
    background-color: #fefce8;
    color: #854d0e;
    padding: 0.75rem 1rem;
    border-radius: 0.5rem;
    margin-bottom: 1rem;
    text-align: center;
  }

  .mb-2 { margin-bottom: 0.5rem; }
  .mb-4 { margin-bottom: 1rem; }
  .mb-6 { margin-bottom: 1.5rem; }

  .welcome-header h2 {
    font-size: 1.4rem;
    font-weight: 600;
    line-height: 1.5;
    color: var(--text-color);
  }

  /* Responsive stacking for smaller screens */
  @media (max-width: 992px) {
    .home-container {
      flex-direction: column;
    }
  }
</style>