import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createRun } from '../api/client'

type FormState = {
  seed: number
  horizon_days: number
  baseline_end_day: number
  experiment_start_day: number
  customer_count: number
  baseline_order_price: number
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
  weekend_factor: number
  weekday_factor: number
  seasonal_amplitude: number
  promo_first_order_only: boolean
  promo_max_uses_per_customer: number
  promo_cooldown_days: number
  campaign_budget: number | null
}

const defaults: FormState = {
  seed: 42,
  horizon_days: 90,
  baseline_end_day: 30,
  experiment_start_day: 31,
  customer_count: 300,
  baseline_order_price: 15,
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
  weekend_factor: 1.12,
  weekday_factor: 1,
  seasonal_amplitude: 0.05,
  promo_first_order_only: false,
  promo_max_uses_per_customer: 999,
  promo_cooldown_days: 0,
  campaign_budget: null,
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
      const body = {
        ...form,
        campaign_budget: form.campaign_budget === null ? null : form.campaign_budget,
      }
      const res = await createRun(body as unknown as Record<string, unknown>)
      nav(`/runs/${res.id}`)
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
        Configure population, horizon, baseline vs experiment (delivery fee lever), temporal
        and promo settings. Runs execute in the background; you are redirected to the run
        summary.
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
              <label>Free delivery threshold</label>
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

        {err && <p className="error">{err}</p>}
        <button type="submit" disabled={loading}>
          {loading ? 'Starting…' : 'Start simulation'}
        </button>
      </form>
    </div>
  )
}
