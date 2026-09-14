import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/lib/utils'

const badgeVariants = cva('inline-flex items-center rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em]', {
  variants: {
    variant: {
      default: 'border-cyan-400/20 bg-cyan-400/10 text-cyan-200',
      secondary: 'border-slate-700 bg-slate-800/80 text-slate-300',
      success: 'border-emerald-400/20 bg-emerald-400/10 text-emerald-300',
      warning: 'border-amber-400/20 bg-amber-400/10 text-amber-200',
      danger: 'border-rose-400/20 bg-rose-400/10 text-rose-200',
      muted: 'border-slate-800 bg-slate-900 text-slate-400',
    },
  },
  defaultVariants: { variant: 'default' },
})

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { Badge }
