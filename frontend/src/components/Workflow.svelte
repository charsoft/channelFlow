<!-- src/components/Workflow.svelte -->
<script lang="ts">
  export let activeAgent: string = '';
  const agents = ['Ingestion', 'Transcription', 'Analysis', 'Copywriting', 'Visuals', 'Publisher'];
</script>

<section class="workflow-section p-4 bg-white rounded-lg shadow-sm">
  <h3 class="text-lg font-semibold mb-3">Live Workflow</h3>
  <div class="flex flex-col space-y-2">
    {#each agents as agent, i}
      <div class="flex items-center">
        <div
          class="px-3 py-1 rounded font-medium"
          class:bg-indigo-600={activeAgent === agent}
          class:text-white={activeAgent === agent}
          class:bg-gray-200={activeAgent !== agent}
          class:text-gray-700={activeAgent !== agent}
        >
          {agent}
        </div>
        {#if i < agents.length - 1}
          <div class="mx-2 text-gray-400">↓</div>
        {/if}
      </div>
    {/each}
  </div>
</section>
