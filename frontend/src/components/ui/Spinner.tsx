import { Loader2 } from 'lucide-react'
import { cn } from '../../lib/cn'

interface SpinnerProps {
  className?: string
  label?: string
}

export function Spinner({ className, label = 'Loading' }: SpinnerProps) {
  return (
    <span role="status" className="inline-flex items-center">
      <Loader2 aria-hidden="true" className={cn('h-4 w-4 animate-spin', className)} />
      <span className="sr-only">{label}</span>
    </span>
  )
}
