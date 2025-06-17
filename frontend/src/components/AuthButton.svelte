<script lang="ts">
  import { currentUser, signInWithGoogle, signOut } from '../lib/auth';
  import { get } from 'svelte/store';

  function handleClick() {
    const user = get(currentUser);
    user ? signOut() : signInWithGoogle();
  }
</script>

<button on:click={handleClick}>
  {#if $currentUser}Sign Out{:else}Sign In with Google{/if}
</button>
