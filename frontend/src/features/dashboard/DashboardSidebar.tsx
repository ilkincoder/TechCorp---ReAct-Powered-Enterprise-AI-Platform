import { NavLink } from 'react-router-dom';
import { useTheme } from '@/context/ThemeContext';
import { useRole } from '@/context/RoleContext';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  AlertTriangle,
  Ticket,
  FolderKanban,
  CreditCard,
  Users,
  FileText,
  Settings,
  MessageSquare,
  Sun,
  Moon,
  LogOut,
  Menu,
} from 'lucide-react';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/chat', label: 'Chat', icon: MessageSquare },
  { to: '/incidents', label: 'Incidents', icon: AlertTriangle },
  { to: '/tickets', label: 'Support Tickets', icon: Ticket },
  { to: '/projects', label: 'Projects', icon: FolderKanban },
  { to: '/subscriptions', label: 'Subscriptions', icon: CreditCard },
  { to: '/team', label: 'Team', icon: Users },
  { to: '/reports', label: 'Reports', icon: FileText },
  { to: '/settings', label: 'Settings', icon: Settings },
];

const ROLE_LABELS: Record<string, string> = {
  engineering_admin: 'Administrator',
  sales_intern: 'Sales Intern',
  support_agent: 'Support Agent',
};

function SidebarContent() {
  const { theme, toggleTheme } = useTheme();
  const { activeRole, userName, logout } = useRole();

  return (
    <div className="flex flex-col h-full bg-sidebar border-r border-border">
      {/* Brand */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-border">
        <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
          <span className="text-primary-foreground font-bold text-sm">TC</span>
        </div>
        <span className="font-semibold text-sm leading-tight">
          TechCorp Enterprise Platform
        </span>
      </div>

      {/* Navigation */}
      <ul className="flex-1 flex flex-col gap-0.5 px-3 py-3 overflow-y-auto">
        {NAV_ITEMS.map((item) => (
          <li key={item.label}>
            <NavLink
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors duration-200',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-accent hover:text-foreground'
                )
              }
            >
              <item.icon className="w-5 h-5 flex-shrink-0" />
              <span>{item.label}</span>
            </NavLink>
          </li>
        ))}
      </ul>

      {/* Footer: User + Controls */}
      <div className="p-3 border-t border-border space-y-3">
        {/* User profile */}
        <div className="flex items-center gap-3 px-2 pb-3 border-b border-border">
          <Avatar className="w-9 h-9">
            <AvatarFallback className="bg-primary text-primary-foreground text-sm font-semibold">
              {userName ? userName.charAt(0).toUpperCase() : 'I'}
            </AvatarFallback>
          </Avatar>
          <div className="flex flex-col min-w-0">
            <span className="text-sm font-semibold truncate">
              {userName || 'Ilkin Hamzayev'}
            </span>
            <span className="text-xs text-muted-foreground">
              {ROLE_LABELS[activeRole] || 'Administrator'}
            </span>
          </div>
        </div>

        {/* Controls */}
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="icon"
            onClick={toggleTheme}
            title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
            className="flex-1"
          >
            {theme === 'dark' ? (
              <Sun className="w-4 h-4" />
            ) : (
              <Moon className="w-4 h-4" />
            )}
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={logout}
            title="End session"
            className="flex-1 text-muted-foreground hover:text-destructive"
          >
            <LogOut className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}

export default function DashboardSidebar() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex w-[260px] flex-shrink-0 h-screen sticky top-0">
        <SidebarContent />
      </aside>

      {/* Tablet: collapsed icons */}
      <aside className="hidden md:flex lg:hidden w-[64px] flex-shrink-0 h-screen sticky top-0">
        <div className="flex flex-col h-full bg-card border-r border-border items-center py-4 gap-1">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center mb-4">
            <span className="text-primary-foreground font-bold text-xs">TC</span>
          </div>
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.label}
              to={item.to}
              end={item.end}
              title={item.label}
              className={({ isActive }) =>
                cn(
                  'flex items-center justify-center w-10 h-10 rounded-lg transition-colors duration-200',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-accent hover:text-foreground'
                )
              }
            >
              <item.icon className="w-5 h-5" />
            </NavLink>
          ))}
        </div>
      </aside>

      {/* Mobile: drawer */}
      <div className="md:hidden fixed top-0 left-0 z-50 p-3">
        <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
          <SheetTrigger asChild>
            <Button variant="outline" size="icon">
              <Menu className="w-5 h-5" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-[260px] p-0">
            <SidebarContent />
          </SheetContent>
        </Sheet>
      </div>
    </>
  );
}
