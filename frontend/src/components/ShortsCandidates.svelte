<script lang="ts">
  import type { Writable } from 'svelte/store';
  import Swal from 'sweetalert2';
  import { sanitizeTitleForFilename } from '../lib/utils';

  // --- Props ---
  export let candidates: any[] = [];
  export let videoId: string;
  export let videoTitle: string;
  
  // --- Local State ---
  let shortsWithState: any[] = [];

  // Reactive statement to update local state when props change
  $: {
    shortsWithState = candidates.map(c => ({
      ...c,
      isGenerating: false,
      editedStartTime: parseFloat(c.start_time).toFixed(1),
      editedEndTime: parseFloat(c.end_time).toFixed(1),
    }));
  }

  // --- Methods ---
  async function generateClip(index: number) {
    const short = shortsWithState[index];
    if (!short) return;

    short.isGenerating = true;
    
    try {
        const response = await fetch(`/api/video/${videoId}/generate-clip`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                start_time: short.editedStartTime,
                end_time: short.editedEndTime,
                suggested_title: short.suggested_title
            })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Unknown server error' }));
            throw new Error(errorData.detail || `Server error: ${response.statusText}`);
        }

        const data = await response.json();
        
        // Assume the backend returns the URL of the generated clip
        short.generated_clip_url = data.clip_url; 
        
        Swal.fire({
            toast: true,
            position: 'top-end',
            icon: 'success',
            title: 'Clip generated!',
            showConfirmButton: false,
            timer: 2500
        });

    } catch (error: any) {
        console.error('Clip generation failed:', error);
        Swal.fire('Clip Generation Error', `Could not generate the clip: ${error.message}`, 'error');
    } finally {
        short.isGenerating = false;
    }
  }
</script>

<div class="detail-section" id="shorts-candidates">
  {#if shortsWithState && shortsWithState.length > 0}
    <ul class="shorts-list">
      {#each shortsWithState as short, index}
        <li class="short-candidate-item">
          <div class="short-info">
            <h4>{short.suggested_title}</h4>
            <p><strong>Reason:</strong> {short.reason}</p>
            {#if short.transcript_snippet}
              <p class="snippet"><em>"{short.transcript_snippet}"</em></p>
            {/if}
            <div class="timestamp-editor">
              <label for="start-time-{index}">Start (s):</label>
              <input type="number" step="0.1" id="start-time-{index}" class="time-input" bind:value={short.editedStartTime}>
              <label for="end-time-{index}">End (s):</label>
              <input type="number" step="0.1" id="end-time-{index}" class="time-input" bind:value={short.editedEndTime}>
            </div>
          </div>
          <div class="short-actions">
            {#if short.generated_clip_url}
              <div class="clip-preview-container">
                <video controls src={short.generated_clip_url} width="200" preload="metadata"></video>
                <div class="clip-buttons">
                  <a href={short.generated_clip_url} download="{sanitizeTitleForFilename(short.suggested_title)}.mp4" class="button-secondary">Download</a>
                  <button class="button-danger" on:click={() => generateClip(index)} disabled={short.isGenerating}>
                    {#if short.isGenerating}Re-generating...{:else}Re-generate{/if}
                  </button>
                </div>
              </div>
            {:else}
              <button class="button-secondary" on:click={() => generateClip(index)} disabled={short.isGenerating}>
                {#if short.isGenerating}Generating...{:else}Generate Clip{/if}
              </button>
            {/if}
          </div>
        </li>
      {/each}
    </ul>
  {:else}
    <p>No shorts candidates were identified for this video.</p>
  {/if}
</div>

<style>
  .shorts-list {
    list-style: none;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .short-candidate-item {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 2rem;
    padding: 1.5rem;
    background-color: #f8fafc;
    border-radius: 0.5rem;
    border: 1px solid #e2e8f0;
    align-items: center;
  }

  .short-info h4 {
    margin: 0 0 0.5rem 0;
    font-size: 1.2rem;
    color: #374151;
  }

  .short-info p {
    margin: 0.5rem 0;
    color: #475569;
    line-height: 1.5;
  }
  .short-info .snippet {
    color: #64748b;
    font-size: 0.95rem;
    border-left: 3px solid #e2e8f0;
    padding-left: 1rem;
    margin-top: 1rem;
  }

  .timestamp-editor {
    margin-top: 1.5rem;
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .timestamp-editor label {
    font-weight: 500;
  }

  .time-input {
    width: 80px;
    padding: 0.5rem;
    border-radius: 0.375rem;
    border: 1px solid #d1d5db;
  }

  .short-actions {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 1rem;
  }
  
  .clip-buttons {
    display: flex;
    gap: 0.5rem;
    margin-top: 0.5rem;
  }

  /* Standard button styles from VideoDetail.svelte */
  :global(.button-secondary) {
    background: none;
    border: 1px solid #d1d5db;
    color: #475569;
    padding: 0.5rem 1rem;
    font-size: 0.9rem;
    border-radius: 0.375rem;
    cursor: pointer;
    transition: background-color 0.2s, color 0.2s;
    text-decoration: none;
  }
  :global(.button-secondary:hover) {
    background-color: #f3f4f6;
    border-color: #9ca3af;
  }
  :global(.button-danger) {
    background-color: #fee2e2;
    border: 1px solid #fecaca;
    color: #b91c1c;
  }
  :global(.button-danger:hover) {
    background-color: #fecaca;
  }

  /* Responsive */
  @media (max-width: 768px) {
    .short-candidate-item {
      grid-template-columns: 1fr;
      gap: 1.5rem;
    }
    .short-actions {
      align-items: flex-start;
    }
  }
</style> 