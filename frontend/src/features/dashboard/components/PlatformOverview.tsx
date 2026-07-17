import { PieChart, Pie, Cell, ResponsiveContainer, Label } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface PlatformOverviewProps {
  itemsNeedAttention: number;
  bySeverity: Record<string, number>;
  projectsInFlight: number;
}

const SEVERITY_COLORS = {
  Critical: '#EF4444',
  High: '#F59E0B',
  Medium: '#EAB308',
  Low: '#3B82F6',
};

const SEVERITY_LABELS: Record<string, string> = {
  P1: 'Critical',
  P2: 'High',
  P3: 'Medium',
};

export default function PlatformOverview({ itemsNeedAttention, bySeverity, projectsInFlight }: PlatformOverviewProps) {
  const total = Object.values(bySeverity).reduce((sum, v) => sum + v, 0);
  const resolved = Math.max(0, 60 - total); // Total incidents ~60 from CSV

  const donutData = [
    { name: 'Critical', value: bySeverity.P1 || 0, color: SEVERITY_COLORS.Critical },
    { name: 'High', value: bySeverity.P2 || 0, color: SEVERITY_COLORS.High },
    { name: 'Medium', value: bySeverity.P3 || 0, color: SEVERITY_COLORS.Medium },
    { name: 'Resolved', value: resolved, color: '#374151' },
  ].filter(d => d.value > 0);

  const severityItems = [
    { label: 'Critical', value: bySeverity.P1 || 0, color: 'bg-accent-red' },
    { label: 'High', value: bySeverity.P2 || 0, color: 'bg-accent-orange' },
    { label: 'Medium', value: bySeverity.P3 || 0, color: 'bg-yellow-500' },
    { label: 'Low', value: 0, color: 'bg-accent-blue' },
  ];

  return (
    <Card className="rounded-2xl border-border shadow-card">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg font-semibold">Platform Overview</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col sm:flex-row items-center gap-6">
          {/* Donut Chart */}
          <div className="w-[180px] h-[180px] flex-shrink-0">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={donutData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={85}
                  paddingAngle={2}
                  dataKey="value"
                  strokeWidth={0}
                >
                  {donutData.map((entry, index) => (
                    <Cell key={index} fill={entry.color} />
                  ))}
                  <Label
                    value={itemsNeedAttention}
                    position="center"
                    className="text-3xl font-bold"
                    fill="currentColor"
                  />
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Breakdown */}
          <div className="flex-1 space-y-4">
            <p className="text-sm text-muted-foreground">
              <span className="text-2xl font-bold text-foreground">{itemsNeedAttention}</span> items need attention
            </p>

            <div className="space-y-2.5">
              {severityItems.map((item) => (
                <div key={item.label} className="flex items-center gap-3">
                  <div className={cn('w-3 h-3 rounded-full flex-shrink-0', item.color)} />
                  <span className="text-sm text-muted-foreground w-16">{item.label}</span>
                  <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className={cn('h-full rounded-full', item.color)}
                      style={{ width: `${total > 0 ? (item.value / 60) * 100 : 0}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium tabular-nums w-6 text-right">{item.value}</span>
                </div>
              ))}
            </div>

            <p className="text-sm text-muted-foreground pt-1">
              <span className="font-semibold text-foreground">{projectsInFlight}</span> projects currently in flight
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
