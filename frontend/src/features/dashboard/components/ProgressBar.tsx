import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

interface ProgressBarProps {
  value: number;
  color?: string;
  showLabel?: boolean;
  className?: string;
}

const COLOR_MAP: Record<string, string> = {
  blue: 'bg-accent-blue',
  green: 'bg-accent-green',
  orange: 'bg-accent-orange',
  purple: 'bg-accent-purple',
  red: 'bg-accent-red',
};

export default function ProgressBar({ value, color = 'blue', showLabel = false, className }: ProgressBarProps) {
  const fillColor = COLOR_MAP[color] || 'bg-primary';
  const clampedValue = Math.min(100, Math.max(0, value));

  return (
    <div className={cn('flex items-center gap-3', className)}>
      <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
        <motion.div
          className={cn('h-full rounded-full', fillColor)}
          initial={{ width: 0 }}
          animate={{ width: `${clampedValue}%` }}
          transition={{ duration: 1, ease: 'easeOut', delay: 0.3 }}
        />
      </div>
      {showLabel && (
        <span className="text-xs text-muted-foreground tabular-nums w-9 text-right">
          {clampedValue}%
        </span>
      )}
    </div>
  );
}
