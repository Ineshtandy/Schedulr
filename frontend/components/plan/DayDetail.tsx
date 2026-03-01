'use client';

import { DayPlan } from '@/lib/types';

interface DayDetailProps {
  day: DayPlan;
}

export default function DayDetail({ day }: DayDetailProps) {
  return (
    <div className="space-y-3">
      <div>
        <h4 className="font-semibold text-gray-900">{day.date}</h4>
        <p className="text-xs text-gray-700">{day.tasks.length} tasks</p>
      </div>

      {day.tasks.length === 0 && (
        <div className="text-sm text-gray-800">No tasks on this day.</div>
      )}

      {day.tasks.map((task, idx) => (
        <div key={`${task.title}-${idx}`} className="border border-gray-200 rounded-lg p-3">
          <div className="flex items-start justify-between gap-2">
            <p className="font-medium text-gray-900">{task.title}</p>
            <span className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-700">{task.priority}</span>
          </div>
          <p className="text-sm text-gray-800 mt-1">{task.duration_min} min</p>
          {task.notes && <p className="text-sm text-gray-900 mt-2 whitespace-pre-wrap">{task.notes}</p>}
        </div>
      ))}
    </div>
  );
}
