# Notebook quality standards — Pricing Simulator

Use this checklist when authoring or editing notebooks under `notebooks/`.

## Opening motivation (required)

After the title, include a short markdown block (2–4 sentences) that answers:

- **Why** this notebook exists (business or engineering question).
- **Who** it is for (analyst, engineer, stakeholder).
- **What** the reader will be able to do after running it.

Template:

> **Why this notebook:** …  
> **Audience:** …  
> **Outcome:** After running this notebook you will …

## Section conclusions (required)

Replace open-ended “follow-up questions” as the *only* ending with **Key insights** (3–5 bullets) that reference **numbers or plots actually shown** in that section. Optional: add 1–2 “Dig deeper” bullets for exploration.

## Closing synthesis (required)

End every notebook with a markdown cell:

- **What you learned** (3 bullets max).
- **Next up:** link to the next notebook by filename and one-line purpose.

## Interactivity

- Prefer **`ipywidgets.interact`** for one-off parameter sweeps (sliders, dropdowns).
- Prefer **Plotly** for charts where hover, zoom, or overlay comparison helps.
- Use `%matplotlib inline` (or IPython’s default) when mixing widgets with Matplotlib.

Minimal pattern:

```python
import ipywidgets as widgets
from IPython.display import display

def _preview(x: float) -> None:
    ...

widgets.interact(_preview, x=widgets.FloatSlider(value=1.0, min=0.0, max=2.0, step=0.05))
```

## Notation (align with docs)

- **`B`**: customer **budget** (trait).
- **`S` or `S_d`**: **basket subtotal** for day *d* (from lognormal draw); do not reuse `B` for basket in narrative cells.
- Point readers to [`docs/mathematical-models.md`](../docs/mathematical-models.md) for full equations.

## Diagrams in Jupyter

- **Avoid Mermaid** in notebook markdown unless the team standard viewer supports it; prefer a **Matplotlib** DAG or flow sketch for universal rendering.

## Run size and CI

- Small `customer_count` / `horizon` values are fine for **fast local runs and CI**; add a **callout** recommending larger sizes for “production-like” analysis.
- Notebook tests may set `SKIP_NOTEBOOK_TESTS=1`; mention when a cell is intentionally heavy.

## Canonical stats path

- Prefer **`load_experiment_arm_rollups`** + **`build_experiment_inference`** from `app.services.stats.inference` when teaching experiment inference, and cross-check ad-hoc scipy/statsmodels calls against that path when both appear.

## Stale imports and promises

- Remove unused imports and fix narrative/code mismatches (e.g. table says 500 customers but code uses 80).
- If the intro promises an optional cell (e.g. DB-backed), **include that cell** or remove the promise.
