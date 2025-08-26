export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export type Onboarding = {
  identity: { name: string; one_line?: string };
  intent: {
    problem_statement: string;
    north_star?: string;
    business_objectives?: string[];
    out_of_scope?: string[];
    top_use_cases?: { title: string; success_criteria?: string[] }[];
  };
  users: { personas: { name: string }[] };
  metrics: { primary_objectives: any[]; guardrails: any[] };
  delivery: { milestones: any[] };
  artifacts: {
    prds: string[];
    designs: string[];
    tech_docs: string[];
    data_schema?: { type: "link" | "inline"; value: string } | null;
  };
  derived: { confidence_index: number; next_best_actions: string[] };
};

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `HTTP ${res.status}`);
  }
  return (await res.json()) as T;
}

export async function listProjects() {
  return http<{ id: string; name: string; description?: string }[]>(`/projects`);
}
export async function createProject(name: string, description = "") {
  return http<{ id: string; name: string }>(`/projects`, {
    method: "POST",
    body: JSON.stringify({ name, description }),
  });
}
export async function getOnboarding(projectId: string) {
  return http<Onboarding>(`/projects/${projectId}/onboarding`);
}
export async function patchOnboarding(projectId: string, patch: Partial<Onboarding>) {
  return http<Onboarding>(`/projects/${projectId}/onboarding`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}
export async function commitOnboarding(projectId: string) {
  return http<Onboarding>(`/projects/${projectId}/onboarding/commit`, { method: "POST" });
}
