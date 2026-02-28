'use client';

import { useState } from 'react';
import { deployPlan } from '@/lib/api';
import { Plan } from '@/lib/types';

interface PlanViewerProps {
  plan: Plan | null;
  planId: string | null;
  onDeploySuccess: () => void;
}

export default function PlanViewer({
  plan,
  planId,
  onDeploySuccess,
}: PlanViewerProps) {
  const [isDeploying, setIsDeploying] = useState(false);
  const [deployMessage, setDeployMessage] = useState('');
  const [expandedDays, setExpandedDays] = useState<Set<number>>(new Set([0]));

  async function handleDeploy() {
    if (!planId) return;

    setIsDeploying(true);
    setDeployMessage('');

    try {
      const response = await deployPlan({ plan_id: planId });
      setDeployMessage(
        `✅ Successfully deployed ${response.created_count} tasks to Google Tasks!`
      );
      onDeploySuccess();
    } catch (error: any) {
      setDeployMessage(`❌ Deployment failed: ${error.message}`);
    } finally {
      setIsDeploying(false);
    }
  }

  function toggleDay(dayIndex: number) {
    const newExpanded = new Set(expandedDays);
    if (newExpanded.has(dayIndex)) {
      newExpanded.delete(dayIndex);
    } else {
      newExpanded.add(dayIndex);
    }
    setExpandedDays(newExpanded);
  }

  if (!plan) {
    return (
      <div className="flex items-center justify-center h-full p-8 text-center text-gray-500">
        <div>
          <div className="text-6xl mb-4">📋</div>
          <p className="text-lg">No plan yet.</p>
          <p className="text-sm mt-2">Start chatting to generate one!</p>
        </div>
      </div>
    );
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'bg-red-100 text-red-800';
      case 'med':
        return 'bg-yellow-100 text-yellow-800';
      case 'low':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-6 border-b border-gray-200 bg-white">
        <h2 className="text-xl font-bold text-gray-900 mb-2">{plan.goal}</h2>
        <p className="text-sm text-gray-600">
          {plan.num_days} days • {plan.minutes_per_day} min/day
        </p>
        <p className="text-xs text-gray-500 mt-1">
          Starting {plan.start_date}
        </p>

        {/* Deploy Button */}
        <button
          onClick={handleDeploy}
          disabled={isDeploying}
          className="mt-4 w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-semibold"
        >
          {isDeploying ? 'Deploying...' : '🚀 Deploy to Google Tasks'}
        </button>

        {deployMessage && (
          <div
            className={`mt-3 p-2 rounded text-sm ${
              deployMessage.startsWith('✅')
                ? 'bg-green-50 text-green-800'
                : 'bg-red-50 text-red-800'
            }`}
          >
            {deployMessage}
          </div>
        )}
      </div>

      {/* Days List */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {plan.days.map((day, dayIndex) => (
          <div key={dayIndex} className="border border-gray-200 rounded-lg overflow-hidden">
            {/* Day Header */}
            <button
              onClick={() => toggleDay(dayIndex)}
              className="w-full px-4 py-3 bg-gray-50 hover:bg-gray-100 flex items-center justify-between transition-colors"
            >
              <div className="text-left">
                <h3 className="font-semibold text-gray-900">
                  Day {dayIndex + 1}
                </h3>
                <p className="text-sm text-gray-600">{day.date}</p>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-500">
                  {day.tasks.length} tasks
                </span>
                <span className="text-gray-400">
                  {expandedDays.has(dayIndex) ? '▼' : '▶'}
                </span>
              </div>
            </button>

            {/* Tasks */}
            {expandedDays.has(dayIndex) && (
              <div className="p-4 space-y-3">
                {day.tasks.map((task, taskIndex) => (
                  <div
                    key={taskIndex}
                    className="border border-gray-200 rounded p-3 hover:border-gray-300 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <h4 className="font-medium text-gray-900 flex-1">
                        {task.title}
                      </h4>
                      <span
                        className={`px-2 py-1 text-xs rounded ${getPriorityColor(
                          task.priority
                        )}`}
                      >
                        {task.priority}
                      </span>
                    </div>

                    <div className="mt-2 text-sm text-gray-600">
                      ⏱️ {task.duration_min} min
                    </div>

                    {task.notes && (
                      <div className="mt-2 text-sm text-gray-700 whitespace-pre-wrap">
                        {task.notes}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
