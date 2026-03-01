'use client';

import Calendar from 'react-calendar';
import { DayPlan } from '@/lib/types';

interface PlanCalendarProps {
  days: DayPlan[];
  selectedDate: string;
  onSelectDate: (date: string) => void;
}

export default function PlanCalendar({ days, selectedDate, onSelectDate }: PlanCalendarProps) {
  const taskDates = new Set(days.filter((day) => day.tasks.length > 0).map((day) => day.date));
  const selected = selectedDate ? new Date(selectedDate) : new Date();

  return (
    <div className="rounded-lg border border-gray-200 p-2 bg-white">
      <Calendar
        value={selected}
        onChange={(value) => {
          const picked = Array.isArray(value) ? value[0] : value;
          if (!picked) return;
          onSelectDate(picked.toISOString().slice(0, 10));
        }}
        tileContent={({ date, view }) => {
          if (view !== 'month') return null;
          const iso = date.toISOString().slice(0, 10);
          if (!taskDates.has(iso)) return null;
          return <div className="mx-auto mt-1 h-1.5 w-1.5 rounded-full bg-blue-600" />;
        }}
      />
    </div>
  );
}
