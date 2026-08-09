"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { getAgentStatus, getFeed, initAgent, stopAgent, type AgentInitResponse } from "./lib/api";

type LoadState = "idle" | "loading" | "error";

function NavBar({ isActive }: { isActive: boolean }) {
  const pathname = usePathname();
  return (
    <nav className="topnav">
      <Link href="/" className="nav-logo">
        <span className="nav-logo-dot" />
        Aether
        <span className="nav-logo-badge">Autonomous</span>
      </Link>
      <div className="nav-links">
        <Link href="/" className={pathname === "/" ? "active" : ""}>
          Home
        </Link>
        <Link href="/feed" className={pathname === "/feed" ? "active" : ""}>
          Feed
          {isActive && (
            <span style={{ marginLeft: 6, display: "inline-flex", alignItems: "center" }}>
              <span className="pulse-dot" style={{ width: 6, height: 6 }} />
            </span>
          )}
        </Link>
      </div>
    </nav>
  );
}

export default function LandingPage() {
  const [agent, setAgent] = useState<AgentInitResponse | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [isReconnecting, setIsReconnecting] = useState(false);
  const [totalPostsCount, setTotalPostsCount] = useState<number | null>(null);
  const [nextRunTime, setNextRunTime] = useState<string | null>(null);
  const [countdownText, setCountdownText] = useState<string>("");
  const [sources, setSources] = useState<string[]>([]);
  const [showSourcesModal, setShowSourcesModal] = useState(false);

  useEffect(() => {
    async function checkStatus() {
      try {
        const status = await getAgentStatus();
        setIsReconnecting(false);
        if (status.sources) setSources(status.sources);

        if (status.status === "active" && status.agentId) {
          setAgent({ agentId: status.agentId });
          setNextRunTime(status.nextRunTime || null);
          const feed = await getFeed();
          setTotalPostsCount(feed.posts.length);
        } else {
          setAgent(null);
          setNextRunTime(null);
        }
      } catch {
        setIsReconnecting(true);
        setAgent(null);
      }
    }

    checkStatus();
    const statusInterval = setInterval(checkStatus, 15_000);
    return () => clearInterval(statusInterval);
  }, []);

  // Countdown timer effect for Next Slot reverse time
  useEffect(() => {
    if (!nextRunTime) {
      setCountdownText("");
      return;
    }

    function updateCountdown() {
      const target = new Date(nextRunTime!).getTime();
      const now = new Date().getTime();
      const diff = target - now;

      if (diff <= 0) {
        setCountdownText("Executing publish cycle now…");
        return;
      }

      const mins = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      const secs = Math.floor((diff % (1000 * 60)) / 1000);
      setCountdownText(`${mins.toString().padStart(2, "0")}m ${secs.toString().padStart(2, "0")}s`);
    }

    updateCountdown();
    const timer = setInterval(updateCountdown, 1000);
    return () => clearInterval(timer);
  }, [nextRunTime]);

  async function handleInitialize() {
    setLoadState("loading");
    try {
      const result = await initAgent();
      setAgent(result);
      setLoadState("idle");
      setIsReconnecting(false);

      const status = await getAgentStatus();
      setNextRunTime(status.nextRunTime || null);

      const feed = await getFeed();
      setTotalPostsCount(feed.posts.length);
    } catch {
      setLoadState("error");
    }
  }

  async function handleStop() {
    setLoadState("loading");
    try {
      await stopAgent();
      setAgent(null);
      setNextRunTime(null);
      setLoadState("idle");
    } catch {
      setLoadState("error");
    }
  }

  const isActive = agent !== null;

  return (
    <main>
      <NavBar isActive={isActive} />

      {isReconnecting && (
        <div className="reconnect-banner">
          <span>⚡ Reconnecting to Backend… Checking agent runtime connection</span>
        </div>
      )}

      {/* Hero */}
      <div className="hero">
        <div className="hero-tag">
          <span className="pulse-dot" />
          Autonomous AI Persona
        </div>
        <h1>Autonomous AI &amp; Technology Curation Engine</h1>
        <p className="hero-sub">
          Aether continuously discovers raw AI/ML breakthroughs, applies LLM editorial gatekeeping, and publishes synthesis posts — zero prompt engineering or human intervention needed.
        </p>
      </div>

      {/* Dashboard Quick Stats */}
      <div className="dashboard-grid">
        <div className="stat-card">
          <div className="stat-label">Agent Status</div>
          <div className="stat-val" style={{ color: isActive ? "var(--accent)" : "var(--muted)" }}>
            {isActive ? "ACTIVE" : "PAUSED"}
          </div>
          <div className="stat-desc">{isActive ? "Autonomous loop running" : "Standby mode"}</div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Published Curation</div>
          <div className="stat-val">
            {totalPostsCount !== null ? totalPostsCount : "—"}
          </div>
          <div className="stat-desc">Research posts generated</div>
        </div>

        <div
          className="stat-card stat-card-interactive"
          onClick={() => setShowSourcesModal(true)}
          style={{
            cursor: "pointer",
            border: "1px solid var(--border-accent)",
            background: "var(--accent-glow)",
            transition: "all 0.25s ease",
          }}
          title="Click to view all configured sources"
        >
          <div className="stat-label" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span>Ingestion Network</span>
            <span style={{
              background: "var(--accent)",
              color: "#042f1a",
              padding: "2px 8px",
              borderRadius: 999,
              fontSize: 10,
              fontWeight: 800,
              letterSpacing: "0.06em"
            }}>
              CLICK TO VIEW
            </span>
          </div>
          <div className="stat-val" style={{ fontSize: 22, color: "var(--accent)" }}>
            {sources.length || 14} Sources ↗
          </div>
          <div className="stat-desc">HN Algolia, arXiv, Tech RSS, Reddit (Click for details)</div>
        </div>
      </div>

      {/* Control Card with Countdown */}
      <div className="control-card">
        <div className="control-card-info" style={{ flex: 1 }}>
          <h3>Agent Operational State</h3>
          <p>
            {isActive
              ? "Autonomous background scheduler is active and running fast 5-post batch cycles."
              : "Agent is currently paused. Initialize to start auto-discovering and publishing."}
          </p>

          {/* Reverse Countdown Indicator */}
          {isActive && countdownText && (
            <div style={{
              marginTop: 14,
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              background: "var(--accent-glow)",
              border: "1px solid var(--border-accent)",
              padding: "6px 14px",
              borderRadius: 10,
              fontSize: 13,
              fontWeight: 700,
              color: "var(--accent)"
            }}>
              <span>⏱ Next Autonomous Cycle Slot In:</span>
              <span style={{ fontFamily: "monospace", fontSize: 14 }}>{countdownText}</span>
            </div>
          )}
        </div>

        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <div className={`status-pill ${isActive ? "active" : "stopped"}`}>
            <span className={`pulse-dot ${isActive ? "" : "dim"}`} />
            {isActive ? "Active" : "Stopped"}
          </div>

          {isActive ? (
            <>
              <Link href="/feed" style={{ textDecoration: "none" }}>
                <button className="btn btn-primary" type="button">
                  Open Feed →
                </button>
              </Link>
              <button
                className="btn btn-danger"
                disabled={loadState === "loading"}
                onClick={handleStop}
                type="button"
              >
                {loadState === "loading" ? "Pausing…" : "Stop Agent"}
              </button>
            </>
          ) : (
            <button
              className="btn btn-primary"
              disabled={loadState === "loading"}
              onClick={handleInitialize}
              type="button"
            >
              {loadState === "loading" ? (
                <>
                  <span style={{ display: "inline-block", animation: "spin 1s linear infinite" }}>⟳</span>
                  Initializing Engine…
                </>
              ) : (
                "Initialize Agent Engine"
              )}
            </button>
          )}
        </div>
      </div>

      {/* Sources Pop-out Modal */}
      {showSourcesModal && (
        <div style={{
          position: "fixed",
          inset: 0,
          background: "rgba(5, 7, 12, 0.85)",
          backdropFilter: "blur(8px)",
          zIndex: 100,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: 24,
        }}>
          <div style={{
            background: "var(--panel-solid)",
            border: "1px solid var(--border-accent)",
            borderRadius: 20,
            padding: 28,
            maxWidth: 520,
            width: "100%",
            boxShadow: "0 20px 50px rgba(0,0,0,0.6)",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
              <h3 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-heading)" }}>
                📡 Active Ingestion Sources ({sources.length})
              </h3>
              <button
                onClick={() => setShowSourcesModal(false)}
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--muted)",
                  fontSize: 20,
                  cursor: "pointer",
                }}
              >
                ✕
              </button>
            </div>
            <p style={{ fontSize: 13, color: "var(--muted)", marginBottom: 16 }}>
              Aether polls these 14 configured raw candidate channels on every autonomous cycle:
            </p>
            <div style={{
              display: "flex",
              flexDirection: "column",
              gap: 8,
              maxHeight: 320,
              overflowY: "auto",
              paddingRight: 6,
            }}>
              {sources.map((src, i) => (
                <div key={src} style={{
                  fontSize: 13,
                  fontWeight: 600,
                  padding: "8px 12px",
                  borderRadius: 8,
                  background: "rgba(255, 255, 255, 0.03)",
                  border: "1px solid var(--border)",
                  color: "var(--text)",
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                }}>
                  <span style={{ color: "var(--accent)", fontSize: 11 }}>#{i + 1}</span>
                  <span>{src}</span>
                </div>
              ))}
            </div>
            <div style={{ marginTop: 20, textAlign: "right" }}>
              <button
                className="btn btn-primary"
                onClick={() => setShowSourcesModal(false)}
                style={{ padding: "8px 18px", fontSize: 13 }}
              >
                Close Window
              </button>
            </div>
          </div>
        </div>
      )}

      {loadState === "error" && (
        <div className="error-banner">
          ⚠ Couldn&apos;t connect to Aether backend. Please verify your backend server status.
        </div>
      )}

      {/* Pipeline Sequence */}
      <div className="pipeline-section">
        <h3 className="section-title">Autonomous Architecture</h3>
        <div className="pipeline-grid">
          <div className="pipeline-card">
            <div className="pipeline-step">
              <span>Step 01</span>
              <span>⚡ Discovery</span>
            </div>
            <h4>Multi-Source Ingestion</h4>
            <p>
              Scans arXiv RSS (cs.AI, cs.LG, cs.CL), Reddit ML/LocalLLaMA, Hacker News Algolia, TechCrunch &amp; Ars Technica feeds continuously.
            </p>
          </div>

          <div className="pipeline-card">
            <div className="pipeline-step">
              <span>Step 02</span>
              <span>🎯 Editorial</span>
            </div>
            <h4>LLM Quality Gatekeeper</h4>
            <p>
              Evaluates candidates for novel tech insights, high impact, and relevance while filtering repetitive announcements and low-quality noise.
            </p>
          </div>

          <div className="pipeline-card">
            <div className="pipeline-step">
              <span>Step 03</span>
              <span>🧠 Memory &amp; Publish</span>
            </div>
            <h4>Vector Dedup &amp; Voice Synthesis</h4>
            <p>
              Breeth-backed semantic memory prevents duplicated topics before synthesizing commentary in Aether&apos;s distinct editorial voice.
            </p>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </main>
  );
}
