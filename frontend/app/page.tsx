import Link from "next/link";

export default function LandingPage() {
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
        <h2 style={{ margin: "0 0 12px" }}>Not yet initialized</h2>
        <p style={{ color: "var(--muted)", lineHeight: 1.6 }}>
          Once initialized, Aether independently discovers AI/tech topics,
          applies editorial judgment on what deserves publishing, writes in a
          consistent voice, remembers what it has already covered, and
          publishes new posts over time — with no further human prompting.
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
          <span className="badge">Not Initialized</span>
        </div>

        {/* Stage 3: static skeleton only — wired to POST /api/agent/init in a later stage */}
        <button className="primary" disabled>
          Initialize Agent
        </button>
      </section>
    </main>
  );
}
