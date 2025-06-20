<script lang="ts">
  import Swal from 'sweetalert2';

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

<div class="maintenance-page">
    <div class="maintenance-content">
        <h1>Maintenance</h1>
        <p>Use these tools for site-wide administrative tasks.</p>

        <div class="task-card">
            <h3>Clean Up Video Cache</h3>
            <p class="description">
                Immediately deletes all temporarily cached video files from the server's storage. This is useful for freeing up disk space but will require videos to be re-downloaded if transcription is re-triggered.
            </p>
            <button class="button-danger" on:click={handleCleanup}>Clean Up Video Cache</button>
        </div>
    </div>
</div>

<style>
    .maintenance-page {
        max-width: 900px;
        margin: 0 auto;
        font-family: 'Inter', sans-serif;
    }

    .maintenance-content {
        background-color: #ffffff;
        border-radius: 0.75rem;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1);
        padding: 2rem;
    }

    h1 {
        font-size: 2.5rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
        color: #1e293b;
    }

    p {
        font-size: 1.1rem;
        color: #64748b;
        margin-bottom: 3rem;
    }

    .task-card {
        background-color: #ffffff;
        border-radius: 0.75rem;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1);
        padding: 2rem;
    }

    .task-card h3 {
        font-size: 1.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        color: #374151;
    }

    .task-card .description {
        font-size: 1rem;
        line-height: 1.6;
        color: #4b5563;
        margin-bottom: 1.5rem;
    }

    .button-danger {
        background-color: #fee2e2;
        border: 1px solid #fecaca;
        color: #b91c1c;
        padding: 0.6rem 1.2rem;
        font-size: 0.9rem;
        font-weight: 600;
        border-radius: 0.375rem;
        cursor: pointer;
        transition: background-color 0.2s;
    }
    .button-danger:hover {
        background-color: #fecaca;
    }
</style> 