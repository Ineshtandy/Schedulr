'use client';

import { DayPlan } from '@/lib/types';

interface DayButtonsProps {
  days: DayPlan[];
  selectedIndex: number;
  onSelectIndex: (index: number) => void;
}

export default function DayButtons({ days, selectedIndex, onSelectIndex }: DayButtonsProps) {
  return (
    <div className="overflow-x-auto py-2">
      <div className="flex gap-2 min-w-max">
        {days.map((day, idx) => (
          <button
            key={`${day.date}-${idx}`}
            onClick={() => onSelectIndex(idx)}
            className={`px-3 py-1.5 rounded-full border text-sm ${
              idx === selectedIndex
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
            }`}
          >
            Day {idx + 1}
          </button>
        ))}
      </div>
    </div>
  );
}
