import { motion } from 'framer-motion';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import AnimatedNumber from './AnimatedNumber';
import type { ReactNode } from 'react';

interface KPICardProps {
  title: string;
  value: number;
  subtitle: string;
  accent: 'red' | 'blue' | 'green' | 'purple' | 'orange';
  sparklineData?: { value: number }[];
  icon?: ReactNode;
  children?: ReactNode;
}

const ACCENT_BORDERS: Record<string, string> = {
  red: 'border-l-accent-red',
  blue: 'border-l-accent-blue',
  green: 'border-l-accent-green',
  purple: 'border-l-accent-purple',
  orange: 'border-l-accent-orange',
};

const ACCENT_BG: Record<string, string> = {
  red: 'bg-red-500/10',
  blue: 'bg-blue-500/10',
  green: 'bg-green-500/10',
  purple: 'bg-purple-500/10',
  orange: 'bg-orange-500/10',
};

const ACCENT_TEXT: Record<string, string> = {
  red: 'text-red-500',
  blue: 'text-blue-500',
  green: 'text-green-500',
  purple: 'text-purple-500',
  orange: 'text-orange-500',
};

export default function KPICard({ title, value, subtitle, accent, icon, children }: KPICardProps) {
  return (
    <motion.div whileHover={{ y: -2 }} transition={{ duration: 0.2 }}>
      <Card
        className={cn(
          'h-[220px] border-l-4 rounded-2xl shadow-card hover:shadow-card-hover transition-all duration-200 cursor-pointer overflow-hidden',
          ACCENT_BORDERS[accent]
        )}
      >
        <CardContent className="p-5 flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
              {title}
            </span>
            {icon && (
              <span className={cn('p-1.5 rounded-lg', ACCENT_BG[accent], ACCENT_TEXT[accent])}>
                {icon}
              </span>
            )}
          </div>

          {/* Value */}
          <div className={cn('text-4xl font-bold mb-1', ACCENT_TEXT[accent])}>
            <AnimatedNumber value={value} />
          </div>

          {/* Subtitle */}
          <p className="text-sm text-muted-foreground leading-relaxed">{subtitle}</p>

          {/* Extra content (sparkline, etc.) */}
          {children && <div className="mt-auto pt-3">{children}</div>}
        </CardContent>
      </Card>
    </motion.div>
  );
}
