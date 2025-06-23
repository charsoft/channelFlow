<!-- src/components/GeneratedImages.svelte -->
<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import Swal from 'sweetalert2';
  import { generateNewPrompts, generateOnDemandImage } from '../lib/api';

  // --- Props from Parent ---
  export let videoId: string;
  export let videoSummary: string = '';
  export let generatedThumbnails: any[] = [];
  export let onDemandThumbnails: any[] = [];

  // --- Local State ---
  let newPrompts: string[] = [];
  let isLoadingPrompts = false;
  let imageGenerationStates: { [key: number]: { model: string; isLoading: boolean } } = {};

  const imagenModels = [
    'imagegeneration@006',
    'imagegeneration@005',
    'imagegeneration@002',
    'imagen-3.0-generate-002',
    'imagen-3.0-fast-generate-001'
  ];

  const dispatch = createEventDispatcher();

  function showImageModal(imageUrl: string) {
    dispatch('showImageModal', { imageUrl });
  }

  // --- On-Demand Generation ---
  async function handleGeneratePrompts() {
    isLoadingPrompts = true;
    newPrompts = [];
    imageGenerationStates = {};

    try {
      const prompts = await generateNewPrompts(videoId, videoSummary);
      newPrompts = prompts;
      prompts.forEach((_, index) => {
        imageGenerationStates[index] = { model: 'imagegeneration@006', isLoading: false };
      });
    } catch (error: any) {
      Swal.fire('Error', `Could not generate prompts: ${error.message}`, 'error');
    } finally {
      isLoadingPrompts = false;
    }
  }

  async function handleGenerateImage(prompt: string, index: number) {
    const state = imageGenerationStates[index];
    state.isLoading = true;
    imageGenerationStates = { ...imageGenerationStates }; // Trigger reactivity

    try {
      const newImage = await generateOnDemandImage(videoId, prompt, state.model);
      dispatch('newOnDemandImage', newImage);
      // Remove the used prompt from the list
      newPrompts = newPrompts.filter(p => p !== prompt);
    } catch (error: any) {
      Swal.fire('Error', `Image generation failed: ${error.message}`, 'error');
      state.isLoading = false;
      imageGenerationStates = { ...imageGenerationStates };
    }
  }
</script>

<!-- Existing Thumbnails -->
<div class="detail-section">
  <h2>Generated Thumbnails</h2>
  <p class="section-description">Thumbnails created by the agent pipeline. Click an image to view it in full size.</p>

  {#if generatedThumbnails.length === 0 && onDemandThumbnails.length === 0}
    <p class="empty-state">No thumbnails have been generated for this video yet.</p>
  {:else}
    <div class="thumbnails-grid">
      {#each [...(generatedThumbnails || []), ...(onDemandThumbnails || [])] as thumb}
        {@const imageUrl = thumb.image_url}
        {#if imageUrl}
          <div class="thumbnail-item">
            <button type="button" class="thumbnail-image-wrapper" on:click={() => showImageModal(imageUrl)}>
              <img src={imageUrl} alt={thumb.prompt || 'Generated visual'}>
            </button>
            <div class="thumbnail-footer">
                <p>{thumb.prompt || 'No prompt'}</p>
            </div>
          </div>
        {/if}
      {/each}
    </div>
  {/if}
</div>

<!-- On-Demand Generation -->
<div class="detail-section">
  <h2>On-Demand Generation</h2>
  <p class="section-description">Generate new image prompts based on the video's content, then select an image model to create a new visual on the fly.</p>
  <div class="on-demand-controls">
    <button class="button-primary" on:click={handleGeneratePrompts} disabled={isLoadingPrompts}>
      {#if isLoadingPrompts}Generating...{:else}✨ Generate New Prompts{/if}
    </button>
  </div>

  {#if newPrompts.length > 0}
    <ul class="new-prompts-list">
      {#each newPrompts as prompt, index (prompt)}
        {@const state = imageGenerationStates[index]}
        <li class:generating={state?.isLoading}>
          <span class="prompt-text">{prompt}</span>
          <div class="prompt-controls">
            <div class="control-group">
              <select bind:value={imageGenerationStates[index].model} disabled={state?.isLoading}>
                {#each imagenModels as model}
                  <option value={model}>{model}</option>
                {/each}
              </select>
            </div>
            <button class="button-secondary generate-image-btn" on:click={() => handleGenerateImage(prompt, index)} disabled={state?.isLoading}>
              {#if state?.isLoading}Generating...{:else}Generate Image{/if}
            </button>
          </div>
        </li>
      {/each}
    </ul>
  {/if}
</div>

<style>
  .detail-section { background-color: #ffffff; padding: 1.5rem; border-radius: 1rem; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 2rem; }
  .detail-section h2 { font-size: 1.5rem; font-weight: 700; color: #1a202c; margin-bottom: 0.5rem; }
  .section-description { font-size: 0.9rem; color: #718096; margin-bottom: 1.5rem; }
  .thumbnails-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 1.5rem; }
  .thumbnail-item { display: flex; flex-direction: column; border-radius: 0.75rem; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out; }
  .thumbnail-item:hover { transform: translateY(-5px); box-shadow: 0 10px 15px rgba(0,0,0,0.1); }
  .thumbnail-image-wrapper { display: block; width: 100%; aspect-ratio: 16 / 9; cursor: pointer; border: none; padding: 0; background-color: #f7fafc; }
  .thumbnail-image-wrapper img { width: 100%; height: 100%; object-fit: cover; }
  .thumbnail-footer { background-color: #f9fafb; padding: 1rem; border-top: 1px solid #e2e8f0; flex-grow: 1; }
  .thumbnail-footer p { margin: 0; font-size: 0.85rem; color: #4a5568; line-height: 1.4; }
  .empty-state { color: #718096; text-align: center; padding: 2rem; background-color: #f9fafb; border-radius: 0.75rem; }

  /* On-demand styles */
  .button-primary { background-color: #4F46E5; color: white; padding: 0.6rem 1.2rem; font-weight: 600; border-radius: 9999px; border: none; cursor: pointer; transition: background-color 0.2s; }
  .button-primary:hover { background-color: #4338ca; }
  .button-primary:disabled { background-color: #a5b4fc; cursor: not-allowed; }
  .button-secondary { background: none; border: 1px solid #d1d5db; color: #475569; padding: 0.5rem 1rem; font-size: 0.9rem; border-radius: 0.375rem; cursor: pointer; }
  .on-demand-controls { margin-bottom: 1.5rem; }
  .new-prompts-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 1rem; }
  .new-prompts-list li { background-color: #f7fafc; padding: 1rem; border-radius: 0.5rem; border: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center; gap: 1rem; }
  .new-prompts-list li.generating { opacity: 0.6; pointer-events: none; }
  .prompt-text { flex-grow: 1; font-size: 0.9rem; color: #4a5568; }
  .prompt-controls { display: flex; align-items: center; gap: 0.75rem; }
  select { font-size: 0.8rem; padding: 0.4rem 0.6rem; border-radius: 0.375rem; border: 1px solid #d1d5db; }
</style>