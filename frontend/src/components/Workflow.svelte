<!-- src/components/Workflow.svelte -->
<script lang="ts">
  export let activeAgent: string = '';
  const agents = ['Ingestion', 'Transcription', 'Analysis', 'Copywriting', 'Visuals', 'Publisher'];
</script>

<section class="workflow-section">
  <h3 class="text-lg font-semibold mb-4 text-gray-700">Live Workflow</h3>
  <div class="workflow-container">
    {#each agents as agent, i}
      <div
        class="workflow-step"
        class:active={activeAgent === agent}
      >
        {agent}
      </div>
      {#if i < agents.length - 1}
        <div class="workflow-arrow" />
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
    border: 1px solid #d1d5db;
  }
  .workflow-step.active {
    background-color: #4f46e5; /* bg-indigo-600 */
    color: #ffffff; /* text-white */
    transform: scale(1.05);
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  }
  .workflow-arrow {
    width: 0;
    height: 0;
    border-top: 10px solid transparent;
    border-bottom: 10px solid transparent;
    border-left: 10px solid #9ca3af; /* text-gray-400 */
    margin: 0 1rem; /* Adjust spacing */
  }
</style>
