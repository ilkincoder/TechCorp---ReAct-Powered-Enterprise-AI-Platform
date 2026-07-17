import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import StatusBadge from '@/features/dashboard/components/StatusBadge';
import Pagination from '@/features/dashboard/components/Pagination';
import { formatDate } from '@/lib/utils';
import { ALL_SUBSCRIPTIONS } from '@/data/subscriptions.gen';

const PAGE_SIZE = 30;

export default function SubscriptionsPage() {
  const [page, setPage] = useState(1);
  const activeCount = ALL_SUBSCRIPTIONS.filter(s => s.status === 'Active').length;
  const trialCount = ALL_SUBSCRIPTIONS.filter(s => s.status === 'Trial').length;
  const paged = ALL_SUBSCRIPTIONS.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <div className="space-y-6 max-w-[1440px] mx-auto">
      <div>
        <h2 className="text-lg font-semibold">Subscriptions</h2>
        <p className="text-sm text-muted-foreground">
          {ALL_SUBSCRIPTIONS.length} total · {activeCount} active · {trialCount} trial
        </p>
      </div>

      <Card className="rounded-2xl border-border shadow-card">
        <CardHeader className="pb-4">
          <CardTitle className="text-lg font-semibold">All Subscriptions</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-6">Plan</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Seats</TableHead>
                <TableHead className="pr-6 text-right">Start Date</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paged.map((s, i) => (
                <TableRow key={i} className="hover:bg-muted/50 transition-colors">
                  <TableCell className="pl-6 font-medium">{s.plan}</TableCell>
                  <TableCell><StatusBadge label={s.status} type="status" /></TableCell>
                  <TableCell className="text-right tabular-nums">{s.seats}</TableCell>
                  <TableCell className="pr-6 text-right text-muted-foreground text-sm tabular-nums">
                    {formatDate(s.start_date)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <Pagination page={page} pageSize={PAGE_SIZE} total={ALL_SUBSCRIPTIONS.length} onPageChange={setPage} />
        </CardContent>
      </Card>
    </div>
  );
}
