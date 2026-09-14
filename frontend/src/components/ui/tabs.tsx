import * as TabsPrimitive from '@radix-ui/react-tabs'

import { cn } from '@/lib/utils'

const Tabs = TabsPrimitive.Root
const TabsList = ({ className, ...props }: TabsPrimitive.TabsListProps) => <TabsPrimitive.List className={cn('inline-flex items-center rounded-lg border border-slate-800 bg-slate-950/70 p-1', className)} {...props} />
const TabsTrigger = ({ className, ...props }: TabsPrimitive.TabsTriggerProps) => <TabsPrimitive.Trigger className={cn('rounded-md px-3 py-2 text-xs font-medium text-slate-400 transition data-[state=active]:bg-slate-800 data-[state=active]:text-slate-100', className)} {...props} />
const TabsContent = ({ className, ...props }: TabsPrimitive.TabsContentProps) => <TabsPrimitive.Content className={cn('mt-4 outline-none', className)} {...props} />

export { Tabs, TabsList, TabsTrigger, TabsContent }
