/**
 * Centralized API endpoint constants.
 * All backend paths live here — never hardcode strings in hooks or pages.
 */
export const API = {
  // Auth
  AUTH: {
    LOGIN: "/api/v1/auth/login",
    REGISTER: "/api/v1/auth/register",
    ME: "/api/v1/auth/me",
    REFRESH: "/api/v1/auth/refresh",
    LOGOUT: "/api/v1/auth/logout",
    FORGOT_PASSWORD: "/api/v1/auth/forgot-password",
    RESET_PASSWORD: "/api/v1/auth/reset-password",
    ACCEPT_INVITE: "/api/v1/auth/accept-invite",
  },

  // OIDC
  OIDC: {
    REDIRECT: "/api/v1/oidc/redirect",
    CALLBACK: "/api/v1/oidc/callback",
  },

  // Hosts
  HOSTS: {
    LIST: "/api/v1/hosts",
    CREATE: "/api/v1/hosts",
    DETAIL: (id: string) => `/api/v1/hosts/${id}`,
    RISK: (id: string) => `/api/v1/hosts/${id}/risk`,
    RISK_HISTORY: (id: string) => `/api/v1/hosts/${id}/risk/history`,
    ENROLLMENT_TOKEN: (id: string) => `/api/v1/hosts/${id}/enrollment-token`,
    REVOKE_TOKEN: (hostId: string, tokenId: string) => `/api/v1/hosts/${hostId}/tokens/${tokenId}`,
  },

  // Events
  EVENTS: {
    LIST: "/api/v1/events",
    TYPES: "/api/v1/events/types",
    EXPORT: "/api/v1/events/export",
  },

  // Alerts
  ALERTS: {
    LIST: "/api/v1/alerts",
    EXPORT: "/api/v1/alerts/export",
    STATUS: (id: string) => `/api/v1/alerts/${id}/status`,
    BULK: "/api/v1/alerts/bulk",
    TRIAGE: (id: string) => `/api/v1/alerts/${id}/triage`,
  },

  // Alert Rules
  ALERT_RULES: {
    LIST: "/api/v1/alert-rules",
    CREATE: "/api/v1/alert-rules",
    DETAIL: (id: string) => `/api/v1/alert-rules/${id}`,
    UPDATE: (id: string) => `/api/v1/alert-rules/${id}`,
    DELETE: (id: string) => `/api/v1/alert-rules/${id}`,
  },

  // Correlation Rules
  CORRELATION_RULES: {
    LIST: "/api/v1/correlation-rules",
    CREATE: "/api/v1/correlation-rules",
    DETAIL: (id: string) => `/api/v1/correlation-rules/${id}`,
    UPDATE: (id: string) => `/api/v1/correlation-rules/${id}`,
    DELETE: (id: string) => `/api/v1/correlation-rules/${id}`,
    VALIDATE: "/api/v1/correlation-rules/validate",
    PREVIEW: "/api/v1/correlation-rules/preview",
  },

  // Offenses
  OFFENSES: {
    LIST: "/api/v1/offenses",
    DETAIL: (id: string) => `/api/v1/offenses/${id}`,
    STATUS: (id: string) => `/api/v1/offenses/${id}/status`,
    PROMOTE: (id: string) => `/api/v1/offenses/${id}/promote-to-incident`,
    AI_BRIEF: (id: string) => `/api/v1/offenses/${id}/ai-brief`,
  },

  // Incidents
  INCIDENTS: {
    LIST: "/api/v1/incidents",
    CREATE: "/api/v1/incidents",
    DETAIL: (id: string) => `/api/v1/incidents/${id}`,
    STATUS: (id: string) => `/api/v1/incidents/${id}/status`,
    NOTES: (id: string) => `/api/v1/incidents/${id}/notes`,
  },

  // Investigation
  INVESTIGATION: {
    WORKSPACE: "/api/v1/investigation/workspace",
    TRAIL: (params: string) => `/api/v1/investigation/trail${params}`,
  },

  // Metrics
  METRICS: {
    HOST: (id: string) => `/api/v1/metrics/${id}`,
    HOST_HISTORY: (id: string) => `/api/v1/metrics/${id}/history`,
  },

  // Analytics / SIEM
  SIEM: {
    EXECUTIVE: "/api/v1/siem/executive",
    MITRE: "/api/v1/siem/mitre",
    HOST_HEALTH: "/api/v1/siem/host-health",
    EVENT_TREND: "/api/v1/siem/event-trend",
    ATTACK_TIMELINES: "/api/v1/siem/attack-timelines",
    TOP_RISKY_HOSTS: "/api/v1/siem/top-risky-hosts",
  },

  // Analytics
  ANALYTICS: {
    SUMMARY: "/api/v1/analytics/summary",
    UEBA_ANOMALIES: "/api/v1/analytics/ueba/anomalies",
    THREAT_SCORES: "/api/v1/analytics/threat-scores",
    RISK_TRENDS: "/api/v1/analytics/risk-trends",
  },

  // Threat Scores
  THREAT_SCORES: {
    RANKED: "/api/v1/threat-scores/ranked",
    HISTORY: (hostId: string) => `/api/v1/threat-scores/${hostId}/history`,
  },

  // Timeline
  TIMELINE: {
    LIST: "/api/v1/timeline",
    DETAIL: (id: string) => `/api/v1/timeline/${id}`,
    EVENTS: (id: string) => `/api/v1/timeline/${id}/events`,
  },

  // Search
  SEARCH: {
    QUERY: "/api/v1/search",
    GLOBAL: "/api/v1/search/global",
    SAVED: "/api/v1/saved-searches",
    SAVED_RUN: (id: string) => `/api/v1/saved-searches/${id}/run`,
  },

  // Simulation
  SIMULATION: {
    SCENARIOS: "/api/v1/simulation/scenarios",
    EVENT_TYPES: "/api/v1/simulation/event-types",
    RUN: (scenario: string) => `/api/v1/simulation/run/${scenario}`,
    CUSTOM: "/api/v1/simulation/custom",
    RUNS: "/api/v1/simulation/runs",
    RUN_DETAIL: (id: string) => `/api/v1/simulation/runs/${id}`,
    PURGE: "/api/v1/simulation/purge",
  },

  // Reports
  REPORTS: {
    TEMPLATES: "/api/v1/reports/templates",
    EXECUTIVE: "/api/v1/reports/executive",
    EXPORT: (id: string) => `/api/v1/reports/${id}/export`,
  },

  // Audit
  AUDIT: {
    LIST: "/api/v1/audit",
    VERIFY: "/api/v1/audit/verify",
  },

  // Network
  NETWORK: {
    FLOW: "/api/v1/network/flow",
  },

  // MITRE
  MITRE: {
    STATS: "/api/v1/mitre/stats",
    TECHNIQUE: (id: string) => `/api/v1/mitre/technique/${id}`,
  },

  // Notifications
  NOTIFICATIONS: {
    SETTINGS: "/api/v1/notifications/settings",
    HISTORY: "/api/v1/notifications/history",
    UNREAD: "/api/v1/notifications/unread-count",
    MARK_READ: (id: string) => `/api/v1/notifications/${id}/read`,
    MARK_ALL_READ: "/api/v1/notifications/read-all",
    TEST: "/api/v1/notifications/test",
  },

  // Settings
  SETTINGS: {
    PUBLIC: "/api/v1/settings/public",
    NOTIFICATION_RULES: "/api/v1/notification-rules",
    PLAYBOOKS: "/api/v1/playbooks",
  },

  // Users
  USERS: {
    LIST: "/api/v1/users",
    INVITE: "/api/v1/users/invite",
    MFA_ENABLE: "/api/v1/auth/mfa/enable",
    MFA_DISABLE: "/api/v1/auth/mfa/disable",
  },

  // Reference Sets
  REFERENCE_SETS: {
    LIST: "/api/v1/reference-sets",
  },

  // Building Blocks
  BUILDING_BLOCKS: {
    LIST: "/api/v1/building-blocks",
  },

  // IOCs
  IOC: {
    LOOKUP: "/api/v1/ioc/lookup",
  },

  // Assistant
  ASSISTANT: {
    ASK: "/api/v1/assistant/ask",
  },

  // System
  SYSTEM: {
    HEALTH: "/api/v1/system/health",
    BACKUPS: "/api/v1/backups",
    BACKUP_CONFIG: "/api/v1/backups/config",
    BACKUP_RUN: "/api/v1/backups/run",
  },

  // Telemetry
  TELEMETRY: {
    EVENT: "/api/v1/telemetry/events",
    FUNNEL: "/api/v1/telemetry/funnel",
  },

  // WebSocket
  WS: {
    TOKEN: "/api/v1/ws/token",
  },

  // Overview
  OVERVIEW: "/api/v1/overview",

  // Dashboard
  DASHBOARD: {
    LAYOUT: "/api/v1/dashboard/layout",
  },

  // Maintenance
  MAINTENANCE: {
    LIST: "/api/v1/maintenance-windows",
  },

  // Agent
  AGENT: {
    EVENTS: "/api/v1/agent/events",
    METRICS: "/api/v1/agent/metrics",
    HEARTBEAT: "/api/v1/agent/heartbeat",
  },

  // Health
  HEALTH: {
    LIVE: "/health/live",
    READY: "/health/ready",
    STARTUP: "/health/startup",
  },
} as const;
