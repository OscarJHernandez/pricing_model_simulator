const base = import.meta.env.VITE_API_BASE ?? ''

async function parse<T>(res: Promise<Response>): Promise<T> {
  const r = await res
  if (!r.ok) {
    const t = await r.text()
    throw new Error(t || r.statusText)
  }
  return r.json() as Promise<T>
}

export function getHealth() {
  return parse<{ status: string }>(fetch(`${base}/api/health`))
}

export type RunListItem = {
  id: string
  status: string
  seed: number
  horizon_days: number
  customer_count: number
  created_at: string | null
  completed_at: string | null
}

export type RunDetail = RunListItem & {
  baseline_end_day: number
  experiment_start_day: number
  error_message: string | null
  parameters: Record<string, unknown>
}

export type DailyRow = {
  day: number
  phase: string
  treatment: string | null
  location_zone: string | null
  metrics: Record<string, number>
}

export type CustomerRow = {
  id: number
  customer_index: number
  budget: number
  buy_propensity: number
  price_threshold: number
  basket_mean: number
  location_zone: string
}

export type TreatmentRow = { customer_id: number; treatment: string }

export async function listRuns() {
  return parse<RunListItem[]>(fetch(`${base}/api/runs`))
}

export async function createRun(body: Record<string, unknown>) {
  return parse<{ id: string; status: string }>(
    fetch(`${base}/api/runs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  )
}

export async function getRun(id: string) {
  return parse<RunDetail>(fetch(`${base}/api/runs/${id}`))
}

export async function getDaily(id: string) {
  return parse<DailyRow[]>(fetch(`${base}/api/runs/${id}/daily`))
}

export async function getCustomers(id: string, limit = 500) {
  return parse<CustomerRow[]>(
    fetch(`${base}/api/runs/${id}/customers?limit=${limit}`),
  )
}

export async function getTreatments(id: string) {
  return parse<TreatmentRow[]>(fetch(`${base}/api/runs/${id}/treatments`))
}
