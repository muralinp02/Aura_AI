// src/contexts/ScanContext.tsx
import React, { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import { getAuth } from "firebase/auth";
import { db } from "@/firebase";
import { collection, addDoc, serverTimestamp } from "firebase/firestore";

type ScanMode = "Quick" | "Full" | "Custom";

interface ScanOptions {
  url?: string;
  scanType?: ScanMode;
  username?: string;
  password?: string;
}

interface ScanContextType {
  scanResult: any;
  setScanResult: (r: any) => void;
  scanOptions: ScanOptions;
  setScanOptions: (o: ScanOptions) => void;
  triggerScan: (options: ScanOptions) => Promise<void>;
  loading: boolean;
  error: string | null;
  lastUpdated: number;
  refreshAllPages: () => void;
}

const ScanContext = createContext<ScanContextType | undefined>(undefined);

// Persist latest result across route changes
let globalScanResult: any = null;

// API base (keep 8000 since your uvicorn runs there)
const API_BASE = import.meta.env.VITE_API_BASE?.trim() || "http://127.0.0.1:8000";

export function ScanProvider({ children }: { children: React.ReactNode }) {
  const [scanResult, setScanResult] = useState<any>(globalScanResult);
  const [scanOptions, setScanOptions] = useState<ScanOptions>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<number>(Date.now());
  const activeScanRef = useRef<AbortController | null>(null);

  // keep global cache in sync
  useEffect(() => {
    if (scanResult) {
      globalScanResult = scanResult;
      setLastUpdated(Date.now());
    }
  }, [scanResult]);

  // restore from global on mount
  useEffect(() => {
    if (globalScanResult && !scanResult) {
      setScanResult(globalScanResult);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const refreshAllPages = () => setLastUpdated(Date.now());

  const triggerScan = useMemo(
    () => async (options: ScanOptions) => {
      // cancel any in-flight scan
      if (activeScanRef.current) {
        try {
          activeScanRef.current.abort();
        } catch {
          /* noop */
        }
      }

      setScanResult(null);
      globalScanResult = null;
      setLoading(true);
      setError(null);
      setScanOptions(options);

      const controller = new AbortController();
      activeScanRef.current = controller;

      try {
        // Build FormData to match FastAPI's Form(...) params
        const form = new FormData();
        if (options.url) form.append("url", options.url);
        form.append("scan_type", options.scanType || "Full"); // <-- never None
        if (options.username) form.append("username", options.username);
        if (options.password) form.append("password", options.password);

        const res = await fetch(`${API_BASE}/fullscan`, {
          method: "POST",
          body: form,               // IMPORTANT: do not set Content-Type manually
          signal: controller.signal,
        });

        const raw = await res.text();
        if (!res.ok) {
          throw new Error(`HTTP ${res.status} ${res.statusText}${raw ? " - " + raw.slice(0, 500) : ""}`);
        }

        let data: any = {};
        try {
          data = raw ? JSON.parse(raw) : {};
        } catch {
          // non-JSON fallback (shouldn't happen, but safe)
          data = {};
        }

        // Normalize so UI never breaks if backend omits fields
        const normalized = {
          url: options.url || data?.url || "",
          threat_level: data?.threat_level ?? 0,
          vulnerabilities: Array.isArray(data?.vulnerabilities) ? data.vulnerabilities : [],
          network: data?.network ?? { nodes: [], edges: [] },
          attack_paths: Array.isArray(data?.attack_paths) ? data.attack_paths : [],
          alerts: Array.isArray(data?.alerts) ? data.alerts : [],
          attackProbabilities: Array.isArray(data?.attackProbabilities) ? data.attackProbabilities : [],
          totalScans: data?.totalScans ?? 0,
          totalVulnerabilities: data?.totalVulnerabilities ?? (data?.vulnerabilities?.length ?? 0),
          resolvedVulnerabilities: data?.resolvedVulnerabilities ?? 0,
          unresolvedVulnerabilities: data?.unresolvedVulnerabilities ?? Math.max(0, (data?.vulnerabilities?.length || 0) - (data?.resolvedVulnerabilities || 0)),
          attackSources: data?.attackSources ?? 0,
          charts: data?.charts ?? {},
        };

        console.log("fullscan result ->", normalized);

        setScanResult(normalized);
        globalScanResult = normalized;
        setLastUpdated(Date.now());

        // Best-effort Firestore write (non-blocking)
        try {
          const user = getAuth().currentUser;
          if (user) {
            await addDoc(collection(db, "users", user.uid, "scans"), {
              ...normalized,
              createdAt: serverTimestamp(),
            });
          }
        } catch (firebaseErr) {
          console.error("Failed to store scan in Firestore:", firebaseErr);
        }
      } catch (err: any) {
        console.error("Scan error:", err);
        const friendly =
          err?.name === "AbortError"
            ? "Scan was cancelled."
            : err?.message?.includes("Failed to fetch")
            ? "Cannot reach backend. Is the server running and CORS allowed?"
            : err?.message || "Unknown error";
        setError(friendly);
      } finally {
        if (activeScanRef.current === controller) activeScanRef.current = null;
        setLoading(false);
      }
    },
    []
  );

  const value: ScanContextType = {
    scanResult,
    setScanResult,
    scanOptions,
    setScanOptions,
    triggerScan,
    loading,
    error,
    lastUpdated,
    refreshAllPages,
  };

  return <ScanContext.Provider value={value}>{children}</ScanContext.Provider>;
}

export function useScan() {
  const ctx = useContext(ScanContext);
  if (!ctx) throw new Error("useScan must be used within a ScanProvider");
  return ctx;
}
