import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
import { getFirestore } from "firebase/firestore";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyBwjclJSSuRepvcQQelH59-r6Omr7cYumI",
  authDomain: "aura-ai-31887.firebaseapp.com",
  projectId: "aura-ai-31887",
  storageBucket: "aura-ai-31887.appspot.com",
  messagingSenderId: "618323573679",
  appId: "1:618323573679:web:f1d8e2a9397688f90d0d5a",
  measurementId: "G-TZ9DT3KSDY",
};
const app = initializeApp(firebaseConfig);
export const db = getFirestore(app);
const auth = getAuth(app);
const analytics = getAnalytics(app);
export { app, analytics, auth };