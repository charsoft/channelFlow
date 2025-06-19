<!-- src/components/Workflow.svelte -->
<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { videoStatus } from '../lib/stores';

  export let retriggerable = false;
  const dispatch = createEventDispatcher();

  const agents = ['Ingestion', 'Transcription', 'Analysis', 'Copywriting', 'Visuals', 'Publisher'];

  const statusMap: Record<string, { agent: string; state: 'active' | 'completed' | 'failed' }> = {
    'ingesting': { agent: 'Ingestion', state: 'active' },
    'ingested': { agent: 'Ingestion', state: 'completed' },
    'ingestion_failed': { agent: 'Ingestion', state: 'failed' },
    'transcribing': { agent: 'Transcription', state: 'active' },
    'transcribed': { agent: 'Transcription', state: 'completed' },
    'transcription_failed': { agent: 'Transcription', state: 'failed' },
    'auth_failed': { agent: 'Transcription', state: 'failed' },
    'analyzing': { agent: 'Analysis', state: 'active' },
    'analyzed': { agent: 'Analysis', state: 'completed' },
    'analysis_failed': { agent: 'Analysis', state: 'failed' },
    'generating_copy': { agent: 'Copywriting', state: 'active' },
    'copy_generated': { agent: 'Copywriting', state: 'completed' },
    'copy_failed': { agent: 'Copywriting', state: 'failed' },
    'generating_visuals': { agent: 'Visuals', state: 'active' },
    'visuals_generated': { agent: 'Visuals', state: 'completed' },
    'visuals_failed': { agent: 'Visuals', state: 'failed' },
    'publishing': { agent: 'Publisher', state: 'active' },
    'published': { agent: 'Publisher', state: 'completed' },
    'publishing_failed': { agent: 'Publisher', state: 'failed' },
  };

  let agentStates: Record<string, 'pending' | 'active' | 'completed' | 'failed'> = {};

  $: {
    const newStates: Record<string, 'pending' | 'active' | 'completed' | 'failed'> = {};
    let completedUpTo = -1;

    if ($videoStatus?.status) {
      const current = statusMap[$videoStatus.status];
      if (current) {
        if (current.state === 'completed') {
          completedUpTo = agents.indexOf(current.agent);
        }
        // Set state for all agents up to and including the one that just completed
        for (let i = 0; i <= completedUpTo; i++) {
          newStates[agents[i]] = 'completed';
        }
        // Set the current agent's specific state
        newStates[current.agent] = current.state;
      }
    }
    agentStates = newStates;
  }
</script>

<section class="workflow-section">
  <h3 class="text-lg font-semibold mb-4 text-gray-700">Live Workflow</h3>
  <div class="workflow-container">
    {#each agents as agent, i}
      <div class="workflow-step-container">
        <div
          class="workflow-step"
          class:active={agentStates[agent] === 'active'}
          class:completed={agentStates[agent] === 'completed'}
          class:failed={agentStates[agent] === 'failed'}
        >
          {agent}
        </div>
        {#if retriggerable && (agentStates[agent] === 'completed' || agentStates[agent] === 'failed')}
          <button 
            class="retrigger-button" 
            on:click={() => dispatch('retrigger', { stage: agent })}
          >
            Re-run
          </button>
        {/if}
      </div>
      {#if i < agents.length - 1}
        <div 
          class="workflow-arrow"
          class:completed={agentStates[agent] === 'completed'}
        />
      {/if}
    {/each}
  </div>
</section>

<style>
  .workflow-section {
    padding: 1.5rem;
    background-color: #ffffff;
    border-radius: 0.5rem;
    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
  }
  .workflow-container {
    display: flex;
    align-items: center;
    flex-wrap: wrap; /* Allows steps to wrap on smaller screens */
  }
  .workflow-step {
    padding: 0.5rem 1rem;
    border-radius: 0.375rem; /* rounded-md */
    font-weight: 500; /* font-medium */
    background-color: #e5e7eb; /* bg-gray-200 */
    color: #374151; /* text-gray-700 */
    transition: all 0.3s ease;
    border: 1px solid #d1d5db; /* Default border */
  }
  .workflow-step.completed {
    background-color: #dcfce7; /* bg-green-100 */
    color: #166534; /* text-green-800 */
    border-color: #86efac; /* border-green-300 */
  }
  .workflow-step.active {
    background-color: #cffafe; /* bg-cyan-100 */
    color: #0e7490; /* text-cyan-800 */
    border-color: #67e8f9; /* border-cyan-300 */
    transform: scale(1.05);
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  }
  .workflow-step.failed {
    background-color: #fee2e2; /* bg-red-100 */
    color: #991b1b; /* text-red-800 */
    border-color: #fca5a5; /* border-red-300 */
  }
  .workflow-arrow {
    width: 0;
    height: 0;
    border-top: 10px solid transparent;
    border-bottom: 10px solid transparent;
    border-left: 10px solid #9ca3af; /* text-gray-400 */
    margin: 0 1rem; /* Adjust spacing */
    transition: all 0.3s ease;
  }
  .workflow-arrow.completed {
    border-left-color: #166534; /* text-green-800 */
  }
  .workflow-step-container {
    display: flex;
    flex-direction: column;
    align-items: center;
  }
  .retrigger-button {
    font-size: 0.75rem;
    padding: 0.1rem 0.5rem;
    margin-top: 0.5rem;
    border: 1px solid #9ca3af;
    border-radius: 0.25rem;
    background-color: #f3f4f6;
    cursor: pointer;
  }
  .retrigger-button:hover {
    background-color: #e5e7eb;
  }
</style>
