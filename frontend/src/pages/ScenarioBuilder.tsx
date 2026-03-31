import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createRun, createRunBatch } from '../api/client'

type FormState = {
  seed: number
  horizon_days: number
  baseline_end_day: number
  experiment_start_day: number
  customer_count: number
  baseline_delivery_fee: number
  baseline_service_fee: number
  baseline_discount: number
  free_delivery_threshold: number | null
  control_delivery_fee: number
  variant_delivery_fee: number
  variant_extra_discount: number
  variable_cost_rate: number
  budget_mean: number
  budget_std: number
  propensity_alpha: number
  propensity_beta: number
  basket_log_mean: number
  basket_log_sigma: number
  zones_csv: string
  zone_weights_csv: string
  zone_modifiers_json: string
  treatment_split: number
  channel_propensity_modifiers_json: string
  churn_base_rate: number
  clv_projected_days: number
  discount_rate_annual: number
  clv_validation_days: number
  weekend_factor: number
  weekday_factor: number
  seasonal_amplitude: number
  promo_first_order_only: boolean
  promo_max_uses_per_customer: number
  promo_cooldown_days: number
  campaign_budget: number | null
  batch_seeds_csv: string
}

const defaults: FormState = {
  seed: 42,
  horizon_days: 90,
  baseline_end_day: 30,
  experiment_start_day: 31,
  customer_count: 300,
  baseline_delivery_fee: 2.99,
  baseline_service_fee: 1,
  baseline_discount: 0,
  free_delivery_threshold: 25,
  control_delivery_fee: 2.99,
  variant_delivery_fee: 1.99,
  variant_extra_discount: 0,
  variable_cost_rate: 0.35,
  budget_mean: 40,
  budget_std: 12,
  propensity_alpha: 2,
  propensity_beta: 5,
  basket_log_mean: 2.2,
  basket_log_sigma: 0.35,
  zones_csv: 'A,B,C',
  zone_weights_csv: '0.5,0.3,0.2',
  zone_modifiers_json: '',
  treatment_split: 0.5,
  channel_propensity_modifiers_json: '',
  churn_base_rate: 0.002,
  clv_projected_days: 90,
  discount_rate_annual: 0.1,
  clv_validation_days: 0,
  weekend_factor: 1.12,
  weekday_factor: 1,
  seasonal_amplitude: 0.05,
  promo_first_order_only: false,
  promo_max_uses_per_customer: 999,
  promo_cooldown_days: 0,
  campaign_budget: null,
  batch_seeds_csv: '',
}

function parseCsvList(s: string): string[] {
  return s
    .split(',')
    .map((x) => x.trim())
    .filter(Boolean)
}

function parseCsvFloats(s: string): number[] {
  return parseCsvList(s).map((x) => Number(x))
}

function parseOptionalJsonObject(
  raw: string,
): Record<string, number> | null | 'invalid' {
  const t = raw.trim()
  if (!t) return null
  try {
    const v = JSON.parse(t) as unknown
    if (v === null || typeof v !== 'object' || Array.isArray(v)) return 'invalid'
    const out: Record<string, number> = {}
    for (const [k, val] of Object.entries(v)) {
      if (typeof val !== 'number' || Number.isNaN(val)) return 'invalid'
      out[k] = val
    }
    return out
  } catch {
    return 'invalid'
  }
}

function buildRunPayload(form: FormState): Record<string, unknown> {
  const zones = parseCsvList(form.zones_csv)
  const zone_weights = parseCsvFloats(form.zone_weights_csv)
  const zm = parseOptionalJsonObject(form.zone_modifiers_json)
  if (zm === 'invalid') throw new Error('Zone modifiers must be valid JSON object of numbers')
  const ch = parseOptionalJsonObject(form.channel_propensity_modifiers_json)
  if (ch === 'invalid') throw new Error('Channel modifiers must be valid JSON object of numbers')
  if (zones.length !== zone_weights.length) {
    throw new Error('Zones and zone weights must have the same number of entries')
  }
  return {
    seed: form.seed,
    horizon_days: form.horizon_days,
    baseline_end_day: form.baseline_end_day,
    experiment_start_day: form.experiment_start_day,
    customer_count: form.customer_count,
    baseline_delivery_fee: form.baseline_delivery_fee,
    baseline_service_fee: form.baseline_service_fee,
    baseline_discount: form.baseline_discount,
    free_delivery_threshold: form.free_delivery_threshold,
    control_delivery_fee: form.control_delivery_fee,
    variant_delivery_fee: form.variant_delivery_fee,
    variant_extra_discount: form.variant_extra_discount,
    variable_cost_rate: form.variable_cost_rate,
    budget_mean: form.budget_mean,
    budget_std: form.budget_std,
    propensity_alpha: form.propensity_alpha,
    propensity_beta: form.propensity_beta,
    basket_log_mean: form.basket_log_mean,
    basket_log_sigma: form.basket_log_sigma,
    zones,
    zone_weights,
    zone_modifiers: zm,
    treatment_split: form.treatment_split,
    channel_propensity_modifiers: ch,
    churn_base_rate: form.churn_base_rate,
    clv_projected_days: form.clv_projected_days,
    discount_rate_annual: form.discount_rate_annual,
    clv_validation_days: form.clv_validation_days,
    weekend_factor: form.weekend_factor,
    weekday_factor: form.weekday_factor,
    seasonal_amplitude: form.seasonal_amplitude,
    promo_first_order_only: form.promo_first_order_only,
    promo_max_uses_per_customer: form.promo_max_uses_per_customer,
    promo_cooldown_days: form.promo_cooldown_days,
    campaign_budget: form.campaign_budget === null ? null : form.campaign_budget,
  }
}

export function ScenarioBuilder() {
  const nav = useNavigate()
  const [form, setForm] = useState(defaults)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  function set<K extends keyof FormState>(k: K, v: FormState[K]) {
    setForm((f) => ({ ...f, [k]: v }))
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setErr(null)
    setLoading(true)
    try {
      const run = buildRunPayload(form)
      const batchRaw = form.batch_seeds_csv.trim()
      if (batchRaw) {
        const seeds = parseCsvList(batchRaw).map((x) => parseInt(x, 10))
        if (seeds.some((n) => Number.isNaN(n))) {
          setErr('Batch seeds must be comma-separated integers')
          setLoading(false)
          return
        }
        if (seeds.length < 1) {
          setErr('Provide at least one seed for batch mode')
          setLoading(false)
          return
        }
        const res = await createRunBatch({ seeds, run })
        nav(`/runs/${res.ids[0]}`)
      } else {
        const res = await createRun(run)
        nav(`/runs/${res.id}`)
      }
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : 'Request failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1>Scenario builder</h1>
      <p className="muted" style={{ marginBottom: '1rem' }}>
        Every engine field from <code>RunConfig</code> is editable below except{' '}
        <code>baseline_order_price</code>, which is deprecated and omitted from the request body so
        the API keeps its documented default (unused in the live basket + fees pricing path). API
        base path: <code>/api/runs</code>.
      </p>
      <form onSubmit={submit}>
        <div className="panel">
          <h2>Simulation</h2>
          <div className="field-grid">
            <div>
              <label>Seed</label>
              <input
                type="number"
                value={form.seed}
                onChange={(e) => set('seed', +e.target.value)}
              />
            </div>
            <div>
              <label>Horizon (days)</label>
              <input
                type="number"
                value={form.horizon_days}
                onChange={(e) => set('horizon_days', +e.target.value)}
              />
            </div>
            <div>
              <label>Baseline end day</label>
              <input
                type="number"
                value={form.baseline_end_day}
                onChange={(e) => set('baseline_end_day', +e.target.value)}
              />
            </div>
            <div>
              <label>Experiment start day</label>
              <input
                type="number"
                value={form.experiment_start_day}
                onChange={(e) => set('experiment_start_day', +e.target.value)}
              />
            </div>
            <div>
              <label>Customer count</label>
              <input
                type="number"
                value={form.customer_count}
                onChange={(e) => set('customer_count', +e.target.value)}
              />
            </div>
            <div>
              <label>Variant fraction (treatment split)</label>
              <input
                type="number"
                step="0.01"
                min={0.01}
                max={0.99}
                value={form.treatment_split}
                onChange={(e) => set('treatment_split', +e.target.value)}
              />
            </div>
          </div>
        </div>

        <div className="panel">
          <h2>Population and cohort</h2>
          <div className="field-grid">
            <div>
              <label>Budget mean</label>
              <input
                type="number"
                step="0.1"
                value={form.budget_mean}
                onChange={(e) => set('budget_mean', +e.target.value)}
              />
            </div>
            <div>
              <label>Budget std</label>
              <input
                type="number"
                step="0.1"
                value={form.budget_std}
                onChange={(e) => set('budget_std', +e.target.value)}
              />
            </div>
            <div>
              <label>Propensity α (Beta)</label>
              <input
                type="number"
                step="0.1"
                value={form.propensity_alpha}
                onChange={(e) => set('propensity_alpha', +e.target.value)}
              />
            </div>
            <div>
              <label>Propensity β (Beta)</label>
              <input
                type="number"
                step="0.1"
                value={form.propensity_beta}
                onChange={(e) => set('propensity_beta', +e.target.value)}
              />
            </div>
            <div>
              <label>Basket log mean</label>
              <input
                type="number"
                step="0.01"
                value={form.basket_log_mean}
                onChange={(e) => set('basket_log_mean', +e.target.value)}
              />
            </div>
            <div>
              <label>Basket log σ</label>
              <input
                type="number"
                step="0.01"
                value={form.basket_log_sigma}
                onChange={(e) => set('basket_log_sigma', +e.target.value)}
              />
            </div>
          </div>
        </div>

        <div className="panel">
          <h2>Geography</h2>
          <div className="field-grid">
            <div style={{ gridColumn: '1 / -1' }}>
              <label>Zones (comma-separated)</label>
              <input
                type="text"
                value={form.zones_csv}
                onChange={(e) => set('zones_csv', e.target.value)}
                placeholder="A,B,C"
              />
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <label>Zone weights (comma-separated, same length as zones)</label>
              <input
                type="text"
                value={form.zone_weights_csv}
                onChange={(e) => set('zone_weights_csv', e.target.value)}
                placeholder="0.5,0.3,0.2"
              />
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <label>Zone demand modifiers (JSON object, optional)</label>
              <textarea
                rows={2}
                value={form.zone_modifiers_json}
                onChange={(e) => set('zone_modifiers_json', e.target.value)}
                placeholder='{"A":1.0,"B":1.05}'
                className="code-block"
                style={{ width: '100%', fontFamily: 'monospace' }}
              />
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <label>Channel propensity modifiers (JSON, optional)</label>
              <textarea
                rows={2}
                value={form.channel_propensity_modifiers_json}
                onChange={(e) =>
                  set('channel_propensity_modifiers_json', e.target.value)
                }
                placeholder='{"organic":1,"paid":0.85,"referral":1.15}'
                className="code-block"
                style={{ width: '100%', fontFamily: 'monospace' }}
              />
            </div>
          </div>
        </div>

        <div className="panel">
          <h2>Pricing</h2>
          <div className="field-grid">
            <div>
              <label>Baseline delivery fee</label>
              <input
                type="number"
                step="0.01"
                value={form.baseline_delivery_fee}
                onChange={(e) => set('baseline_delivery_fee', +e.target.value)}
              />
            </div>
            <div>
              <label>Service fee</label>
              <input
                type="number"
                step="0.01"
                value={form.baseline_service_fee}
                onChange={(e) => set('baseline_service_fee', +e.target.value)}
              />
            </div>
            <div>
              <label>Baseline discount</label>
              <input
                type="number"
                step="0.01"
                value={form.baseline_discount}
                onChange={(e) => set('baseline_discount', +e.target.value)}
              />
            </div>
            <div>
              <label>Free delivery threshold (blank = none)</label>
              <input
                type="number"
                step="0.01"
                value={form.free_delivery_threshold ?? ''}
                onChange={(e) =>
                  set(
                    'free_delivery_threshold',
                    e.target.value === '' ? null : +e.target.value,
                  )
                }
              />
            </div>
            <div>
              <label>Control delivery (experiment)</label>
              <input
                type="number"
                step="0.01"
                value={form.control_delivery_fee}
                onChange={(e) => set('control_delivery_fee', +e.target.value)}
              />
            </div>
            <div>
              <label>Variant delivery (experiment)</label>
              <input
                type="number"
                step="0.01"
                value={form.variant_delivery_fee}
                onChange={(e) => set('variant_delivery_fee', +e.target.value)}
              />
            </div>
            <div>
              <label>Variant extra discount (promo)</label>
              <input
                type="number"
                step="0.01"
                value={form.variant_extra_discount}
                onChange={(e) => set('variant_extra_discount', +e.target.value)}
              />
            </div>
            <div>
              <label>Variable cost rate</label>
              <input
                type="number"
                step="0.01"
                value={form.variable_cost_rate}
                onChange={(e) => set('variable_cost_rate', +e.target.value)}
              />
            </div>
          </div>
          <p className="muted" style={{ marginTop: '0.75rem', fontSize: '0.9rem' }}>
            Deprecated <code>baseline_order_price</code> is not sent to the API; baskets use
            lognormal draws from each customer&apos;s <code>basket_mean</code> (see spec mapping
            doc).
          </p>
        </div>

        <div className="panel">
          <h2>Churn and CLV</h2>
          <div className="field-grid">
            <div>
              <label>Churn base rate (daily)</label>
              <input
                type="number"
                step="0.0001"
                value={form.churn_base_rate}
                onChange={(e) => set('churn_base_rate', +e.target.value)}
              />
            </div>
            <div>
              <label>CLV projected days</label>
              <input
                type="number"
                value={form.clv_projected_days}
                onChange={(e) => set('clv_projected_days', +e.target.value)}
              />
            </div>
            <div>
              <label>Discount rate (annual)</label>
              <input
                type="number"
                step="0.01"
                value={form.discount_rate_annual}
                onChange={(e) => set('discount_rate_annual', +e.target.value)}
              />
            </div>
            <div>
              <label>CLV validation days (0 = off)</label>
              <input
                type="number"
                value={form.clv_validation_days}
                onChange={(e) => set('clv_validation_days', +e.target.value)}
              />
            </div>
          </div>
        </div>

        <div className="panel">
          <h2>Demand context</h2>
          <div className="field-grid">
            <div>
              <label>Weekend factor</label>
              <input
                type="number"
                step="0.01"
                value={form.weekend_factor}
                onChange={(e) => set('weekend_factor', +e.target.value)}
              />
            </div>
            <div>
              <label>Weekday factor</label>
              <input
                type="number"
                step="0.01"
                value={form.weekday_factor}
                onChange={(e) => set('weekday_factor', +e.target.value)}
              />
            </div>
            <div>
              <label>Seasonal amplitude</label>
              <input
                type="number"
                step="0.01"
                value={form.seasonal_amplitude}
                onChange={(e) => set('seasonal_amplitude', +e.target.value)}
              />
            </div>
          </div>
        </div>

        <div className="panel">
          <h2>Promo constraints</h2>
          <div className="field-grid">
            <div>
              <label>First order only</label>
              <select
                value={form.promo_first_order_only ? 'yes' : 'no'}
                onChange={(e) =>
                  set('promo_first_order_only', e.target.value === 'yes')
                }
              >
                <option value="no">No</option>
                <option value="yes">Yes</option>
              </select>
            </div>
            <div>
              <label>Max uses / customer</label>
              <input
                type="number"
                value={form.promo_max_uses_per_customer}
                onChange={(e) =>
                  set('promo_max_uses_per_customer', +e.target.value)
                }
              />
            </div>
            <div>
              <label>Cooldown (days)</label>
              <input
                type="number"
                value={form.promo_cooldown_days}
                onChange={(e) => set('promo_cooldown_days', +e.target.value)}
              />
            </div>
            <div>
              <label>Campaign budget (blank = none)</label>
              <input
                type="number"
                step="0.01"
                value={form.campaign_budget ?? ''}
                onChange={(e) =>
                  set(
                    'campaign_budget',
                    e.target.value === '' ? null : +e.target.value,
                  )
                }
              />
            </div>
          </div>
        </div>

        <div className="panel">
          <h2>Batch runs (spec section 9)</h2>
          <p className="muted" style={{ marginBottom: '0.5rem' }}>
            Leave blank for a single run with the seed above. Otherwise comma-separated seeds
            enqueue <code>POST /api/runs/batch</code> with identical config; you are redirected
            to the first run.
          </p>
          <div>
            <label>Batch seeds (optional)</label>
            <input
              type="text"
              value={form.batch_seeds_csv}
              onChange={(e) => set('batch_seeds_csv', e.target.value)}
              placeholder="e.g. 1,2,3,4,5"
            />
          </div>
        </div>

        {err && <p className="error">{err}</p>}
        <button type="submit" disabled={loading}>
          {loading ? 'Starting…' : 'Start simulation'}
        </button>
      </form>
    </div>
  )
}
