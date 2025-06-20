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
    thumbnails?: string[];
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
                    <a href={`#/video/${video.video_id}`} class="video-card">
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
                            <div class="footer-thumbnails">
                                {#if video.thumbnails && video.thumbnails.length > 0}
                                    {#each video.thumbnails as thumbUrl}
                                        <div class="footer-thumbnail" style="background-image: url({thumbUrl})"></div>
                                    {/each}
                                {:else}
                                    <div class="footer-thumbnail-placeholder"></div>
                                    <div class="footer-thumbnail-placeholder"></div>
                                    <div class="footer-thumbnail-placeholder"></div>
                                    <div class="footer-thumbnail-placeholder"></div>
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
                    </a>
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
        margin: 0;
        padding: 2rem;
        font-family: 'Inter', sans-serif;
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
        text-decoration: none; /* Reset link styles for the card */
        color: inherit; /* Make card text use the default color */
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
        margin: 0;
        color: #1e293b;
    }

    .card-hook {
        font-size: 0.9rem;
        color: #64748b;
        margin-top: 0.5rem;
        line-height: 1.5;
    }
    
    .card-footer {
        padding: 0.75rem;
        background-color: #f8fafc;
        border-top: 1px solid #e2e8f0;
    }

    .footer-thumbnails {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 0.75rem;
    }

    .footer-thumbnail {
        width: 25%;
        padding-top: 25%;
        background-size: cover;
        background-position: center;
        border-radius: 0.375rem;
    }

    .footer-thumbnail-placeholder {
        width: 25%;
        padding-top: 25%;
        background-color: #e2e8f0;
        border-radius: 0.375rem;
    }

    .footer-meta {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.8rem;
        color: #64748b;
    }

    .processed-date {
        /* styles for date */
    }

    .reprocess-button {
        background: none;
        border: 1px solid #d1d5db;
        color: #475569;
        padding: 0.25rem 0.5rem;
        font-size: 0.75rem;
        border-radius: 0.375rem;
        cursor: pointer;
        transition: background-color 0.2s;
    }
    .reprocess-button:hover {
        background-color: #f3f4f6;
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