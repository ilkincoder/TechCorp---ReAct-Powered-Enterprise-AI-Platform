import { Outlet } from 'react-router-dom';
import DashboardSidebar from './DashboardSidebar';
import TopHeader from './TopHeader';

export default function DashboardLayout() {
  return (
    <div className="flex h-screen bg-background">
      <DashboardSidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopHeader />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
