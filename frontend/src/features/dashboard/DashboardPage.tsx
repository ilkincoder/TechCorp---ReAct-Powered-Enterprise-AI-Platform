import { motion } from 'framer-motion';
import { useDashboardData } from './hooks/useDashboardData';
import KPIRow from './components/KPIRow';
import PlatformOverview from './components/PlatformOverview';
import RecentIncidentsPanel from './components/RecentIncidentsPanel';
import ActivityFeed from './components/ActivityFeed';
import ActiveProjectsTable from './components/ActiveProjectsTable';
import SubscriptionOverview from './components/SubscriptionOverview';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.08, delayChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

export default function DashboardPage() {
  const { data, loading } = useDashboardData();

  if (loading || !data) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-muted-foreground">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="max-w-[1440px] mx-auto space-y-6"
    >
      {/* KPI Row */}
      <motion.div variants={itemVariants}>
        <KPIRow data={data} />
      </motion.div>

      {/* Row 1: Platform Overview + Subscription Overview */}
      <motion.div variants={itemVariants} className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <PlatformOverview
          itemsNeedAttention={data.itemsNeedAttention}
          bySeverity={data.incidents.bySeverity}
          projectsInFlight={data.projectsInFlight}
        />
        <SubscriptionOverview subscriptions={data.subscriptions} />
      </motion.div>

      {/* Row 2: Incidents + Activity Feed */}
      <motion.div variants={itemVariants} className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <RecentIncidentsPanel incidents={data.incidents.list} />
        </div>
        <div className="lg:col-span-1">
          <ActivityFeed activities={data.activities} />
        </div>
      </motion.div>

      {/* Row 3: Active Projects (full width) */}
      <motion.div variants={itemVariants}>
        <ActiveProjectsTable projects={data.projects.list} />
      </motion.div>
    </motion.div>
  );
}
