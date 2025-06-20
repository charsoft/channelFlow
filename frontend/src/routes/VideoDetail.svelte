<script lang="ts">
  import { onMount } from 'svelte';
  import Swal from 'sweetalert2';

  import { listenForUpdates } from '../lib/api';

  export let params: { id?: string } = {};

  // --- State ---
  let videoData: any = null;
  let isLoading = true;
  let errorMessage = '';
  let activeTab = 'overview';
  let isImageModalVisible = false;
  let modalImageUrl = '';

  // --- Lifecycle ---
  onMount(() => {
    loadVideoDetails();
  });

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
      const response = await fetch(`/api/video/${params.id}`);
      if (!response.ok) {
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

  // --- Helpers ---
  function getStatusClass(status: string): string {
    if (!status) return 'status-unknown';
    if (status.includes('failed')) return 'status-failed';
    if (status === 'published' || status.includes('completed') || status.includes('generated')) return 'status-success';
    if (status) return 'status-in-progress';
    return 'status-unknown';
  }

  function sanitizeTitleForFilename(title: string): string {
    if (!title) return 'video_clip';
    const sanitized = title.replace(/[*:"<>?|/\\.]/g, '').replace(/\s+/g, '_').toLowerCase();
    return (sanitized.substring(0, 80) || 'video_clip');
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
</script>

{#if isLoading}
  <div class="loader"></div>
{:else if errorMessage}
  <p class="error-message">{errorMessage}</p>
{:else if videoData}
<div class="detail-container">
    <header class="detail-header">
        <div class="header-top-row">
            <div class="header-left">
                <a href="/" class="logo-link">
                    <img src="/channel-flow-logo.png" alt="ChannelFlow Logo" class="logo-icon">
                </a>
            </div>
            <div class="header-top-right">
                <span class="video-meta-item">
                    Processed: {videoData.received_at ? new Date(videoData.received_at).toLocaleDateString() : 'N/A'}
                </span>
                <div class="status-banner {getStatusClass(videoData.status)}">
                    Status: {videoData.status.replace(/_/g, ' ')}
                </div>
                <nav class="nav-links">
                    <a href="#/dashboard" class="nav-link button-secondary">← Back to Dashboard</a>
                </nav>
            </div>
        </div>
        <h1>{videoData.video_title || 'Untitled Video'}</h1>
    </header>

    <div class="video-detail-content">
        <!-- Tab Navigation -->
        <div class="tab-nav">
            <button class="tab-link" class:active={activeTab === 'overview'} on:click={() => activeTab = 'overview'}>Overview</button>
            <button class="tab-link" class:active={activeTab === 'assets'} on:click={() => activeTab = 'assets'}>Generated Assets</button>
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
        
        {#if activeTab === 'assets'}
        <div class="tab-content active">
             <div class="detail-section">
                <h2>Generated Thumbnails</h2>
                <p class="section-description">Thumbnails generated by the agent. Click an image to view it in full size or preview the post.</p>
                <div class="thumbnails-grid">
                    {#each videoData.generated_thumbnails || [] as thumb}
                        <div class="thumbnail-item">
                            <div class="thumbnail-image-wrapper" on:click={() => showImageModal(thumb.image_url)}>
                                <img src={thumb.image_url} alt="Generated visual">
                            </div>
                            <div class="thumbnail-prompt">
                                <h4>Prompt:</h4>
                                <p>{thumb.prompt}</p>
                                <button class="button-secondary preview-post-btn" on:click={() => showPostPreview(thumb.image_url)}>Preview Post</button>
                            </div>
                        </div>
                    {/each}
                </div>
            </div>
            
            {#if videoData.marketing_copy}
            <div class="detail-section">
                <h2>Generated Copy</h2>
                <div class="copy-assets">
                    {#if videoData.marketing_copy.facebook_post}
                    <div class="copy-asset-card">
                        <h4>Facebook / Instagram Post</h4>
                        <div contenteditable="true" class="copy-text">{@html videoData.marketing_copy.facebook_post}</div>
                    </div>
                    {/if}
                     {#if videoData.marketing_copy.email_newsletter}
                     <div class="copy-asset-card">
                        <h4>Email Newsletter</h4>
                        {#if typeof videoData.marketing_copy.email_newsletter === 'object'}
                            <h5 class="newsletter-subject">{videoData.marketing_copy.email_newsletter.subject}</h5>
                            <div contenteditable="true" class="copy-text">{@html videoData.marketing_copy.email_newsletter.body}</div>
                        {:else}
                             <div contenteditable="true" class="copy-text">{@html videoData.marketing_copy.email_newsletter}</div>
                        {/if}
                    </div>
                    {/if}
                </div>
            </div>
            {/if}

            {#if videoData.substack_gcs_uri}
             <div class="detail-section">
                 <h2>Substack Article</h2>
                <a href={videoData.substack_gcs_uri.replace("gs://", "https://storage.googleapis.com/")} class="button-link" download>
                    Download Formatted Article
                </a>
             </div>
            {/if}
        </div>
        {/if}

        {#if activeTab === 'shorts'}
        <div class="tab-content active">
             <!-- Shorts content will go here -->
             <p>Shorts candidates are under construction.</p>
        </div>
        {/if}
    </div>
</div>
{/if}

<!-- Image Modal -->
{#if isImageModalVisible}
<div class="modal-overlay" on:click={() => isImageModalVisible = false}>
    <span class="modal-close-button" on:click={() => isImageModalVisible = false}>&times;</span>
    <img class="modal-content-image" src={modalImageUrl} alt="Full size generated visual" on:click|stopPropagation>
</div>
{/if}


<style>
/* Base Layout */
.detail-container {
    width: 100%;
    max-width: 1400px;
    margin: 0 auto;
    padding: 2rem;
    font-family: 'Inter', sans-serif;
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
.header-top-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
}
.header-left, .header-top-right {
    display: flex;
    align-items: center;
    gap: 1.5rem;
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
    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
    gap: 1.5rem;
}
.thumbnail-item {
    background-color: #fff;
    border-radius: 0.5rem;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
.thumbnail-image-wrapper {
    cursor: pointer;
}
.thumbnail-image-wrapper img {
    width: 100%;
    display: block;
}
.thumbnail-prompt {
    padding: 1rem;
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
}
.modal-content-image {
    max-width: 90vw;
    max-height: 90vh;
    object-fit: contain;
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
    max-width: 500px;
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
</style>

