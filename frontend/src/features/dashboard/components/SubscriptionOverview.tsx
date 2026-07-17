import { PieChart, Pie, Cell, ResponsiveContainer, Label } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { SubscriptionStats } from '@/types/dashboard';

interface SubscriptionOverviewProps {
  subscriptions: SubscriptionStats;
}

const COLORS = {
  Active: '#22C55E',
  Trial: '#F59E0B',
  Cancelled: '#6B7280',
  Expired: '#9CA3AF',
};

export default function SubscriptionOverview({ subscriptions }: SubscriptionOverviewProps) {
  const { active, trial, cancelled, expired, total } = subscriptions;

  const chartData = [
    { name: 'Active', value: active, color: COLORS.Active },
    { name: 'Trial', value: trial, color: COLORS.Trial },
    { name: 'Cancelled', value: cancelled, color: COLORS.Cancelled },
    { name: 'Expired', value: expired, color: COLORS.Expired },
  ].filter(d => d.value > 0);

  return (
    <Card className="rounded-2xl border-border shadow-card">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg font-semibold">Subscription Overview</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col sm:flex-row items-center gap-6">
          {/* Donut Chart */}
          <div className="w-[180px] h-[180px] flex-shrink-0">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={85}
                  paddingAngle={2}
                  dataKey="value"
                  strokeWidth={0}
                >
                  {chartData.map((entry, index) => (
                    <Cell key={index} fill={entry.color} />
                  ))}
                  <Label
                    value={total}
                    position="center"
                    className="text-3xl font-bold"
                    fill="currentColor"
                  />
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Legend */}
          <div className="flex-1 space-y-3">
            {chartData.map((item) => (
              <div key={item.name} className="flex items-center gap-3">
                <div
                  className="w-3 h-3 rounded-full flex-shrink-0"
                  style={{ backgroundColor: item.color }}
                />
                <span className="text-sm text-muted-foreground w-20">{item.name}</span>
                <span className="text-sm font-semibold tabular-nums ml-auto">{item.value}</span>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
