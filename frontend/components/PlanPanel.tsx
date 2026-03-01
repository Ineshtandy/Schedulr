'use client';

import { useEffect, useMemo, useState } from 'react';
import { deletePlanDeployment, deployPlan, updatePlanDeployment } from '@/lib/api';
import { Conversation, Plan } from '@/lib/types';
import PlanCalendar from '@/components/plan/PlanCalendar';
import DayButtons from '@/components/plan/DayButtons';
import DayDetail from '@/components/plan/DayDetail';

interface PlanPanelProps {
  plan: Plan | null;
  planId: string | null;
  isLoading: boolean;
  planUpdating?: boolean;
  conversation: Conversation | null;
  onRefreshConversation?: () => void;
}

export default function PlanPanel({ 
  plan, 
  planId, 
  isLoading, 
  planUpdating = false,
  conversation,
  onRefreshConversation,
}: PlanPanelProps) {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [isDeploying, setIsDeploying] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [status, setStatus] = useState('');
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  useEffect(() => {
    setSelectedIndex(0);
  }, [planId]);

  const selectedDay = useMemo(() => {
    if (!plan || plan.days.length === 0) return null;
    return plan.days[Math.min(selectedIndex, plan.days.length - 1)];
  }, [plan, selectedIndex]);

  const isDeployed = conversation?.is_deployed || false;

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
      // Refresh conversation to get updated deployment status
      if (onRefreshConversation) {
        setTimeout(() => onRefreshConversation(), 500);
      }
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Deployment failed';
      setStatus(`❌ ${message}`);
    } finally {
      setIsDeploying(false);
    }
  }

  async function onUpdateDeployment() {
    if (!planId) return;
    setIsUpdating(true);
    setStatus('');
    try {
      const result = await updatePlanDeployment(planId);
      setStatus(`✅ Plan updated: ${result.created_count} tasks deployed`);
      // Refresh conversation to get updated deployment status
      if (onRefreshConversation) {
        setTimeout(() => onRefreshConversation(), 500);
      }
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Update failed';
      setStatus(`❌ ${message}`);
    } finally {
      setIsUpdating(false);
    }
  }

  async function onDeleteDeployment() {
    if (!planId) return;
    setIsDeleting(true);
    setStatus('');
    setShowDeleteConfirm(false);
    try {
      await deletePlanDeployment(planId);
      setStatus('✅ Plan deleted from Google Tasks');
      // Refresh conversation to clear deployment status
      if (onRefreshConversation) {
        setTimeout(() => onRefreshConversation(), 500);
      }
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Deletion failed';
      setStatus(`❌ ${message}`);
    } finally {
      setIsDeleting(false);
    }
  }

  if (!plan) {
    return (
      <div className="h-full flex items-center justify-center text-center text-gray-700 p-6">
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
            <p className="text-sm text-gray-800">Updating plan…</p>
          </div>
        </div>
      )}

      {/* Delete confirmation modal */}
      {showDeleteConfirm && (
        <div className="absolute inset-0 bg-black/40 z-20 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Delete Plan from Google Tasks?</h3>
            <p className="text-sm text-gray-700 mb-4">
              This will permanently delete the task list from Google Tasks. This action cannot be undone.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="flex-1 px-4 py-2 bg-gray-100 border border-gray-400 rounded-lg hover:bg-gray-200 text-gray-800"
              >
                Cancel
              </button>
              <button
                onClick={onDeleteDeployment}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="p-6 border-b border-gray-200 space-y-3">
        <div className="flex items-start gap-2">
          <h3 className="text-lg font-semibold text-gray-900 line-clamp-2 flex-1">{plan.goal}</h3>
          {isDeployed && <span className="text-xl flex-shrink-0">✅</span>}
        </div>
        <p className="text-sm text-gray-800">{plan.num_days} days • {plan.minutes_per_day} min/day</p>
        
        {!isDeployed ? (
          <button
            onClick={onDeploy}
            disabled={isDeploying || isLoading || !planId}
            className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
          >
            {isDeploying ? 'Deploying…' : 'Deploy to Google Tasks'}
          </button>
        ) : (
          <div className="flex gap-2">
            <button
              onClick={onUpdateDeployment}
              disabled={isUpdating || isLoading || !planId}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {isUpdating ? 'Updating…' : 'Update plan'}
            </button>
            <button
              onClick={() => setShowDeleteConfirm(true)}
              disabled={isDeleting || isLoading || !planId}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
            >
              {isDeleting ? 'Deleting…' : 'Delete plan'}
            </button>
          </div>
        )}
        
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
