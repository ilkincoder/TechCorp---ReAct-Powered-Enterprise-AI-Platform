export interface IncidentItem {
  id: number;
  title: string;
  severity: 'P1' | 'P2' | 'P3';
  status: string;
  service: string;
  created_at: string;
}

export interface IncidentStats {
  open: number;
  critical: number;
  bySeverity: Record<string, number>;
  latest: IncidentItem | null;
  list: IncidentItem[];
}

export interface TicketStats {
  open: number;
  inProgress: number;
  closed: number;
  resolved: number;
}

export interface ProjectItem {
  id: number;
  name: string;
  status: string;
  owner: string;
  progress: number;
  dueDate: string | null;
}

export interface ProjectStats {
  active: number;
  onHold: number;
  completed: number;
  list: ProjectItem[];
}

export interface SubscriptionStats {
  active: number;
  trial: number;
  cancelled: number;
  expired: number;
  total: number;
}

export interface EmployeeStats {
  total: number;
  departments: number;
  departmentNames: string[];
}

export interface ActivityItem {
  id: number;
  type: 'employee' | 'project' | 'ticket' | 'subscription' | 'incident';
  icon: string;
  title: string;
  description: string;
  timestamp: string;
}

export interface DashboardStats {
  incidents: IncidentStats;
  tickets: TicketStats;
  projects: ProjectStats;
  subscriptions: SubscriptionStats;
  employees: EmployeeStats;
  activities: ActivityItem[];
  itemsNeedAttention: number;
  projectsInFlight: number;
}
