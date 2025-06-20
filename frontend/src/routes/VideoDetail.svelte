<script lang="ts">
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import Swal from 'sweetalert2';
  import { marked } from 'marked';
  import { accessToken } from '../lib/auth';
  import { getHeaders } from '../lib/api';

  import { listenForUpdates } from '../lib/api';
  import { sanitizeTitleForFilename } from '../lib/utils';
  import ShortsCandidates from '../components/ShortsCandidates.svelte';

  export let params: { id?: string } = {};

  // --- State ---
  let videoData: any = null;
  let isLoading = true;
  let errorMessage = '';
  let activeTab = 'overview';
  let isImageModalVisible = false;
  let modalImageUrl = '';
  let selectedModel = 'imagen-4.0-generate-preview-06-06'; // Default model
  let newPrompts: string[] = [];
  let promptsLoader = false;
  let isEditingPrompts = false;
  let editedPrompts: { [key: number]: string } = {};
  let promptGenerationStates: { [key: number]: { selectedModel: string; isGenerating: boolean } } = {};
  let substackHtml = '';
  let isLoadingSubstack = false;
  let processedNewsletterHtml = '';
  
  let newsletterPreImageHtml = '';
  let newsletterPostImageHtml = '';
  let availableImages: any[] = [];
  let isImageSelectorVisible = false;
  let selectedNewsletterImage = '';

  const imagenModels = [
    'imagen-4.0-generate-preview-06-06',
    'imagen-4.0-ultra-generate-preview-06-06',
    'imagen-4.0-fast-generate-preview-06-06',
    'imagen-3.0-generate-002',
    'imagen-3.0-fast-generate-001'
  ];

  // --- Lifecycle ---
  onMount(() => {
    if (!$accessToken) {
      push('/');
      return;
    }
    loadVideoDetails();
  });

  $: if (activeTab === 'copy') {
    loadSubstackContent();
  }

  $: {
    if (activeTab === 'copy' && videoData) {
        availableImages = [...(videoData.image_urls || []), ...(videoData.on_demand_thumbnails || []).map((t: any) => t.image_url)];

        if(videoData.marketing_copy?.email_newsletter) {
            let markdownBody = '';
            if (typeof videoData.marketing_copy.email_newsletter === 'object') {
                markdownBody = videoData.marketing_copy.email_newsletter.body;
            } else {
                markdownBody = videoData.marketing_copy.email_newsletter;
            }

            const parts = markdownBody.split(/\[Image\]/g);
            newsletterPreImageHtml = marked(parts[0]) as string;
            if (parts.length > 1) {
                newsletterPostImageHtml = marked(parts.slice(1).join('')) as string;
            } else {
                newsletterPostImageHtml = '';
            }
        }
    }
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
        if (isImageModalVisible) isImageModalVisible = false;
        if (isImageSelectorVisible) isImageSelectorVisible = false;
    }
  }

  // --- Data Loading ---
  async function loadVideoDetails() {
    console.log(`[VideoDetail] loadVideoDetails called for video ID: ${params.id}`);
    if (!params.id) {
      errorMessage = 'No video ID specified.';
      isLoading = false;
      return;
    }
    
    isLoading = true;
    try {
      const response = await fetch(`/api/video/${params.id}`, {
        headers: await getHeaders()
      });
      if (!response.ok) {
        if (response.status === 401) {
            push('/');
            return;
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      videoData = data.video;
    } catch (error: any) {
      errorMessage = 'Could not load video details. Please try again later.';
      console.error('Failed to load video details:', error);
    } finally {
      isLoading = false;
    }
  }

  async function loadSubstackContent() {
    if (!videoData?.substack_gcs_uri || isLoadingSubstack || substackHtml) return;
    
    isLoadingSubstack = true;
    try {
        const url = videoData.substack_gcs_uri.replace("gs://", "https://storage.googleapis.com/");
        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to fetch article content.');
        const markdown = await response.text();
        substackHtml = marked(markdown) as string;
    } catch (error) {
        console.error("Error loading Substack content:", error);
        // Optionally, show an error message to the user
    } finally {
        isLoadingSubstack = false;
    }
  }

  // --- Helpers ---
  function getStatusClass(status: string): string {
    if (!status) return 'status-unknown';
    if (status.includes('failed')) return 'status-failed';
    if (status === 'published' || status.includes('completed') || status.includes('generated')) return 'status-success';
    if (status) return 'status-in-progress';
    return 'status-unknown';
  }

  // --- Event Handlers ---
  function showImageModal(imageUrl: string) {
    modalImageUrl = imageUrl;
    isImageModalVisible = true;
  }
  
  async function downloadImage(imageUrl: string, videoTitle: string) {
      try {
          const response = await fetch(imageUrl, { cache: 'no-cache' });
          if (!response.ok) throw new Error(`Network response was not ok: ${response.statusText}`);
          
          const blob = await response.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.style.display = 'none';
          a.href = url;
          const safeTitle = sanitizeTitleForFilename(videoTitle);
          a.download = `channel_post_${safeTitle}.png`;
          document.body.appendChild(a);
          a.click();
          window.URL.revokeObjectURL(url);
          a.remove();
      } catch (err) {
          console.error('Failed to download image:', err);
          Swal.fire('Download Error', 'Could not download the image.', 'error');
      }
  }

  function showPostPreview(imageUrl: string) {
    const postContent = videoData?.marketing_copy?.facebook_post;
    if (!postContent) {
        Swal.fire('Error', 'Could not find post content.', 'error');
        return;
    }

    const plainTextPost = postContent.replace(/<br\s*\/?>/gi, '\n');

    Swal.fire({
        title: 'Post Preview',
        html: `
            <div class="social-preview-content">
                <img src="${imageUrl}" alt="Post image preview" style="max-width: 100%; border-radius: 8px;">
                <div class="social-preview-caption">${postContent}</div>
            </div>
        `,
        confirmButtonText: 'Copy Text & Download Image',
        showCancelButton: true,
        cancelButtonText: 'Just Close',
        customClass: { popup: 'social-preview-popup' }
    }).then((result) => {
        if (result.isConfirmed) {
            navigator.clipboard.writeText(plainTextPost).then(() => {
                downloadImage(imageUrl, videoData.video_title);
                Swal.fire({
                    toast: true,
                    position: 'top-end',
                    icon: 'success',
                    title: 'Copied & Downloading!',
                    showConfirmButton: false,
                    timer: 2500
                });
            }).catch(() => {
                Swal.fire('Error', 'Could not copy text.', 'error');
            });
        }
    });
  }

  async function handleGeneratePrompts() {
    if (!videoData?.structured_data?.summary) {
        Swal.fire('Error', 'Video summary is not available to generate prompts.', 'error');
        return;
    }
    
    promptsLoader = true;
    newPrompts = [];
    promptGenerationStates = {};

    try {
        const response = await fetch(`/api/video/${params.id}/generate-prompts`, { 
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ context: videoData.structured_data.summary })
        });
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Unknown server error' }));
            throw new Error(errorData.detail || `Server error: ${response.statusText}`);
        }
        const data = await response.json();
        newPrompts = data.prompts || [];
        // Initialize state for each new prompt
        newPrompts.forEach((_, index) => {
            promptGenerationStates[index] = {
                selectedModel: 'imagen-4.0-generate-preview-06-06', // Default model
                isGenerating: false
            };
        });
    } catch (error: any) {
        console.error('Failed to generate new prompts:', error);
        Swal.fire('Error', `Could not generate prompts: ${error.message}`, 'error');
    } finally {
        promptsLoader = false;
    }
  }
  
  function startEditing() {
      editedPrompts = {}; // Reset edits
      isEditingPrompts = true;
  }

  function cancelEditing() {
      isEditingPrompts = false;
  }

  async function handleGenerateImage(prompt: string, index: number) {
      const state = promptGenerationStates[index];
      if (!state) return;

      state.isGenerating = true;

      try {
          const response = await fetch(`/api/video/${params.id}/generate-image`, {
              method: 'POST',
              headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({ prompt: prompt, model_name: state.selectedModel })
          });

          if (!response.ok) throw new Error('Failed to generate image');
          
          const newImage = await response.json();
          
          // Add the new thumbnail to the list for immediate display
          videoData.on_demand_thumbnails = [...(videoData.on_demand_thumbnails || []), newImage];
          
          // Remove the prompt from the list once used
          newPrompts = newPrompts.filter((_, i) => i !== index);

      } catch (error) {
          console.error("On-demand thumbnail generation failed:", error);
          Swal.fire('Error', 'Image generation failed.', 'error');
      } finally {
          state.isGenerating = false;
      }
  }

  function selectImageForNewsletter(imageUrl: string) {
    selectedNewsletterImage = imageUrl;
    isImageSelectorVisible = false;
  }
</script>

<svelte:window on:keydown={handleKeydown}/>

{#if isLoading}
  <div class="loader"></div>
{:else if errorMessage}
  <p class="error-message">{errorMessage}</p>
{:else if videoData}
<div class="detail-container">
    <header class="detail-header">
        <h1>{videoData.video_title || 'Untitled Video'}</h1>
        <div class="header-meta">
            <span class="video-meta-item">
                Processed: {videoData.received_at ? new Date(videoData.received_at).toLocaleDateString() : 'N/A'}
            </span>
            <div class="status-banner {getStatusClass(videoData.status)}">
                Status: {videoData.status.replace(/_/g, ' ')}
            </div>
        </div>
    </header>

    <div class="video-detail-content">
        <!-- Tab Navigation -->
        <div class="tab-nav">
            <button class="tab-link" class:active={activeTab === 'overview'} on:click={() => activeTab = 'overview'}>Overview</button>
            <button class="tab-link" class:active={activeTab === 'images'} on:click={() => activeTab = 'images'}>Generated Images</button>
            <button class="tab-link" class:active={activeTab === 'copy'} on:click={() => activeTab = 'copy'}>Generated Copy</button>
            <button class="tab-link" class:active={activeTab === 'shorts'} on:click={() => activeTab = 'shorts'}>Shorts Candidates</button>
        </div>

        <!-- Tab Content Panels -->
        {#if activeTab === 'overview'}
        <div class="tab-content active">
            <div class="overview-grid">
                 <div class="video-player-wrapper">
                    <iframe
                        class="youtube-iframe"
                        src={`https://www.youtube.com/embed/${videoData.video_id}`}
                        title="YouTube video player"
                        frameborder="0"
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                        allowfullscreen
                    ></iframe>
                </div>
                {#if videoData.structured_data?.summary}
                <div class="detail-section" id="summary-section">
                    <h2>Summary</h2>
                    <p>{videoData.structured_data.summary}</p>
                </div>
                {/if}
            </div>
        </div>
        {/if}
        
        {#if activeTab === 'images'}
        <div class="tab-content active">
             <div class="detail-section">
                <h2>Generated Thumbnails</h2>
                <p class="section-description">Thumbnails generated by the agent. Click an image to view it in full size or preview the post.</p>
                <div class="thumbnails-grid">
                    {#each [...(videoData.image_urls || []), ...(videoData.on_demand_thumbnails || [])] as thumb}
                        {@const imageUrl = typeof thumb === 'string' ? thumb : thumb.image_url}
                        <div class="thumbnail-item">
                            <button type="button" class="thumbnail-image-wrapper" on:click={() => showImageModal(imageUrl)}>
                                <img src={imageUrl} alt="Generated visual">
                            </button>
                            <div class="thumbnail-footer">
                                <button class="button-secondary preview-post-btn" on:click|stopPropagation={() => showPostPreview(imageUrl)}>
                                    Preview Post
                                </button>
                            </div>
                        </div>
                    {/each}
                </div>
            </div>
            
            <div class="detail-section">
                <h2>On-Demand Generation</h2>
                <p class="section-description">First, generate a set of prompts based on the video's summary. Then, for any prompt you like, select an image model and generate a new visual.</p>
                <div class="on-demand-controls">
                     <button class="button-primary" on:click={handleGeneratePrompts} disabled={promptsLoader}>
                        {#if promptsLoader}Generating Prompts...{:else}Generate New Prompts{/if}
                    </button>
                </div>

                <ul class="new-prompts-list">
                    {#each newPrompts as prompt, index (prompt)}
                        {@const state = promptGenerationStates[index]}
                         <li class:generating={state?.isGenerating}>
                            <span class="prompt-text">{prompt}</span>
                            <div class="prompt-controls">
                                 <div class="control-group">
                                    <select bind:value={promptGenerationStates[index].selectedModel} disabled={state?.isGenerating}>
                                        {#each imagenModels as model}
                                            <option value={model}>{model.replace(/-generate-preview-\d{2}-\d{2}/, '').replace(/-generate-\d{3}/, '')}</option>
                                        {/each}
                                    </select>
                                </div>
                                <button class="button-secondary generate-image-btn" on:click={() => handleGenerateImage(prompt, index)} disabled={state?.isGenerating}>
                                    {#if state?.isGenerating}Generating...{:else}Generate Image{/if}
                                </button>
                            </div>
                        </li>
                    {/each}
                </ul>
            </div>
        </div>
        {/if}

        {#if activeTab === 'copy'}
        <div class="tab-content active">
            {#if videoData.marketing_copy}
            <div class="detail-section">
                <h2>Generated Copy</h2>
                <div class="copy-assets">
                    {#if videoData.marketing_copy.facebook_post}
                    <div class="copy-asset-card">
                        <h4>Facebook / Instagram Post</h4>
                        <div class="copy-text">{@html videoData.marketing_copy.facebook_post}</div>
                    </div>
                    {/if}
                     {#if videoData.marketing_copy.email_newsletter}
                     <div class="copy-asset-card">
                        <h4>Email Newsletter</h4>
                        {#if typeof videoData.marketing_copy.email_newsletter === 'object'}
                            <h5 class="newsletter-subject">{videoData.marketing_copy.email_newsletter.subject}</h5>
                        {/if}
                        <div class="copy-text newsletter-container">
                            {@html newsletterPreImageHtml}
                            
                            {#if selectedNewsletterImage}
                                <img src={selectedNewsletterImage} alt="Selected newsletter visual" class="newsletter-image">
                            {:else if availableImages.length > 0}
                                <div class="image-placeholder">
                                    <button class="button-secondary" on:click={() => isImageSelectorVisible = true}>
                                        Select an Image
                                    </button>
                                </div>
                            {/if}

                            {@html newsletterPostImageHtml}
                        </div>
                    </div>
                    {/if}
                </div>
            </div>
            {/if}

            {#if videoData.substack_gcs_uri}
             <div class="detail-section">
                <h2>Substack Article</h2>
                <div class="substack-preview">
                    {#if isLoadingSubstack}
                        <div class="loader-small"></div>
                    {:else if substackHtml}
                        <div class="copy-text">
                            {@html substackHtml}
                        </div>
                    {/if}
                </div>
                <a href={videoData.substack_gcs_uri.replace("gs://", "https://storage.googleapis.com/")} class="button-link" download>
                    Download Formatted Article
                </a>
             </div>
            {/if}

            {#if !videoData.marketing_copy && !videoData.substack_gcs_uri}
                <div class="detail-section">
                    <p>No generated copy is available for this video yet.</p>
                </div>
            {/if}
        </div>
        {/if}

        {#if activeTab === 'shorts'}
        <div class="tab-content active">
             <!-- Shorts content will go here -->
            <ShortsCandidates
                candidates={videoData.structured_data?.shorts_candidates || []}
                videoId={videoData.video_id}
                bind:videoData
            />
        </div>
        {/if}
    </div>
</div>
{/if}

<!-- Image Modal -->
{#if isImageModalVisible}
<div class="modal-overlay" role="dialog" aria-modal="true" on:click={() => isImageModalVisible = false}>
    <button type="button" class="modal-close-button" on:click={() => isImageModalVisible = false}>&times;</button>
    <img class="modal-content-image" src={modalImageUrl} alt="Full size generated visual">
</div>
{/if}

<!-- Image Selector Modal -->
{#if isImageSelectorVisible}
<div class="modal-overlay" role="dialog" aria-modal="true" on:click={() => isImageSelectorVisible = false}>
    <div class="modal-content" role="document" on:click|stopPropagation>
        <div class="modal-header">
            <h3>Select an Image</h3>
            <button type="button" class="modal-close-button" on:click={() => isImageSelectorVisible = false}>&times;</button>
        </div>
        <div class="modal-body">
            <div class="thumbnails-grid">
                 {#each availableImages as imageUrl}
                    <button class="thumbnail-selector" on:click={() => selectImageForNewsletter(imageUrl)}>
                        <img src={imageUrl} alt="Selectable thumbnail">
                    </button>
                 {/each}
            </div>
        </div>
    </div>
</div>
{/if}


<style>
/* Base Layout */
.detail-container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 2rem;
    font-family: 'Inter', sans-serif;
    background-color: #ffffff;
    border-radius: 0.75rem;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1);
}

.loader {
    border: 8px solid #f3f3f3;
    border-top: 8px solid #4F46E5;
    border-radius: 50%;
    width: 60px;
    height: 60px;
    animation: spin 1s linear infinite;
    margin: 4rem auto;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

/* Header */
.detail-header {
    margin-bottom: 2rem;
}
.header-meta {
    display: flex;
    align-items: center;
    gap: 1.5rem;
    margin-top: 1rem;
}
.logo-icon { height: 50px; }
.video-meta-item { color: #64748b; font-size: 0.9rem; }
.status-banner {
    padding: 0.3rem 1rem;
    border-radius: 9999px;
    font-size: 0.9rem;
    font-weight: 600;
    color: white;
    text-transform: capitalize;
}
.status-success { background-color: #16a34a; }
.status-failed { background-color: #dc2626; }
.status-in-progress { background-color: #f59e0b; }
.status-unknown { background-color: #64748b; }

.detail-header h1 {
    font-size: 2.5rem;
    font-weight: 800;
    color: #1e293b;
    line-height: 1.2;
}

/* Tabs */
.tab-nav {
    display: flex;
    border-bottom: 1px solid #e5e7eb;
    margin-bottom: 2rem;
}
.tab-link {
    padding: 0.75rem 1.5rem;
    cursor: pointer;
    border: none;
    background: none;
    font-size: 1rem;
    font-weight: 600;
    color: #6b7280;
    border-bottom: 3px solid transparent;
    transition: color 0.2s, border-color 0.2s;
}
.tab-link:hover {
    color: #374151;
}
.tab-link.active {
    color: #4F46E5;
    border-bottom-color: #4F46E5;
}

/* Content Sections */
.tab-content.active {
    display: block;
}
.detail-section {
    margin-bottom: 3rem;
}
.detail-section h2 {
    font-size: 1.75rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
    color: #374151;
}
.section-description {
    font-size: 1rem;
    color: #64748b;
    max-width: 700px;
    margin-bottom: 1.5rem;
}

/* Overview Tab */
.overview-grid {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 2rem;
    align-items: flex-start;
}
.video-player-wrapper {
    position: relative;
    padding-top: 56.25%; /* 16:9 Aspect Ratio */
    background-color: #000;
    border-radius: 0.5rem;
    overflow: hidden;
}
.youtube-iframe {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
}

/* Assets Tab */
.thumbnails-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 1rem;
    max-width: 900px; /* Constrains the grid from stretching too far */
}
.thumbnail-item {
    background-color: #fff;
    border-radius: 0.5rem;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    display: flex;
    flex-direction: column;
}
.thumbnail-image-wrapper {
    cursor: pointer;
    aspect-ratio: 1 / 1; /* Modern CSS for 1:1 Aspect Ratio */
    background-color: #f0f2f5;
    overflow: hidden;
    border: none;
    padding: 0;
}
.thumbnail-image-wrapper img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
    transition: transform 0.2s ease-in-out;
}
.thumbnail-image-wrapper:hover img {
    transform: scale(1.05);
}
.thumbnail-footer {
    padding: 0.75rem;
    background-color: #f8fafc;
    border-top: 1px solid #e2e8f0;
    display: flex;
    justify-content: center;
}

.preview-post-btn {
    width: 100%;
}

.thumbnail-prompt {
    padding: 1rem;
    flex-grow: 1; /* Allows the bottom part to fill space if needed */
}
.thumbnail-prompt h4 {
    margin: 0 0 0.5rem 0;
    font-size: 0.9rem;
    color: #374151;
}
.thumbnail-prompt p {
    margin: 0 0 1rem 0;
    font-size: 0.9rem;
    color: #64748b;
    line-height: 1.5;
}

.copy-assets {
    display: grid;
    gap: 1.5rem;
}

.copy-asset-card {
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 0.5rem;
    padding: 1.5rem;
}
.copy-asset-card h4 {
    margin: 0 0 1rem 0;
    font-size: 1.1rem;
}
.newsletter-subject {
    font-weight: 600;
    font-size: 1.05rem;
    margin-bottom: 0.75rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid #e2e8f0;
}
.copy-text {
    background: white;
    padding: 1rem;
    border-radius: 0.25rem;
    border: 1px solid #e2e8f0;
    line-height: 1.6;
    color: #374151;
}

.copy-text.newsletter-container {
    overflow: auto; /* Simple clearfix to contain the floated element */
}

.newsletter-image {
    float: right;
    width: 250px;
    max-width: 40%;
    border-radius: 8px;
    margin-left: 1.5rem;
    margin-bottom: 1rem;
}

.image-placeholder {
    float: right;
    width: 250px;
    max-width: 40%;
    min-height: 220px;
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 2rem;
    margin-left: 1.5rem;
    margin-bottom: 1rem;
    border: 2px dashed #e2e8f0;
    border-radius: 8px;
    background-color: #f8fafc;
}

/* Modal */
.modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.7);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
}
.modal-close-button {
    position: absolute;
    top: 20px;
    right: 30px;
    font-size: 2.5rem;
    color: white;
    cursor: pointer;
    background: none;
    border: none;
    line-height: 1;
}
.modal-content-image {
    max-width: 90vw;
    max-height: 90vh;
    object-fit: contain;
}

.modal-content {
    background: white;
    padding: 1.5rem;
    border-radius: 0.5rem;
    max-width: 800px;
    width: 90%;
    max-height: 80vh;
    display: flex;
    flex-direction: column;
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #e5e7eb;
    padding-bottom: 1rem;
    margin-bottom: 1rem;
}

.modal-header h3 {
    margin: 0;
    font-size: 1.5rem;
}

.modal-body {
    overflow-y: auto;
}

.thumbnail-selector {
    border: 2px solid transparent;
    border-radius: 0.5rem;
    padding: 0;
    cursor: pointer;
    overflow: hidden;
    transition: border-color 0.2s;
}
.thumbnail-selector:hover {
    border-color: #4F46E5;
}
.thumbnail-selector img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
}

/* Buttons */
.button-secondary {
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
.button-secondary:hover {
    background-color: #f3f4f6;
    border-color: #9ca3af;
}

/* Social Preview */
:global(.social-preview-popup) {
    max-width: 700px;
    min-width: 600px;
   
    min-height: 300px;
}
.social-preview-caption {
    text-align: left;
    margin-top: 1rem;
    padding: 1rem;
    background-color: #f8fafc;
    border-radius: 0.5rem;
    max-height: 200px;
    overflow-y: auto;
    font-size: 0.95rem;
    line-height: 1.5;
}

.on-demand-controls {
    display: flex;
    align-items: center;
    gap: 1.5rem;
    margin-bottom: 1.5rem;
}
.control-group {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
select {
    padding: 0.5rem;
    border-radius: 0.375rem;
    border: 1px solid #d1d5db;
    background-color: white;
    font-family: inherit;
    font-size: 0.9rem;
}

.new-prompts-list {
    list-style: none;
    padding: 0;
    margin-top: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.new-prompts-list li {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem;
    background-color: #f8fafc;
    border-radius: 0.5rem;
    border: 1px solid #e2e8f0;
    gap: 1rem;
}

.new-prompts-list li.generating {
    opacity: 0.5;
    pointer-events: none;
}

.prompt-text {
    flex-grow: 1;
    margin-right: 1rem;
    color: #374151;
    line-height: 1.5;
}

.prompt-controls {
    display: flex;
    align-items: center;
    gap: 1rem;
    flex-shrink: 0;
}

.prompt-input {
    flex-grow: 1;
    margin-right: 1rem;
    padding: 0.5rem;
    border: 1px solid #d1d5db;
    border-radius: 0.375rem;
    font-size: 0.9rem;
}

.prompt-editing-controls {
    margin-bottom: 1rem;
    display: flex;
    justify-content: flex-end;
}

/* --- Responsive Design --- */
@media (max-width: 768px) {
    .detail-container {
        padding: 1rem;
    }

    .header-meta {
        flex-direction: column;
        align-items: flex-start;
        gap: 0.75rem;
    }

    .detail-header h1 {
        font-size: 2rem;
    }

    .overview-grid {
        grid-template-columns: 1fr;
    }

    .thumbnails-grid {
        grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    }
    
    .new-prompts-list li {
        flex-direction: column;
        align-items: stretch;
        gap: 1rem;
    }

    .prompt-controls {
        justify-content: space-between;
    }
}

.substack-preview {
    margin-bottom: 1rem;
}

.loader-small {
    border: 4px solid #f3f3f3;
    border-top: 4px solid #4F46E5;
    border-radius: 50%;
    width: 30px;
    height: 30px;
    animation: spin 1s linear infinite;
    margin: 2rem auto;
}
</style>

