import type { HTMLAttributes, ReactNode } from 'react'
import { cn } from '../../lib/cn'

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode
}

export function Card({ className, children, ...rest }: CardProps) {
  return (
    <div
      className={cn('rounded-md border border-border bg-surface p-5 sm:p-6', className)}
      {...rest}
    >
      {children}
    </div>
  )
}
