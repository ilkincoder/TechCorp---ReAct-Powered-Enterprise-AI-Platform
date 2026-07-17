import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import StatusBadge from '@/features/dashboard/components/StatusBadge';
import Pagination from '@/features/dashboard/components/Pagination';
import { formatDate, getSeverityLabel } from '@/lib/utils';
import { ALL_INCIDENTS } from '@/data/incidents.gen';

const PAGE_SIZE = 30;

export default function IncidentsPage() {
  const [page, setPage] = useState(1);
  const openCount = ALL_INCIDENTS.filter(i => !['Resolved', 'Closed'].includes(i.status)).length;
  const criticalCount = ALL_INCIDENTS.filter(i => i.severity === 'P1' && !['Resolved', 'Closed'].includes(i.status)).length;
  const paged = ALL_INCIDENTS.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <div className="space-y-6 max-w-[1440px] mx-auto">
      <div>
        <h2 className="text-lg font-semibold">Incidents</h2>
        <p className="text-sm text-muted-foreground">
          {ALL_INCIDENTS.length} total · {openCount} open · {criticalCount} critical
        </p>
      </div>

      <Card className="rounded-2xl border-border shadow-card">
        <CardHeader className="pb-4">
          <CardTitle className="text-lg font-semibold">All Incidents</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-6 w-[100px]">Severity</TableHead>
                <TableHead>Title</TableHead>
                <TableHead>Service</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="pr-6 text-right w-[130px]">Date</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paged.map((inc, i) => (
                <TableRow key={i} className="hover:bg-muted/50 transition-colors">
                  <TableCell className="pl-6">
                    <StatusBadge label={getSeverityLabel(inc.severity)} type="severity" />
                  </TableCell>
                  <TableCell className="font-medium max-w-[400px] truncate">{inc.title}</TableCell>
                  <TableCell className="text-muted-foreground">{inc.service}</TableCell>
                  <TableCell><StatusBadge label={inc.status} type="status" /></TableCell>
                  <TableCell className="pr-6 text-right text-muted-foreground text-sm tabular-nums">
                    {formatDate(inc.created_at)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <Pagination page={page} pageSize={PAGE_SIZE} total={ALL_INCIDENTS.length} onPageChange={setPage} />
        </CardContent>
      </Card>
    </div>
  );
}
