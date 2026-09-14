import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent, DragEvent } from 'react'
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Check,
  ChevronDown,
  CircleDot,
  FileCode2,
  FileText,
  Loader2,
  Play,
  ShieldCheck,
  UploadCloud,
  XCircle,
  Zap,
} from 'lucide-react'
import { toast, Toaster } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { cn } from '@/lib/utils'

type StageStatus = 'pending' | 'running' | 'done' | 'skipped' | 'failed'
type Stage = { name: string; status: StageStatus; detail: string }
type Anomaly = { timestamp: string; severity: string; message: string; raw_context: string }
type Diagnosis = { likely_cause: string; confidence: 'high' | 'medium' | 'low'; explanation: string; suggested_fix_type: 'code' | 'config' | 'infra' | 'unknown' }
type FixDraft = { fix_type: 'code' | 'config' | 'manual'; file_hint: string; diff_or_snippet: string; explanation: string; risk_level: 'low' | 'medium' | 'high' }
type TestResult = { status: 'passed' | 'failed' | 'skipped'; checks_run: string[]; summary: string }
type DiagnosisEntry = { anomaly: Anomaly; diagnosis: Diagnosis; fix_draft: FixDraft; test_result: TestResult }
type AnalyzeResponse = { anomalies: Anomaly[]; diagnoses: DiagnosisEntry[]; status: string }

const API_URL = 'http://localhost:8000'
const stageNames = ['Log Watcher', 'Root Cause', 'Fix Drafting', 'Test Runner']
const emptyStages: Stage[] = stageNames.map((name, index) => ({ name, status: index === 0 ? 'running' : 'pending', detail: index === 0 ? 'Ready to scan signals' : 'Waiting to begin' }))

function App() {
  const [samples, setSamples] = useState<string[]>([])
  const [selectedSample, setSelectedSample] = useState('')
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null)
  const [stages, setStages] = useState<Stage[]>(emptyStages)
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [fileName, setFileName] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const [activeAnomaly, setActiveAnomaly] = useState('0')
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    let cancelled = false
    const fetchSamples = async () => {
      try {
        const response = await fetch(`${API_URL}/samples`)
        if (!response.ok) throw new Error('Unable to load sample logs')
        const data = await response.json()
        if (cancelled) return
        setSamples(data.samples ?? [])
        if (data.samples?.length) setSelectedSample(data.samples[0])
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Could not load sample logs')
      }
    }
    void fetchSamples()
    return () => { cancelled = true }
  }, [])

  const setStage = (index: number, status: StageStatus, detail: string) => {
    setStages((current) => current.map((stage, stageIndex) => stageIndex === index ? { ...stage, status, detail } : stage))
  }

  const setSelectedFile = (file?: File) => {
    if (!file) return
    setFileName(file.name)
    setSelectedSample('')
  }

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => setSelectedFile(event.target.files?.[0])
  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setIsDragging(false)
    setSelectedFile(event.dataTransfer.files?.[0])
  }

  const runAnalysis = async () => {
    setIsLoading(true)
    setError('')
    setAnalysis(null)
    setActiveAnomaly('0')
    setStages(stageNames.map((name, index) => ({ name, status: index === 0 ? 'running' : 'pending', detail: index === 0 ? 'Scanning log signals' : 'Waiting to begin' })))

    try {
      const formData = new FormData()
      const uploadedFile = fileInputRef.current?.files?.[0]
      if (uploadedFile) formData.append('file', uploadedFile)
      else if (selectedSample) formData.append('sample_name', selectedSample)
      else throw new Error('Select a sample log or upload a log file first.')

      setStage(1, 'running', 'Correlating evidence')
      const response = await fetch(`${API_URL}/analyze`, { method: 'POST', body: formData })
      if (!response.ok) throw new Error((await response.text()) || 'Pipeline request failed')
      const data: AnalyzeResponse = await response.json()
      setAnalysis(data)
      const first = data.diagnoses[0]
      setStages([
        { name: 'Log Watcher', status: 'done', detail: `${data.anomalies.length} signal${data.anomalies.length === 1 ? '' : 's'} flagged` },
        { name: 'Root Cause', status: 'done', detail: first?.diagnosis.confidence ? `${first.diagnosis.confidence} confidence` : 'Diagnosis complete' },
        { name: 'Fix Drafting', status: first?.fix_draft.fix_type === 'manual' ? 'skipped' : 'done', detail: first?.fix_draft.file_hint || 'Reviewable proposal returned' },
        { name: 'Test Runner', status: first?.test_result.status === 'skipped' ? 'skipped' : first?.test_result.status === 'failed' ? 'failed' : 'done', detail: first?.test_result.status === 'passed' ? 'Static checks passed' : first?.test_result.summary || 'Manual review required' },
      ])
      toast.success('Pipeline complete', { description: `${data.anomalies.length} anomaly results are ready for review.` })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Analysis failed'
      setError(message)
      setStages((current) => current.map((stage, index) => index === 0 ? { ...stage, status: 'failed', detail: 'Pipeline stopped' } : { ...stage, status: 'pending', detail: 'Blocked by previous stage' }))
      toast.error('Pipeline failed', { description: message })
    } finally {
      setIsLoading(false)
    }
  }

  const currentEntry = analysis?.diagnoses[Number(activeAnomaly)]

  return (
    <div className="min-h-screen overflow-x-hidden bg-black text-slate-100">
      <Toaster position="bottom-right" theme="dark" toastOptions={{ className: 'border-slate-700 bg-slate-900 text-slate-100' }} />
      <div className="relative mx-auto max-w-7xl px-5 py-6 sm:px-8 lg:py-8">
        <header className="mb-10 flex items-center justify-between border-b border-slate-800/80 pb-5">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-cyan-400/30 bg-cyan-400/10 text-cyan-300"><Activity className="h-5 w-5" /></div>
            <div><p className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-300">DevOps Agent</p><p className="mt-1 text-xs text-slate-500">Infrastructure intelligence workspace</p></div>
          </div>
        </header>

        <main className="space-y-7">
          <section className="grid gap-6 lg:grid-cols-[1fr_0.62fr] lg:items-end">
            <div><p className="mb-3 text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Incident analysis</p><h1 className="max-w-3xl text-3xl font-semibold tracking-tight text-white sm:text-4xl">Find the signal before it becomes an outage.</h1><p className="mt-4 max-w-2xl text-sm leading-6 text-slate-400">Send a production log through four focused agents. Review the evidence, root cause, proposed remediation, and safe validation state in one place.</p></div>
            <Card className="border-cyan-400/10 bg-slate-900/60"><CardContent className="flex items-center gap-4 p-4"><div className="rounded-lg bg-emerald-400/10 p-2.5 text-emerald-300"></div><div><p className="text-xs uppercase tracking-[0.18em] text-slate-500">System posture</p><p className="mt-1 text-sm font-medium text-slate-200">Ready for incident review</p></div></CardContent></Card>
          </section>

          <Card className="overflow-hidden border-slate-800/90 bg-slate-900/80">
            <CardHeader className="border-b border-slate-800/80"><CardTitle>Choose an evidence source</CardTitle><CardDescription>Use a fixture for the demo or bring a sanitized log from your own service.</CardDescription></CardHeader>
            <CardContent className="grid gap-5 p-5 lg:grid-cols-[1fr_1fr_auto] lg:items-end">
              <div className="space-y-2"><label className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Sample log</label><Select value={selectedSample} onValueChange={(value) => { setSelectedSample(value); setFileName('') }}><SelectTrigger><SelectValue placeholder="Select a sample" /></SelectTrigger><SelectContent>{samples.map((sample) => <SelectItem key={sample} value={sample}>{sample}</SelectItem>)}</SelectContent></Select></div>
              <div className="space-y-2"><label className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Custom evidence</label><div onDragOver={(event) => { event.preventDefault(); setIsDragging(true) }} onDragLeave={() => setIsDragging(false)} onDrop={handleDrop} onClick={() => fileInputRef.current?.click()} className={cn('flex h-10 cursor-pointer items-center gap-3 rounded-lg border border-dashed px-3 text-sm transition-all', isDragging ? 'border-cyan-300 bg-cyan-400/10 text-cyan-100' : 'border-slate-700 bg-slate-950/50 text-slate-400 hover:border-slate-500 hover:text-slate-200')}><UploadCloud className="h-4 w-4 text-cyan-300" /><span className="truncate">{fileName || 'Drop a .log file or browse'}</span><input ref={fileInputRef} type="file" accept=".log,.txt" onChange={handleFileChange} className="hidden" /></div></div>
              <Button onClick={() => void runAnalysis()} disabled={isLoading} size="lg" className="min-w-40">{isLoading ? <><Loader2 className="h-4 w-4 animate-spin" />Analyzing</> : <><Play className="h-4 w-4 fill-current" />Analyze log</>}</Button>
            </CardContent>
            {error && <div className="mx-5 mb-5 flex items-start gap-3 rounded-lg border border-rose-500/20 bg-rose-500/10 p-3 text-sm text-rose-200"><XCircle className="mt-0.5 h-4 w-4 shrink-0" />{error}</div>}
          </Card>

          <section>
            <div className="mb-4 flex items-end justify-between"><div><p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Execution graph</p><h2 className="mt-1 text-lg font-semibold text-white">Pipeline status</h2></div><p className="text-xs text-slate-500">{isLoading ? 'Live processing' : analysis ? 'Run complete' : 'Awaiting input'}</p></div>
            <div className="relative grid gap-3 md:grid-cols-4">
              {stages.map((stage, index) => <div key={stage.name} className="relative flex items-stretch gap-3 md:block"><StageCard stage={stage} index={index} entry={analysis?.diagnoses[0]} isLoading={isLoading} />{index < stages.length - 1 && <div className="hidden md:absolute md:-right-3 md:top-1/2 md:flex md:-translate-y-1/2 md:translate-x-1/2 md:items-center"><ArrowRight className={cn('h-4 w-4 transition-colors', stage.status === 'done' ? 'text-emerald-400' : 'text-slate-700')} /></div>}</div>)}
            </div>
          </section>

          {isLoading && <Card className="border-slate-800/90"><CardHeader><Skeleton className="h-4 w-32" /><Skeleton className="h-3 w-64" /></CardHeader><CardContent className="space-y-3"><Skeleton className="h-16 w-full" /><Skeleton className="h-16 w-full" /></CardContent></Card>}

          {analysis && !isLoading && <ResultsPanel analysis={analysis} activeAnomaly={activeAnomaly} setActiveAnomaly={setActiveAnomaly} currentEntry={currentEntry} />}
        </main>

        <footer className="mt-12 flex items-center justify-between border-t border-slate-800/70 pt-5 text-xs text-slate-600"><span>Deterministic detection · evidence-first reasoning</span><span>v0.4 demo workspace</span></footer>
      </div>
    </div>
  )
}

function StageCard({ stage, index, entry, isLoading }: { stage: Stage; index: number; entry?: DiagnosisEntry; isLoading: boolean }) {
  const [open, setOpen] = useState(false)
  const statusVariant = stage.status === 'done' ? 'success' : stage.status === 'skipped' ? 'warning' : stage.status === 'failed' ? 'danger' : stage.status === 'running' ? 'default' : 'muted'
  const detail = index === 1 ? entry?.diagnosis.explanation : index === 2 ? entry?.fix_draft.explanation : index === 3 ? entry?.test_result.summary : `${entry?.anomaly.message || 'Scanning source evidence'}`
  return <Card className={cn('min-h-36 transition-all duration-200', stage.status === 'running' && 'border-cyan-400/40 shadow-lg shadow-cyan-950/20 stage-running', stage.status === 'done' && 'border-emerald-500/20', stage.status === 'skipped' && 'border-amber-500/20')}>
    <CardHeader className="flex-row items-start justify-between space-y-0 pb-3"><div className="flex items-center gap-2.5"><span className="font-mono text-xs text-slate-600">0{index + 1}</span><CardTitle>{stage.name}</CardTitle></div><Badge variant={statusVariant}>{stage.status}</Badge></CardHeader>
    <CardContent className="pb-4"><p className="line-clamp-2 min-h-10 text-xs leading-5 text-slate-400">{isLoading && stage.status === 'running' ? 'Working through the evidence…' : stage.detail}</p>{entry && (stage.status === 'done' || stage.status === 'skipped') && <Collapsible open={open} onOpenChange={setOpen}><CollapsibleTrigger asChild><button className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-cyan-300 hover:text-cyan-200">{open ? 'Hide details' : 'View details'}<ChevronDown className={cn('h-3.5 w-3.5 transition-transform', open && 'rotate-180')} /></button></CollapsibleTrigger><CollapsibleContent className="mt-3 border-t border-slate-800 pt-3 text-xs leading-5 text-slate-400">{detail}</CollapsibleContent></Collapsible>}</CardContent>
  </Card>
}

function ResultsPanel({ analysis, activeAnomaly, setActiveAnomaly, currentEntry }: { analysis: AnalyzeResponse; activeAnomaly: string; setActiveAnomaly: (value: string) => void; currentEntry?: DiagnosisEntry }) {
  return <section className="animate-in fade-in slide-in-from-bottom-2 space-y-4 duration-300"><div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between"><div><p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Review queue</p><h2 className="mt-1 text-lg font-semibold text-white">Agent findings</h2></div><Badge variant="secondary"><AlertTriangle className="mr-1.5 h-3 w-3" />{analysis.anomalies.length} anomalies detected</Badge></div><Tabs value={activeAnomaly} onValueChange={setActiveAnomaly}><TabsList>{analysis.diagnoses.map((entry, index) => <TabsTrigger key={index} value={String(index)}>Anomaly {String(index + 1).padStart(2, '0')} · {entry.anomaly.severity}</TabsTrigger>)}</TabsList>{analysis.diagnoses.map((entry, index) => <TabsContent key={index} value={String(index)}><Finding entry={entry} /></TabsContent>)}</Tabs>{currentEntry && <p className="text-xs text-slate-600">Static validation is intentionally conservative and never executes generated content.</p>}</section>
}

function Finding({ entry }: { entry: DiagnosisEntry }) {
  const { anomaly, diagnosis, fix_draft: fix, test_result: test } = entry
  return <div className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]"><Card><CardHeader><div className="flex items-start justify-between gap-4"><div><CardTitle className="flex items-center gap-2"><FileText className="h-4 w-4 text-cyan-300" />Signal evidence</CardTitle><CardDescription className="mt-1">{anomaly.timestamp}</CardDescription></div><Badge variant={severityVariant(anomaly.severity)}>{anomaly.severity}</Badge></div></CardHeader><CardContent><p className="mb-3 text-sm font-medium text-slate-200">{anomaly.message}</p><pre className="max-h-52 overflow-auto rounded-lg border border-slate-800 bg-slate-950/80 p-3 font-mono text-[11px] leading-5 text-slate-400">{anomaly.raw_context}</pre></CardContent></Card><div className="space-y-4"><Card><CardHeader><div className="flex items-center justify-between"><CardTitle>Root cause</CardTitle><Badge variant={confidenceVariant(diagnosis.confidence)}>{diagnosis.confidence} confidence</Badge></div></CardHeader><CardContent><p className="text-base font-medium text-slate-100">{diagnosis.likely_cause}</p><p className="mt-3 text-sm leading-6 text-slate-400">{diagnosis.explanation}</p></CardContent></Card><Card><CardHeader><div className="flex items-center justify-between"><CardTitle className="flex items-center gap-2"><FileCode2 className="h-4 w-4 text-cyan-300" />Proposed remediation</CardTitle><Badge variant={riskVariant(fix.risk_level)}>{fix.risk_level} risk</Badge></div><CardDescription>{fix.file_hint || 'No file identified'}</CardDescription></CardHeader><CardContent><pre className="min-h-16 overflow-auto rounded-lg border border-slate-800 bg-[#050b13] p-4 font-mono text-xs leading-5 text-cyan-100">{fix.diff_or_snippet || fix.explanation}</pre><div className="mt-3 flex items-center justify-between text-xs text-slate-500"><span>{fix.fix_type === 'manual' ? 'Manual review required' : `${fix.fix_type} proposal`}</span><span className="flex items-center gap-1.5"><TestStatusIcon status={test.status} />Test Runner: {test.status}</span></div></CardContent></Card></div></div>
}

function TestStatusIcon({ status }: { status: TestResult['status'] }) { return status === 'passed' ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : status === 'failed' ? <XCircle className="h-3.5 w-3.5 text-rose-400" /> : <CircleDot className="h-3.5 w-3.5 text-amber-400" /> }
function severityVariant(value: string) { return value.toLowerCase() === 'error' || value.toLowerCase() === 'critical' ? 'danger' as const : value.toLowerCase() === 'warning' ? 'warning' as const : 'secondary' as const }
function confidenceVariant(value: string) { return value === 'high' ? 'success' as const : value === 'medium' ? 'warning' as const : 'danger' as const }
function riskVariant(value: string) { return value === 'low' ? 'success' as const : value === 'medium' ? 'warning' as const : 'danger' as const }

export default App
