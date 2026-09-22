import type { HTMLAttributes, ReactNode } from 'react'
import { cn } from '../../lib/cn'

type Tone = 'neutral' | 'accent' | 'success' | 'warning' | 'danger'

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: Tone
  children: ReactNode
}

const TONE_CLASSES: Record<Tone, string> = {
  neutral: 'bg-ink/5 text-ink-secondary',
  accent: 'bg-accent-tint text-accent',
  success: 'bg-success-tint text-success',
  warning: 'bg-warning-tint text-warning',
  danger: 'bg-danger-tint text-danger',
}

/** A small status tag -- deliberately a low-radius rectangle, not a full pill (DESIGN.md section 6:
 * pills are retired as the default tag shape). */
export function Badge({ tone = 'neutral', className, children, ...rest }: BadgeProps) {
  return (
    <span
      className={cn(
        'text-caption inline-flex items-center rounded-sm px-1.5 py-0.5 font-medium',
        TONE_CLASSES[tone],
        className,
      )}
      {...rest}
    >
      {children}
    </span>
  )
}
