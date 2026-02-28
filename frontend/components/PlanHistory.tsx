'use client';

import { getPlan } from '@/lib/api';
import { Plan, PlanHistoryItem } from '@/lib/types';

interface PlanHistoryProps {
  history: PlanHistoryItem[];
  currentPlanId: string | null;
  onPlanSelect: (plan: Plan) => void;
}

export default function PlanHistory({
  history,
  currentPlanId,
  onPlanSelect,
}: PlanHistoryProps) {
  async function handlePlanClick(planId: string) {
    try {
      const plan = await getPlan(planId);
      onPlanSelect(plan);
    } catch (error) {
      console.error('Failed to load plan:', error);
    }
  }

  function formatDate(dateString: string | null) {
    if (!dateString) return 'No date';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return 'Invalid date';
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 bg-gray-50">
        <h2 className="font-semibold text-gray-900">Plan History</h2>
        <p className="text-xs text-gray-500 mt-1">
          {history.length} plan{history.length !== 1 ? 's' : ''}
        </p>
      </div>

      {/* History List */}
      <div className="flex-1 overflow-y-auto">
        {history.length === 0 ? (
          <div className="p-4 text-center text-gray-500 text-sm">
            <p>No plans yet.</p>
            <p className="mt-1">Start chatting to create your first plan!</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {history.map((item) => (
              <button
                key={item.plan_id}
                onClick={() => handlePlanClick(item.plan_id)}
                className={`w-full p-4 text-left hover:bg-gray-50 transition-colors ${
                  currentPlanId === item.plan_id ? 'bg-blue-50 border-l-4 border-blue-600' : ''
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-medium text-gray-900 text-sm line-clamp-2 flex-1">
                    {item.goal}
                  </h3>
                  {currentPlanId === item.plan_id && (
                    <span className="px-2 py-1 bg-blue-600 text-white text-xs rounded">
                      Current
                    </span>
                  )}
                </div>
                <div className="mt-2 flex items-center gap-2 text-xs text-gray-500">
                  <span>{item.num_days} days</span>
                  <span>•</span>
                  <span>{formatDate(item.created_at)}</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
