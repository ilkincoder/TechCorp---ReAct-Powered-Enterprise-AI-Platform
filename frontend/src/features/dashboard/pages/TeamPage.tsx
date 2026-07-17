import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Users, Building } from 'lucide-react';
import { ALL_DEPARTMENTS } from '@/data/departments.gen';

export default function TeamPage() {
  const totalEmployees = ALL_DEPARTMENTS.reduce((sum, d) => sum + d.headcount, 0);
  const avgTeamSize = Math.round(totalEmployees / ALL_DEPARTMENTS.length);

  return (
    <div className="space-y-6 max-w-[1440px] mx-auto">
      <div>
        <h2 className="text-lg font-semibold">Team</h2>
        <p className="text-sm text-muted-foreground">
          {totalEmployees} employees · {ALL_DEPARTMENTS.length} departments · ~{avgTeamSize} avg team size
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
        <Card className="rounded-2xl border-border shadow-card">
          <CardContent className="p-6 flex items-center gap-4">
            <div className="p-3 rounded-xl bg-blue-500/10 text-blue-500">
              <Users className="w-6 h-6" />
            </div>
            <div>
              <p className="text-3xl font-bold">{totalEmployees}</p>
              <p className="text-sm text-muted-foreground">Total Employees</p>
            </div>
          </CardContent>
        </Card>
        <Card className="rounded-2xl border-border shadow-card">
          <CardContent className="p-6 flex items-center gap-4">
            <div className="p-3 rounded-xl bg-purple-500/10 text-purple-500">
              <Building className="w-6 h-6" />
            </div>
            <div>
              <p className="text-3xl font-bold">{ALL_DEPARTMENTS.length}</p>
              <p className="text-sm text-muted-foreground">Departments</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="rounded-2xl border-border shadow-card">
        <CardHeader className="pb-4">
          <CardTitle className="text-lg font-semibold">Departments</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-6">Department</TableHead>
                <TableHead className="text-right">Headcount</TableHead>
                <TableHead className="pr-6 text-right">% of Total</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {ALL_DEPARTMENTS.map((d) => (
                <TableRow key={d.name} className="hover:bg-muted/50 transition-colors">
                  <TableCell className="pl-6 font-medium">{d.name}</TableCell>
                  <TableCell className="text-right tabular-nums">{d.headcount}</TableCell>
                  <TableCell className="pr-6 text-right text-muted-foreground tabular-nums">
                    {Math.round((d.headcount / totalEmployees) * 100)}%
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
