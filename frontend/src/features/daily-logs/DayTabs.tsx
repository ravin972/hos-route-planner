import { useState, type ReactNode } from 'react'
import { Tabs } from '../../components/ui/Tabs'
import type { DailyLog } from '../../types/trip'

interface DayTabsProps {
  days: DailyLog[]
  children: (day: DailyLog) => ReactNode
}

export function DayTabs({ days, children }: DayTabsProps) {
  const [activeId, setActiveId] = useState(days[0] ? String(days[0].day_number) : '')
  const activeDay = days.find((day) => String(day.day_number) === activeId) ?? days[0]

  if (!activeDay) return null

  return (
    <div className="space-y-4">
      <Tabs
        aria-label="Select day"
        items={days.map((day) => ({ id: String(day.day_number), label: `Day ${day.day_number}` }))}
        activeId={activeId}
        onChange={setActiveId}
      />
      {children(activeDay)}
    </div>
  )
}
