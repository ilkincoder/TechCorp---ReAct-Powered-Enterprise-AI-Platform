import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import StatusBadge from '@/features/dashboard/components/StatusBadge';
import ProgressBar from '@/features/dashboard/components/ProgressBar';
import Pagination from '@/features/dashboard/components/Pagination';
import { formatDate } from '@/lib/utils';
import { ALL_PROJECTS } from '@/data/projects.gen';

const PAGE_SIZE = 30;

function getProgressColor(status: string): string {
  switch (status.toLowerCase()) {
    case 'completed': return 'green';
    case 'in progress': return 'blue';
    case 'planning': return 'orange';
    case 'on hold': return 'orange';
    default: return 'blue';
  }
}

export default function ProjectsPage() {
  const [page, setPage] = useState(1);
  const activeCount = ALL_PROJECTS.filter(p => ['In Progress', 'Planning'].includes(p.status)).length;
  const completedCount = ALL_PROJECTS.filter(p => p.status === 'Completed').length;

  const sorted = [...ALL_PROJECTS].sort((a, b) => {
    const order: Record<string, number> = { 'In Progress': 0, 'Planning': 1, 'On Hold': 2, 'Completed': 3 };
    return (order[a.status] ?? 99) - (order[b.status] ?? 99);
  });
  const paged = sorted.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <div className="space-y-6 max-w-[1440px] mx-auto">
      <div>
        <h2 className="text-lg font-semibold">Projects</h2>
        <p className="text-sm text-muted-foreground">
          {ALL_PROJECTS.length} total · {activeCount} active · {completedCount} completed
        </p>
      </div>

      <Card className="rounded-2xl border-border shadow-card">
        <CardHeader className="pb-4">
          <CardTitle className="text-lg font-semibold">All Projects</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-6">Project</TableHead>
                <TableHead>Owner</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="w-[160px]">Progress</TableHead>
                <TableHead className="pr-6 text-right w-[120px]">Due Date</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paged.map((p, i) => (
                <TableRow key={i} className="hover:bg-muted/50 transition-colors">
                  <TableCell className="pl-6 font-medium">{p.name}</TableCell>
                  <TableCell className="text-muted-foreground">{p.owner}</TableCell>
                  <TableCell><StatusBadge label={p.status} type="status" /></TableCell>
                  <TableCell>
                    <ProgressBar value={p.progress} color={getProgressColor(p.status)} showLabel />
                  </TableCell>
                  <TableCell className="pr-6 text-right text-muted-foreground text-sm tabular-nums">
                    {formatDate(p.dueDate || '')}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <Pagination page={page} pageSize={PAGE_SIZE} total={sorted.length} onPageChange={setPage} />
        </CardContent>
      </Card>
    </div>
  );
}
