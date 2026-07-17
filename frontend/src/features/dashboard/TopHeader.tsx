import { Search, Bell, ChevronDown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';

export default function TopHeader() {
  return (
    <header className="h-[72px] border-b border-border bg-card flex items-center px-6 gap-6 flex-shrink-0">
      {/* Left: Breadcrumb */}
      <div className="flex flex-col min-w-0">
        <h1 className="text-lg font-semibold leading-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground leading-tight truncate">
          Live enterprise overview and platform insights
        </p>
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Search */}
      <div className="hidden md:flex items-center relative max-w-[320px] flex-1">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
        <Input
          type="search"
          placeholder="Search..."
          className="pl-9 pr-14 h-10 bg-background border-border rounded-lg text-sm"
        />
        <kbd className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none inline-flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground bg-muted rounded border border-border">
          <span>⌘</span><span>K</span>
        </kbd>
      </div>

      {/* Notifications */}
      <Button variant="outline" size="icon" className="relative">
        <Bell className="w-5 h-5" />
        <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-accent-red rounded-full border-2 border-card" />
      </Button>

      {/* Date Selector */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" className="hidden sm:flex gap-2 text-sm">
            Last 30 days
            <ChevronDown className="w-4 h-4 text-muted-foreground" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem>Last 7 days</DropdownMenuItem>
          <DropdownMenuItem>Last 30 days</DropdownMenuItem>
          <DropdownMenuItem>Last 90 days</DropdownMenuItem>
          <DropdownMenuItem>This year</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}
