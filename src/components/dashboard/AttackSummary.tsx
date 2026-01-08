import { useEffect, useMemo, useRef, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import {
  Terminal,
  ShieldAlert,
  Webhook,
  BarChart,
  AlertTriangle,
  CircleX,
} from "lucide-react";
import { onAuthStateChanged, getAuth } from "firebase/auth";
import { doc, getDoc } from "firebase/firestore";
import { db } from "@/firebase";

type Risk = "high" | "medium" | "low";

interface AttackData {
  category: string;
  count: number;
  color: string;
  icon?: string;
  risk: Risk;
  description: string;
}

const ICON_MAP: Record<string, any> = {
  Terminal,
  ShieldAlert,
  Webhook,
  BarChart,
  AlertTriangle,
  CircleX,
};

const FALLBACK_DATA: AttackData[] = [
  {
    category: "SQL Injection",
    count: 8,
    color: "#ef4444",
    icon: "ShieldAlert",
    risk: "high",
    description: "Malicious SQL patterns detected on authentication endpoints.",
  },
  {
    category: "Brute Force",
    count: 14,
    color: "#f97316",
    icon: "AlertTriangle",
    risk: "medium",
    description: "Repeated failed login attempts across multiple IP addresses.",
  },
  {
    category: "XSS Attempts",
    count: 6,
    color: "#eab308",
    icon: "Webhook",
    risk: "medium",
    description: "Script injection payloads detected in user inputs.",
  },
  {
    category: "Reconnaissance",
    count: 11,
    color: "#38bdf8",
    icon: "BarChart",
    risk: "low",
    description: "Port scans and endpoint enumeration activity observed.",
  },
];

function normalizeData(raw: any): AttackData[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((x) => ({
    category: String(x?.category ?? "Unknown"),
    count: Number(x?.count) || 0,
    color: typeof x?.color === "string" ? x.color : "#94a3b8",
    icon: typeof x?.icon === "string" ? x.icon : "Terminal",
    risk: x?.risk === "high" || x?.risk === "medium" || x?.risk === "low" ? x.risk : "low",
    description: String(x?.description ?? ""),
  }));
}

export function AttackSummary() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [attackData, setAttackData] = useState<AttackData[]>(FALLBACK_DATA);

  useEffect(() => {
    const auth = getAuth();

    const unsub = onAuthStateChanged(auth, async (user) => {
      try {
        if (!user) return;

        const ref = doc(db, "users", user.uid, "dashboard", "attackSummary");
        const snap = await getDoc(ref);

        if (snap.exists()) {
          const normalized = normalizeData(snap.data()?.attackData);
          if (normalized.length > 0) {
            setAttackData(normalized);
          }
        }
      } catch {
        // Silent fallback — intentionally ignored
      }
    });

    return () => unsub();
  }, []);

  const totalAttacks = useMemo(
    () => attackData.reduce((sum, a) => sum + a.count, 0),
    [attackData]
  );

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    canvas.width = 160;
    canvas.height = 160;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const cx = canvas.width / 2;
    const cy = canvas.height / 2;
    const r = Math.min(cx, cy) * 0.8;

    if (totalAttacks <= 0) return;

    let start = 0;
    attackData.forEach((item) => {
      const angle = (item.count / totalAttacks) * Math.PI * 2;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, r, start, start + angle);
      ctx.closePath();
      ctx.fillStyle = item.color;
      ctx.fill();
      start += angle;
    });

    ctx.beginPath();
    ctx.arc(cx, cy, r * 0.6, 0, Math.PI * 2);
    ctx.fillStyle = "#1A1F2C";
    ctx.fill();

    ctx.fillStyle = "white";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.font = "bold 24px Inter";
    ctx.fillText(totalAttacks.toString(), cx, cy - 8);
    ctx.font = "12px Inter";
    ctx.fillText("ATTACKS TODAY", cx, cy + 12);
  }, [attackData, totalAttacks]);

  const getRiskColor = (risk: Risk) => {
    switch (risk) {
      case "high":
        return "bg-red-500/20 text-red-400 border-red-500/40";
      case "medium":
        return "bg-orange-500/20 text-orange-400 border-orange-500/40";
      case "low":
        return "bg-blue-500/20 text-blue-400 border-blue-500/40";
      default:
        return "bg-gray-500/20 text-gray-400 border-gray-500/40";
    }
  };

  return (
    <Card className="cyber-card h-full">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg font-mono text-gray-300 flex items-center gap-2">
          <ShieldAlert size={18} className="text-cyber-blue" />
          Attack Summary
        </CardTitle>
      </CardHeader>

      <CardContent className="flex flex-col p-4 gap-4">
        <div className="flex justify-center">
          <canvas ref={canvasRef} />
        </div>

        <ScrollArea className="flex-1 pr-4 max-h-[180px]">
          <div className="space-y-3">
            {attackData.map((item, idx) => {
              const Icon = ICON_MAP[item.icon || "Terminal"] || Terminal;
              return (
                <div
                  key={idx}
                  className="flex items-center gap-3 p-2 rounded-md hover:bg-cyber-blue/5 transition"
                >
                  <div
                    className="w-8 h-8 rounded-md flex items-center justify-center"
                    style={{ backgroundColor: `${item.color}20` }}
                  >
                    <Icon size={16} style={{ color: item.color }} />
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-center">
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-gray-300 font-medium truncate">
                          {item.category}
                        </span>
                        <Badge className={getRiskColor(item.risk)}>
                          {item.risk}
                        </Badge>
                      </div>
                      <span className="text-sm font-mono text-gray-400">
                        {item.count}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 truncate">
                      {item.description}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
