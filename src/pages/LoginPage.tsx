// src/pages/LoginPage.tsx
import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Shield, Mail, Lock } from "lucide-react";

import { auth, db } from "@/firebase";
import {
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  updateProfile,
} from "firebase/auth";
import { setDoc, doc } from "firebase/firestore";

const API_BASE = (import.meta.env.VITE_API_BASE || "").toString().trim(); // optional backend

const LoginPage = () => {
  const navigate = useNavigate();
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // login state
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  // signup state
  const [signupName, setSignupName] = useState("");
  const [signupEmail, setSignupEmail] = useState("");
  const [signupPassword, setSignupPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  // ui state
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // ---- LOGIN (Firebase; optional backend notify) ----
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    setSuccess(null);

    try {
      const cred = await signInWithEmailAndPassword(auth, email, password);
      const user = cred.user;

      // Update last login in Firestore (best-effort)
      try {
        await setDoc(
          doc(db, "users", user.uid),
          { uid: user.uid, email: user.email, lastLoginAt: new Date().toISOString() },
          { merge: true }
        );
      } catch (_) {
        // non-fatal
      }

      // (Optional) notify backend if you have /api/login
      if (API_BASE) {
        try {
          const token = await user.getIdToken();
          await fetch(`${API_BASE}/api/login`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
              uid: user.uid,
              email: user.email,
              login_time: new Date().toISOString(),
            }),
          }).catch(() => {});
        } catch {
          // do not block login on backend failure
        }
      }

      setSuccess("Login successful!");
      navigate("/dashboard");
    } catch (err: any) {
      console.error("Login error:", err);
      const code = err?.code || "";
      const map: Record<string, string> = {
        "auth/invalid-credential": "Invalid email or password.",
        "auth/user-not-found": "No account found with that email.",
        "auth/wrong-password": "Incorrect password.",
        "auth/too-many-requests": "Too many attempts. Try again later.",
        "auth/network-request-failed": "Network error. Check your connection.",
        "auth/invalid-api-key":
          "Firebase API key is invalid. Check env vars on Netlify (VITE_FIREBASE_*).",
      };
      setError(map[code] || err?.message || "Login failed.");
    } finally {
      setBusy(false);
    }
  };

  // ---- SIGNUP (Firebase + Firestore) ----
  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    setSuccess(null);

    if (!signupName.trim()) {
      setError("Name is required.");
      setBusy(false);
      return;
    }
    if (signupPassword !== confirmPassword) {
      setError("Passwords do not match.");
      setBusy(false);
      return;
    }

    try {
      const cred = await createUserWithEmailAndPassword(
        auth,
        signupEmail,
        signupPassword
      );

      await updateProfile(cred.user, { displayName: signupName });

      await setDoc(doc(db, "users", cred.user.uid), {
        uid: cred.user.uid,
        name: signupName,
        email: signupEmail,
        createdAt: new Date().toISOString(),
      });

      setSuccess("Account created! You can now log in.");
      setSignupName("");
      setSignupEmail("");
      setSignupPassword("");
      setConfirmPassword("");
    } catch (err: any) {
      console.error("Signup error:", err);
      const code = err?.code || "";
      const map: Record<string, string> = {
        "auth/email-already-in-use": "Email already in use.",
        "auth/weak-password": "Password is too weak (min 6 characters).",
        "auth/invalid-email": "Invalid email address.",
      };
      setError(map[code] || err?.message || "Signup failed.");
    } finally {
      setBusy(false);
    }
  };

  // Matrix-style background animation
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();

    const characters = "アイウエオカキクケコサシスセソタチツテト0123456789";
    const fontSize = 14;
    let columns = Math.floor(canvas.width / fontSize);
    let drops: number[] = Array.from({ length: columns }, () =>
      Math.floor(Math.random() * -100)
    );

    const draw = () => {
      ctx.fillStyle = "rgba(34, 31, 38, 0.05)";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = "#0FA0CE";
      ctx.font = `${fontSize}px 'JetBrains Mono'`;

      for (let i = 0; i < drops.length; i++) {
        const text = characters[Math.floor(Math.random() * characters.length)];
        ctx.fillText(text, i * fontSize, drops[i] * fontSize);
        if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) {
          drops[i] = 0;
        }
        drops[i]++;
      }
    };

    const interval = setInterval(draw, 50);
    const onResize = () => {
      resize();
      columns = Math.floor(canvas.width / fontSize);
      drops = Array.from({ length: columns }, () =>
        Math.floor(Math.random() * -100)
      );
    };
    window.addEventListener("resize", onResize);

    return () => {
      clearInterval(interval);
      window.removeEventListener("resize", onResize);
    };
  }, []);

  return (
    <div className="h-screen w-full flex items-center justify-center relative overflow-hidden">
      {/* Animated Background */}
      <canvas ref={canvasRef} className="absolute inset-0 z-0" />

      {/* Login/Signup Card */}
      <div className="z-10 w-full max-w-md">
        <div className="glass-panel p-8 border border-cyber-blue/30 shadow-lg animate-fade-in">
          <div className="flex justify-center mb-6">
            <div className="h-16 w-16 rounded-full bg-cyber-blue/20 border border-cyber-blue/40 flex items-center justify-center animate-pulse-glow">
              <Shield size={32} className="text-cyber-blue" />
            </div>
          </div>

          <h1 className="text-center text-2xl font-bold font-mono tracking-tight text-cyber-blue mb-2">
            Aura-AI
          </h1>
          <p className="text-center text-sm text-gray-400 mb-6">
            Advanced Penetration Testing Platform
          </p>

          <Tabs defaultValue="login" className="w-full">
            <TabsList className="grid w-full grid-cols-2 mb-6">
              <TabsTrigger value="login">Log In</TabsTrigger>
              <TabsTrigger value="signup">Sign Up</TabsTrigger>
            </TabsList>

            {/* Login Tab */}
            <TabsContent value="login">
              {error && (
                <div className="mb-4 text-red-500 text-center text-sm">{error}</div>
              )}
              {success && (
                <div className="mb-4 text-green-500 text-center text-sm">
                  {success}
                </div>
              )}

              <form onSubmit={handleLogin}>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="email">Email</Label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-2.5 h-5 w-5 text-muted-foreground" />
                      <Input
                        id="email"
                        type="email"
                        className="pl-10 cyber-input"
                        placeholder="you@example.com"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        autoComplete="username"
                        required
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="password">Password</Label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-2.5 h-5 w-5 text-muted-foreground" />
                      <Input
                        id="password"
                        type="password"
                        className="pl-10 cyber-input"
                        placeholder="••••••••"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        autoComplete="current-password"
                        required
                      />
                    </div>
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        id="remember"
                        className="h-4 w-4 rounded border-gray-300 text-cyber-blue focus:ring-cyber-blue"
                      />
                      <label
                        htmlFor="remember"
                        className="text-sm text-gray-400"
                      >
                        Remember me
                      </label>
                    </div>
                    <a
                      href="#"
                      className="text-sm text-cyber-blue hover:underline"
                    >
                      Forgot password?
                    </a>
                  </div>

                  <Button
                    type="submit"
                    disabled={busy}
                    className="w-full text-black bg-cyber-blue hover:bg-cyber-blue/90"
                  >
                    {busy ? "Please wait..." : "Log In"}
                  </Button>
                </div>
              </form>
            </TabsContent>

            {/* Sign Up Tab */}
            <TabsContent value="signup">
              <form onSubmit={handleSignup}>
                <div className="space-y-2">
                  <Label htmlFor="signup-name">Name</Label>
                  <Input
                    id="signup-name"
                    type="text"
                    className="pl-4 cyber-input"
                    placeholder="Your Name"
                    value={signupName}
                    onChange={(e) => setSignupName(e.target.value)}
                    autoComplete="name"
                    required
                  />
                </div>

                <div className="space-y-4 mt-4">
                  <div className="space-y-2">
                    <Label htmlFor="signup-email">Email</Label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-2.5 h-5 w-5 text-muted-foreground" />
                      <Input
                        id="signup-email"
                        type="email"
                        className="pl-10 cyber-input"
                        placeholder="you@example.com"
                        value={signupEmail}
                        onChange={(e) => setSignupEmail(e.target.value)}
                        autoComplete="username"
                        required
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="signup-password">Password</Label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-2.5 h-5 w-5 text-muted-foreground" />
                      <Input
                        id="signup-password"
                        type="password"
                        className="pl-10 cyber-input"
                        placeholder="••••••••"
                        value={signupPassword}
                        onChange={(e) => setSignupPassword(e.target.value)}
                        autoComplete="new-password"
                        required
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="confirm-password">Confirm Password</Label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-2.5 h-5 w-5 text-muted-foreground" />
                      <Input
                        id="confirm-password"
                        type="password"
                        className="pl-10 cyber-input"
                        placeholder="••••••••"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        autoComplete="new-password"
                        required
                      />
                    </div>
                  </div>

                  <Button
                    disabled={busy}
                    className="w-full text-black bg-cyber-blue hover:bg-cyber-blue/90"
                  >
                    {busy ? "Creating..." : "Create Account"}
                  </Button>
                </div>
              </form>
            </TabsContent>
          </Tabs>

          <p className="text-center text-xs text-gray-400 mt-6">
            Protected by advanced encryption &amp; multi-factor authentication
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
