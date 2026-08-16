"""
CHRISHEM Chaos & Nonlinear Systems Engine
==========================================
Real, from-scratch numerical engines for nonlinear dynamics and forecasting.
No fabricated "AI" metrics — every number is genuinely computed.

Capabilities
  - Real SciPy ODE integration (odeint/LSODA) for 3-state nonlinear systems
  - Lyapunov-style expansion-rate heuristic (finite-difference local growth)
  - Rolling variance / autocorrelation early-warning signals
  - Bifurcation scan (local-maxima vs parameter sweeps)
  - Monte Carlo uncertainty ensemble (perturbed initial conditions)
  - 2D sensitivity heatmap (parameter grid)
  - Holt-Winters exponential smoothing (level+trend+seasonal)
  - Autoregressive AR(p) fit via ordinary least squares
  - Z-score anomaly detection

Owner: Kula Chris (CHRISHEM)
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.integrate import odeint


# ---------------------------------------------------------------------------
# ODE Integration
# ---------------------------------------------------------------------------
def solve_ode_system(rhs_fn, initial_state, t, args=()):
    """Thin wrapper around SciPy's real ODE integrator (odeint / LSODA)."""
    return odeint(rhs_fn, initial_state, t, args=args)


def default_ode(state, t, a, b, c, shock_val=0.0, t_max=200):
    """Generic 3-state nonlinear system with a mid-run shock window."""
    x, y, z = state
    shock = shock_val if (0.45 * t_max <= t <= 0.55 * t_max) else 0.0
    return [x - z - (y - a) * x + shock, 1 - b * y - x ** 2, x - c * z]


# ---------------------------------------------------------------------------
# Dynamics metrics
# ---------------------------------------------------------------------------
def lyapunov_style_heuristic(x_traj, dt):
    """
    Finite-difference estimate of local expansion rate (early-warning heuristic).
    Disclosed as a heuristic, not a rigorous Lyapunov exponent.
    """
    growth = np.abs(np.gradient(x_traj)) + 1e-6
    return float(np.mean(np.log(growth)) / dt)


def rolling_variance_autocorr(x_traj, window=20):
    var_series, ac_series = [], []
    for i in range(1, len(x_traj) + 1):
        seg = x_traj[max(0, i - window):i]
        var_series.append(float(np.var(seg)))
        if len(seg) > 1:
            ac = np.corrcoef(seg[:-1], seg[1:])[0, 1]
            ac_series.append(0.0 if np.isnan(ac) else float(ac))
        else:
            ac_series.append(0.0)
    return var_series, ac_series


def classify_state(mlce: float) -> str:
    if mlce < 0:
        return "STABLE"
    if mlce < 0.2:
        return "BORDERLINE"
    return "CRITICAL"


# ---------------------------------------------------------------------------
# Bifurcation scan
# ---------------------------------------------------------------------------
def bifurcation_scan(rhs_fn, initial_state, t, param_range, param_idx=1, args_base=(), shock=0.0):
    """
    Sweep a scalar parameter and record local maxima of the first state variable.
    Returns (param_values, peak_values) for a bifurcation diagram.
    param_idx: index in args tuple to vary (default 1 => the 'b' friction term).
    """
    peaks, b_pts = [], []
    for pval in param_range:
        args = list(args_base)
        args[param_idx] = pval
        sol = solve_ode_system(rhs_fn, initial_state, t, args=tuple(args))[:, 0]
        local_max = sol[np.r_[False, sol[1:] > sol[:-1]] & np.r_[sol[:-1] > sol[1:], False]]
        for mx in local_max[-10:]:
            peaks.append(float(mx))
            b_pts.append(float(pval))
    return np.array(b_pts), np.array(peaks)


# ---------------------------------------------------------------------------
# Monte Carlo ensemble
# ---------------------------------------------------------------------------
def monte_carlo_ensemble(rhs_fn, initial_state, t, args, n_runs=30, noise_scale=0.05, seed=42):
    """
    Run an ensemble of ODE integrations with perturbed initial conditions.
    Returns array of shape (len(t), n_runs) of the first state variable.
    """
    rng = np.random.default_rng(seed)
    runs = []
    for _ in range(n_runs):
        perturbed = [v + rng.normal(0, noise_scale) for v in initial_state]
        runs.append(solve_ode_system(rhs_fn, perturbed, t, args=args)[:, 0])
    return np.array(runs).T


# ---------------------------------------------------------------------------
# Sensitivity heatmap
# ---------------------------------------------------------------------------
def sensitivity_heatmap(rhs_fn, initial_state, t, a_range, b_range, args_base=()):
    """
    Compute the max amplitude of the first state over a 2D parameter grid (a vs b).
    Returns (a_grid, b_grid, Z) where Z[i,j] = max amplitude at (a_grid[j], b_grid[i]).
    """
    A_m, B_m = np.meshgrid(a_range, b_range)
    Z_m = np.zeros_like(A_m)
    for i in range(A_m.shape[0]):
        for j in range(A_m.shape[1]):
            args = list(args_base)
            args[0] = A_m[i, j]
            args[1] = B_m[i, j]
            sol = solve_ode_system(rhs_fn, initial_state, t, args=tuple(args))[:, 0]
            Z_m[i, j] = np.max(sol)
    return a_range, b_range, Z_m


# ---------------------------------------------------------------------------
# Forecasting engines (real statistics, no ML black box)
# ---------------------------------------------------------------------------
def holt_winters_forecast(series, periods=12, alpha=0.4, beta=0.2, gamma=0.1, season_len=0):
    """
    From-scratch Holt-Winters exponential smoothing (optional additive seasonality).
    Returns (fitted_values, forecast_values).
    """
    y = np.asarray(series, dtype=float)
    n = len(y)
    if n < 2:
        return y, np.repeat(y[-1] if n else 0.0, periods)

    if season_len and season_len > 1 and n >= 2 * season_len:
        level = np.mean(y[:season_len])
        trend = (np.mean(y[season_len:2 * season_len]) - np.mean(y[:season_len])) / season_len
        seasonal = [y[i] - level for i in range(season_len)]
        fitted = []
        for i in range(n):
            s_idx = i % season_len
            fitted.append(level + trend + seasonal[s_idx])
            val = y[i]
            last_level = level
            level = alpha * (val - seasonal[s_idx]) + (1 - alpha) * (level + trend)
            trend = beta * (level - last_level) + (1 - beta) * trend
            seasonal[s_idx] = gamma * (val - level) + (1 - gamma) * seasonal[s_idx]
        forecast = []
        for h in range(1, periods + 1):
            s_idx = (n + h - 1) % season_len
            forecast.append(level + h * trend + seasonal[s_idx])
        return np.array(fitted), np.array(forecast)
    else:
        level, trend = y[0], (y[1] - y[0]) if n > 1 else 0.0
        fitted = [level]
        for i in range(1, n):
            val = y[i]
            last_level = level
            level = alpha * val + (1 - alpha) * (level + trend)
            trend = beta * (level - last_level) + (1 - beta) * trend
            fitted.append(level)
        forecast = [level + h * trend for h in range(1, periods + 1)]
        return np.array(fitted), np.array(forecast)


def ar_least_squares_forecast(series, lags=3, periods=12):
    """
    Autoregressive AR(p) model fit via ordinary least squares (normal equations).
    Returns (fitted, forecast, coefficients).
    """
    y = np.asarray(series, dtype=float)
    n = len(y)
    lags = max(1, min(lags, n - 2))
    X = np.column_stack([y[lags - k - 1: n - k - 1] for k in range(lags)])
    X = np.column_stack([np.ones(len(X)), X])
    target = y[lags:]
    coeffs, *_ = np.linalg.lstsq(X, target, rcond=None)
    fitted = X @ coeffs
    history = list(y[-lags:])
    forecast = []
    for _ in range(periods):
        row = np.array([1.0] + history[-lags:][::-1])
        nxt = float(row @ coeffs)
        forecast.append(nxt)
        history.append(nxt)
    return fitted, np.array(forecast), coeffs


def anomaly_flags(series, z_thresh=2.5):
    """Honest z-score anomaly detector."""
    y = np.asarray(series, dtype=float)
    mu, sigma = np.mean(y), np.std(y) + 1e-9
    z = (y - mu) / sigma
    return np.abs(z) > z_thresh, z


# ---------------------------------------------------------------------------
# Domain ODE models (real, parameterized simulation engines)
# ---------------------------------------------------------------------------
def grid_failure_model(y, t, demand_mult, renewables):
    """Energy grid stress: instability, storage, thermal strain."""
    Instability, StorageLevel, ThermalStrain = y
    dInstability = 0.05 * demand_mult - 0.03 * (renewables * 0.01) + 0.02 * ThermalStrain
    dStorage = -0.04 * demand_mult + 0.02 * (renewables * 0.01)
    dThermal = 0.08 * (demand_mult - 1.0) - 0.01 * StorageLevel
    return [dInstability, dStorage, dThermal]


def food_model(y, t, consumption, stress, fertil_inflate):
    """Food reserve depletion: stock, vulnerability, price."""
    Stock, Vuln, Price = y
    dStock = -consumption * 0.001 - (stress * 12.0)
    dVuln = 0.05 * stress + 0.01 * (1.0 / (Stock + 1.0))
    dPrice = 0.4 * fertil_inflate + 0.2 * stress - 0.1 * Price
    return [dStock, dVuln, dPrice]


def macro_model(y, t, rate, shock, fx_depr):
    """Macro-financial debt sustainability: debt, fx reserves, inflation."""
    D, FX, Infl = y
    dD = (rate - 4.0) * D * 0.01 - 0.02 + (shock * 0.05)
    dFX = -0.1 * (rate - 5.0) - (shock * 0.15)
    dInfl = 0.5 * (fx_depr * 0.1) + 0.2 * shock - 0.1 * Infl
    return [dD, dFX, dInfl]


def seir_model(y, t, beta, gamma, icu_rate, mitigation):
    """SEIR + ICU compartmental epidemic model."""
    S, E, I, R, ICU = y
    eff_beta = beta * (1.0 - mitigation)
    N = S + E + I + R + ICU + 1e-6
    dS = -eff_beta * S * I / N
    dE = eff_beta * S * I / N - 0.2 * E
    dI = 0.2 * E - gamma * I
    dR = gamma * I * (1.0 - icu_rate)
    dICU = gamma * I * icu_rate - 0.1 * ICU
    return [dS, dE, dI, dR, dICU]


if __name__ == "__main__":
    t = np.linspace(0, 200, 400)
    sol = solve_ode_system(default_ode, [0.1, 0.1, 0.1], t, args=(1.5, 0.9, 1.0, 0.0, 200))
    mlce = lyapunov_style_heuristic(sol[:, 0], t[1] - t[0])
    print(f"mLCE-style heuristic: {mlce:.4f} -> {classify_state(mlce)}")
    fitted, fc = holt_winters_forecast(np.linspace(100, 145, 60) + 6 * np.sin(np.linspace(0, 6 * np.pi, 60)), periods=12)
    print(f"Holt-Winters forecast length: {len(fc)}")
