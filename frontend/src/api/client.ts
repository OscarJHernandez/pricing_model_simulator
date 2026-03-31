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
  segment: string
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

export async function createRunBatch(body: {
  seeds: number[]
  run: Record<string, unknown>
}) {
  return parse<{ ids: string[]; status: string }>(
    fetch(`${base}/api/runs/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  )
}

export type BayesianArmStats = {
  treatment: string
  posterior_alpha: number
  posterior_beta: number
  conversion_rate_posterior_mean: number
  conversion_rate_credible_low: number
  conversion_rate_credible_high: number
}

export type BayesianComparison = {
  prob_variant_superior: number
  lift_absolute_mean: number
  lift_absolute_median: number
  lift_relative_mean: number | null
  lift_relative_median: number | null
  relative_lift_effective_sample_fraction: number
}

export type BayesianExperimentInference = {
  prior_alpha: number
  prior_beta: number
  mc_samples: number
  relative_lift_p_c_epsilon: number
  control: BayesianArmStats
  variant: BayesianArmStats
  comparison: BayesianComparison
}

export type ExperimentArmStats = {
  treatment: string
  customer_days: number
  orders: number
  conversion_rate: number
  conversion_rate_wilson_low: number
  conversion_rate_wilson_high: number
  net_revenue: number
  contribution_margin: number
}

export type ExperimentInference = {
  run_id: string
  control: ExperimentArmStats
  variant: ExperimentArmStats
  conversion_lift_absolute: number
  conversion_lift_relative: number
  two_proportion_z_statistic: number
  two_proportion_p_value_two_sided: number
  bayesian: BayesianExperimentInference
}

export async function getExperimentInference(
  id: string,
  opts?: { priorAlpha?: number; priorBeta?: number },
) {
  const q = new URLSearchParams()
  if (opts?.priorAlpha != null) q.set('prior_alpha', String(opts.priorAlpha))
  if (opts?.priorBeta != null) q.set('prior_beta', String(opts.priorBeta))
  const qs = q.toString()
  const url =
    qs.length > 0
      ? `${base}/api/runs/${id}/experiment-inference?${qs}`
      : `${base}/api/runs/${id}/experiment-inference`
  return parse<ExperimentInference>(fetch(url))
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
