"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getFeed, initAgent, stopAgent, type AgentInitResponse } from "./lib/api";

type LoadState = "idle" | "loading" | "error";

export default function LandingPage() {
  const [agent, setAgent] = useState<AgentInitResponse | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("idle");

  useEffect(() => {
    // On mount, check if agent is already active by checking feed/backend
    async function checkStatus() {
      try {
        const feed = await getFeed();
        // If feed endpoint responds fine, agent exists or backend is initialized
        if (feed) {
          setAgent({ agentId: "active" });
        }
      } catch {
        // Backend not initialized or down
      }
    }
    checkStatus();
  }, []);

  async function handleInitialize() {
    setLoadState("loading");
    try {
      const result = await initAgent();
      setAgent(result);
      setLoadState("idle");
    } catch {
      setLoadState("error");
    }
  }

  async function handleStop() {
    setLoadState("loading");
    try {
      await stopAgent();
      setAgent(null);
      setLoadState("idle");
    } catch {
      setLoadState("error");
    }
  }

  const isActive = agent !== null;

  return (
    <main>
      <nav className="topnav">
        <Link href="/">Landing</Link>
        <Link href="/feed">Feed</Link>
      </nav>

      <h1 style={{ marginBottom: 8 }}>Aether</h1>
      <p style={{ color: "var(--muted)", marginTop: 0, marginBottom: 32 }}>
        Autonomous AI Technology Research Persona
      </p>

      <section className="card" style={{ marginBottom: 24 }}>
        <p style={{ marginTop: 0, color: "var(--muted)", fontSize: 13 }}>
          Persona
        </p>
        <h2 style={{ margin: "0 0 12px" }}>
          {agent ? "Initialized & Active" : "Paused / Not Initialized"}
        </h2>
        <p style={{ color: "var(--muted)", lineHeight: 1.6 }}>
          Once initialized, Aether independently discovers AI/tech topics, applies editorial judgment on what deserves publishing, writes in a consistent voice, remembers what it has already covered, and publishes new posts over time — with no further human prompting.
        </p>
      </section>

      <section
        className="card"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 16,
        }}
      >
        <div>
          <p style={{ margin: 0, color: "var(--muted)", fontSize: 13 }}>
            Agent Status
          </p>
          <span className="badge">
            {isActive ? "Active (Running)" : "Stopped / Paused"}
          </span>
        </div>

        {isActive ? (
          <button
            className="secondary"
            disabled={loadState === "loading"}
            onClick={handleStop}
            style={{
              padding: "8px 16px",
              cursor: "pointer",
              backgroundColor: "#ef4444",
              color: "#fff",
              border: "none",
              borderRadius: "6px",
              fontWeight: 500,
            }}
          >
            {loadState === "loading" ? "Stopping…" : "Stop Agent"}
          </button>
        ) : (
          <button
            className="primary"
            disabled={loadState === "loading"}
            onClick={handleInitialize}
          >
            {loadState === "loading" ? "Initializing…" : "Initialize Agent"}
          </button>
        )}
      </section>

      {loadState === "error" && (
        <p style={{ color: "var(--muted)", marginTop: 16, fontSize: 13 }}>
          Couldn't reach the backend. Is it running?
        </p>
      )}

      {isActive && (
        <p style={{ color: "var(--muted)", marginTop: 16, fontSize: 13 }}>
          Head to the{" "}
          <Link href="/feed" style={{ color: "var(--accent)" }}>
            Feed
          </Link>{" "}
          to watch posts appear automatically as the agent publishes.
        </p>
      )}
    </main>
  );
}
