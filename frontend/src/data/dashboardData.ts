import type { DashboardStats } from '@/types/dashboard';

export const MOCK_DASHBOARD_DATA: DashboardStats = {
  incidents: {
    open: 11,
    critical: 5,
    bySeverity: { P1: 5, P2: 6 },
    latest: {
      id: 1,
      title: 'SSO authentication failure',
      severity: 'P1',
      status: 'Investigating',
      service: 'Authentication Service',
      created_at: '2024-08-21T00:00:00',
    },
    list: [
      { id: 1, title: 'Privilege escalation vulnerability in TechCorp AI Core', severity: 'P2', status: 'Investigating', service: 'AI Core', created_at: '2025-05-24T00:00:00' },
      { id: 2, title: 'DDoS mitigation triggered on tenant', severity: 'P2', status: 'Investigating', service: 'Network Security', created_at: '2025-04-05T00:00:00' },
      { id: 3, title: 'API rate limiting incorrectly applied to internal services', severity: 'P2', status: 'In Progress', service: 'API Gateway', created_at: '2025-04-04T00:00:00' },
      { id: 4, title: 'Cross-region failover not triggering for APAC customers', severity: 'P1', status: 'In Progress', service: 'Infrastructure', created_at: '2025-02-15T00:00:00' },
      { id: 5, title: 'Email notification pipeline down since deployment', severity: 'P1', status: 'In Progress', service: 'Notifications', created_at: '2025-02-05T00:00:00' },
      { id: 6, title: 'CustomerIQ ML inference pipeline returning stale predictions', severity: 'P1', status: 'In Progress', service: 'ML Pipeline', created_at: '2025-01-08T00:00:00' },
      { id: 7, title: 'DDoS mitigation triggered on TechBridge Solutions tenant', severity: 'P2', status: 'In Progress', service: 'Network Security', created_at: '2024-10-14T00:00:00' },
      { id: 8, title: 'Database replication lag causing read inconsistencies', severity: 'P2', status: 'In Progress', service: 'Database', created_at: '2024-08-23T00:00:00' },
      { id: 9, title: 'SSO authentication failure for Singapore Health Systems', severity: 'P1', status: 'Investigating', service: 'Authentication Service', created_at: '2024-08-21T00:00:00' },
      { id: 10, title: 'SSO authentication failure', severity: 'P1', status: 'Investigating', service: 'Authentication Service', created_at: '2024-07-16T00:00:00' },
    ],
  },
  tickets: {
    open: 57,
    inProgress: 88,
    closed: 207,
    resolved: 48,
  },
  projects: {
    active: 12,
    onHold: 6,
    completed: 7,
    list: [
      { id: 1, name: 'Internal Knowledge Graph Build', status: 'In Progress', owner: 'Yuki Okafor', progress: 65, dueDate: '2025-08-15' },
      { id: 2, name: 'Identity Access Management Overhaul', status: 'In Progress', owner: 'Fatima Kowalski', progress: 50, dueDate: '2025-09-01' },
      { id: 3, name: 'Vendor Risk Assessment', status: 'In Progress', owner: 'Hiroshi Williams', progress: 70, dueDate: '2025-07-30' },
      { id: 4, name: 'Chatbot Intent Expansion', status: 'In Progress', owner: 'Yuki Okafor', progress: 55, dueDate: '2025-08-20' },
      { id: 5, name: 'Marketing Attribution Model', status: 'In Progress', owner: 'Sofia Tanaka', progress: 40, dueDate: '2025-10-01' },
      { id: 6, name: 'Platform Scalability Benchmark', status: 'In Progress', owner: 'Hiroshi Tanaka', progress: 75, dueDate: '2025-07-15' },
      { id: 7, name: 'Data Lake Migration', status: 'Planning', owner: 'Priya Novak', progress: 10, dueDate: '2025-12-01' },
      { id: 8, name: 'Real-Time Analytics Dashboard', status: 'Planning', owner: 'Thabo Kowalski', progress: 15, dueDate: '2025-11-15' },
      { id: 9, name: 'Sales Forecasting Pipeline', status: 'Planning', owner: 'Wei Rossi', progress: 8, dueDate: '2025-12-20' },
      { id: 10, name: 'Sentiment Analysis Pipeline', status: 'Planning', owner: 'Yuki Bauer', progress: 20, dueDate: '2025-10-30' },
      { id: 11, name: 'CRM Data Quality Initiative', status: 'Planning', owner: 'Carlos Rodriguez', progress: 5, dueDate: '2026-01-15' },
      { id: 12, name: 'Threat Detection Upgrade', status: 'Planning', owner: 'Olga Rahman', progress: 12, dueDate: '2025-11-01' },
      { id: 13, name: 'Customer Onboarding Portal', status: 'On Hold', owner: 'Diego Andersson', progress: 35, dueDate: null },
      { id: 14, name: 'AI Model Fine-Tuning Sprint', status: 'On Hold', owner: 'Samuel Lee', progress: 45, dueDate: null },
      { id: 15, name: 'Automated Testing Framework', status: 'On Hold', owner: 'Arjun Patel', progress: 30, dueDate: null },
      { id: 16, name: 'Cloud Cost Optimization', status: 'On Hold', owner: 'Sana Santos', progress: 55, dueDate: null },
      { id: 17, name: 'Disaster Recovery Drill', status: 'On Hold', owner: 'Nia Rossi', progress: 25, dueDate: null },
      { id: 18, name: 'Multi-Region Deployment', status: 'On Hold', owner: 'Hiroshi Okafor', progress: 40, dueDate: null },
    ],
  },
  subscriptions: {
    active: 62,
    trial: 8,
    cancelled: 11,
    expired: 5,
    total: 86,
  },
  employees: {
    total: 149,
    departments: 11,
    departmentNames: [
      'AI', 'Customer Support', 'Engineering', 'Finance', 'HR',
      'IT', 'Legal', 'Marketing', 'Operations', 'Sales', 'Security',
    ],
  },
  activities: [
    {
      id: 1,
      type: 'employee',
      icon: 'UserPlus',
      title: 'New employee onboarded',
      description: 'Linh Dubois joined the Engineering department',
      timestamp: '2024-10-01T09:00:00',
    },
    {
      id: 2,
      type: 'project',
      icon: 'CheckCircle',
      title: 'Project completed',
      description: 'Data Export Service Enhancement delivered ahead of schedule',
      timestamp: '2025-06-20T16:30:00',
    },
    {
      id: 3,
      type: 'ticket',
      icon: 'Ticket',
      title: 'Ticket resolved',
      description: 'Cannot reset password for admin account — resolved by Support team',
      timestamp: '2025-06-20T14:00:00',
    },
    {
      id: 4,
      type: 'subscription',
      icon: 'CreditCard',
      title: 'New subscription activated',
      description: 'TechBridge Solutions upgraded to Enterprise plan',
      timestamp: '2025-06-19T11:00:00',
    },
    {
      id: 5,
      type: 'incident',
      icon: 'ShieldCheck',
      title: 'Incident resolved',
      description: 'SSO authentication failure — root cause identified and fixed',
      timestamp: '2025-06-18T08:15:00',
    },
    {
      id: 6,
      type: 'incident',
      icon: 'ShieldCheck',
      title: 'Incident resolved',
      description: 'Email notification pipeline restored after deployment rollback',
      timestamp: '2025-06-17T11:20:00',
    },
    {
      id: 7,
      type: 'employee',
      icon: 'UserPlus',
      title: 'New employee onboarded',
      description: 'Thabo Kim joined the AI department',
      timestamp: '2024-08-15T09:00:00',
    },
    {
      id: 8,
      type: 'ticket',
      icon: 'Ticket',
      title: 'Ticket resolved',
      description: 'Audit log missing entries — schema fix deployed',
      timestamp: '2025-06-15T10:30:00',
    },
    {
      id: 9,
      type: 'project',
      icon: 'CheckCircle',
      title: 'Project milestone reached',
      description: 'Platform Scalability Benchmark completed performance testing phase',
      timestamp: '2025-06-14T15:00:00',
    },
    {
      id: 10,
      type: 'subscription',
      icon: 'CreditCard',
      title: 'Trial converted',
      description: 'FinEdge Analytics converted from trial to active subscription',
      timestamp: '2025-06-12T09:45:00',
    },
  ],
  itemsNeedAttention: 68,
  projectsInFlight: 12,
};

// ── Full lists for section pages ─────────────────────────────────

export interface FullIncident {
  severity: string;
  title: string;
  status: string;
  service: string;
  created_at: string;
}

export const ALL_INCIDENTS: FullIncident[] = [
  { severity: 'P1', title: 'SSO authentication failure for', status: 'Closed', service: 'Authentication Service', created_at: '2025-06-17' },
  { severity: 'P1', title: 'Email notification pipeline down since deployment', status: 'Closed', service: 'Notifications', created_at: '2025-06-15' },
  { severity: 'P2', title: 'Privilege escalation vulnerability in TechCorp AI Core', status: 'Resolved', service: 'Platform', created_at: '2025-06-02' },
  { severity: 'P3', title: 'Data export service degradation', status: 'Closed', service: 'Data Export', created_at: '2025-05-24' },
  { severity: 'P2', title: 'Privilege escalation vulnerability in TechCorp AI Core', status: 'Investigating', service: 'Platform', created_at: '2025-05-24' },
  { severity: 'P2', title: 'DDoS mitigation triggered on Andean Commodities SA tenant', status: 'Resolved', service: 'Network Security', created_at: '2025-05-21' },
  { severity: 'P2', title: 'API rate limiting incorrectly applied to internal services', status: 'Resolved', service: 'API Gateway', created_at: '2025-05-21' },
  { severity: 'P2', title: 'DDoS mitigation triggered on tenant', status: 'Closed', service: 'Network Security', created_at: '2025-05-18' },
  { severity: 'P2', title: 'DDoS mitigation triggered on MediCare Plus tenant', status: 'Closed', service: 'Network Security', created_at: '2025-05-15' },
  { severity: 'P2', title: 'Database replication lag causing read inconsistencies', status: 'Closed', service: 'Database', created_at: '2025-04-30' },
  { severity: 'P2', title: 'API rate limiting incorrectly applied to internal services', status: 'Resolved', service: 'API Gateway', created_at: '2025-04-27' },
  { severity: 'P1', title: 'DataVault Backup ML inference pipeline returning stale predictions', status: 'Closed', service: 'ML Pipeline', created_at: '2025-04-12' },
  { severity: 'P2', title: 'API rate limiting incorrectly applied to internal services', status: 'Resolved', service: 'API Gateway', created_at: '2025-04-08' },
  { severity: 'P1', title: 'SSO authentication failure for', status: 'Closed', service: 'Authentication Service', created_at: '2025-04-06' },
  { severity: 'P2', title: 'DDoS mitigation triggered on Sunrise Medical Devices tenant', status: 'Resolved', service: 'Network Security', created_at: '2025-04-05' },
  { severity: 'P2', title: 'DDoS mitigation triggered on tenant', status: 'Investigating', service: 'Network Security', created_at: '2025-04-05' },
  { severity: 'P2', title: 'API rate limiting incorrectly applied to internal services', status: 'In Progress', service: 'API Gateway', created_at: '2025-04-04' },
  { severity: 'P1', title: 'CustomerIQ ML inference pipeline returning stale predictions', status: 'Closed', service: 'ML Pipeline', created_at: '2025-03-30' },
  { severity: 'P1', title: 'SSO authentication failure for', status: 'Closed', service: 'Authentication Service', created_at: '2025-03-15' },
  { severity: 'P1', title: 'Email notification pipeline down since deployment', status: 'Resolved', service: 'Notifications', created_at: '2025-03-11' },
  { severity: 'P2', title: 'Database replication lag causing read inconsistencies', status: 'Resolved', service: 'Database', created_at: '2025-03-07' },
  { severity: 'P1', title: 'Email notification pipeline down since deployment', status: 'Resolved', service: 'Notifications', created_at: '2025-02-26' },
  { severity: 'P1', title: 'Cross-region failover not triggering for APAC customers', status: 'In Progress', service: 'Infrastructure', created_at: '2025-02-15' },
  { severity: 'P2', title: 'Database replication lag causing read inconsistencies', status: 'Resolved', service: 'Database', created_at: '2025-02-11' },
  { severity: 'P1', title: 'Cross-region failover not triggering for APAC customers', status: 'Resolved', service: 'Infrastructure', created_at: '2025-02-10' },
  { severity: 'P1', title: 'Email notification pipeline down since deployment', status: 'In Progress', service: 'Notifications', created_at: '2025-02-05' },
  { severity: 'P1', title: 'SSO authentication failure for Northern Trust Bank', status: 'Resolved', service: 'Authentication Service', created_at: '2025-02-05' },
  { severity: 'P1', title: 'CustomerIQ ML inference pipeline returning stale predictions', status: 'Resolved', service: 'ML Pipeline', created_at: '2025-02-01' },
  { severity: 'P1', title: 'SSO authentication failure for', status: 'Closed', service: 'Authentication Service', created_at: '2025-01-25' },
  { severity: 'P1', title: 'Email notification pipeline down since deployment', status: 'Resolved', service: 'Notifications', created_at: '2025-01-18' },
  { severity: 'P1', title: 'CustomerIQ ML inference pipeline returning stale predictions', status: 'In Progress', service: 'ML Pipeline', created_at: '2025-01-08' },
  { severity: 'P3', title: 'Data export service degradation', status: 'Resolved', service: 'Data Export', created_at: '2025-01-06' },
  { severity: 'P3', title: 'Data export service degradation', status: 'Closed', service: 'Data Export', created_at: '2025-01-02' },
  { severity: 'P3', title: 'Data export service degradation', status: 'Resolved', service: 'Data Export', created_at: '2024-12-26' },
  { severity: 'P1', title: 'SSO authentication failure for Northern Trust Bank', status: 'Resolved', service: 'Authentication Service', created_at: '2024-12-01' },
  { severity: 'P1', title: 'SSO authentication failure for InnoSys Dynamics', status: 'Resolved', service: 'Authentication Service', created_at: '2024-11-25' },
  { severity: 'P2', title: 'DDoS mitigation triggered on tenant', status: 'Resolved', service: 'Network Security', created_at: '2024-11-23' },
  { severity: 'P2', title: 'InsightFlow Analytics dashboard latency exceeding SLA', status: 'Closed', service: 'Analytics', created_at: '2024-11-13' },
  { severity: 'P2', title: 'Database replication lag causing read inconsistencies', status: 'Resolved', service: 'Database', created_at: '2024-11-07' },
  { severity: 'P2', title: 'DDoS mitigation triggered on TechBridge Solutions tenant', status: 'In Progress', service: 'Network Security', created_at: '2024-10-14' },
  { severity: 'P2', title: 'Privilege escalation vulnerability in TechCorp AI Core', status: 'Closed', service: 'Platform', created_at: '2024-10-11' },
  { severity: 'P2', title: 'Privilege escalation vulnerability in TechCorp AI Core', status: 'Resolved', service: 'Platform', created_at: '2024-10-03' },
  { severity: 'P1', title: 'SSO authentication failure for', status: 'Resolved', service: 'Authentication Service', created_at: '2024-09-26' },
  { severity: 'P1', title: 'Cross-region failover not triggering for APAC customers', status: 'Closed', service: 'Infrastructure', created_at: '2024-09-25' },
  { severity: 'P1', title: 'Email notification pipeline down since deployment', status: 'Resolved', service: 'Notifications', created_at: '2024-09-25' },
  { severity: 'P2', title: 'DDoS mitigation triggered on NovaTech Innovations tenant', status: 'Resolved', service: 'Network Security', created_at: '2024-09-24' },
  { severity: 'P1', title: 'SSO authentication failure for Sunrise Medical Devices', status: 'Resolved', service: 'Authentication Service', created_at: '2024-09-21' },
  { severity: 'P1', title: 'Cross-region failover not triggering for APAC customers', status: 'Closed', service: 'Infrastructure', created_at: '2024-09-14' },
  { severity: 'P2', title: 'API rate limiting incorrectly applied to internal services', status: 'Resolved', service: 'API Gateway', created_at: '2024-09-06' },
  { severity: 'P1', title: 'SSO authentication failure for Sunrise Medical Devices', status: 'Resolved', service: 'Authentication Service', created_at: '2024-09-05' },
  { severity: 'P2', title: 'Database replication lag causing read inconsistencies', status: 'In Progress', service: 'Database', created_at: '2024-08-23' },
  { severity: 'P3', title: 'Data export service degradation', status: 'Resolved', service: 'Data Export', created_at: '2024-08-21' },
  { severity: 'P1', title: 'SSO authentication failure for Singapore Health Systems', status: 'Investigating', service: 'Authentication Service', created_at: '2024-08-21' },
  { severity: 'P3', title: 'Data export service degradation', status: 'Resolved', service: 'Data Export', created_at: '2024-08-14' },
  { severity: 'P2', title: 'Database replication lag causing read inconsistencies', status: 'Resolved', service: 'Database', created_at: '2024-08-10' },
  { severity: 'P1', title: 'Email notification pipeline down since deployment', status: 'Resolved', service: 'Notifications', created_at: '2024-07-29' },
  { severity: 'P2', title: 'Privilege escalation vulnerability in TechCorp AI Core', status: 'Resolved', service: 'Platform', created_at: '2024-07-23' },
  { severity: 'P2', title: 'API rate limiting incorrectly applied to internal services', status: 'Closed', service: 'API Gateway', created_at: '2024-07-18' },
  { severity: 'P1', title: 'SSO authentication failure for', status: 'Investigating', service: 'Authentication Service', created_at: '2024-07-16' },
  { severity: 'P2', title: 'Database replication lag causing read inconsistencies', status: 'In Progress', service: 'Database', created_at: '2024-07-06' },
];

export interface FullTicket {
  priority: string;
  subject: string;
  status: string;
  created_date: string;
}

export const ALL_TICKETS: FullTicket[] = [
  { priority: 'Medium', subject: 'Email notification not triggering', status: 'Open', created_date: '2025-06-27' },
  { priority: 'Low', subject: 'CSV import silently dropping non-ASCII characters', status: 'Open', created_date: '2025-06-26' },
  { priority: 'Low', subject: 'Data export exceeds 100k row limit', status: 'Open', created_date: '2025-06-22' },
  { priority: 'Low', subject: 'Cannot reset password for admin account', status: 'Resolved', created_date: '2025-06-20' },
  { priority: 'Critical', subject: 'Audit log missing entries for last week', status: 'Open', created_date: '2025-06-18' },
  { priority: 'Medium', subject: 'Session timeout values not respecting admin settings', status: 'Closed', created_date: '2025-06-17' },
  { priority: 'Medium', subject: 'Missing data in weekly analytics report', status: 'Closed', created_date: '2025-06-16' },
  { priority: 'Low', subject: 'Session timeout values not respecting admin settings', status: 'Closed', created_date: '2025-06-15' },
  { priority: 'Medium', subject: 'Custom domain SSL certificate verification failing', status: 'Closed', created_date: '2025-06-11' },
  { priority: 'High', subject: 'Unable to add new team members', status: 'Closed', created_date: '2025-06-11' },
  { priority: 'Low', subject: 'API rate limit exceeded during peak hours', status: 'Closed', created_date: '2025-06-08' },
  { priority: 'Low', subject: 'Report generation timed out', status: 'Closed', created_date: '2025-05-29' },
  { priority: 'High', subject: 'Dashboard widget configuration reset', status: 'Closed', created_date: '2025-05-28' },
  { priority: 'Low', subject: 'Session timeout values not respecting admin settings', status: 'Open', created_date: '2025-05-27' },
  { priority: 'High', subject: 'Search returning incomplete results', status: 'Open', created_date: '2025-05-20' },
  { priority: 'Medium', subject: 'Email notification not triggering', status: 'Closed', created_date: '2025-05-19' },
  { priority: 'Low', subject: 'SSO certificate about to expire', status: 'Closed', created_date: '2025-05-15' },
  { priority: 'Medium', subject: 'Scheduled task not executing', status: 'Closed', created_date: '2025-05-14' },
  { priority: 'Medium', subject: 'Data sync delay between modules', status: 'Closed', created_date: '2025-05-13' },
  { priority: 'Medium', subject: 'Bulk user import failed with validation errors', status: 'Resolved', created_date: '2025-05-13' },
];

export interface FullProject {
  name: string;
  owner: string;
  status: string;
  progress: number;
  dueDate: string | null;
}

export const ALL_PROJECTS: FullProject[] = [
  { name: 'Deploy RAG Pipeline v2', owner: 'Kwame Bauer', status: 'Completed', progress: 100, dueDate: '2023-03-19' },
  { name: 'Invoice Processing Automation', owner: 'Leila Gupta', status: 'Completed', progress: 100, dueDate: '2025-02-25' },
  { name: 'Q3 Security Audit', owner: 'Chen Kowalski', status: 'Completed', progress: 100, dueDate: '2025-05-29' },
  { name: 'Compliance Automation Initiative', owner: 'Jin Nakamura', status: 'Completed', progress: 100, dueDate: '2024-07-10' },
  { name: 'Employee Onboarding Automation', owner: 'Yuki Okafor', status: 'Completed', progress: 100, dueDate: '2024-02-11' },
  { name: 'Self-Service Support Portal', owner: 'Chen Okafor', status: 'Completed', progress: 100, dueDate: '2023-06-21' },
  { name: 'Partner API Gateway', owner: 'Isabella Ali', status: 'Completed', progress: 100, dueDate: '2023-09-25' },
  { name: 'Chatbot Intent Expansion', owner: 'Yuki Okafor', status: 'In Progress', progress: 55, dueDate: null },
  { name: 'Vendor Risk Assessment', owner: 'Hiroshi Williams', status: 'In Progress', progress: 70, dueDate: null },
  { name: 'Marketing Attribution Model', owner: 'Sofia Tanaka', status: 'In Progress', progress: 40, dueDate: null },
  { name: 'Platform Scalability Benchmark', owner: 'Hiroshi Tanaka', status: 'In Progress', progress: 75, dueDate: null },
  { name: 'Internal Knowledge Graph Build', owner: 'Yuki Okafor', status: 'In Progress', progress: 65, dueDate: null },
  { name: 'Identity Access Management Overhaul', owner: 'Fatima Kowalski', status: 'In Progress', progress: 50, dueDate: null },
  { name: 'Automated Testing Framework', owner: 'Arjun Patel', status: 'On Hold', progress: 30, dueDate: null },
  { name: 'Disaster Recovery Drill', owner: 'Nia Rossi', status: 'On Hold', progress: 25, dueDate: null },
  { name: 'Multi-Region Deployment', owner: 'Hiroshi Okafor', status: 'On Hold', progress: 40, dueDate: null },
  { name: 'AI Model Fine-Tuning Sprint', owner: 'Samuel Lee', status: 'On Hold', progress: 45, dueDate: null },
  { name: 'Customer Onboarding Portal', owner: 'Diego Andersson', status: 'On Hold', progress: 35, dueDate: null },
  { name: 'Cloud Cost Optimization', owner: 'Sana Santos', status: 'On Hold', progress: 55, dueDate: null },
  { name: 'Sales Forecasting Pipeline', owner: 'Wei Rossi', status: 'Planning', progress: 8, dueDate: null },
  { name: 'Real-Time Analytics Dashboard', owner: 'Thabo Kowalski', status: 'Planning', progress: 15, dueDate: null },
  { name: 'Sentiment Analysis Pipeline', owner: 'Yuki Bauer', status: 'Planning', progress: 20, dueDate: null },
  { name: 'Data Lake Migration', owner: 'Priya Novak', status: 'Planning', progress: 10, dueDate: null },
  { name: 'CRM Data Quality Initiative', owner: 'Carlos Rodriguez', status: 'Planning', progress: 5, dueDate: null },
  { name: 'Threat Detection Upgrade', owner: 'Olga Rahman', status: 'Planning', progress: 12, dueDate: null },
];

export interface FullSubscription {
  plan: string;
  status: string;
  seats: number;
  start_date: string;
}

export const ALL_SUBSCRIPTIONS: FullSubscription[] = [
  { plan: 'Sentinel Security Suite', status: 'Active', seats: 440, start_date: '2022-05-04' },
  { plan: 'InsightFlow Analytics', status: 'Active', seats: 91, start_date: '2023-03-02' },
  { plan: 'CustomerIQ', status: 'Active', seats: 130, start_date: '2022-11-18' },
  { plan: 'Sentinel Security Suite', status: 'Active', seats: 168, start_date: '2024-07-11' },
  { plan: 'DataVault Backup', status: 'Active', seats: 43, start_date: '2024-07-18' },
  { plan: 'InsightFlow Analytics', status: 'Active', seats: 38, start_date: '2023-02-10' },
  { plan: 'InsightFlow Analytics', status: 'Active', seats: 354, start_date: '2022-10-19' },
  { plan: 'CustomerIQ', status: 'Active', seats: 99, start_date: '2022-09-12' },
  { plan: 'InsightFlow Analytics', status: 'Active', seats: 66, start_date: '2023-07-12' },
  { plan: 'TeamSync Collaboration', status: 'Cancelled', seats: 42, start_date: '2022-03-23' },
  { plan: 'InsightFlow Analytics', status: 'Trial', seats: 345, start_date: '2022-02-12' },
  { plan: 'TechCorp AI Core', status: 'Active', seats: 142, start_date: '2024-08-21' },
  { plan: 'Sentinel Security Suite', status: 'Active', seats: 52, start_date: '2022-07-06' },
  { plan: 'CustomerIQ', status: 'Cancelled', seats: 98, start_date: '2022-08-03' },
  { plan: 'TeamSync Collaboration', status: 'Expired', seats: 80, start_date: '2023-08-14' },
  { plan: 'TeamSync Collaboration', status: 'Active', seats: 6, start_date: '2022-06-30' },
  { plan: 'Sentinel Security Suite', status: 'Cancelled', seats: 11, start_date: '2024-11-19' },
  { plan: 'TechCorp AI Core', status: 'Active', seats: 73, start_date: '2024-11-27' },
  { plan: 'InsightFlow Analytics', status: 'Active', seats: 80, start_date: '2024-06-24' },
  { plan: 'TeamSync Collaboration', status: 'Active', seats: 459, start_date: '2022-09-06' },
];

export interface DepartmentInfo {
  name: string;
  headcount: number;
}

export const ALL_DEPARTMENTS: DepartmentInfo[] = [
  { name: 'AI', headcount: 14 },
  { name: 'Customer Support', headcount: 15 },
  { name: 'Engineering', headcount: 14 },
  { name: 'Finance', headcount: 15 },
  { name: 'HR', headcount: 13 },
  { name: 'IT', headcount: 14 },
  { name: 'Legal', headcount: 12 },
  { name: 'Marketing', headcount: 12 },
  { name: 'Operations', headcount: 12 },
  { name: 'Sales', headcount: 13 },
  { name: 'Security', headcount: 15 },
];

/** Map from the API response shape to DashboardStats */
export function transformApiResponse(api: Record<string, unknown>): DashboardStats {
  const incidents = api.incidents as Record<string, unknown> || {};
  const tickets = api.tickets as Record<string, unknown> || {};
  const projects = api.projects as Record<string, unknown> || {};
  const subscriptions = api.subscriptions as Record<string, unknown> || {};
  const employees = api.employees as Record<string, unknown> || {};

  return {
    incidents: {
      open: (incidents.open as number) || 0,
      critical: (incidents.critical as number) || 0,
      bySeverity: (incidents.bySeverity as Record<string, number>) || {},
      latest: (incidents.latest as MOCK_DASHBOARD_DATA['incidents']['latest']) || null,
      list: (incidents.list as MOCK_DASHBOARD_DATA['incidents']['list']) || [],
    },
    tickets: {
      open: (tickets.Open as number) || (tickets.open as number) || 0,
      inProgress: (tickets['In Progress'] as number) || (tickets.inProgress as number) || 0,
      closed: (tickets.Closed as number) || (tickets.closed as number) || 0,
      resolved: (tickets.Resolved as number) || (tickets.resolved as number) || 0,
    },
    projects: {
      active: ((projects['In Progress'] as number) || 0) + ((projects.Planning as number) || 0) + ((projects.active as number) || 0),
      onHold: (projects['On Hold'] as number) || (projects.onHold as number) || 0,
      completed: (projects.Completed as number) || (projects.completed as number) || 0,
      list: (projects.list as MOCK_DASHBOARD_DATA['projects']['list']) || [],
    },
    subscriptions: {
      active: (subscriptions.Active as number) || (subscriptions.active as number) || 0,
      trial: (subscriptions.Trial as number) || (subscriptions.trial as number) || 0,
      cancelled: (subscriptions.Cancelled as number) || (subscriptions.cancelled as number) || 0,
      expired: (subscriptions.Expired as number) || (subscriptions.expired as number) || 0,
      total: (subscriptions.total as number) || 0,
    },
    employees: {
      total: (employees.total as number) || 0,
      departments: (employees.departments as number) || 0,
      departmentNames: (employees.departmentNames as string[]) || [],
    },
    activities: (api.activities as MOCK_DASHBOARD_DATA['activities']) || [],
    itemsNeedAttention: (api.itemsNeedAttention as number) || (
      (incidents.open as number || 0) + (tickets.Open as number || tickets.open as number || 0)
    ),
    projectsInFlight: (api.projectsInFlight as number) || (
      ((projects['In Progress'] as number) || 0) + ((projects.Planning as number) || 0)
    ),
  };
}
