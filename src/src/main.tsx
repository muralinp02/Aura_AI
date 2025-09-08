import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import './index.css'

createRoot(document.getElementById("root")!).render(<App />);
import { initAnalytics } from "@/firebase/client";

initAnalytics(); // fire and forget