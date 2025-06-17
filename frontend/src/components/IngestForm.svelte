<script lang="ts">
  import { idToken } from '../lib/auth';
  import { checkVideo, sendIngest } from '../lib/api';
  import Swal from 'sweetalert2';
  import { createEventDispatcher } from 'svelte';

  let youtubeUrl = '';
  let busy = false;
  const dispatch = createEventDispatcher();

  async function submit() {
    if (!youtubeUrl.trim()) return Swal.fire('Enter URL');
    const token = $idToken;
    if (!token) return Swal.fire('Log in first');
    busy = true;

    const { exists, video_id } = await checkVideo(youtubeUrl, token);
    if (exists) {
      const result = await Swal.fire({
        title: 'Exists—Reprocess?',
        showDenyButton: true,
        confirmButtonText: 'Reprocess',
        denyButtonText: 'View Existing'
      });
      if (result.isDenied) {
        return dispatch('view', { videoId: video_id });
      }
    }

    const id = await sendIngest(youtubeUrl, true, token);
    dispatch('started', { videoId: id });
  }
</script>

<form on:submit|preventDefault={submit}>
  <input type="url" bind:value={youtubeUrl} placeholder="YouTube URL" />
  <button disabled={busy}>{busy ? '…' : 'Amplify'}</button>
</form>
