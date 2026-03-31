# Mathematical models reference

This document states the **equations implemented in code** for the pricing simulator: cohort sampling, daily purchase probability, churn, predictive customer lifetime value (CLV), and experiment-phase statistics. For narrative context and file pointers, see [`docs/pricing-model.md`](pricing-model.md) and [`app/domain/customer.py`](../app/domain/customer.py).

**Math rendering:** Inline math uses single dollar signs (`$…$`); display equations use `$$` on their own lines before and after the block. [GitHub-flavored Markdown](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/writing-mathematical-expressions) renders these on **github.com**. In **VS Code / Cursor**, the built-in Markdown preview often does **not** typeset math; install an extension such as **Markdown+Math** (or **LaTeX Workshop** with math support) and use that preview, or view the file on GitHub.

Notation: $d$ is the simulation day index; customer subscripts are omitted where clear.

---

## 1. Cohort generation (static traits)

Each customer is drawn once at run start ([`generate_customers`](../app/services/simulation/engine.py)).

| Quantity | Distribution / rule |
|----------|---------------------|
| Budget $B$ | $B = \max(8,\, Z)$ with $Z \sim \mathcal{N}(\mu_B, \sigma_B^2)$ from `budget_mean`, `budget_std`. |
| Buy propensity $\pi_0$ | $\pi_0 \sim \mathrm{Beta}(\alpha,\beta)$ then clipped to $[0.02,\,0.95]$ (`propensity_alpha`, `propensity_beta`). |
| Price threshold $T$ | $T = U \cdot B$ with $U \sim \mathrm{Uniform}(0.35,\,0.85)$. |
| Repeat boost $\rho$ | $\rho \sim \mathrm{Uniform}(0.15,\,0.55)$. |
| Basket mean $\mu_\mathrm{basket}$ | $\mu_\mathrm{basket} = \max(4,\, e^X)$ with $X \sim \mathcal{N}(m_\ell,\,\sigma_\ell^2)$ (`basket_log_mean`, `basket_log_sigma`). |
| Zone | Categorical draw with probabilities proportional to `zone_weights`. |
| Sensitivities $\sigma_r,\,\sigma_p$ | i.i.d. $\mathrm{Uniform}(0.2,\,0.9)$ for retention and promo sensitivity. |
| Channel modifier $\gamma_c$ | Lookup from `channel_propensity_modifiers` (defaults include organic 1.0, paid 0.85, referral 1.15). |

**Segment** (deterministic rule [`derive_segment`](../app/domain/customer.py)):

- If $T/B < 0.42$ and $B>0$: `price_sensitive`.
- Else if $\pi_0 \ge 0.42$: `loyal`.
- Else: `casual`.

---

## 2. Daily basket subtotal

Given cohort trait $\mu_\mathrm{basket}$, the **order subtotal** $S_d$ each active day is

$$
S_d = \max\bigl(3,\, \exp(Y)\bigr), \qquad Y \sim \mathcal{N}\bigl(\ln(\max(\mu_\mathrm{basket},1)),\, 0.25^2\bigr).
$$

So $S_d$ is lognormal with **per-day** $\sigma = 0.25$, distinct from cohort $\mu_\mathrm{basket}$ sampling ([`_sample_basket`](../app/services/simulation/engine.py)).

---

## 3. Customer-facing total price

Let $S$ be the basket subtotal, $f_\mathrm{del}$ the applicable delivery fee for the phase/arm, $f_\mathrm{svc}$ the baseline service fee, $D_\mathrm{base}$ the baseline discount, $D_\mathrm{extra}$ the variant extra discount (only if promo-eligible), and $F$ the free-delivery threshold (possibly `None`). Delivery charged is

$$
\mathrm{del}(f) = \begin{cases}
0 & \text{if } F \text{ is set and } S \ge F \\
f & \text{otherwise.}
\end{cases}
$$

**Baseline / washout:**

$$
P = S + \mathrm{del}(f_\mathrm{base}) + f_\mathrm{svc} - D_\mathrm{base}.
$$

**Experiment control arm:** same structure with control delivery fee.

**Experiment variant arm:**

$$
P = S + \mathrm{del}(f_\mathrm{var}) + f_\mathrm{svc} - D_\mathrm{base} - D_\mathrm{extra}\,\mathbb{1}\{\text{promo eligible}\}.
$$

---

## 4. Purchase probability

Let $P$ be the offered total, $B$ the customer budget, $\pi_0$ buy propensity, $\gamma_c$ channel modifier, $T$ price threshold, $k$ purchase count, $R$ retention score, $\sigma_r$ retention sensitivity, $\sigma_p$ promo sensitivity, $\rho$ repeat boost. Let $m_t = m_{\mathrm{temp}}(d)$ and $m_g$ be temporal and geographic multipliers, and $e \in \{0,1\}$ promo eligibility in context (variant-only ineligibility applies the 0.85 factor).

**Budget gate:**

$$
\mathbb{1}_{P \le B}
$$

If false, probability is 0.

**Price effect** (for $T>0$; else 1):

$$
r = \min(P/T,\, 3), \qquad \phi_\mathrm{price} = \frac{1}{1 + \max(0,\, r - 1)}.
$$

**Repeat vs first-time:**

$$
\phi_\mathrm{repeat} = \begin{cases}
1 + \rho\,(1 + 0.1 k) & \text{if purchased before} \\
\max(0.15,\, 1 - 0.45\,\sigma_p) & \text{otherwise.}
\end{cases}
$$

**Calendar and promo:**

$$
\phi_\mathrm{cal} = m_t\, m_g \times \begin{cases} 0.85 & \text{if } e = 0 \\ 1 & \text{if } e = 1 \end{cases}
$$

**Retention:**

$$
\phi_\mathrm{ret} = 1 + 0.15\,(R - 1)\,\sigma_r.
$$

**Raw then clipped:**

$$
p = \mathrm{clip}_{[0,1]}\Bigl( \pi_0\,\gamma_c\,\phi_\mathrm{price}\,\phi_\mathrm{repeat}\,\phi_\mathrm{cal}\,\phi_\mathrm{ret} \Bigr).
$$

Implemented in [`compute_purchase_probability`](../app/domain/customer.py).

### 4.1 Temporal multiplier

Day $d$ maps to weekday via $(d-1) \bmod 7$ with day 1 = Monday; weekend if index $\ge 5$.

$$
m_{\mathrm{temp}}(d) = b_{\mathrm{dow}} \cdot \bigl(1 + a \sin(d/14)\bigr),
$$

where $b_{\mathrm{dow}}$ is `weekend_factor` or `weekday_factor`, and $a$ is `seasonal_amplitude` ([`temporal_multiplier`](../app/services/pricing/temporal.py)).

### 4.2 Geographic multiplier

Zone $z$ maps through a table defaulting to $\{A:1.0,\, B:1.08,\, C:0.92\}$ merged with `zone_modifiers` ([`zone_multiplier`](../app/services/pricing/geographic.py)).

---

## 5. Purchase draw (Bernoulli)

With $U \sim \mathrm{Uniform}(0,1)$ independent each day (except where incrementality ties draws; see below),

$$
\text{purchase} = \mathbb{1}\{ U < p \}.
$$

---

## 6. Retention score dynamics

Initial $R = 1$. After each purchase ([`register_purchase`](../app/domain/customer.py)):

$$
R \leftarrow \min\bigl(2.5,\, R + 0.12\,\sigma_r\bigr).
$$

If $u \ge 1$ days since last purchase, before the day’s decisions ([`decay_retention`](../app/domain/customer.py)):

$$
R \leftarrow \max\bigl(1,\, R - 0.01 \cdot \min(u,\,30)\bigr).
$$

---

## 7. Daily churn probability

With base rate $\lambda =$ `churn_base_rate` ([`compute_churn_probability`](../app/domain/customer.py)):

$$
p_{\mathrm{churn}} = \mathrm{clip}_{[0,1]}\Bigl( \lambda \cdot \max(0,\, 2 - R) \Bigr).
$$

So for $R \ge 2$, $p_{\mathrm{churn}} = 0$; for $R = 1$, $p_{\mathrm{churn}} = \lambda$.

---

## 8. Predictive CLV (discounted geometric survival)

Computed for active customers in [`compute_predictive_clv`](../app/domain/customer.py). Inputs: horizon length $N =$ `clv_projected_days`, annual discount rate $r$, churn base $\lambda$, and a **representative** offered price $\tilde P$ (engine uses customer-typical total so $p_{\mathrm{buy}}$ matches scale).

$$
p_{\mathrm{buy}} = p(\tilde P), \qquad R_{\mathrm{day}} = p_{\mathrm{buy}} \cdot \mu_\mathrm{basket}.
$$

($R_{\mathrm{day}}$ uses `basket_mean`, not the random $S_d$.)

$$
p_{\mathrm{churn}} = \lambda \cdot \max(0,\, 2 - R), \qquad
\delta = 1 - \frac{r}{365}.
$$

**Per-day survival–discount factor:**

$$
s = (1 - p_{\mathrm{churn}})\,\delta.
$$

If $0 < s < 1$, the present value of expected daily revenue over $N$ days is the finite geometric sum

$$
\mathrm{CLV} = R_{\mathrm{day}} \sum_{t=1}^{N} s^{\,t}
= R_{\mathrm{day}} \cdot \frac{s\,(1 - s^{N})}{1 - s}.
$$

If $s \ge 1$ or $s \le 0$ (degenerate in code), the implementation falls back to $\mathrm{CLV} = R_{\mathrm{day}} \cdot N$. Inactive (churned) customers: $\mathrm{CLV} = 0$.

This is a **closed-form predictive** metric, not a Monte Carlo path simulation.

---

## 9. Incrementality (shared uniform for variant)

On experiment days for the **variant** arm, let $p_v = p(P_v)$ and $p_c = p(P_c)$ where $P_c$ is the **counterfactual control total** for the same basket. One draw $U \sim \mathrm{Uniform}(0,1)$:

$$
\text{purchase} = \mathbb{1}\{U < p_v\}, \qquad
\text{counterfactual purchase} = \mathbb{1}\{U < p_c\}.
$$

**Incremental order** flags purchase with variant pricing that would not have occurred under control pricing at the same random draw ([`execute_simulation`](../app/services/simulation/engine.py)).

---

## 10. Experiment inference (aggregated run statistics)

After the run, experiment-phase **conversion** is summarized as orders per **customer-day** (sum of `customers_evaluated` over experiment days per arm). Let $x_j$ be orders and $n_j$ customer-days for arm $j \in \{c,v\}$.

**Point estimates:** $\hat p_j = x_j / n_j$ (if $n_j>0$).

### 10.1 Wilson score interval for a binomial proportion

With $z = 1.96$ (standard normal critical value for ~95% two-sided), let $\hat p = x/n$. Define

$$
\mathrm{denom} = 1 + \frac{z^2}{n}, \quad
\mathrm{centre} = \hat p + \frac{z^2}{2n}, \quad
\mathrm{margin} = z \sqrt{\frac{\hat p(1-\hat p) + z^2/(4n)}{n}}.
$$

Endpoints (clipped to $[0,1]$):

$$
L = \max\left(0,\,\frac{\mathrm{centre} - \mathrm{margin}}{\mathrm{denom}}\right), \quad
U = \min\left(1,\,\frac{\mathrm{centre} + \mathrm{margin}}{\mathrm{denom}}\right).
$$

See [`wilson_interval`](../app/services/stats/inference.py).

### 10.2 Pooled two-proportion z-test

Pooled proportion $p = (x_c + x_v)/(n_c + n_v)$. Standard error

$$
\mathrm{SE} = \sqrt{p(1-p)\left(\frac{1}{n_c} + \frac{1}{n_v}\right)}.
$$

Statistic $z_{\mathrm{stat}} = (\hat p_v - \hat p_c) / \mathrm{SE}$; two-sided p-value uses the standard normal CDF $\Phi$:

$$
p_{\mathrm{two}} = 2\,\Phi(-|z_{\mathrm{stat}}|).
$$

See [`two_proportion_z_test_p_value`](../app/services/stats/inference.py). **Note:** Customer-days are treated as independent Bernoulli trials here; in reality the same customer contributes multiple correlated days, so this is a **practical summary test** on rolled-up metrics, not a full hierarchical model.

### 10.3 Beta–binomial Bayesian summaries (dual with §10.1–10.2)

The API and [`build_experiment_inference`](../app/services/stats/inference.py) attach a **Bayesian** block alongside the Wilson interval and z-test. The same rolled-up counts $(x_j, n_j)$ are used.

**Prior (per arm, independent):** $p_j \sim \mathrm{Beta}(\alpha_0, \beta_0)$ with hyperparameters $\alpha_0, \beta_0 > 0$ chosen by the caller (`prior_alpha`, `prior_beta` on `GET /api/runs/{id}/experiment-inference`; defaults $\alpha_0=\beta_0=1$).

**Posterior:** With Binomial likelihood $x_j \mid p_j, n_j \sim \mathrm{Binomial}(n_j, p_j)$,

$$
p_j \mid \text{data} \sim \mathrm{Beta}(\alpha_0 + x_j,\; \beta_0 + n_j - x_j).
$$

**Posterior mean:** $\mathbb{E}[p_j \mid \text{data}] = \dfrac{\alpha_0 + x_j}{\alpha_0 + \beta_0 + n_j}$.

**Equal-tailed 95% credible intervals** for $p_j$ are computed in code from Monte Carlo draws (fixed RNG seed) matching the Gamma–Beta sampler used for arm comparisons.

**Probability variant beats control:** Independent posteriors for the two arms imply

$$
\mathbb{P}(p_v > p_c \mid \text{data}) = \iint \mathbf{1}\{p_v > p_c\}\, \pi(p_c \mid x_c, n_c)\, \pi(p_v \mid x_v, n_v) \,\mathrm{d}p_c\, \mathrm{d}p_v,
$$

estimated by the fraction of paired posterior draws with $p_v > p_c$ ([`build_bayesian_experiment_inference`](../app/services/stats/inference.py)).

**Lift summaries:** For paired draws $(p_c, p_v)$, **absolute lift** $p_v - p_c$ yields a posterior sample; report mean and median of that sample. **Relative lift** $(p_v - p_c) / p_c$ is summarized only on draws with $p_c > \varepsilon$ (implementation uses $\varepsilon = 10^{-6}$); if no draw qualifies, relative-lift summaries are omitted (`null` in JSON). The response includes the fraction of draws used for relative lift.

The same **customer-day correlation caveat** as in §10.2 applies: independent Beta posteriors on rolled-up binomial counts are a practical summary, not a hierarchical model over repeated customer sequences.

---

## 11. Holdout validation revenue (actual)

When `clv_validation_days > 0`, the engine extends the simulation at baseline pricing without new churn. **Actual** validation revenue per customer is accumulated in the database for calibration against `predicted_clv`; it is not another closed-form formula in this doc.

---

## References in repo

| Topic | Primary code |
|-------|----------------|
| Purchase probability, churn, CLV | [`app/domain/customer.py`](../app/domain/customer.py) |
| Cohort sampling, basket, prices, shared draw | [`app/services/simulation/engine.py`](../app/services/simulation/engine.py) |
| Wilson / z-test / Beta–binomial Bayesian | [`app/services/stats/inference.py`](../app/services/stats/inference.py) |
| Tunable parameters | [`app/schemas/run_config.py`](../app/schemas/run_config.py) |
