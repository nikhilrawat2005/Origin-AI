/**
 * Stage 19 — thin fetch wrappers for the backend's two public
 * endpoints. Kept deliberately tiny (no SDK, no client library) since
 * the PRD scopes the frontend down to exactly two pages calling
 * exactly two endpoints — anything more here would be scope creep for
 * what's still just two `fetch()` calls.
 *
 * NEXT_PUBLIC_API_URL must be set at build time to reach a
 * non-localhost backend (e.g. once deployed on Railway); see
 * frontend/.env.local.example.
 */
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type AgentInitResponse = {
  agentId: string;
  status: string;
  personaName: string;
  personaDescription: string | null;
  breethAgentRef: string | null;
  createdAt: string;
};

export type FeedPost = {
  id: string;
  title: string;
  content: string;
  rationale: string;
  sources: string[];
  createdAt: string;
};

export type FeedResponse = {
  agentId: string | null;
  personaName: string | null;
  status: string | null;
  posts: FeedPost[];
};

export async function initAgent(): Promise<AgentInitResponse> {
  const res = await fetch(`${API_URL}/api/agent/init`, { method: "POST" });
  if (!res.ok) {
    throw new Error(`Init failed: ${res.status}`);
  }
  return res.json();
}

export async function getFeed(): Promise<FeedResponse> {
  const res = await fetch(`${API_URL}/api/agent/feed`, {
    // Always hit the live backend — this is polled repeatedly per the
    // PRD's "feed must grow on its own" success criterion, so a
    // cached response would defeat the point.
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Feed fetch failed: ${res.status}`);
  }
  return res.json();
}
