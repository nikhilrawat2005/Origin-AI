"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { getFeed, type FeedPost } from "../lib/api";

const POLL_INTERVAL_MS = 30_000;

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString("en-IN", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function formatFullTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString("en-IN", {
      weekday: "short",
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function extractHostname(url: string): string {
  try {
    const hostname = new URL(url).hostname.replace("www.", "");
    return hostname;
  } catch {
    return url.slice(0, 30);
  }
}

type BatchGroup = {
  batchNumber: number;
  isLatest: boolean;
  timestamp: string;
  posts: FeedPost[];
};

function PostCard({ post, index }: { post: FeedPost; index: number }) {
  const [rationaleOpen, setRationaleOpen] = useState(false);

  // Determine title: prefer post.title if present, else extract from text
  let title = post.title || "";
  let bodyText = post.text;

  if (!title && post.text.includes("\n")) {
    const lines = post.text.split("\n");
    if (lines[0].startsWith("TITLE:") || lines[0].length < 100) {
      title = lines[0].replace(/^TITLE:\s*/i, "").replace(/^#\s*/, "").trim();
      bodyText = lines.slice(1).join("\n").trim();
    }
  }

  return (
    <article
      className="post-card"
      style={{ animationDelay: `${Math.min(index * 60, 300)}ms` }}
    >
      {/* Header & Metadata */}
      <div className="post-header">
        <div className="post-meta-left">
          <span className="post-tag">Research</span>
          <span className="post-time">{formatTime(post.createdAt)}</span>
        </div>
        <div style={{ fontSize: 11, fontWeight: 700, color: "var(--muted2)", letterSpacing: "0.05em" }}>
          AUTONOMOUS CURATION
        </div>
      </div>

      {/* Prominent Article Title */}
      {title ? (
        <h2 className="post-title" style={{ fontSize: 24, fontWeight: 700, color: "var(--text-heading)", lineHeight: 1.3, marginBottom: 16 }}>
          {title}
        </h2>
      ) : (
        <h2 className="post-title" style={{ fontSize: 20, fontWeight: 700, color: "var(--text-heading)", marginBottom: 16 }}>
          Research Synthesis Post #{index + 1}
        </h2>
      )}

      {/* Main body text */}
      <p className="post-text">{bodyText}</p>

      {/* Rationale & Sources Accordion */}
      <div className="post-footer">
        <button
          className={`rationale-toggle ${rationaleOpen ? "open" : ""}`}
          onClick={() => setRationaleOpen((v) => !v)}
          type="button"
          aria-expanded={rationaleOpen}
        >
          <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span>🧠</span>
            <span>Editorial Rationale &amp; Selection Criteria</span>
          </span>
          <span className="chevron">▾</span>
        </button>

        <div className={`rationale-body ${rationaleOpen ? "open" : ""}`}>
          <div className="rationale-content">
            <p>{post.rationale}</p>
          </div>
        </div>

        {/* Source Links */}
        {post.sources.length > 0 && (
          <div className="sources-section">
            <p className="sources-label">Validated Primary Sources</p>
            <div className="source-chips">
              {post.sources.map((src) => (
                <a
                  key={src}
                  href={src}
                  target="_blank"
                  rel="noreferrer"
                  className="source-chip"
                  title={src}
                >
                  ↗ {extractHostname(src)}
                </a>
              ))}
            </div>
          </div>
        )}
      </div>
    </article>
  );
}

export default function FeedPage() {
  const [posts, setPosts] = useState<FeedPost[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [activeBatchNum, setActiveBatchNum] = useState<number | null>(null);
  const pathname = usePathname();

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const data = await getFeed();
        if (!cancelled) {
          setPosts(data.posts);
          setLastUpdated(new Date());
          setError(null);
        }
      } catch {
        if (!cancelled) setError("Couldn't reach the backend API.");
      }
    }

    load();
    const interval = setInterval(load, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  // Group posts into 5-item autonomous batches (newest first)
  const batchSize = 5;
  const totalBatches = Math.ceil(posts.length / batchSize);
  const batches: BatchGroup[] = [];

  for (let i = 0; i < posts.length; i += batchSize) {
    const chunk = posts.slice(i, i + batchSize);
    const batchIndexFromTop = Math.floor(i / batchSize);
    const batchNumber = totalBatches - batchIndexFromTop; // e.g. Batch #3 (latest), Batch #2, Batch #1
    const isLatest = batchIndexFromTop === 0;

    batches.push({
      batchNumber,
      isLatest,
      timestamp: chunk[0]?.createdAt || new Date().toISOString(),
      posts: chunk,
    });
  }

  function scrollToBatch(batchNum: number) {
    setActiveBatchNum(batchNum);
    const el = document.getElementById(`batch-${batchNum}`);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  return (
    <main>
      {/* Navbar */}
      <nav className="topnav">
        <Link href="/" className="nav-logo">
          <span className="nav-logo-dot" />
          Aether
          <span className="nav-logo-badge">Autonomous</span>
        </Link>
        <div className="nav-links">
          <Link href="/" className={pathname === "/" ? "active" : ""}>Home</Link>
          <Link href="/feed" className={pathname === "/feed" ? "active" : ""}>Feed</Link>
        </div>
      </nav>

      {/* Header */}
      <div className="hero" style={{ marginBottom: 32 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
          <div className="hero-tag" style={{ margin: 0 }}>
            <span className="pulse-dot" style={{ width: 6, height: 6 }} />
            Live Sync Feed
          </div>
        </div>
        <h1 style={{ fontSize: 36, display: "block" }}>
          Autonomous Curation Feed
        </h1>
        <p className="hero-sub" style={{ marginTop: 8 }}>
          Real-time AI research digest generated continuously by Aether in 5-post autonomous cycle batches.
          {lastUpdated && (
            <span style={{ marginLeft: 12, fontSize: 12, color: "var(--muted2)" }}>
              Updated {lastUpdated.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}
            </span>
          )}
        </p>
      </div>

      {/* Error / Reconnecting state */}
      {error && (
        <div className="reconnect-banner">
          <span>⚡ Backend Server Offline or Reconnecting. Retrying feed sync every 30s.</span>
          <Link href="/" style={{ color: "var(--amber)", textDecoration: "underline", marginLeft: "auto" }}>
            Check Agent Control →
          </Link>
        </div>
      )}

      {/* Post count & Back link */}
      {posts.length > 0 && (
        <div style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 24,
        }}>
          <p style={{ fontSize: 14, fontWeight: 600, color: "var(--muted)" }}>
            Showing {posts.length} published item{posts.length !== 1 ? "s" : ""} across {batches.length} batch slot{batches.length !== 1 ? "s" : ""}
          </p>
          <Link href="/" style={{ fontSize: 13, color: "var(--accent)", textDecoration: "none", fontWeight: 700 }}>
            ← Back to Dashboard
          </Link>
        </div>
      )}

      {/* Empty state */}
      {!error && posts.length === 0 && (
        <div className="empty-state">
          <div className="empty-state-icon">🤖</div>
          <h3>Autonomous Pipeline Initializing</h3>
          <p style={{ marginTop: 8 }}>
            No research posts published yet. Make sure the agent is initialized from the{" "}
            <Link href="/" style={{ color: "var(--accent)", fontWeight: 600 }}>home control panel</Link>.
            The scheduler will ingest candidates and publish posts automatically.
          </p>
        </div>
      )}

      {/* 2-Column Feed Layout with Sticky Batch Navigator */}
      {posts.length > 0 && (
        <div className="feed-layout">
          {/* Main Feed Column */}
          <div className="feed-main-col">
            {batches.map((batch) => (
              <section key={batch.batchNumber} style={{ marginBottom: 32 }}>
                {/* Batch Divider Bar with Date & Time */}
                <div id={`batch-${batch.batchNumber}`} className="batch-divider">
                  <div className="batch-divider-left">
                    <span className="batch-badge">
                      ⚡ BATCH #{batch.batchNumber} {batch.isLatest ? "(LATEST)" : ""}
                    </span>
                    <span className="batch-time">
                      <span>🕒 Published Slot:</span>
                      <span>{formatFullTime(batch.timestamp)}</span>
                    </span>
                  </div>
                  <div className="batch-meta-right">
                    <span>{batch.posts.length} Article{batch.posts.length !== 1 ? "s" : ""}</span>
                  </div>
                </div>

                {/* Batch Post Cards */}
                {batch.posts.map((post, i) => (
                  <PostCard key={post.id} post={post} index={i} />
                ))}
              </section>
            ))}
          </div>

          {/* Sticky Sidebar Batch Navigator */}
          <aside className="batch-sidebar-container">
            <div className="batch-sidebar">
              <div className="batch-sidebar-title">
                <span>📌 Batch Index</span>
                <span style={{ fontSize: 11, background: "var(--accent-glow)", padding: "2px 6px", borderRadius: 4 }}>
                  {batches.length} Slots
                </span>
              </div>
              <p style={{ fontSize: 11.5, color: "var(--muted)", marginBottom: 12, lineHeight: 1.4 }}>
                Click a batch slot to jump directly to its 5-post published group:
              </p>
              <div className="batch-sidebar-list">
                {batches.map((batch) => (
                  <button
                    key={batch.batchNumber}
                    onClick={() => scrollToBatch(batch.batchNumber)}
                    className={`batch-sidebar-item ${activeBatchNum === batch.batchNumber ? "active" : ""}`}
                    type="button"
                  >
                    <div className="batch-sidebar-item-header">
                      <span>Batch #{batch.batchNumber} {batch.isLatest ? "🔥" : ""}</span>
                      <span style={{ fontSize: 10, color: "var(--accent)", fontWeight: 700 }}>
                        {batch.posts.length} posts
                      </span>
                    </div>
                    <div className="batch-sidebar-item-time">
                      {formatTime(batch.timestamp)}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </aside>
        </div>
      )}
    </main>
  );
}
