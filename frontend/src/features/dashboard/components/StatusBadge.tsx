import { Badge } from '@/components/ui/badge';
import { cn, getSeverityColor, getStatusColor } from '@/lib/utils';

interface StatusBadgeProps {
  label: string;
  type?: 'severity' | 'status';
  className?: string;
}

export default function StatusBadge({ label, type = 'status', className }: StatusBadgeProps) {
  const colorClass = type === 'severity' ? getSeverityColor(label) : getStatusColor(label);

  return (
    <Badge
      variant="outline"
      className={cn('font-semibold text-[11px] px-2 py-0.5 border', colorClass, className)}
    >
      {label}
    </Badge>
  );
}
