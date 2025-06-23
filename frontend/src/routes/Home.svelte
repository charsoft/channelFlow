<script lang="ts">
  import IngestForm from '../components/IngestForm.svelte';
  import StatusLog from '../components/StatusLog.svelte';
  import Workflow from '../components/Workflow.svelte';
  import botWorkingGif from '../assets/bot-working-gif.gif';
  import ConnectYouTubeButton from '../components/ConnectYouTubeButton.svelte';
  import { accessToken } from '../lib/auth';
  import { videoStatus, youtubeConnectionStatus } from '../lib/stores';
  import { listenForUpdates, checkYouTubeConnection, disconnectYouTube, retriggerStage } from '../lib/api';
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import Swal from 'sweetalert2';
  import SystemFlow from './SystemFlow.svelte';
  import WorkflowManager from '../components/WorkflowManager.svelte';


  let isRestartMode = true;
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
    const status = await checkYouTubeConnection();
    youtubeConnectionStatus.set(status);
  } catch {
    youtubeConnectionStatus.set({ isConnected: false });
  }
}


  // 3) Fired when your ConnectYouTubeButton emits `on:connected`
  function onYouTubeConnected() {
    console.log('Youtube connection status:', youtubeConnectionStatus);
    refreshConnection();
  }

  // 4) Your existing disconnect flow
 async function handleDisconnect() {
  try {
    await disconnectYouTube();
    youtubeConnectionStatus.set({ isConnected: false, email: undefined });
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
        listenForUpdates(currentVideoId); // ✅ This ensures UI stays synced
      } catch (err: any) {
        Swal.fire(
          'Error!',
          err.message || 'Failed to re-trigger the process.',
          'error'
        );
      }
    }

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

   const agentDetails = [
    {
      name: 'Ingestion',
      description: 'The system is preparing to download the video.',
      longDescription: 'The Ingest stage downloads and stores your YouTube video securely in cloud storage, preparing it for transcription and processing.'
    },
    {
      name: 'Transcription',
      description: 'Awaiting video download to begin transcription.',
      longDescription: 'This stage uses advanced speech-to-text AI to convert the spoken content of the video into a text transcript.'
    },
    {
      name: 'Analysis',
      description: 'Awaiting transcript to begin content analysis.',
      longDescription: 'The AI analyzes the transcript to extract key topics, identify "shorts" candidates, and create a structured summary.'
    },
    {
      name: 'Copywriting',
      description: 'Awaiting analysis to begin generating marketing copy.',
      longDescription: 'Using the analysis, this agent generates materials like social media posts, email newsletters, and articles.'
    },
    {
      name: 'Visuals',
      description: 'Awaiting analysis to begin generating visual assets.',
      longDescription: 'This agent generates relevant visual assets, like thumbnails and quote graphics, based on the marketing copy and analysis.'
    },
    {
      name: 'Publisher',
      description: 'Awaiting content to publish.',
      longDescription: 'The final stage, where the generated content and visuals are prepared for publishing.'
    }
  ];

   const statusMap: Record<string, { agent: string; state: 'active' | 'completed' | 'failed' }> = {
    'ingesting':         { agent: 'Ingestion',     state: 'active'    },
    'downloading':       { agent: 'Transcription', state: 'active'    },
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
  /* This console log is commented out to reduce noise in the browser console.
     The stream sends data every 2 seconds to keep the connection alive, and this
     was logging every single message.
  $: if ($videoStatus) {
    console.log('Received video status from backend:', $videoStatus);
  }
  */

  $: stages = agentDetails.map((detail, index) => {
    let status: 'pending' | 'active' | 'completed' | 'failed' = 'pending';
    let description = detail.description;
    const currentStatusString = $videoStatus?.status;
    const statusMessage = $videoStatus?.status_message;

    if (currentStatusString) {
        const entry = statusMap[currentStatusString];
        if (entry) {
            const currentAgentName = entry.agent;
            const currentState = entry.state;
            const agentNames = agentDetails.map(d => d.name);
            const currentIndex = agentNames.indexOf(currentAgentName);
            const thisIndex = agentNames.indexOf(detail.name);

            if (thisIndex < currentIndex) {
              status = 'completed';
              description = `Stage ${detail.name} completed successfully.`;
            } else if (thisIndex === currentIndex) {
              status = currentState;
              description = statusMessage || `Task is ${currentState}.`;
            }
        }
    }
    
    // When the whole process is done, mark all as complete.
    if (currentStatusString === 'published' || currentStatusString === 'complete') {
      status = 'completed';
      description = `Stage ${detail.name} completed successfully.`;
    }

    return {
        ...detail,
        status: status,
        description: description
    };
  });

 let tokenCheckTimeout: ReturnType<typeof setTimeout>;
$: if ($accessToken) {
  clearTimeout(tokenCheckTimeout);
  tokenCheckTimeout = setTimeout(() => {
    refreshConnection();
  }, 200); // waits 200ms before calling refreshConnection
}



 // --- DEBUG LOGGING: STAGES ARRAY ---
///  $: if (stages && stages.length > 0) {
 //   console.log('[Home.svelte] Calculated stages array:', JSON.parse(JSON.stringify(stages)));
 // } else {
 //   console.log('[Home.svelte] Debug: `stages` array is either not defined or empty.', stages);
 // }
</script>
 
{#if $accessToken}
  <div class="home-container">
    <div class="content-column">
      <h1 class="mb-2">Amplify your message.</h1>
      <p class="mb-4">
        Paste a YouTube link to transform a single video into a complete,
        multi-platform marketing campaign, orchestrated by autonomous AI agents.
      </p>
    <div class="mb-6">
       {#if youtubeConnectionStatus.isConnected}
         <div class="ingestion-controls">
           <div class="youtube-connected-status">
             <span class="icon">✅</span>
             <span class="status-text">
               YouTube Connected
               {#if youtubeConnectionStatus.email}
                 <span class="email-display">({youtubeConnectionStatus.email})</span>
               {/if}
             </span>
             <button on:click={handleDisconnect} class="disconnect-button" title="Disconnect YouTube Account">×</button>
           </div>
         
           <div class="ingestion-container">
             <IngestForm on:new-ingestion={handleNewIngestion} />
             {#if currentVideoId}
               <button class="button-secondary view-details-btn" on:click={() => push(`/video/${currentVideoId}`)}>
                 View Details
               </button>
             {/if}
           </div>
         </div>
          
       {:else}
         <div class="youtube-connect-prompt">
           <p>To get started, connect your YouTube account.</p>
           <ConnectYouTubeButton on:connected={onYouTubeConnected} />
         </div>
       {/if}
     </div>
     
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
         <WorkflowManager 
            video={$videoStatus}
            stagesMetadata={agentDetails}
            on:retrigger={handleRetrigger}
          />
          <StatusLog />
        </div>
      {/if}
    </div>
   <!-- <p style="color:blue">DEBUG: $videoStatus = {JSON.stringify($videoStatus)}</p> -->
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
    justify-content: flex-start;
    padding: 2rem;
    
  }

  .content-column {
    justify-content: center;
    min-height:90vh;
    max-width: 800px;
    width: 100%;
    text-align: left;
    margin: 0 auto; /* Center the column itself */
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
    border: 1px solid var(--border-color);
    padding: 1.5rem;
    border-radius: 0.5rem;
    background-color: var(--background-color-light);
  }

  .youtube-connected-status {
    display: flex;
    align-items: center;
    margin-bottom: 1.5rem;
    background-color: #e8f5e9; /* Light green */
    color: #2e7d32; /* Dark green */
    padding: 0.75rem 1rem;
    border-radius: 0.375rem;
    font-weight: 500;
  }

  .youtube-connected-status .icon {
    margin-right: 0.5rem;
  }

  .youtube-connected-status .email-display {
    font-weight: 400;
    margin-left: 0.5rem;
    color: #616161;
  }

  .disconnect-button {
    margin-left: auto;
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

  .agent-stage-btn {
  all: unset; /* ✅ Wipe out all inherited styles */
  display: inline-block;
  padding: 0.5rem 1rem;
  margin: 0.25rem;
  border-radius: 0.375rem;
  font-weight: 500;
  background-color: #f3f4f6; /* gray-100 */
  border: 1px solid #e5e7eb; /* gray-200 */
  color: #374151; /* gray-700 */
  cursor: pointer;
  transition: background-color 0.2s ease, transform 0.2s ease;
}

.agent-stage-btn:hover {
  background-color: #e5e7eb; /* slightly darker gray */
  transform: translateY(-2px);
}

.ingestion-container {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.view-details-btn {
  flex-shrink: 0; /* Prevents the button from shrinking */
  padding: 0.6rem 1.2rem;
}

</style>