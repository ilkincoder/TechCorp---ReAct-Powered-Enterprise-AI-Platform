import { useState, useEffect, useRef } from 'react';
import { cn } from '@/lib/utils';

interface AnimatedNumberProps {
  value: number;
  duration?: number;
  className?: string;
}

export default function AnimatedNumber({ value, duration = 1.5, className }: AnimatedNumberProps) {
  const [display, setDisplay] = useState(0);
  const raf = useRef<number | null>(null);
  const startTime = useRef<number | null>(null);
  const startValue = useRef(0);

  useEffect(() => {
    startValue.current = display;
    startTime.current = null;
    const durationMs = duration * 1000;

    function animate(timestamp: number) {
      if (!startTime.current) startTime.current = timestamp;
      const elapsed = timestamp - startTime.current;
      const progress = Math.min(elapsed / durationMs, 1);
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = Math.round(startValue.current + (value - startValue.current) * eased);
      setDisplay(current);

      if (progress < 1) {
        raf.current = requestAnimationFrame(animate);
      }
    }

    raf.current = requestAnimationFrame(animate);
    return () => {
      if (raf.current) cancelAnimationFrame(raf.current);
    };
  }, [value, duration]);

  return (
    <span className={cn('tabular-nums', className)}>
      {display}
    </span>
  );
}
