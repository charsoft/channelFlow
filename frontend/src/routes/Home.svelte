<script lang="ts">
  import IngestForm from '../components/IngestForm.svelte';
  import StatusLog from '../components/StatusLog.svelte';
  import Workflow from '../components/Workflow.svelte';
  import ConnectYouTubeButton from '../components/ConnectYouTubeButton.svelte';
  import { accessToken } from '../lib/auth';
  import { videoStatus } from '../lib/stores';
  import { listenForUpdates, checkYouTubeConnection, disconnectYouTube, retriggerStage } from '../lib/api';
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import Swal from 'sweetalert2';
  import SystemFlow from './SystemFlow.svelte';

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
    if (videoId) {
      hasHandledFirstStatus = false; // Reset for new video
      listenForUpdates(videoId);
    }
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

  // This reactive block automatically enters "Restart Mode"
  // if the loaded video is already past the 'ingesting' stage.
  $: if ($videoStatus?.status && !hasHandledFirstStatus) {
    if ($videoStatus.status !== 'ingesting') {
        isRestartMode = true;
    }
    hasHandledFirstStatus = true;
  }

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
    'downloading':       { agent: 'Ingestion',     state: 'active'    },
    'ingested':          { agent: 'Ingestion',     state: 'completed' },
    'ingestion_failed':  { agent: 'Ingestion',     state: 'failed'    },

    'pending_transcription_rerun': { agent: 'Transcription', state: 'active' },
    'transcribing':      { agent: 'Transcription', state: 'active'    },
    'transcribed':       { agent: 'Transcription', state: 'completed' },
    'transcribing_failed': { agent: 'Transcription', state: 'failed' },
    'transcription_failed': { agent: 'Transcription', state: 'failed' },
    'auth_failed':       { agent: 'Transcription', state: 'failed'    },

    'analyzing':         { agent: 'Analysis',      state: 'active'    },
    'analyzed':          { agent: 'Analysis',      state: 'completed' },
    'analyzing_failed':   { agent: 'Analysis',      state: 'failed'    },
    'analysis_failed':   { agent: 'Analysis',      state: 'failed'    },

    'generating_copy':   { agent: 'Copywriting',   state: 'active'    },
    'copy_generated':    { agent: 'Copywriting',   state: 'completed' },
    'generating_copy_failed': { agent: 'Copywriting',   state: 'failed'    },
    'copy_failed':       { agent: 'Copywriting',   state: 'failed'    },

    'generating_visuals':{ agent: 'Visuals',       state: 'active'    },
    'visuals_generated': { agent: 'Visuals',       state: 'completed' },
    'generating_visuals_failed': { agent: 'Visuals',       state: 'failed'    },
    'visuals_failed':    { agent: 'Visuals',       state: 'failed'    },

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

{#if $accessToken}
  <div class="home-container">
    <div class="content-column">
      <h1 class="mb-2">Amplify your message.</h1>
      <p class="mb-4">
        Paste a YouTube link to transform a single video into a complete,
        multi-platform marketing campaign, orchestrated by autonomous AI agents.
      </p>
    <p class="mb-6">
       {#if isYouTubeConnected}
         <div class="ingestion-controls">
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
     </p>
     

      {#if $videoStatus}
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
{:else}
  <div class="home-container" style="padding-bottom: 0; min-height: 0;">
    <div class="content-column" style="min-height: initial; text-align: center;">
        <h1 class="mb-2">Amplify your message.</h1>
        <p class="mb-4">
          Paste a YouTube link to transform a single video into a complete,
          multi-platform marketing campaign, orchestrated by autonomous AI agents.
        </p>
    </div>
  </div>
  <SystemFlow showTitle={false} />
{/if}

<style>
  .home-container {
    display: flex;
    justify-content: center;
    padding: 2rem;
  }

  .content-column {
    justify-content: center;
    min-height:90vh;
    max-width: none;
    width: 75%;
    justify-content: center;
    background-color: #ffffff;
    padding: 2.5rem;
    border-radius: 0.75rem;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1);
  }

  .restart-prompt {
    font-size: 0.9rem;
    font-style: italic;
    color: #4b5563; /* gray-600 */
    margin: 0.5rem 0;
    padding: 0.5rem;
    background-color: #f3f4f6; /* gray-100 */
    border-radius: 0.375rem;
  }
  .workflow-controls {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }
  .processing-section {
    margin-top: 2rem;
    border-top: 1px solid #e5e7eb; /* gray-200 */
    padding-top: 2rem;
  }
  .ingestion-controls {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
    width: 100%;
  }

  .youtube-connected-status {
    display: flex;
    align-items: center;
    padding: 0.5rem 0.5rem 0.5rem 1rem; /* Adjusted padding */
    background-color: #f0fdf4; /* green-50 */
    border: 1px solid #bbf7d0; /* green-200 */
    border-radius: 0.5rem;
    color: #166534; /* green-800 */
    font-weight: 500;
    flex-shrink: 0; /* Prevent this from shrinking */
  }

  .status-text {
    margin-right: 0.75rem;
  }

  .disconnect-button {
    background: none;
    border: none;
    color: #9ca3af; /* gray-400 */
    font-size: 1.5rem;
    line-height: 1;
    cursor: pointer;
    padding: 0 0.25rem;
    border-radius: 9999px;
  }
  .disconnect-button:hover {
    color: #111827; /* gray-900 */
    background-color: #d1d5db; /* gray-300 */
  }

  .icon {
    margin-right: 0.5rem;
  }
</style>