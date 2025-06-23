import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import path from 'path'



// https://vitejs.dev/config/
export default defineConfig({
  plugins: [svelte()],
  envDir: path.resolve(__dirname, '..'),
  server: {
    port: 5173, // 👈 add this
    proxy: {
      // string shorthand
      // '/foo': 'http://localhost:4567/foo',
      // with options
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        secure: false, // 👈 add this
      }
    }
  }
})
