import * as SelectPrimitive from '@radix-ui/react-select'
import { Check, ChevronDown } from 'lucide-react'

import { cn } from '@/lib/utils'

const Select = SelectPrimitive.Root
const SelectValue = SelectPrimitive.Value
const SelectGroup = SelectPrimitive.Group

const SelectContent = ({ className, children, position = 'popper', ...props }: SelectPrimitive.SelectContentProps & { position?: 'item-aligned' | 'popper' }) => (
  <SelectPrimitive.Portal>
    <SelectPrimitive.Content className={cn('relative z-50 min-w-[12rem] overflow-hidden rounded-lg border border-slate-700 bg-slate-900 text-slate-100 shadow-2xl', position === 'popper' && 'translate-y-1', className)} position={position} {...props}>
      <SelectPrimitive.Viewport className="p-1">{children}</SelectPrimitive.Viewport>
    </SelectPrimitive.Content>
  </SelectPrimitive.Portal>
)

const SelectItem = ({ className, children, ...props }: SelectPrimitive.SelectItemProps) => (
  <SelectPrimitive.Item className={cn('relative flex w-full cursor-default select-none items-center rounded-md py-2 pl-8 pr-3 text-sm outline-none focus:bg-slate-800 data-[disabled]:pointer-events-none data-[disabled]:opacity-50', className)} {...props}>
    <span className="absolute left-2 flex h-4 w-4 items-center justify-center"><SelectPrimitive.ItemIndicator><Check className="h-4 w-4 text-cyan-300" /></SelectPrimitive.ItemIndicator></span>
    <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
  </SelectPrimitive.Item>
)

function SelectTriggerStyled({ className, children, ...props }: SelectPrimitive.SelectTriggerProps) {
  return <SelectPrimitive.Trigger className={cn('flex h-10 w-full items-center justify-between rounded-lg border border-slate-700 bg-slate-950/70 px-3 text-sm text-slate-100 outline-none transition-colors focus:border-cyan-400/70 data-[placeholder]:text-slate-500', className)} {...props}>{children}<SelectPrimitive.Icon><ChevronDown className="h-4 w-4 text-slate-500" /></SelectPrimitive.Icon></SelectPrimitive.Trigger>
}

export { Select, SelectValue, SelectGroup, SelectTriggerStyled as SelectTrigger, SelectContent, SelectItem }
