import { useState } from 'react';
import Chat from '@/pages/Chat';
import InsightsPanel from '@/layout/InsightsPanel';

export default function ChatPageWrapper() {
  const [insightsCollapsed, setInsightsCollapsed] = useState(true);

  return (
    <div className="flex h-full">
      <div className="flex-1 min-w-0">
        <Chat />
      </div>
      <InsightsPanel
        collapsed={insightsCollapsed}
        onCollapseChange={setInsightsCollapsed}
      />
    </div>
  );
}
