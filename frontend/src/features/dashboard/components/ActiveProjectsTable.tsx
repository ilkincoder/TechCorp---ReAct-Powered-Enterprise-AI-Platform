import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import StatusBadge from './StatusBadge';
import ProgressBar from './ProgressBar';
import { formatDate } from '@/lib/utils';
import type { ProjectItem } from '@/types/dashboard';

interface ActiveProjectsTableProps {
  projects: ProjectItem[];
}

function getProgressColor(status: string): string {
  switch (status.toLowerCase()) {
    case 'completed': return 'green';
    case 'in progress': return 'blue';
    case 'planning': return 'orange';
    case 'on hold': return 'orange';
    default: return 'blue';
  }
}

export default function ActiveProjectsTable({ projects }: ActiveProjectsTableProps) {
  const sorted = [...projects].sort((a, b) => {
    const order: Record<string, number> = { 'In Progress': 0, 'Planning': 1, 'On Hold': 2, 'Completed': 3 };
    return (order[a.status] ?? 99) - (order[b.status] ?? 99);
  });

  return (
    <Card className="rounded-2xl border-border shadow-card">
      <CardHeader className="pb-4">
        <CardTitle className="text-lg font-semibold">Active Projects</CardTitle>
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
            {sorted.map((project) => (
              <TableRow key={project.id} className="hover:bg-muted/50 transition-colors">
                <TableCell className="pl-6 font-medium">{project.name}</TableCell>
                <TableCell className="text-muted-foreground">{project.owner}</TableCell>
                <TableCell>
                  <StatusBadge label={project.status} type="status" />
                </TableCell>
                <TableCell>
                  <ProgressBar
                    value={project.progress}
                    color={getProgressColor(project.status)}
                    showLabel
                  />
                </TableCell>
                <TableCell className="pr-6 text-right text-muted-foreground text-sm tabular-nums">
                  {formatDate(project.dueDate || '')}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
