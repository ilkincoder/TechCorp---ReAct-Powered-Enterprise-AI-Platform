import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import StatusBadge from './StatusBadge';
import { formatRelativeTime, getSeverityLabel } from '@/lib/utils';
import type { IncidentItem } from '@/types/dashboard';

interface RecentIncidentsPanelProps {
  incidents: IncidentItem[];
}

function extractService(title: string): string {
  const lower = title.toLowerCase();
  if (lower.includes('sso') || lower.includes('auth')) return 'Authentication Service';
  if (lower.includes('ddos') || lower.includes('security')) return 'Network Security';
  if (lower.includes('api')) return 'API Gateway';
  if (lower.includes('email') || lower.includes('notification')) return 'Notifications';
  if (lower.includes('database') || lower.includes('replication')) return 'Database';
  if (lower.includes('ml') || lower.includes('inference') || lower.includes('pipeline')) return 'ML Pipeline';
  if (lower.includes('failover') || lower.includes('region')) return 'Infrastructure';
  return 'Platform';
}

export default function RecentIncidentsPanel({ incidents }: RecentIncidentsPanelProps) {
  return (
    <Card className="rounded-2xl border-border shadow-card">
      <CardHeader className="pb-4">
        <CardTitle className="text-lg font-semibold">Recent Incidents</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="pl-6 w-[100px]">Severity</TableHead>
              <TableHead>Title</TableHead>
              <TableHead className="hidden sm:table-cell">Service</TableHead>
              <TableHead className="pr-6 text-right w-[130px]">Time</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {incidents.slice(0, 8).map((incident) => (
              <TableRow key={incident.id} className="hover:bg-muted/50 transition-colors">
                <TableCell className="pl-6">
                  <StatusBadge
                    label={getSeverityLabel(incident.severity)}
                    type="severity"
                  />
                </TableCell>
                <TableCell className="font-medium max-w-[300px] truncate">
                  {incident.title}
                </TableCell>
                <TableCell className="hidden sm:table-cell text-muted-foreground">
                  {incident.service || extractService(incident.title)}
                </TableCell>
                <TableCell className="pr-6 text-right text-muted-foreground text-sm tabular-nums">
                  {formatRelativeTime(incident.created_at)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
