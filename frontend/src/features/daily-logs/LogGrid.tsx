import { DUTY_STATUS_LABEL } from '../../lib/constants'
import { LOG_GRID_GEOMETRY, ROW_ORDER, buildLogPath, generateTicks } from '../../lib/logGeometry'
import type { DailyLogSegment } from '../../types/trip'

const GEOMETRY = LOG_GRID_GEOMETRY
const TOTALS_COLUMN_X = GEOMETRY.gridLeft + GEOMETRY.gridWidth + 40
const VIEW_WIDTH = TOTALS_COLUMN_X + 40
const VIEW_HEIGHT = GEOMETRY.gridTop + ROW_ORDER.length * GEOMETRY.rowHeight + 40

interface LogGridProps {
  segments: DailyLogSegment[]
  totals: { OFF: number; SB: number; D: number; ON: number }
  title?: string
}

export function LogGrid({ segments, totals, title }: LogGridProps) {
  const ticks = generateTicks(GEOMETRY)
  const gridBottom = GEOMETRY.gridTop + ROW_ORDER.length * GEOMETRY.rowHeight
  const path = buildLogPath(segments, GEOMETRY)

  return (
    <div className="overflow-x-auto">
      <svg
        viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`}
        role="img"
        className="w-full min-w-[900px] bg-surface"
      >
        <title>{title ?? 'Daily duty status log'}</title>
        <desc>
          A 24-hour grid with four duty-status rows: Off Duty, Sleeper Berth, Driving, On Duty (Not
          Driving). See the remarks table below for the same information as accessible text.
        </desc>

        {ROW_ORDER.map((status, index) => {
          const y = GEOMETRY.gridTop + index * GEOMETRY.rowHeight
          return (
            <g key={status}>
              <rect
                x={GEOMETRY.gridLeft}
                y={y}
                width={GEOMETRY.gridWidth}
                height={GEOMETRY.rowHeight}
                fill={index % 2 === 0 ? '#ffffff' : '#fafbfc'}
                stroke="#e3e6ea"
              />
              <text
                x={GEOMETRY.gridLeft - 8}
                y={y + GEOMETRY.rowHeight / 2}
                textAnchor="end"
                dominantBaseline="middle"
                fontSize={11}
                fontFamily="var(--font-sans)"
                fill="#5b6472"
              >
                {DUTY_STATUS_LABEL[status]}
              </text>
              <text
                x={TOTALS_COLUMN_X}
                y={y + GEOMETRY.rowHeight / 2}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize={12}
                fontWeight={600}
                fontFamily="var(--font-mono)"
                fill="#14181f"
              >
                {totals[status].toFixed(2)}
              </text>
            </g>
          )
        })}

        {ticks.map((tick) => {
          const length = tick.weight === 'hour' ? 10 : tick.weight === 'half' ? 6 : 3
          return (
            <line
              key={tick.minute}
              x1={tick.x}
              x2={tick.x}
              y1={gridBottom}
              y2={gridBottom + length}
              stroke="#8b93a1"
              strokeWidth={tick.weight === 'hour' ? 1 : 0.5}
            />
          )
        })}
        {ticks
          .filter((tick) => tick.weight === 'hour')
          .map((tick) => (
            <text
              key={`label-${tick.minute}`}
              x={tick.x}
              y={gridBottom + 22}
              textAnchor="middle"
              fontSize={8}
              fontFamily="var(--font-sans)"
              fill="#8b93a1"
            >
              {tick.label}
            </text>
          ))}

        <path d={path} fill="none" stroke="#14181f" strokeWidth={2.5} strokeLinejoin="round" />
      </svg>
    </div>
  )
}
