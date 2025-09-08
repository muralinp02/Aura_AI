import axios, { AxiosError } from "axios";

// Read base URL from env, fallback to 127.0.0.1 for Windows stability
const API_BASE =
  import.meta.env.VITE_API_BASE?.trim() || "http://127.0.0.1:8000";

// Single axios instance (helps with headers, timeouts, logging)
export const api = axios.create({
  baseURL: API_BASE,
  timeout: 120_000, // 120s; adjust if scans take longer
  // withCredentials: true, // enable only if you actually use cookies/sessions
});

// Helpful logging
api.interceptors.response.use(
  (r) => r,
  (err: AxiosError) => {
    const data =
      typeof err.response?.data === "string"
        ? err.response?.data
        : JSON.stringify(err.response?.data);
    console.error(
      `[API ${err.config?.method?.toUpperCase()} ${err.config?.url}]`,
      `status=${err.response?.status} data=${data}`
    );
    return Promise.reject(err);
  }
);

// ---------- Endpoints ----------

export async function health() {
  const r = await api.get("/health");
  return r.data;
}

export async function crawlWebsite(url: string) {
  const form = new FormData();
  form.append("url", url);
  const res = await api.post("/crawl", form);
  return res.data;
}

export async function predictVulnerability(file: File) {
  const form = new FormData();
  form.append("file", file);
  const res = await api.post("/predict", form);
  return res.data;
}

export async function getNetworkGraph(
  endpoints: string[],
  connections: [string, string][]
) {
  // FastAPI can accept JSON body for this one
  const res = await api.post("/network/graph", { endpoints, connections });
  return res.data;
}

export async function getAttackPaths(start: string, end: string) {
  const form = new FormData();
  form.append("start", start);
  form.append("end", end);
  const res = await api.post("/network/paths", form);
  return res.data;
}

export async function pushAlert(alertData: any) {
  const res = await api.post("/alert", alertData);
  return res.data;
}

// The big one your UI needs:
export async function fullScan(opts: {
  url?: string;
  scanType?: "Quick" | "Full" | "Custom";
  file?: File;
}) {
  const form = new FormData();
  if (opts.url) form.append("url", opts.url);
  if (opts.scanType) form.append("scan_type", opts.scanType); // snake_case matches FastAPI
  if (opts.file) form.append("file", opts.file); // only if you support uploads
  const res = await api.post("/fullscan", form);
  return res.data;
}

// Optional: quick runtime check
console.log("API_BASE =", API_BASE);
