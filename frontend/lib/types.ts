export type Persona = "student" | "faculty" | "tpo";

export interface SessionUser {
  id: number;
  name: string;
  email: string;
  role: string;
  persona: Persona;
  avatar_initials: string;
  program: string;
}

export interface LoginResult {
  token: string;
  expires_at: string;
  user: SessionUser;
}
export type Status = "BACKLOG" | "IN_PROGRESS" | "AI_REVIEW" | "MASTERED";
export type View = "dashboard" | "board" | "skills" | "placement" | "signals" | "faculty" | "tpo" | "security";

export interface Actor {
  id: number;
  name: string;
  role: string;
  department: string;
  semester: number;
  avatar_initials: string;
  anon_token: string;
  program: string;
  cgpa: number;
}

export interface Sprint {
  id: number;
  title: string;
  course_code: string;
  start_date: string;
  end_date: string;
  co_po_tags: string[];
  kind: string;
  lwi_count: number;
  mastered_count: number;
  progress_percent: number;
}

export interface LWI {
  id: number;
  sprint_id: number;
  student_id: number;
  ticket_code: string;
  title: string;
  description: string;
  type: string;
  status: Status;
  story_points: number;
  skill_tag: string;
  prerequisite_id: number | null;
  prerequisite_code: string | null;
  prerequisite_title: string | null;
  blocked: boolean;
  block_reason: string | null;
  co_tag: string;
  rubric_criteria: string[];
  ai_feedback: Record<string, unknown> | null;
  cosigned_by_id?: number | null;
  cosigned_at?: string | null;
}

export interface ChainNode {
  id: number;
  ticket_code: string;
  title: string;
  status: string;
  blocked: boolean;
}

export interface LWIDetail extends LWI {
  prerequisite_chain: ChainNode[];
  dependents: ChainNode[];
}

export interface GuardMeta {
  redactions: number;
  redaction_types: string[];
  injection_flags: string[];
  transport: string;
  schema_valid: boolean;
}

export interface RubricCheck {
  criterion: string;
  passed: boolean;
  note: string;
}

export interface EvaluationResult {
  refused_direct_solution: boolean;
  diagnosed_gap: string;
  guiding_question: string;
  readiness_score: number | null;
  checks: RubricCheck[];
  actionable_fixes: string[];
  remediation_title: string | null;
}

export interface Skill {
  id: number;
  skill_name: string;
  proficiency_score: number;
  verified_lwi_count: number;
  evidence_tickets: string[];
  evidence_hash: string;
  last_updated: string;
}

export interface AIAction {
  result: EvaluationResult;
  lwi: LWI;
  remediation_lwi: LWI | null;
  skills: Skill[];
  guard: GuardMeta;
}

export interface SkillGraph {
  student_id: number;
  student_name: string;
  anon_token: string;
  verified_skill_score: number;
  skills: Skill[];
}

export interface Bootstrap {
  actor: Actor;
  institution: { university: string; college: string; department: string };
  semester_label: string;
  semester_progress: number;
  sprints: Sprint[];
  ai_mode: string;
  security: Record<string, string | boolean>;
  signal_unread: number;
  signal_next_poll: string | null;
}

export interface GenerateResponse {
  sprint: Sprint;
  items: LWI[];
  guard: GuardMeta;
}

export interface JDResponse {
  role_title: string;
  match_percent: number;
  matched_skills: string[];
  missing_skills: string[];
  summary: string;
  sprint: Sprint;
  items: LWI[];
  guard: GuardMeta;
}

export interface CohortStudent {
  id: number;
  name: string;
  avatar_initials: string;
  semester: number;
  cgpa: number;
  velocity_drop_pct: number;
  blocked_core: number;
  at_risk: boolean;
  risk_reasons: string[];
  top_gap: string | null;
  anon_token: string;
  verified_skill_score: number;
}

export interface CohortHealth {
  cohort_size: number;
  at_risk_count: number;
  avg_velocity_drop: number;
  avg_verified_skill: number;
  students: CohortStudent[];
}

export interface ReadinessRow {
  id: number;
  name: string;
  avatar_initials: string;
  program: string;
  cgpa: number;
  verified_skill_score: number;
  verified_lwi_count: number;
  top_skills: string[];
  evidence_hashes: string[];
  shortlist: boolean;
}

export interface ReadinessMatrix {
  rows: ReadinessRow[];
  threshold: number;
}

export interface AuditEvent {
  action: string;
  detail: string;
  actor_role: string;
  created_at: string;
}

export interface Posture {
  ai_mode: string;
  controls: { name: string; detail: string }[];
  recent_audit: AuditEvent[];
}

export interface Preview {
  redacted_text: string;
  redaction_count: number;
  redaction_types: string[];
  injection_flags: string[];
  wrapped_preview: string;
}

export interface SignalMessage {
  id: number;
  title: string;
  url: string;
  source: string;
  published_at: string;
  summary: string;
  brief: string;
  brief_source: string;
  subscription_id: number;
  relevance_score: number;
  relevance_reason: string;
  sentiment: string;
  sentiment_score: number;
  sentiment_reason: string;
  cluster_label: string;
  is_read: boolean;
  created_at: string;
  sources: { source: string; url: string }[];
  badges: StoryBadge[];
  task_lwi_id: number | null;
  quiz_passed: boolean;
  sample?: boolean;
}

export interface ReviewTicket {
  id: number;
  student_id: number;
  student_name: string;
  ticket_code: string;
  title: string;
  skill_tag: string;
  readiness_score: number | null;
  status: string;
}

export interface StoryBadge {
  kind: "task" | "ticket" | "gap" | "placement" | "skill" | string;
  label: string;
  detail: string;
}

export interface StoryTask {
  lwi: LWI;
  sprint: Sprint;
  created: boolean;
  transport: string;
}

export interface StoryExplainer {
  concept: string;
  use_case: string;
  question: string;
  options: string[];
  source: string;
  quiz_passed: boolean;
}

export interface QuizResult {
  correct: boolean;
  why: string;
  xp_awarded: number;
  skill: string | null;
  skill_score: number | null;
  already_passed: boolean;
}

export interface DriftRadar {
  total_stories: number;
  students: number;
  trends: { term: string; stories: number; share: number; in_syllabus: boolean; suggestion: string }[];
  alerts: { level: "watch" | "critical" | string; title: string; detail: string }[];
  subtopics: { label: string; count: number; critical: number; positive: number; watchful: number }[];
}

export interface SignalCluster {
  label: string;
  count: number;
  unread: number;
  dominant_sentiment: string;
  sentiments: Record<string, number>;
}

export interface SignalFeed {
  id: number;
  label: string;
  url: string;
  last_polled_at: string | null;
  next_poll_at: string | null;
  last_status: string;
  last_error: string;
  items_seen: number;
  items_kept: number;
}

export interface SignalInbox {
  unread: number;
  feeds: SignalFeed[];
  clusters: SignalCluster[];
  messages: SignalMessage[];
  pipeline: string[];
}

export interface SentimentRow {
  id: number;
  title: string;
  source: string;
  published_at: string;
  sentiment: string;
  sentiment_score: number;
  relevance_score: number;
  topic: string;
  is_read: boolean;
}

export interface InterestCluster {
  label: string;
  count: number;
  average_sentiment: number;
  dominant_sentiment: string;
  sentiments: Record<string, number>;
  keywords: string[];
  story_ids: number[];
}

export interface InterestAnalysis {
  feed: SignalFeed;
  total: number;
  average_sentiment: number;
  average_relevance: number;
  sentiments: Record<string, number>;
  rows: SentimentRow[];
  clusters: InterestCluster[];
}

export interface Dashboard {
  student: {
    name: string;
    anon_token: string;
    program: string;
    semester: number;
    cgpa: number;
    avatar_initials: string;
  };
  semester_progress: number;
  verified_skill_score: number;
  shortlist_ready: boolean;
  shortlist_bar: number;
  tickets: {
    total: number;
    backlog: number;
    in_progress: number;
    ai_review: number;
    mastered: number;
    blocked: number;
    points_total: number;
    points_mastered: number;
  };
  sprints: Sprint[];
  skills: { count: number; top: { name: string; score: number }[]; weakest: { name: string; score: number } | null };
  interests: {
    topics: number;
    saved: number;
    unread: number;
    sentiments: Record<string, number>;
    next_fetch: string | null;
    latest: { id: number; title: string; sentiment: string; topic: string; is_read: boolean }[];
  };
  next_actions: { kind: string; title: string; detail: string; view: View }[];
  activity: AuditEvent[];
}

export interface SignalPulse {
  clusters: SignalCluster[];
  message_count: number;
}

export interface SubscribeResult {
  feed: SignalFeed;
  seen: number;
  kept: number;
  held: number;
  fused: number;
  next_poll_at: string | null;
}

export interface AIJob {
  id: number;
  title: string;
  steps: string[];
  active: number;
  done: boolean;
  foot: string;
}
