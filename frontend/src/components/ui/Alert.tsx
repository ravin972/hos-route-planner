import { AlertTriangle, Info } from 'lucide-react'
import type { ReactNode } from 'react'
import { cn } from '../../lib/cn'

type Variant = 'info' | 'error' | 'violation'

interface AlertProps {
  variant: Variant
  title?: string
  children: ReactNode
  action?: ReactNode
  className?: string
}

const VARIANT_CLASSES: Record<Variant, string> = {
  info: 'border-accent/20 bg-accent-tint text-ink',
  error: 'border-danger/20 bg-danger-tint text-ink',
  violation: 'border-danger/30 bg-danger-tint text-ink',
}

const ICON_CLASSES: Record<Variant, string> = {
  info: 'text-accent',
  error: 'text-danger',
  violation: 'text-danger',
}

const ICON: Record<Variant, typeof AlertTriangle> = {
  info: Info,
  error: AlertTriangle,
  violation: AlertTriangle,
}

export function Alert({ variant, title, children, action, className }: AlertProps) {
  const Icon = ICON[variant]
  return (
    <div
      role="alert"
      className={cn('flex gap-3 rounded-md border p-4', VARIANT_CLASSES[variant], className)}
    >
      <Icon aria-hidden="true" className={cn('mt-0.5 h-5 w-5 shrink-0', ICON_CLASSES[variant])} />
      <div className="flex-1 space-y-2">
        {title && <p className="text-body font-semibold">{title}</p>}
        <div className="text-body">{children}</div>
        {action}
      </div>
    </div>
  )
}
