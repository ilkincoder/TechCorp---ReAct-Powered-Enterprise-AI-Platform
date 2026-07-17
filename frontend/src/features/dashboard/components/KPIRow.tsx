import { motion } from 'framer-motion';
import {
  AlertTriangle,
  Ticket,
  FolderKanban,
  CreditCard,
  Users,
} from 'lucide-react';
import KPICard from './KPICard';
import type { DashboardStats } from '@/types/dashboard';

const staggerVariants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.1, delayChildren: 0.1 },
  },
};

const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

interface KPIRowProps {
  data: DashboardStats;
}

export default function KPIRow({ data }: KPIRowProps) {
  const { incidents, tickets, projects, subscriptions, employees } = data;

  const kpis = [
    {
      title: 'Open Incidents',
      value: incidents.open,
      subtitle: `${incidents.critical} critical · Latest: SSO authentication failure`,
      accent: 'red' as const,
      icon: <AlertTriangle className="w-4 h-4" />,
    },
    {
      title: 'Support Tickets',
      value: tickets.open + tickets.inProgress,
      subtitle: `${tickets.open} open · ${tickets.inProgress} in progress · ${tickets.closed} closed`,
      accent: 'blue' as const,
      icon: <Ticket className="w-4 h-4" />,
    },
    {
      title: 'Active Projects',
      value: projects.active,
      subtitle: `${projects.onHold} on hold · ${projects.completed} completed`,
      accent: 'green' as const,
      icon: <FolderKanban className="w-4 h-4" />,
    },
    {
      title: 'Subscriptions',
      value: subscriptions.active,
      subtitle: `${subscriptions.trial} trial · ${subscriptions.cancelled} cancelled`,
      accent: 'purple' as const,
      icon: <CreditCard className="w-4 h-4" />,
    },
    {
      title: 'Team',
      value: employees.total,
      subtitle: `${employees.departments} departments`,
      accent: 'orange' as const,
      icon: <Users className="w-4 h-4" />,
    },
  ];

  return (
    <motion.div
      variants={staggerVariants}
      initial="hidden"
      animate="visible"
      className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6"
    >
      {kpis.map((kpi) => (
        <motion.div key={kpi.title} variants={cardVariants}>
          <KPICard
            title={kpi.title}
            value={kpi.value}
            subtitle={kpi.subtitle}
            accent={kpi.accent}
            icon={kpi.icon}
          />
        </motion.div>
      ))}
    </motion.div>
  );
}
