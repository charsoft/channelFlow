//Here’s a little helper module that’ll make your frontend gracefully switch between local and Cloud Run environments depending on how you’re running it.
// src/lib/config.ts

const local = 'http://localhost:8080';
const cloudRun = import.meta.env.VITE_API_BASE_URL;

export const API_BASE_URL =
    import.meta.env.MODE === 'development' ? local : cloudRun || '';

//If you want to fail loudly when VITE_API_BASE_URL is missing in prod:
if (import.meta.env.MODE !== 'development' && !cloudRun) {
    throw new Error('VITE_API_BASE_URL must be defined in production!');
}

//During vite dev, it talks to localhost:8080

//In production, it uses whatever VITE_API_BASE_URL you put in .env.production