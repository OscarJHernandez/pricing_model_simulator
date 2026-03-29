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
  getRun,
  type CustomerRow,
  type DailyRow,
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

function RunSummary({ id }: { id: string }) {
  const { run, daily } = useRun(id)
  const byPhase = useMemo(() => summarizeByPhase(daily), [daily])

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
          Seed {run.seed} · {run.horizon_days} days · {run.customer_count} customers ·
          baseline ends day {run.baseline_end_day} · experiment from day{' '}
          {run.experiment_start_day}
        </p>
      </div>
      {run.status === 'completed' && (
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
      <div className="panel">
        <h2>Sample ({customers.length} rows)</h2>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>#</th>
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
