<!-- src/routes/Dashboard.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import Swal from 'sweetalert2';

  interface Video {
    video_id: string;
    video_title: string;
    video_url: string;
    status: string;
    received_at?: string;
    substack_hook?: string;
    structured_data?: {
      summary?: string;
    };
    generated_thumbnails?: { image_url: string }[];
  }

  let videos: Video[] = [];
  let isLoading = true;
  let errorMessage = '';

  onMount(async () => {
    try {
      const response = await fetch('/api/videos');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      videos = data.videos || [];
    } catch (error: any) {
      errorMessage = 'Could not load video data. Please try again later.';
      console.error('Failed to load videos:', error);
    } finally {
      isLoading = false;
    }
  });

  function getHook(video: Video): string {
    if (video.substack_hook) {
      return video.substack_hook;
    }
    if (video.structured_data?.summary) {
      return video.structured_data.summary.substring(0, 100) + '...';
    }
    return 'No hook or summary available.';
  }

  function getStatusClass(status: string): string {
    if (status.includes('failed')) return 'status-failed';
    if (status === 'published' || status === 'completed') return 'status-success'; // Added 'completed'
    if (status) return 'status-in-progress';
    return 'status-unknown';
  }

  function handleCardClick(videoId: string) {
    push(`/video/${videoId}`);
  }

  function confirmAndReprocess(event: MouseEvent, videoId: string, videoUrl: string) {
    event.stopPropagation();
    Swal.fire({
      title: 'Are you sure?',
      text: "This will delete all existing data and re-process the video from scratch. This cannot be undone.",
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Yes, reprocess it!',
      confirmButtonColor: '#DC2626',
      cancelButtonColor: '#64748B'
    }).then((result) => {
      if (result.isConfirmed) {
        localStorage.setItem('reprocessUrl', videoUrl);
        push('/');
      }
    });
  }
  
  async function handleCleanup() {
      const result = await Swal.fire({
          title: 'Are you sure?',
          text: "This will permanently delete all cached video files from the server.",
          icon: 'warning',
          showCancelButton: true,
          confirmButtonColor: '#d33',
          cancelButtonColor: '#3085d6',
          confirmButtonText: 'Yes, clean it up!'
      });

      if (result.isConfirmed) {
          Swal.fire({
              title: 'Cleaning...',
              text: 'Please wait while the server cleans up the files.',
              allowOutsideClick: false,
              didOpen: () => {
                  Swal.showLoading();
              }
          });

          try {
              const response = await fetch('/api/cleanup-cache', {
                  method: 'POST',
              });
              const data = await response.json();

              if (response.ok) {
                  Swal.fire('Cleaned!', data.message, 'success');
              } else {
                  throw new Error(data.message || 'Failed to clean up cache.');
              }
          } catch (error: any) {
              console.error('Cleanup error:', error);
              Swal.fire('Error!', `An error occurred: ${error.message}`, 'error');
          }
      }
  }
</script>

<div class="management-container">
    <header class="management-header">
        <div class="header-left">
            <a href="/" class="logo-link">
                <img src="/channel-flow-logo.png" alt="ChannelFlow Logo" class="logo-icon">
            </a>
        </div>
        <nav class="nav-links">
            <a href="/" class="button-link">Process New Video</a>
        </nav>
    </header>
    
    <div class="content-body">
        <h1>Content Dashboard</h1>
        <p>Review and manage all processed video content.</p>
        
        {#if isLoading}
            <p>Loading videos...</p>
        {:else if errorMessage}
            <p class="error-message">{errorMessage}</p>
        {:else if videos.length === 0}
            <p>No processed videos found.</p>
        {:else}
            <div id="videos-grid" class="videos-grid">
                {#each videos as video (video.video_id)}
                    <div class="video-card" on:click={() => handleCardClick(video.video_id)}>
                        <div class="card-thumbnail">
                            <img src={`https://img.youtube.com/vi/${video.video_id}/hqdefault.jpg`} alt="Video thumbnail">
                            <span class="card-status {getStatusClass(video.status)}">
                                {video.status.replace(/_/g, ' ')}
                            </span>
                        </div>
                        <div class="card-content">
                            <h3 class="card-title">{video.video_title || 'Untitled Video'}</h3>
                            <p class="card-hook">{getHook(video)}</p>
                        </div>
                        <div class="card-footer">
                            <div class="footer-images">
                                {#if video.generated_thumbnails && video.generated_thumbnails.length > 0}
                                    {#each video.generated_thumbnails.slice(0, 4) as thumb}
                                        <img src={thumb.image_url} alt="Generated thumbnail" class="footer-thumbnail">
                                    {/each}
                                {:else}
                                    <span class="no-images">No images generated</span>
                                {/if}
                            </div>
                            <div class="footer-meta">
                                <span class="processed-date">
                                    Processed: {video.received_at ? new Date(video.received_at).toLocaleDateString() : 'Not available'}
                                </span>
                                <button class="reprocess-button" on:click={(e) => confirmAndReprocess(e, video.video_id, video.video_url)}>
                                    Reprocess
                                </button>
                            </div>
                        </div>
                    </div>
                {/each}
            </div>
        {/if}
    </div>

    <div class="maintenance-section">
        <h2>Site Maintenance</h2>
        <div class="maintenance-controls">
            <button class="button-danger" on:click={handleCleanup}>Clean Up Video Cache</button>
            <p class="description">
                Immediately deletes all temporarily cached video files from the server.
            </p>
        </div>
    </div>
</div>

<style>
    :global(body) {
        background-color: #f8fafc; /* A light gray background */
    }

    .management-container {
        width: 100%; /* Use full available width */
        max-width: 1400px; /* Add a max-width for very large screens */
        margin: 0 auto;
        padding: 2rem;
        font-family: 'Inter', sans-serif;
    }

    .management-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 2rem;
    }

    .logo-link {
        display: flex;
        align-items: center;
        text-decoration: none;
    }

    .logo-icon {
        height: 50px;
    }

    .button-link {
        background-color: #4F46E5; /* Your app's primary purple */
        color: white;
        padding: 0.75rem 1.5rem;
        border-radius: 0.5rem;
        text-decoration: none;
        font-weight: 600;
        transition: background-color 0.3s;
    }

    .button-link:hover {
        background-color: #4338CA;
    }

    .content-body h1 {
        font-size: 2.5rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
        color: #1e293b;
    }

    .content-body p {
        font-size: 1.1rem;
        color: #64748b;
        margin-bottom: 2rem;
    }

    .videos-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 1.5rem;
    }

    .video-card {
        background-color: white;
        border-radius: 0.75rem;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1);
        overflow: hidden;
        cursor: pointer;
        transition: transform 0.2s, box-shadow 0.2s;
        display: flex;
        flex-direction: column;
    }

    .video-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -4px rgba(0,0,0,0.1);
    }
    
    .card-thumbnail {
        position: relative;
    }

    .card-thumbnail img {
        width: 100%;
        height: auto;
        display: block;
    }

    .card-status {
        position: absolute;
        top: 0.75rem;
        right: 0.75rem;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        color: white;
        text-transform: capitalize;
    }

    .status-success { background-color: #16a34a; }
    .status-failed { background-color: #dc2626; }
    .status-in-progress { background-color: #f59e0b; }
    .status-unknown { background-color: #64748b; }

    .card-content {
        padding: 1rem;
        flex-grow: 1;
    }

    .card-title {
        font-size: 1.1rem;
        font-weight: 600;
        margin: 0 0 0.5rem 0;
        color: #1e293b;
    }

    .card-hook {
        font-size: 0.9rem;
        color: #475569;
        line-height: 1.5;
    }
    
    .card-footer {
        padding: 0 1rem 1rem 1rem;
        border-top: 1px solid #e5e7eb;
    }

    .footer-images {
        display: flex;
        gap: 0.5rem;
        margin-top: 1rem;
        min-height: 40px; /* Reserve space */
    }

    .footer-thumbnail {
        width: 40px;
        height: 40px;
        border-radius: 0.25rem;
        object-fit: cover;
    }

    .no-images {
        font-size: 0.8rem;
        color: #94a3b8;
        align-self: center;
    }
    
    .footer-meta {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 1rem;
    }
    
    .processed-date {
        font-size: 0.8rem;
        color: #64748b;
    }

    .reprocess-button {
        background: none;
        border: 1px solid #d1d5db;
        color: #475569;
        padding: 0.25rem 0.75rem;
        font-size: 0.8rem;
        border-radius: 0.375rem;
        cursor: pointer;
        transition: background-color 0.2s, color 0.2s;
    }
    
    .reprocess-button:hover {
        background-color: #f3f4f6;
        border-color: #9ca3af;
    }
    
    .maintenance-section {
        margin-top: 4rem;
        padding-top: 2rem;
        border-top: 1px solid #e2e8f0;
    }

    .maintenance-section h2 {
        font-size: 1.5rem;
        margin-bottom: 1rem;
    }

    .button-danger {
        background-color: #DC2626;
        color: white;
        padding: 0.5rem 1rem;
        border: none;
        border-radius: 0.5rem;
        font-weight: 600;
        cursor: pointer;
        transition: background-color 0.3s;
    }
    
    .button-danger:hover {
        background-color: #B91C1C;
    }

    .description {
        font-size: 0.9rem;
        color: #64748b;
        margin-top: 0.5rem;
    }
</style> 