import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import StatusBadge from '@/features/dashboard/components/StatusBadge';
import Pagination from '@/features/dashboard/components/Pagination';
import { formatDate } from '@/lib/utils';
import { ALL_TICKETS } from '@/data/tickets.gen';

const PAGE_SIZE = 30;

export default function TicketsPage() {
  const [page, setPage] = useState(1);
  const openCount = ALL_TICKETS.filter(t => t.status === 'Open').length;
  const inProgressCount = ALL_TICKETS.filter(t => t.status === 'In Progress').length;
  const paged = ALL_TICKETS.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <div className="space-y-6 max-w-[1440px] mx-auto">
      <div>
        <h2 className="text-lg font-semibold">Support Tickets</h2>
        <p className="text-sm text-muted-foreground">
          {ALL_TICKETS.length} total · {openCount} open · {inProgressCount} in progress
        </p>
      </div>

      <Card className="rounded-2xl border-border shadow-card">
        <CardHeader className="pb-4">
          <CardTitle className="text-lg font-semibold">All Tickets</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-6 w-[100px]">Priority</TableHead>
                <TableHead>Subject</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="pr-6 text-right w-[130px]">Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paged.map((t, i) => (
                <TableRow key={i} className="hover:bg-muted/50 transition-colors">
                  <TableCell className="pl-6">
                    <StatusBadge label={t.priority} type="severity" />
                  </TableCell>
                  <TableCell className="font-medium">{t.subject}</TableCell>
                  <TableCell><StatusBadge label={t.status} type="status" /></TableCell>
                  <TableCell className="pr-6 text-right text-muted-foreground text-sm tabular-nums">
                    {formatDate(t.created_date)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <Pagination page={page} pageSize={PAGE_SIZE} total={ALL_TICKETS.length} onPageChange={setPage} />
        </CardContent>
      </Card>
    </div>
  );
}
