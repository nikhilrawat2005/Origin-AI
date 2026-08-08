import Link from "next/link";

export default function FeedPage() {
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

      {/* Stage 3: static skeleton only — wired to GET /api/agent/feed in Stage 19 */}
      <div className="card">
        <div className="empty-state">
          No posts yet. Feed will populate once the agent is initialized.
        </div>
      </div>
    </main>
  );
}
