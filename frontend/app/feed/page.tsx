"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getFeed, type FeedPost, type FeedResponse } from "../lib/api";

// Stage 19: poll instead of a single fetch-on-mount, since the whole
// point of the PRD's success criterion is that the feed grows on its
// own with zero further human prompting — a page that only fetches
// once would never show that happening without a manual refresh.
const POLL_INTERVAL_MS = 30_000;

function formatCreatedAt(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function PostCard({ post }: { post: FeedPost }) {
  return (
    <article className="card" style={{ marginBottom: 16 }}>
      <p style={{ margin: "0 0 4px", color: "var(--muted)", fontSize: 13 }}>
        {formatCreatedAt(post.createdAt)}
      </p>
      <p style={{ lineHeight: 1.6, whiteSpace: "pre-wrap" }}>{post.text}</p>

      <div
        style={{
          marginTop: 20,
          paddingTop: 16,
          borderTop: "1px solid var(--border)",
        }}
      >
        <p style={{ margin: "0 0 4px", color: "var(--muted)", fontSize: 13 }}>
          Rationale
        </p>
        <p style={{ margin: "0 0 16px", lineHeight: 1.6 }}>{post.rationale}</p>

        {post.sources.length > 0 && (
          <>
            <p style={{ margin: "0 0 4px", color: "var(--muted)", fontSize: 13 }}>
              Sources
            </p>
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              {post.sources.map((src) => (
                <li key={src} style={{ marginBottom: 4 }}>
                  <a
                    href={src}
                    target="_blank"
                    rel="noreferrer"
                    style={{ color: "var(--accent)", wordBreak: "break-all" }}
                  >
                    {src}
                  </a>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </article>
  );
}

export default function FeedPage() {
  const [feed, setFeed] = useState<FeedResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const data = await getFeed();
        if (!cancelled) {
          setFeed(data);
          setError(null);
        }
      } catch {
        if (!cancelled) {
          setError("Couldn't reach the backend. Is it running?");
        }
      }
    }

    load();
    const interval = setInterval(load, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const posts = feed?.posts ?? [];

  return (
    <main>
      <nav className="topnav">
        <Link href="/">Landing</Link>
        <Link href="/feed">Feed</Link>
      </nav>

      <h1 style={{ marginBottom: 8 }}>Feed</h1>
      <p style={{ color: "var(--muted)", marginTop: 0, marginBottom: 32 }}>
        Generated posts, in order of publication.
      </p>

      {error && (
        <div className="card" style={{ marginBottom: 24 }}>
          <p style={{ margin: 0, color: "var(--muted)" }}>{error}</p>
        </div>
      )}

      {!error && posts.length === 0 && (
        <div className="card">
          <div className="empty-state">
            No posts yet. Feed will populate once the agent is initialized.
          </div>
        </div>
      )}

      {posts.map((post) => (
        <PostCard key={post.id} post={post} />
      ))}
    </main>
  );
}
