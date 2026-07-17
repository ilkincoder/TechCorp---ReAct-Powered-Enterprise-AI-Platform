import { motion } from 'framer-motion';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { UserPlus, CheckCircle, Ticket, CreditCard, ShieldCheck, Inbox } from 'lucide-react';
import { cn, formatRelativeTime } from '@/lib/utils';
import type { ActivityItem } from '@/types/dashboard';

interface ActivityFeedProps {
  activities: ActivityItem[];
}

const ICON_MAP: Record<string, typeof UserPlus> = {
  UserPlus,
  CheckCircle,
  Ticket,
  CreditCard,
  ShieldCheck,
};

function ActivityIcon({ type }: { type: string }) {
  const Icon = ICON_MAP[type] || CheckCircle;
  const bgMap: Record<string, string> = {
    employee: 'bg-green-500/10 text-green-500',
    project: 'bg-blue-500/10 text-blue-500',
    ticket: 'bg-orange-500/10 text-orange-500',
    subscription: 'bg-purple-500/10 text-purple-500',
    incident: 'bg-red-500/10 text-red-500',
  };

  return (
    <div className={cn('p-2 rounded-full flex-shrink-0', bgMap[type] || 'bg-muted text-muted-foreground')}>
      <Icon className="w-4 h-4" />
    </div>
  );
}

export default function ActivityFeed({ activities }: ActivityFeedProps) {
  return (
    <Card className="rounded-2xl border-border shadow-card h-full flex flex-col">
      <CardHeader className="pb-4">
        <CardTitle className="text-lg font-semibold">Activity Feed</CardTitle>
      </CardHeader>
      <CardContent className="pb-4 flex-1 flex flex-col">
        {activities.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.4 }}
            className="flex-1 flex flex-col items-center justify-center py-12 text-center"
          >
            <div className="p-4 rounded-full bg-muted mb-4">
              <Inbox className="w-8 h-8 text-muted-foreground" />
            </div>
            <p className="text-base font-medium">No current activities</p>
            <p className="text-sm text-muted-foreground mt-1">
              New activity will show up here as it happens.
            </p>
          </motion.div>
        ) : (
        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-[19px] top-2 bottom-2 w-px bg-border" />

          <div className="space-y-5">
            {activities.slice(0, 6).map((activity, index) => (
              <motion.div
                key={activity.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 + index * 0.1, duration: 0.4 }}
                className="relative flex gap-4 pl-1"
              >
                <div className="relative z-10">
                  <ActivityIcon type={activity.icon || activity.type} />
                </div>
                <div className="flex-1 min-w-0 pb-1">
                  <p className="text-sm font-medium leading-tight">{activity.title}</p>
                  <p className="text-xs text-muted-foreground mt-0.5 leading-tight">
                    {activity.description}
                  </p>
                  <p className="text-[11px] text-muted-foreground mt-1">
                    {formatRelativeTime(activity.timestamp)}
                  </p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
        )}
      </CardContent>
    </Card>
  );
}
