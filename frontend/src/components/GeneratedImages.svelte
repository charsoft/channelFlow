<!-- src/components/GeneratedImages.svelte -->
<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import Swal from 'sweetalert2';
  import { generateNewPrompts, generateOnDemandImage } from '../lib/api';
  import { sanitizeTitleForFilename } from '../lib/utils';

  // --- Props from Parent ---
  export let videoId: string;
  export let videoTitle: string;
  export let generatedThumbnails: any[] = [];
  export let onDemandThumbnails: any[] = [];
  export let facebookPost: string = '';
  let isImageModalVisible = false;
  // --- Local State ---
  let newPrompts: string[] = [];
  let isLoadingPrompts = false;
  let imageGenerationStates: { [key: number]: { model: string; isLoading: boolean } } = {};

  const imagenModels = [
    'imagegeneration@006',
    'imagegeneration@005',
    'imagegeneration@004',
    'imagegeneration@002'
  ];

  const dispatch = createEventDispatcher();

  // --- On-Demand Generation ---
  async function handleGeneratePrompts() {
    isLoadingPrompts = true;
    newPrompts = [];
    imageGenerationStates = {};

    try {
      const prompts = await generateNewPrompts(videoId);
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
      newPrompts = newPrompts.filter(p => p !== prompt);
    } catch (error: any) {
      Swal.fire('Error', `Image generation failed: ${error.message}`, 'error');
      state.isLoading = false;
      imageGenerationStates = { ...imageGenerationStates };
    }
    // No finally block needed as loading is handled per path
  }

  // --- Image Actions ---
  async function downloadImage(imageUrl: string) {
    try {
      const response = await fetch(imageUrl, { cache: 'no-cache' });
      if (!response.ok) throw new Error(`Network response was not ok: ${response.statusText}`);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = `channel_post_${sanitizeTitleForFilename(videoTitle)}.png`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (err: any) {
      Swal.fire('Download Error', `Could not download the image: ${err.message}`, 'error');
    }
  }

  function showPostPreview(imageUrl: string) {
    const plainTextPost = facebookPost.replace(/<br\s*\/?>/gi, '\n');

    Swal.fire({
      title: 'Post Preview',
      html: `
        <div class="social-preview-content">
          <img src="${imageUrl}" alt="Post image preview" style="max-width: 100%; border-radius: 8px;">
          <div class="social-preview-caption">${facebookPost}</div>
          <p class="coming-soon"><i><b>Coming soon:</b> Push this post directly to your social media accounts and stay in the flow!</i></p>
        </div>
      `,
      confirmButtonText: 'Copy Text & Download Image',
      showCancelButton: true,
      cancelButtonText: 'Just Close',
      customClass: { popup: 'social-preview-popup' }
    }).then((result) => {
      if (result.isConfirmed) {
        navigator.clipboard.writeText(plainTextPost).then(() => {
          downloadImage(imageUrl);
          Swal.fire({
            toast: true,
            position: 'top-end',
            icon: 'success',
            title: 'Copied & Downloading!',
            showConfirmButton: false,
            timer: 2500
          });
        }).catch(() => {
          Swal.fire('Error', 'Could not copy text to clipboard.', 'error');
        });
      }
    });
  }
</script>

<!-- Existing Thumbnails -->
<div class="detail-section">
  <h2>Generated Thumbnails</h2>
  <p class="section-description">Thumbnails created by the agent pipeline. Click an image to view or preview the post.</p>
  {#if generatedThumbnails.length === 0 && onDemandThumbnails.length === 0}
    <p class="empty-state">No thumbnails have been generated for this video yet.</p>
  {:else}
    <div class="thumbnails-grid">
      {#each [...(generatedThumbnails || []), ...(onDemandThumbnails || [])] as thumb}
        {@const imageUrl = thumb.image_url}
        {#if imageUrl}
          <div class="thumbnail-item">
            <button type="button" class="thumbnail-image-wrapper" on:click={() => dispatch('showImageModal', { imageUrl })} >
              <img src={imageUrl} alt={thumb.prompt || 'Generated visual'}>
            </button>
            <div class="thumbnail-footer">
              <button class="button-secondary preview-post-btn" on:click|stopPropagation={() => showPostPreview(imageUrl)}>
                Preview Post
              </button>
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
  .thumbnail-item { position: relative; border-radius: 0.75rem; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out; }
  .thumbnail-item:hover { transform: translateY(-5px); box-shadow: 0 10px 15px rgba(0,0,0,0.1); }
  .thumbnail-image-wrapper { display: block; width: 100%; aspect-ratio: 16 / 9; cursor: pointer; border: none; padding: 0; background-color: #f7fafc; }
  .thumbnail-image-wrapper img { width: 100%; height: 100%; object-fit: cover; }
  .thumbnail-footer { position: absolute; bottom: 0; left: 0; right: 0; background: linear-gradient(to top, rgba(0,0,0,0.7) 0%, rgba(0,0,0,0) 100%); padding: 1rem; display: flex; justify-content: center; opacity: 0; transition: opacity 0.2s ease-in-out; }
  .thumbnail-item:hover .thumbnail-footer { opacity: 1; }
  .button-secondary.preview-post-btn { background-color: rgba(255, 255, 255, 0.9); color: #2d3748; border: 1px solid rgba(255, 255, 255, 0.5); font-weight: 600; font-size: 0.8rem; padding: 0.4rem 0.8rem; border-radius: 9999px; cursor: pointer; transition: background-color 0.2s ease; }
  .button-secondary.preview-post-btn:hover { background-color: #ffffff; }
  .on-demand-controls { margin-bottom: 1.5rem; }
  .new-prompts-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 1rem; }
  .new-prompts-list li { background-color: #f7fafc; padding: 1rem; border-radius: 0.5rem; border: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center; gap: 1rem; }
  .new-prompts-list li.generating { opacity: 0.6; pointer-events: none; }
  .prompt-text { flex-grow: 1; font-size: 0.9rem; color: #4a5568; }
  .prompt-controls { display: flex; align-items: center; gap: 0.75rem; }
  select { font-size: 0.8rem; padding: 0.4rem 0.6rem; border-radius: 0.375rem; border: 1px solid #d1d5db; }
  .empty-state { color: #718096; text-align: center; padding: 2rem; background-color: #f9fafb; border-radius: 0.75rem; }
  :global(.social-preview-popup .coming-soon) { font-size: 0.8rem; color: #718096; margin-top: 1rem; border-top: 1px solid #e2e8f0; padding-top: 1rem; }
</style>