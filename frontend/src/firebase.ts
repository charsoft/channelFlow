import { initializeApp, getApp, getApps, type FirebaseOptions } from "firebase/app";
import { getAuth } from "firebase/auth";

let firebaseConfig: FirebaseOptions;

// This code runs when the module is first loaded in the browser.
// Vite supports top-level 'await', allowing us to fetch config asynchronously.
try {
    const response = await fetch('/api/config'); 
    
    if (!response.ok) {
        // Construct a more informative error message
        const errorText = await response.text();
        throw new Error(`Failed to fetch Firebase config: ${response.status} ${response.statusText}. Server response: ${errorText}`);
    }
    
    const config = await response.json();

    // Check for missing keys from the backend
    if (!config.firebase_api_key || !config.firebase_auth_domain || !config.firebase_project_id) {
        throw new Error("Fetched configuration is missing required Firebase keys.");
    }

    firebaseConfig = {
        apiKey: config.firebase_api_key,
        authDomain: config.firebase_auth_domain,
        projectId: config.firebase_project_id,
    };

} catch (error) {
    console.error("CRITICAL: Could not initialize Firebase.", error);
    // Display a user-friendly message on the page itself
    document.body.innerHTML = `
        <div style="font-family: sans-serif; padding: 2rem; text-align: center; background: #fff3f3; color: #b71c1c; border: 1px solid #ffcdd2;">
            <h1>Application Error</h1>
            <p>Could not connect to the backend to get configuration.</p>
            <p>Please ensure the backend server is running and accessible.</p>
            <hr style="border: none; border-top: 1px solid #ffcdd2; margin: 1rem 0;" />
            <p style="font-size: 0.9rem; color: #444;"><strong>Details:</strong> ${error instanceof Error ? error.message : String(error)}</p>
        </div>
    `;
    // Throw an error to halt further script execution
    throw new Error("Firebase initialization failed.");
}

// Initialize Firebase, preventing re-initialization on hot reloads
const app = !getApps().length ? initializeApp(firebaseConfig) : getApp();

// Export the auth service to be used in other parts of the app
export const auth = getAuth(app); 