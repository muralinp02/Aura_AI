// src/firebase.ts

import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";
import { getFirestore } from "firebase/firestore";
import type { Analytics } from "firebase/analytics";
import { getAnalytics, isSupported } from "firebase/analytics";

// ---- Read env (Vite requires VITE_ prefix)
const cfg = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY?.trim(),
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN?.trim(),
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID?.trim(),
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET?.trim(),
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID?.trim(),
  appId: import.meta.env.VITE_FIREBASE_APP_ID?.trim(),
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID?.trim(),
};

// ---- Sanity checks with helpful messages
const missing = Object.entries(cfg)
  .filter(([, v]) => !v)
  .map(([k]) => k);

if (missing.length) {
  console.error(
    `[Firebase] Missing env(s): ${missing.join(
      ", "
    )}. Did you put them in the frontend project's .env and restart "npm run dev"?`
  );
}

if (cfg.apiKey) {
  console.log("[Firebase] apiKey loaded =", cfg.apiKey.slice(0, 8) + "…");
}

// ---- Initialize Firebase
const app = initializeApp(cfg);

// Firestore & Auth are safe everywhere
export const db = getFirestore(app);
export const auth = getAuth(app);

// ---- Analytics (safe check so it won’t crash in dev/SSR)
let analytics: Analytics | null = null;

(async () => {
  try {
    if (
      typeof window !== "undefined" &&
      cfg.measurementId &&
      (await isSupported())
    ) {
      analytics = getAnalytics(app);
      console.log("[Firebase] Analytics initialized");
    } else {
      console.log("[Firebase] Analytics skipped (unsupported or missing ID)");
    }
  } catch (e) {
    console.warn("[Firebase] Analytics init failed (ignored):", e);
  }
})();

export { app, analytics };