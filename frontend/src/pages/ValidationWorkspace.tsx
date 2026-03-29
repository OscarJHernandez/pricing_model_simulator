const notebooks = [
  'customer_model_validation.ipynb',
  'repeat_purchase_validation.ipynb',
  'simulation_smoke_test.ipynb',
  'experiment_comparison_demo.ipynb',
  'context_and_constraints_demo.ipynb',
]

const snippet = `from app.schemas.run_config import RunConfig
from app.domain.customer import Customer, PurchaseContext
from app.services.pricing.temporal import temporal_multiplier

cfg = RunConfig(seed=1, horizon_days=10, baseline_end_day=4, experiment_start_day=5, customer_count=50)
c = Customer(1, 0, 50.0, 0.2, 25.0, 0.3, 18.0, "A")
ctx = PurchaseContext(1.0, 1.0, True)
print(cfg.horizon_days, c.compute_purchase_probability(22.0, 1, ctx), temporal_multiplier(6))`

export function ValidationWorkspace() {
  return (
    <div>
      <h1>Validation workspace</h1>
      <p className="muted" style={{ marginBottom: '1rem' }}>
        Notebooks live in <code>/notebooks</code> and import the same <code>app</code> package as
        the API. Run Jupyter from the repo root with the virtualenv and{' '}
        <code>pip install -e .</code>.
      </p>
      <div className="panel">
        <h2>Notebook files (open locally)</h2>
        <ul>
          {notebooks.map((n) => (
            <li key={n}>
              <code>notebooks/{n}</code>
            </li>
          ))}
        </ul>
      </div>
      <div className="panel">
        <h2>Example checks (Python)</h2>
        <pre className="code-block">{snippet}</pre>
      </div>
      <div className="panel">
        <h2>API health</h2>
        <p className="muted">
          Use <code>GET /api/health</code> from the browser or curl while the backend is running.
        </p>
      </div>
    </div>
  )
}
