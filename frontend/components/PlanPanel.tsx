'use client';

import { useEffect, useMemo, useState } from 'react';
import { deployPlan } from '@/lib/api';
import { Plan } from '@/lib/types';
import PlanCalendar from '@/components/plan/PlanCalendar';
import DayButtons from '@/components/plan/DayButtons';
import DayDetail from '@/components/plan/DayDetail';

interface PlanPanelProps {
  plan: Plan | null;
  planId: string | null;
  isLoading: boolean;
  planUpdating?: boolean;
}

export default function PlanPanel({ plan, planId, isLoading, planUpdating = false }: PlanPanelProps) {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [isDeploying, setIsDeploying] = useState(false);
  const [status, setStatus] = useState('');

  useEffect(() => {
    setSelectedIndex(0);
  }, [planId]);

  const selectedDay = useMemo(() => {
    if (!plan || plan.days.length === 0) return null;
    return plan.days[Math.min(selectedIndex, plan.days.length - 1)];
  }, [plan, selectedIndex]);

  function onSelectDate(date: string) {
    if (!plan) return;
    const idx = plan.days.findIndex((d) => d.date === date);
    if (idx >= 0) setSelectedIndex(idx);
  }

  async function onDeploy() {
    if (!planId) return;
    setIsDeploying(true);
    setStatus('');
    try {
      const result = await deployPlan(planId);
      setStatus(`✅ ${result.created_count} tasks deployed (${result.tasklist_title})`);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Deployment failed';
      setStatus(`❌ ${message}`);
    } finally {
      setIsDeploying(false);
    }
  }

  if (!plan) {
    return (
      <div className="h-full flex items-center justify-center text-center text-gray-500 p-6">
        <div>
          <p className="text-lg font-medium text-gray-800">No plan selected</p>
          <p className="text-sm mt-1">Open or create a chat to generate a plan.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col relative">
      {/* Loading overlay while plan is being generated/updated */}
      {planUpdating && (
        <div className="absolute inset-0 bg-white/70 backdrop-blur-sm z-10 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
            <p className="text-sm text-gray-600">Updating plan…</p>
          </div>
        </div>
      )}

      <div className="p-6 border-b border-gray-200 space-y-3">
        <h3 className="text-lg font-semibold text-gray-900 line-clamp-2">{plan.goal}</h3>
        <p className="text-sm text-gray-600">{plan.num_days} days • {plan.minutes_per_day} min/day</p>
        <button
          onClick={onDeploy}
          disabled={isDeploying || isLoading || !planId}
          className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
        >
          {isDeploying ? 'Deploying…' : 'Deploy to Google Tasks'}
        </button>
        {status && <p className="text-sm text-gray-700">{status}</p>}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <PlanCalendar
          days={plan.days}
          selectedDate={selectedDay?.date || plan.start_date}
          onSelectDate={onSelectDate}
        />

        <DayButtons
          days={plan.days}
          selectedIndex={selectedIndex}
          onSelectIndex={setSelectedIndex}
        />

        {selectedDay && <DayDetail day={selectedDay} />}
      </div>
    </div>
  );
}
