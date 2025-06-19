/// <reference types="svelte" />
/// <reference types="vite/client" />
/// <reference types="vite/client" />

interface ImportMetaEnv {
    readonly VITE_FB_API_KEY: string;
    readonly VITE_FB_AUTH_DOMAIN: string;
    readonly VITE_FB_PROJECT_ID: string;
    // add any other VITE_… vars you use here
}

interface ImportMeta {
    readonly env: ImportMetaEnv;
}

declare module '*.png' {
  const value: string;
  export default value;
}
