<!-- src/components/Workflow.svelte -->
<script lang="ts">
  import { createEventDispatcher } from 'svelte';
 
/** 
   * Now we accept a pre-built list of stages,
   * each with its `name` and one of four statuses.
   */
  export let isRestartMode = true;

  export let stages: {
    name: string;
    status: 'pending' | 'active' | 'completed' | 'failed';
  }[] = [];

  const dispatch = createEventDispatcher();

  function handleStepClick(stage: { name: string; status: string }) {
    if (isRestartMode && stage.status === 'completed') {
      dispatch('retrigger', { stage: stage.name });
    }
  }
  

</script>

<section class="workflow-section">
  <h3 class="text-lg font-semibold mb-4 text-gray-700">Live Workflow</h3>
  <div class="workflow-container">
   {#each stages as stage, i}
     <button
       type="button"
       class="workflow-step"
       class:success={stage.status === 'completed'}
       class:active={stage.status === 'active'}
       class:failed={stage.status === 'failed'}
       class:pending={stage.status === 'pending'}
       class:restart-active={isRestartMode && stage.status === 'completed'}
       on:click={() => handleStepClick(stage)}
      disabled={isRestartMode && stage.status !== 'completed'}
     >
       <div class="workflow-step-container">
        <span>{stage.name}</span>
        {#if isRestartMode && stage.status === 'completed'}
          <button class="retrigger-button" on:click|stopPropagation={() => handleStepClick(stage)}>
            Restart from here
          </button>
        {/if}
      </div>
     </button>

     {#if i < stages.length - 1}
       <div
        class="workflow-arrow"
         class:completed={stage.status === 'completed'}
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
  button.workflow-step {
    /* Base styles */
    padding: 0.5rem 1rem;
    border-radius: 0.375rem; /* rounded-md */
    font-weight: 500; /* font-medium */
    transition: all 0.3s ease;
    border: 1px solid; /* Default border, color will be set by status */
    
    /* Button resets */
    font-family: inherit;
    font-size: 100%;
    margin: 0;
    text-align: center;
    cursor: default; /* Not clickable by default */
  }
  .workflow-step.pending {
    background-color: #e5e7eb; /* bg-gray-200 */
    color: #374151; /* text-gray-700 */
    border-color: #d1d5db; /* border-gray-300 */
  }
  .workflow-step.success {
    background-color: #dcfce7; /* bg-green-100 */
    color: #166534; /* text-green-800 */
    border-color: #86efac; /* border-green-300 */
  }
  .workflow-step.active {
    background-color: #fefce8; /* bg-yellow-50 */
    color: #854d0e; /* text-yellow-800 */
    border-color: #fde047; /* border-yellow-300 */
    transform: scale(1.05);
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  }
  .workflow-step.failed {
    background-color: #fee2e2; /* bg-red-100 */
    color: #991b1b; /* text-red-800 */
    border-color: #fca5a5; /* border-red-300 */
  }
  .workflow-step.restart-active {
    cursor: pointer;
    box-shadow: 0 0 0 3px #9ca3af; /* A gray ring to indicate it's clickable */
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
