import { useEffect, useMemo, useState } from 'react'
import { NavLink, Route, Routes, useParams } from 'react-router-dom'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  getCustomers,
  getDaily,
  getExperimentInference,
  getRun,
  type CustomerRow,
  type DailyRow,
  type ExperimentInference,
  type RunDetail,
} from '../api/client'

function useRun(id: string | undefined) {
  const [run, setRun] = useState<RunDetail | null>(null)
  const [daily, setDaily] = useState<DailyRow[]>([])
  const [customers, setCustomers] = useState<CustomerRow[]>([])
  const [poll, setPoll] = useState(true)

  useEffect(() => {
    const rid = id ?? ''
    if (!rid) return
    let cancelled = false
    async function load() {
      try {
        const r = await getRun(rid)
        if (cancelled) return
        setRun(r)
        if (r.status === 'completed') {
          setPoll(false)
          const [d, c] = await Promise.all([getDaily(rid), getCustomers(rid)])
          if (!cancelled) {
            setDaily(d)
            setCustomers(c)
          }
        } else if (r.status === 'failed') {
          setPoll(false)
        }
      } catch {
        setPoll(false)
      }
    }
    load()
    if (!poll) return
    const t = setInterval(load, 1200)
    return () => {
      cancelled = true
      clearInterval(t)
    }
  }, [id, poll])

  return { run, daily, customers }
}

function RunNav({ id }: { id: string }) {
  return (
    <nav style={{ marginBottom: '1rem', display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
      <NavLink to="/">← Builder</NavLink>
      <NavLink to={`/runs/${id}`} end>
        Summary
      </NavLink>
      <NavLink to={`/runs/${id}/dashboard`}>Results</NavLink>
      <NavLink to={`/runs/${id}/customers`}>Customers</NavLink>
    </nav>
  )
}

function summarizeByPhase(rows: DailyRow[]) {
  const onlyAll = rows.filter((r) => r.location_zone === '__all__')
  const acc: Record<
    string,
    { orders: number; net: number; margin: number; inc_orders: number }
  > = {}
  for (const r of onlyAll) {
    const k = r.phase
    if (!acc[k])
      acc[k] = { orders: 0, net: 0, margin: 0, inc_orders: 0 }
    const m = r.metrics
    acc[k].orders += m.orders ?? 0
    acc[k].net += m.net_revenue ?? 0
    acc[k].margin += m.contribution_margin ?? 0
    acc[k].inc_orders += m.incremental_orders ?? 0
  }
  return acc
}

type ExpArmAgg = {
  customer_days: number
  orders: number
  net: number
  margin: number
  inc_orders: number
  inc_rev: number
  inc_margin: number
}

function summarizeExperimentByTreatment(rows: DailyRow[]) {
  const exp = rows.filter(
    (r) => r.phase === 'experiment' && r.location_zone === '__all__',
  )
  const acc: Record<string, ExpArmAgg> = {}
  for (const r of exp) {
    const tr = r.treatment
    if (!tr) continue
    if (!acc[tr])
      acc[tr] = {
        customer_days: 0,
        orders: 0,
        net: 0,
        margin: 0,
        inc_orders: 0,
        inc_rev: 0,
        inc_margin: 0,
      }
    const m = r.metrics
    acc[tr].customer_days += m.customers_evaluated ?? m.active_customers_evaluated ?? 0
    acc[tr].orders += m.orders ?? 0
    acc[tr].net += m.net_revenue ?? 0
    acc[tr].margin += m.contribution_margin ?? 0
    acc[tr].inc_orders += m.incremental_orders ?? 0
    acc[tr].inc_rev += m.incremental_revenue ?? 0
    acc[tr].inc_margin += m.incremental_margin ?? 0
  }
  return acc
}

function experimentDailySeries(rows: DailyRow[]) {
  const exp = rows.filter(
    (r) => r.phase === 'experiment' && r.location_zone === '__all__',
  )
  const byDay = new Map<
    number,
    { control?: DailyRow; variant?: DailyRow }
  >()
  for (const r of exp) {
    if (!r.treatment) continue
    const cur = byDay.get(r.day) ?? {}
    if (r.treatment === 'control') cur.control = r
    if (r.treatment === 'variant') cur.variant = r
    byDay.set(r.day, cur)
  }
  const days = [...byDay.keys()].sort((a, b) => a - b)
  let cumCo = 0
  let cumVo = 0
  let cumCn = 0
  let cumVn = 0
  let cumCm = 0
  let cumVm = 0
  return days.map((day) => {
    const e = byDay.get(day)!
    const co = e.control?.metrics.orders ?? 0
    const vo = e.variant?.metrics.orders ?? 0
    const cn = e.control?.metrics.net_revenue ?? 0
    const vn = e.variant?.metrics.net_revenue ?? 0
    const cm = e.control?.metrics.contribution_margin ?? 0
    const vm = e.variant?.metrics.contribution_margin ?? 0
    const cc = e.control?.metrics.conversion_rate ?? 0
    const vc = e.variant?.metrics.conversion_rate ?? 0
    cumCo += co
    cumVo += vo
    cumCn += cn
    cumVn += vn
    cumCm += cm
    cumVm += vm
    return {
      day,
      control_orders: co,
      variant_orders: vo,
      control_net: cn,
      variant_net: vn,
      control_conv: cc,
      variant_conv: vc,
      cum_control_orders: cumCo,
      cum_variant_orders: cumVo,
      cum_control_net: cumCn,
      cum_variant_net: cumVn,
      cum_control_margin: cumCm,
      cum_variant_margin: cumVm,
    }
  })
}

function RunSummary({ id }: { id: string }) {
  const { run, daily } = useRun(id)
  const byPhase = useMemo(() => summarizeByPhase(daily), [daily])
  const byTreatment = useMemo(() => summarizeExperimentByTreatment(daily), [daily])
  const [inference, setInference] = useState<ExperimentInference | null>(null)
  const [infErr, setInfErr] = useState<string | null>(null)

  useEffect(() => {
    if (!run || run.status !== 'completed') return
    let cancelled = false
    getExperimentInference(id)
      .then((x) => {
        if (!cancelled) setInference(x)
      })
      .catch(() => {
        if (!cancelled) setInfErr('Inference not available')
      })
    return () => {
      cancelled = true
    }
  }, [id, run?.status])

  if (!run) return <p className="muted">Loading run…</p>

  return (
    <div>
      <RunNav id={id} />
      <h1>Run summary</h1>
      <div className="panel">
        <p>
          <strong>Status:</strong> {run.status}
        </p>
        {run.error_message && (
          <pre className="code-block" style={{ color: '#c43a3a' }}>
            {run.error_message}
          </pre>
        )}
        <p className="muted">
          Seed {run.seed} · {run.horizon_days} days ·{' '}
          <strong>Total customers (cohort):</strong> {run.customer_count} · baseline ends day{' '}
          {run.baseline_end_day} · experiment from day {run.experiment_start_day}
        </p>
        <p className="muted" style={{ fontSize: '0.9rem' }}>
          Daily <code>customers_evaluated</code> / <code>active_customers_evaluated</code> counts
          only non-churned customers still in the simulation that day (spec “active” slice).
        </p>
      </div>
      {run.status === 'completed' && (
        <>
          <div className="panel">
            <h2>Baseline vs experiment (all zones)</h2>
            <table>
              <thead>
                <tr>
                  <th>Phase</th>
                  <th>Orders</th>
                  <th>Net revenue</th>
                  <th>Contribution margin</th>
                  <th>Incremental orders</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(byPhase).map(([phase, v]) => (
                  <tr key={phase}>
                    <td>{phase}</td>
                    <td>{v.orders}</td>
                    <td>{v.net.toFixed(2)}</td>
                    <td>{v.margin.toFixed(2)}</td>
                    <td>{v.inc_orders}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="panel">
            <h2>Experiment phase by treatment</h2>
            <p className="muted" style={{ marginBottom: '0.5rem' }}>
              Totals summed from daily aggregates (<code>location_zone === &apos;__all__&apos;</code>
              ). Conversion = orders ÷ customer-days.
            </p>
            <table>
              <thead>
                <tr>
                  <th>Treatment</th>
                  <th>Customer-days</th>
                  <th>Orders</th>
                  <th>Conversion</th>
                  <th>Net revenue</th>
                  <th>Margin</th>
                  <th>Inc. orders</th>
                  <th>Inc. revenue</th>
                  <th>Inc. margin</th>
                </tr>
              </thead>
              <tbody>
                {['control', 'variant'].map((t) => {
                  const v = byTreatment[t]
                  if (!v) return null
                  const conv =
                    v.customer_days > 0 ? v.orders / v.customer_days : 0
                  return (
                    <tr key={t}>
                      <td>{t}</td>
                      <td>{v.customer_days}</td>
                      <td>{v.orders}</td>
                      <td>{(conv * 100).toFixed(2)}%</td>
                      <td>{v.net.toFixed(2)}</td>
                      <td>{v.margin.toFixed(2)}</td>
                      <td>{v.inc_orders}</td>
                      <td>{v.inc_rev.toFixed(2)}</td>
                      <td>{v.inc_margin.toFixed(2)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          {(inference || infErr) && (
            <div className="panel">
              <h2>Experiment inference</h2>
              <p className="muted" style={{ marginBottom: '1rem' }}>
                Conversion is orders ÷ customer-days in the experiment phase (aggregated). Frequentist
                block uses Wilson intervals and a pooled two-proportion z-test; Bayesian block uses
                independent Beta–binomial posteriors per arm with the stated prior.
              </p>
              {infErr && <p className="muted">{infErr}</p>}
              {inference && (
                <>
                  <h3 style={{ marginTop: 0 }}>Frequentist</h3>
                  <table style={{ marginBottom: '1.25rem' }}>
                    <thead>
                      <tr>
                        <th>Arm</th>
                        <th>Customer-days</th>
                        <th>Orders</th>
                        <th>Rate</th>
                        <th>Wilson 95% low</th>
                        <th>Wilson 95% high</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[inference.control, inference.variant].map((a) => (
                        <tr key={a.treatment}>
                          <td>{a.treatment}</td>
                          <td>{a.customer_days}</td>
                          <td>{a.orders}</td>
                          <td>{(a.conversion_rate * 100).toFixed(2)}%</td>
                          <td>{(a.conversion_rate_wilson_low * 100).toFixed(2)}%</td>
                          <td>{(a.conversion_rate_wilson_high * 100).toFixed(2)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <p>
                    <strong>Lift (point):</strong> Δ ={' '}
                    {(inference.conversion_lift_absolute * 100).toFixed(3)} pp · relative{' '}
                    {(inference.conversion_lift_relative * 100).toFixed(1)}% (vs control MLE)
                  </p>
                  <p>
                    <strong>Two-proportion z-test:</strong> z ={' '}
                    {inference.two_proportion_z_statistic.toFixed(4)}, two-sided p ={' '}
                    {inference.two_proportion_p_value_two_sided.toExponential(3)}
                  </p>

                  <h3>Bayesian (Beta–binomial)</h3>
                  <p className="muted">
                    Prior per arm: Beta({inference.bayesian.prior_alpha},{inference.bayesian.prior_beta}
                    ) · MC samples: {inference.bayesian.mc_samples} · ε for relative lift:{' '}
                    {inference.bayesian.relative_lift_p_c_epsilon}
                  </p>
                  <table style={{ marginBottom: '1rem' }}>
                    <thead>
                      <tr>
                        <th>Arm</th>
                        <th>Posterior α</th>
                        <th>Posterior β</th>
                        <th>Mean rate</th>
                        <th>95% cred. low</th>
                        <th>95% cred. high</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[inference.bayesian.control, inference.bayesian.variant].map((a) => (
                        <tr key={a.treatment}>
                          <td>{a.treatment}</td>
                          <td>{a.posterior_alpha.toFixed(4)}</td>
                          <td>{a.posterior_beta.toFixed(4)}</td>
                          <td>{(a.conversion_rate_posterior_mean * 100).toFixed(2)}%</td>
                          <td>{(a.conversion_rate_credible_low * 100).toFixed(2)}%</td>
                          <td>{(a.conversion_rate_credible_high * 100).toFixed(2)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <p>
                    <strong>P(variant rate &gt; control rate | data):</strong>{' '}
                    {(inference.bayesian.comparison.prob_variant_superior * 100).toFixed(2)}%
                  </p>
                  <p>
                    <strong>Lift (posterior draws):</strong> absolute mean{' '}
                    {(inference.bayesian.comparison.lift_absolute_mean * 100).toFixed(4)} pp, median{' '}
                    {(inference.bayesian.comparison.lift_absolute_median * 100).toFixed(4)} pp
                  </p>
                  <p>
                    <strong>Relative lift</strong> (draws with p_c &gt; ε): mean{' '}
                    {inference.bayesian.comparison.lift_relative_mean != null
                      ? `${(inference.bayesian.comparison.lift_relative_mean * 100).toFixed(2)}%`
                      : '—'}
                    , median{' '}
                    {inference.bayesian.comparison.lift_relative_median != null
                      ? `${(inference.bayesian.comparison.lift_relative_median * 100).toFixed(2)}%`
                      : '—'}
                    · effective draw fraction{' '}
                    {(
                      inference.bayesian.comparison.relative_lift_effective_sample_fraction * 100
                    ).toFixed(2)}
                    %
                  </p>
                </>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}

function chartExperimentOrders(rows: DailyRow[]) {
  const exp = rows.filter(
    (r) => r.phase === 'experiment' && r.location_zone === '__all__',
  )
  const byDay: Record<number, { day: number; control: number; variant: number }> = {}
  for (const r of exp) {
    if (!r.treatment) continue
    if (!byDay[r.day])
      byDay[r.day] = { day: r.day, control: 0, variant: 0 }
    byDay[r.day][r.treatment as 'control' | 'variant'] += r.metrics.orders ?? 0
  }
  return Object.values(byDay).sort((a, b) => a.day - b.day)
}

function RunDashboard({ id }: { id: string }) {
  const { run, daily } = useRun(id)
  const series = useMemo(() => chartExperimentOrders(daily), [daily])
  const merged = useMemo(() => experimentDailySeries(daily), [daily])
  const totals = useMemo(() => {
    const exp = daily.filter(
      (r) => r.phase === 'experiment' && r.location_zone === '__all__',
    )
    const t: Record<string, { orders: number; margin: number }> = {}
    for (const r of exp) {
      const tr = r.treatment ?? 'none'
      if (!t[tr]) t[tr] = { orders: 0, margin: 0 }
      t[tr].orders += r.metrics.orders ?? 0
      t[tr].margin += r.metrics.contribution_margin ?? 0
    }
    return t
  }, [daily])

  if (!run || run.status !== 'completed') {
    return (
      <div>
        <RunNav id={id} />
        <p className="muted">Dashboard available when the run completes.</p>
      </div>
    )
  }

  return (
    <div>
      <RunNav id={id} />
      <h1>Results dashboard</h1>
      <p className="muted">
        Cohort size: <strong>{run.customer_count}</strong> customers. Charts use experiment phase
        and <code>__all__</code> zone.
      </p>
      <div className="panel">
        <h2>Daily orders (experiment, by treatment)</h2>
        <div className="chart-wrap">
          <ResponsiveContainer>
            <LineChart data={series}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="control" stroke="#6b5b95" dot={false} />
              <Line type="monotone" dataKey="variant" stroke="#3d8b6a" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="panel">
        <h2>Daily net revenue (experiment, by treatment)</h2>
        <div className="chart-wrap">
          <ResponsiveContainer>
            <LineChart data={merged}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="control_net" name="control" stroke="#6b5b95" dot={false} />
              <Line type="monotone" dataKey="variant_net" name="variant" stroke="#3d8b6a" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="panel">
        <h2>Daily conversion rate (experiment, by treatment)</h2>
        <div className="chart-wrap">
          <ResponsiveContainer>
            <LineChart data={merged}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day" />
              <YAxis tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
              <Tooltip
                formatter={(v) =>
                  `${((typeof v === 'number' ? v : Number(v)) * 100).toFixed(2)}%`
                }
              />
              <Legend />
              <Line type="monotone" dataKey="control_conv" name="control" stroke="#6b5b95" dot={false} />
              <Line type="monotone" dataKey="variant_conv" name="variant" stroke="#3d8b6a" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="panel">
        <h2>Cumulative net revenue (experiment)</h2>
        <div className="chart-wrap">
          <ResponsiveContainer>
            <LineChart data={merged}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="cum_control_net" name="control" stroke="#6b5b95" dot={false} />
              <Line type="monotone" dataKey="cum_variant_net" name="variant" stroke="#3d8b6a" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="panel">
        <h2>Cumulative orders (experiment)</h2>
        <div className="chart-wrap">
          <ResponsiveContainer>
            <LineChart data={merged}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="cum_control_orders" name="control" stroke="#6b5b95" dot={false} />
              <Line type="monotone" dataKey="cum_variant_orders" name="variant" stroke="#3d8b6a" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="panel">
        <h2>Cumulative contribution margin (experiment)</h2>
        <div className="chart-wrap">
          <ResponsiveContainer>
            <LineChart data={merged}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="cum_control_margin" name="control" stroke="#6b5b95" dot={false} />
              <Line type="monotone" dataKey="cum_variant_margin" name="variant" stroke="#3d8b6a" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="panel">
        <h2>Totals by treatment (experiment)</h2>
        <div className="chart-wrap">
          <ResponsiveContainer>
            <BarChart
              data={Object.entries(totals).map(([name, v]) => ({
                name,
                orders: v.orders,
                margin: v.margin,
              }))}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="orders" fill="#6b5b95" />
              <Bar dataKey="margin" fill="#3d8b6a" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}

function histogram(values: number[], bins: number) {
  if (!values.length) return []
  const min = Math.min(...values)
  const max = Math.max(...values)
  const w = (max - min) / bins || 1
  const counts = new Array(bins).fill(0)
  for (const v of values) {
    const i = Math.min(bins - 1, Math.floor((v - min) / w))
    counts[i]++
  }
  const maxC = Math.max(...counts, 1)
  return counts.map((c, i) => ({
    label: `${(min + i * w).toFixed(1)}–${(min + (i + 1) * w).toFixed(1)}`,
    count: c,
    pct: (c / maxC) * 100,
  }))
}

function RunCustomers({ id }: { id: string }) {
  const { run, customers } = useRun(id)

  const hb = useMemo(
    () => histogram(customers.map((c) => c.budget), 12),
    [customers],
  )
  const hp = useMemo(
    () => histogram(customers.map((c) => c.buy_propensity), 12),
    [customers],
  )
  const ht = useMemo(
    () => histogram(customers.map((c) => c.price_threshold), 12),
    [customers],
  )

  if (!run || run.status !== 'completed') {
    return (
      <div>
        <RunNav id={id} />
        <p className="muted">Customer explorer available when the run completes.</p>
      </div>
    )
  }

  return (
    <div>
      <RunNav id={id} />
      <h1>Customer explorer</h1>
      <p className="muted">Cohort: {run.customer_count} customers · showing up to 500 loaded rows</p>
      <div className="panel">
        <h2>Sample ({customers.length} rows)</h2>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Segment</th>
                <th>Zone</th>
                <th>Budget</th>
                <th>Propensity</th>
                <th>Threshold</th>
                <th>Basket μ</th>
              </tr>
            </thead>
            <tbody>
              {customers.slice(0, 50).map((c) => (
                <tr key={c.id}>
                  <td>{c.customer_index}</td>
                  <td>{c.segment}</td>
                  <td>{c.location_zone}</td>
                  <td>{c.budget.toFixed(2)}</td>
                  <td>{c.buy_propensity.toFixed(3)}</td>
                  <td>{c.price_threshold.toFixed(2)}</td>
                  <td>{c.basket_mean.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="panel">
        <h3>Budget</h3>
        {hb.map((b, i) => (
          <div key={`b-${i}`} className="hist-row">
            <span style={{ width: 120 }}>{b.label}</span>
            <div className="hist-bar" style={{ width: `${b.pct}%` }} />
            <span>{b.count}</span>
          </div>
        ))}
      </div>
      <div className="panel">
        <h3>Buy propensity</h3>
        {hp.map((b, i) => (
          <div key={`p-${i}`} className="hist-row">
            <span style={{ width: 120 }}>{b.label}</span>
            <div className="hist-bar" style={{ width: `${b.pct}%` }} />
            <span>{b.count}</span>
          </div>
        ))}
      </div>
      <div className="panel">
        <h3>Price threshold</h3>
        {ht.map((b, i) => (
          <div key={`t-${i}`} className="hist-row">
            <span style={{ width: 120 }}>{b.label}</span>
            <div className="hist-bar" style={{ width: `${b.pct}%` }} />
            <span>{b.count}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export function RunWorkspace() {
  const { runId } = useParams<{ runId: string }>()
  if (!runId) return null
  return (
    <Routes>
      <Route index element={<RunSummary id={runId} />} />
      <Route path="dashboard" element={<RunDashboard id={runId} />} />
      <Route path="customers" element={<RunCustomers id={runId} />} />
    </Routes>
  )
}
