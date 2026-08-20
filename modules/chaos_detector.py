"""
Real-World Chaos & Nonlinear Dynamics Detector
================================================
A sector-agnostic, data-driven engine for detecting and characterizing
chaotic / nonlinear dynamics in ANY real, uploaded numeric time series
(education metrics, patient vitals, security incident counts, crop
yields, machine telemetry, financial series, whatever the user brings).

Every method here is a named, published, peer-reviewed technique. No
step fabricates a result or a confidence number. Where the data is too
short or too noisy for a method to be reliable, the function says so
explicitly rather than returning a plausible-looking number.

Methods implemented:
  - Average Mutual Information          (Fraser & Swinney, 1986)   -> embedding delay tau
  - False Nearest Neighbors             (Kennel et al., 1992)      -> embedding dimension m
  - Rosenstein's algorithm              (Rosenstein et al., 1993)  -> largest Lyapunov exponent
  - 0-1 Test for Chaos                  (Gottwald & Melbourne, 2004) -> K in [0,1]
  - Grassberger-Procaccia correlation dim (Grassberger & Procaccia, 1983) -> D2, saturation check
  - Sample Entropy                      (Richman & Moorman, 2000)  -> complexity
  - Empirical Mode Decomposition + Hilbert Spectrum (Huang et al., 1998) -> IMFs, inst. freq/amp
  - Recurrence Quantification Analysis  (Marwan et al., 2007)      -> %DET, %LAM, L_mean, ENTR

No step here claims to know which "sector" a series comes from. The
math is identical regardless of domain; sector context only affects
how a human should *interpret* the output, which is why this module
never emits sector-specific numbers, only sector-neutral diagnostics.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from typing import Optional


# --------------------------------------------------------------------------- #
# Data adequacy — refuse to fake confidence on data too short to support it.
# --------------------------------------------------------------------------- #

MIN_N = {
    "mutual_information": 50,
    "false_nearest_neighbors": 50,
    "lyapunov_rosenstein": 100,
    "zero_one_test": 50,
    "correlation_dimension": 200,
    "sample_entropy": 50,
    "emd": 30,
    "rqa": 50,
}


def _adequacy(name: str, n: int) -> Optional[str]:
    need = MIN_N.get(name, 30)
    if n < need:
        return (f"Only {n} data point(s) available; {name.replace('_',' ')} needs at least "
                f"{need} for a statistically defensible result. Reported value is a rough "
                f"estimate only — treat it as unreliable.")
    return None


# --------------------------------------------------------------------------- #
# 1. Average Mutual Information -> optimal embedding delay tau
# --------------------------------------------------------------------------- #

def average_mutual_information(series: np.ndarray, max_tau: int = 50, bins: int = 16):
    x = np.asarray(series, dtype=float)
    n = len(x)
    max_tau = min(max_tau, n // 4) or 1
    hist_range = (x.min(), x.max())
    ami = np.zeros(max_tau)
    for tau in range(1, max_tau + 1):
        xt, xtau = x[:-tau], x[tau:]
        joint, xedges, yedges = np.histogram2d(xt, xtau, bins=bins, range=[hist_range, hist_range])
        joint_p = joint / joint.sum()
        px = joint_p.sum(axis=1, keepdims=True)
        py = joint_p.sum(axis=0, keepdims=True)
        with np.errstate(divide="ignore", invalid="ignore"):
            terms = joint_p * np.log((joint_p + 1e-300) / (px * py + 1e-300))
        ami[tau - 1] = np.nansum(terms[joint_p > 0])
    # Pick tau at the "knee" where AMI stops meaningfully decreasing, rather
    # than the strict first local minimum — for maps that decorrelate fast
    # (e.g. the logistic map), AMI decays monotonically then goes flat/noisy,
    # and a strict-minimum rule locks onto tail noise, not the real knee.
    total_drop = ami[0] - ami[-1]
    tol = max(1e-9, 0.02 * total_drop)
    look = 3
    optimal_tau = max_tau
    for i in range(len(ami) - look):
        if np.all(np.abs(np.diff(ami[i:i + look + 1])) < tol):
            optimal_tau = i + 1
            break
    return optimal_tau, ami


# --------------------------------------------------------------------------- #
# 2. False Nearest Neighbors -> optimal embedding dimension m
# --------------------------------------------------------------------------- #

def time_delay_embed(series: np.ndarray, dim: int, tau: int) -> np.ndarray:
    x = np.asarray(series, dtype=float)
    n = len(x) - (dim - 1) * tau
    if n <= 0:
        raise ValueError("Series too short for the requested embedding dimension/delay.")
    return np.array([x[i:i + n] for i in range(0, dim * tau, tau)]).T


def false_nearest_neighbors(series: np.ndarray, tau: int, max_dim: int = 10,
                             rtol: float = 15.0, atol: float = 2.0):
    x = np.asarray(series, dtype=float)
    sd = np.std(x)
    fnn_pct = []
    chosen_dim = max_dim
    for dim in range(1, max_dim + 1):
        try:
            emb = time_delay_embed(x, dim + 1, tau)
        except ValueError:
            break
        emb_d = emb[:, :dim]
        n_pts = emb_d.shape[0]
        if n_pts < 10:
            break
        # brute-force nearest neighbor (fine for the sample sizes this UI expects)
        false_count = 0
        for i in range(n_pts):
            dists = np.linalg.norm(emb_d - emb_d[i], axis=1)
            dists[i] = np.inf
            j = np.argmin(dists)
            r_d = dists[j]
            if r_d == 0:
                continue
            extra_dim_dist = abs(emb[i, dim] - emb[j, dim])
            if (extra_dim_dist / r_d > rtol) or (np.sqrt(r_d**2 + extra_dim_dist**2) / sd > atol):
                false_count += 1
        pct = 100.0 * false_count / n_pts
        fnn_pct.append(pct)
        if pct < 1.0:
            chosen_dim = dim
            break
    else:
        chosen_dim = max_dim
    if fnn_pct:
        chosen_dim = int(np.argmin(fnn_pct) + 1)
    return chosen_dim, np.array(fnn_pct)


# --------------------------------------------------------------------------- #
# 3. Rosenstein's algorithm -> largest Lyapunov exponent, from real data
# --------------------------------------------------------------------------- #

def rosenstein_lyapunov(series: np.ndarray, dim: int, tau: int, dt: float = 1.0,
                         theiler_window: Optional[int] = None, max_k_frac: float = 0.5):
    x = np.asarray(series, dtype=float)
    emb = time_delay_embed(x, dim, tau)
    n_pts = emb.shape[0]
    theiler = theiler_window if theiler_window is not None else max(tau, 1)

    nn_idx = np.full(n_pts, -1, dtype=int)
    for i in range(n_pts):
        dists = np.linalg.norm(emb - emb[i], axis=1)
        window = slice(max(0, i - theiler), min(n_pts, i + theiler + 1))
        dists[window] = np.inf
        j = np.argmin(dists)
        nn_idx[i] = j if np.isfinite(dists[j]) else -1

    max_horizon = max(5, int(n_pts * max_k_frac))
    log_div_sum = np.zeros(max_horizon)
    log_div_count = np.zeros(max_horizon)
    for i in range(n_pts):
        j = nn_idx[i]
        if j < 0:
            continue
        for k in range(max_horizon):
            if i + k >= n_pts or j + k >= n_pts:
                break
            d = np.linalg.norm(emb[i + k] - emb[j + k])
            if d > 0:
                log_div_sum[k] += np.log(d)
                log_div_count[k] += 1

    valid = log_div_count > (0.1 * n_pts)
    mean_log_div = np.full(max_horizon, np.nan)
    mean_log_div[valid] = log_div_sum[valid] / log_div_count[valid]
    k_axis = np.arange(max_horizon) * dt

    # Auto-detect the initial linear growth region: divergence grows
    # exponentially for a short window, then saturates at the attractor's
    # diameter and flattens/oscillates. Averaging past that point (as a
    # fixed-fraction window does) washes the exponential signal out to ~0.
    # So: walk forward from k=1 while the curve is still net-increasing over
    # a short lookahead; stop at the first sustained non-increase.
    valid_idx = np.flatnonzero(valid)
    if len(valid_idx) < 4:
        return dict(lle=float("nan"), divergence_curve=(k_axis, mean_log_div),
                     note="Not enough valid neighbor pairs to fit a divergence slope reliably.")

    look = 3
    end = valid_idx[-1]
    for pos in range(1, len(valid_idx) - look):
        i0 = valid_idx[pos]
        future = mean_log_div[valid_idx[pos:pos + look]]
        if np.all(np.diff(future) <= 0):
            end = i0
            break
    start = valid_idx[0]
    fit_idx = valid_idx[(valid_idx >= start) & (valid_idx <= end)]
    if len(fit_idx) < 3:
        fit_idx = valid_idx[: max(3, len(valid_idx) // 4)]

    xs = k_axis[fit_idx]
    ys = mean_log_div[fit_idx]
    slope, intercept = np.polyfit(xs, ys, 1)
    return dict(lle=float(slope), divergence_curve=(k_axis, mean_log_div),
                fit_region=(float(xs.min()), float(xs.max())), note=None)


# --------------------------------------------------------------------------- #
# 4. 0-1 Test for Chaos (Gottwald & Melbourne, 2004)
# --------------------------------------------------------------------------- #

def zero_one_test(series: np.ndarray, n_c: int = 100, rng_seed: int = 42):
    x = np.asarray(series, dtype=float)
    x = x - x.mean()

    # The 0-1 test assumes consecutive samples aren't near-redundant. Densely
    # oversampled data (e.g. a fine-step ODE trace, or a sensor logged far
    # faster than the system's own timescale) violates this and biases the
    # test toward K~0 regardless of the true dynamics. Detect that via lag-1
    # autocorrelation and decimate until it's back in a reasonable range —
    # a documented practical requirement of the method, applied automatically
    # rather than silently producing a wrong answer.
    decim = 1
    x_use = x
    for _ in range(6):
        if len(x_use) < 100:
            break
        ac1 = np.corrcoef(x_use[:-1], x_use[1:])[0, 1]
        if ac1 < 0.9:
            break
        decim *= 2
        x_use = x[::decim]
    x = x_use

    n = len(x)
    n_cut = max(10, n // 10)
    rng = np.random.default_rng(rng_seed)
    # avoid c near 0, pi, 2*pi (resonance with system's own periodicities)
    candidates = rng.uniform(np.pi / 5, 4 * np.pi / 5, size=n_c * 3)
    c_values = candidates[: n_c]

    Ks = []
    j_idx = np.arange(1, n + 1)
    for c in c_values:
        cosj, sinj = np.cos(j_idx * c), np.sin(j_idx * c)
        p = np.cumsum(x * cosj)
        q = np.cumsum(x * sinj)

        ns = np.arange(1, n_cut + 1)
        Mn = np.zeros(n_cut)
        Vosc = (np.mean(x) ** 2) * (1 - np.cos(ns * c)) / max(1e-12, (1 - np.cos(c)))
        for idx, nn in enumerate(ns):
            dp = p[nn:] - p[:-nn] if nn < len(p) else np.array([])
            dq = q[nn:] - q[:-nn] if nn < len(q) else np.array([])
            if len(dp) == 0:
                Mn[idx] = np.nan
            else:
                Mn[idx] = np.mean(dp**2 + dq**2)
        Dn = Mn - Vosc
        valid = np.isfinite(Dn)
        if valid.sum() < 5:
            continue
        # correlation coefficient between ns and Dn (Pearson) = growth-rate proxy K_c
        xs, ys = ns[valid].astype(float), Dn[valid]
        if np.std(xs) == 0 or np.std(ys) == 0:
            continue
        Kc = np.corrcoef(xs, ys)[0, 1]
        Ks.append(Kc)

    if not Ks:
        return dict(K=float("nan"), note="0-1 test could not be computed on this series (too short or degenerate).")
    K = float(np.median(Ks))
    K = float(np.clip(K, 0.0, 1.0))
    note = f"Series was decimated by {decim}x before testing (was oversampled)." if decim > 1 else None
    return dict(K=K, n_valid_c=len(Ks), decimation=decim, note=note)


# --------------------------------------------------------------------------- #
# 5. Grassberger-Procaccia correlation dimension + saturation check
# --------------------------------------------------------------------------- #

def correlation_dimension(series: np.ndarray, tau: int, dims=range(2, 8), n_r: int = 20):
    x = np.asarray(series, dtype=float)
    d2_by_dim = {}
    for dim in dims:
        try:
            emb = time_delay_embed(x, dim, tau)
        except ValueError:
            break
        n_pts = emb.shape[0]
        if n_pts < 30:
            break
        # subsample for tractability on larger series
        if n_pts > 800:
            sel = np.linspace(0, n_pts - 1, 800).astype(int)
            emb = emb[sel]
            n_pts = emb.shape[0]
        from scipy.spatial.distance import pdist
        dists = pdist(emb)
        dists = dists[dists > 0]
        if len(dists) < 50:
            break
        r_vals = np.logspace(np.log10(np.percentile(dists, 1)), np.log10(np.percentile(dists, 90)), n_r)
        C_r = np.array([(dists < r).mean() for r in r_vals])
        valid = C_r > 0
        if valid.sum() < 5:
            continue
        log_r, log_C = np.log(r_vals[valid]), np.log(C_r[valid])
        # scaling region = middle 60% of the log-log curve
        lo, hi = int(0.2 * len(log_r)), int(0.8 * len(log_r))
        if hi - lo < 3:
            lo, hi = 0, len(log_r)
        slope, _ = np.polyfit(log_r[lo:hi], log_C[lo:hi], 1)
        d2_by_dim[dim] = float(slope)

    if len(d2_by_dim) < 3:
        return dict(d2_by_dim=d2_by_dim, saturates=None,
                    note="Not enough valid embedding dimensions to test for saturation.")

    dims_used = np.array(sorted(d2_by_dim.keys()))
    vals = np.array([d2_by_dim[d] for d in dims_used])
    tail_n = min(4, len(dims_used))
    slope, _ = np.polyfit(dims_used[-tail_n:], vals[-tail_n:], 1)
    # Stochastic/high-dim series have D2 rising roughly 1-for-1 with embedding
    # dimension (the "correlation dimension" of noise is the embedding dim
    # itself). A low-dimensional attractor's D2 flattens out. Slope near 0
    # -> saturates; slope near 1 -> not saturating, consistent with noise.
    saturates = bool(slope < 0.3)
    return dict(d2_by_dim=d2_by_dim, saturates=saturates, tail_slope=float(slope),
                note=("D2 saturates as embedding dimension grows -> consistent with a low-dimensional "
                      "deterministic attractor." if saturates else
                      "D2 keeps rising roughly with embedding dimension -> consistent with high-dimensional "
                      "or stochastic behavior rather than low-dimensional chaos."))


# --------------------------------------------------------------------------- #
# 6. Sample Entropy (Richman & Moorman, 2000)
# --------------------------------------------------------------------------- #

def sample_entropy(series: np.ndarray, m: int = 2, r: Optional[float] = None):
    x = np.asarray(series, dtype=float)
    n = len(x)
    if r is None:
        r = 0.2 * np.std(x)
    if r == 0:
        return dict(sampen=float("nan"), note="Series has zero variance; sample entropy undefined.")

    def _phi(mm):
        templates = np.array([x[i:i + mm] for i in range(n - mm)])
        count = 0
        for i in range(len(templates)):
            d = np.max(np.abs(templates - templates[i]), axis=1)
            count += np.sum(d <= r) - 1  # exclude self-match
        return count

    B = _phi(m)
    A = _phi(m + 1)
    if B == 0 or A == 0:
        return dict(sampen=float("nan"), note="No matching templates found at this tolerance r; try a larger r.")
    return dict(sampen=float(-np.log(A / B)), note=None)


# --------------------------------------------------------------------------- #
# 7. Empirical Mode Decomposition (Huang et al., 1998) + Hilbert spectrum
# --------------------------------------------------------------------------- #

def _envelope(x, t, extrema_idx):
    from scipy.interpolate import CubicSpline
    if len(extrema_idx) < 2:
        return np.full_like(x, np.nan)
    cs = CubicSpline(t[extrema_idx], x[extrema_idx], bc_type="natural")
    return cs(t)


def empirical_mode_decomposition(series: np.ndarray, max_imfs: int = 8, sd_thresh: float = 0.2,
                                  max_sift: int = 100):
    x = np.asarray(series, dtype=float).copy()
    t = np.arange(len(x))
    imfs = []
    residual = x.copy()

    for _ in range(max_imfs):
        if np.all(np.abs(residual) < 1e-10):
            break
        h = residual.copy()
        for _sift in range(max_sift):
            maxima = (np.diff(np.sign(np.diff(h))) < 0).nonzero()[0] + 1
            minima = (np.diff(np.sign(np.diff(h))) > 0).nonzero()[0] + 1
            if len(maxima) < 2 or len(minima) < 2:
                break
            upper = _envelope(h, t, maxima)
            lower = _envelope(h, t, minima)
            if np.isnan(upper).any() or np.isnan(lower).any():
                break
            mean_env = (upper + lower) / 2.0
            h_new = h - mean_env
            sd = np.sum((h - h_new) ** 2) / max(1e-12, np.sum(h ** 2))
            h = h_new
            if sd < sd_thresh:
                break
        n_extrema = len(maxima) + len(minima) if 'maxima' in dir() else 0
        imfs.append(h)
        residual = residual - h
        # stop when residual is monotonic (no more extrema) or near-constant
        maxima_r = (np.diff(np.sign(np.diff(residual))) < 0).nonzero()[0]
        minima_r = (np.diff(np.sign(np.diff(residual))) > 0).nonzero()[0]
        if len(maxima_r) + len(minima_r) < 3:
            break

    return dict(imfs=np.array(imfs), residual=residual)


def hilbert_spectrum(imfs: np.ndarray, dt: float = 1.0):
    from scipy.signal import hilbert
    inst_amp, inst_freq = [], []
    for imf in imfs:
        analytic = hilbert(imf)
        amp = np.abs(analytic)
        phase = np.unwrap(np.angle(analytic))
        freq = np.diff(phase) / (2 * np.pi * dt)
        freq = np.concatenate([[freq[0] if len(freq) else 0.0], freq])
        inst_amp.append(amp)
        inst_freq.append(freq)
    return dict(inst_amplitude=np.array(inst_amp), inst_frequency=np.array(inst_freq))


# --------------------------------------------------------------------------- #
# 8. Recurrence Quantification Analysis (Marwan et al., 2007)
# --------------------------------------------------------------------------- #

def recurrence_analysis(series: np.ndarray, dim: int, tau: int, epsilon: Optional[float] = None,
                         min_diag: int = 2):
    emb = time_delay_embed(series, dim, tau)
    from scipy.spatial.distance import pdist, squareform
    dm = squareform(pdist(emb))
    if epsilon is None:
        epsilon = 0.1 * dm.max()
    RP = (dm < epsilon).astype(int)
    n = RP.shape[0]
    rec_rate = float(RP.sum() - n) / (n * n - n) if n > 1 else float("nan")  # exclude LOI

    # diagonal line length distribution (excludes the main diagonal itself)
    diag_lengths = []
    for offset in range(1, n):
        diag = np.diagonal(RP, offset=offset)
        run = 0
        for v in diag:
            if v == 1:
                run += 1
            else:
                if run >= min_diag:
                    diag_lengths.append(run)
                run = 0
        if run >= min_diag:
            diag_lengths.append(run)

    diag_lengths = np.array(diag_lengths)
    total_ones = RP.sum() - n
    det = float(diag_lengths.sum() / total_ones) if total_ones > 0 and len(diag_lengths) else 0.0
    l_mean = float(diag_lengths.mean()) if len(diag_lengths) else 0.0
    if len(diag_lengths):
        probs = np.bincount(diag_lengths)[min_diag:]
        probs = probs[probs > 0] / probs.sum()
        entr = float(-np.sum(probs * np.log(probs)))
    else:
        entr = 0.0

    return dict(RP=RP, recurrence_rate=rec_rate, determinism=det, avg_diag_length=l_mean,
                diag_entropy=entr, epsilon_used=float(epsilon))


# --------------------------------------------------------------------------- #
# Orchestrator — runs the full battery and produces an evidence-based,
# multi-method verdict rather than a single fabricated confidence score.
# --------------------------------------------------------------------------- #

@dataclass
class ChaosReport:
    n: int
    tau: int
    embedding_dim: int
    lyapunov: dict
    zero_one: dict
    correlation_dim: dict
    sample_entropy: dict
    warnings: list = field(default_factory=list)
    verdict: str = ""


def analyze_time_series(series, dt: float = 1.0) -> ChaosReport:
    x = np.asarray(series, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    warnings = []

    tau, _ami = average_mutual_information(x)
    dim, _fnn = false_nearest_neighbors(x, tau)
    dim = max(dim, 2)

    for name in ("lyapunov_rosenstein", "zero_one_test", "correlation_dimension", "sample_entropy"):
        msg = _adequacy(name, n)
        if msg:
            warnings.append(f"[{name}] {msg}")

    lle_res = rosenstein_lyapunov(x, dim, tau, dt=dt)
    zot_res = zero_one_test(x)
    cd_res = correlation_dimension(x, tau)
    se_res = sample_entropy(x)

    signals = []
    if np.isfinite(lle_res.get("lle", np.nan)):
        signals.append(("Rosenstein LLE", lle_res["lle"] > 0.01, lle_res["lle"]))
    if np.isfinite(zot_res.get("K", np.nan)):
        signals.append(("0-1 Test K", zot_res["K"] > 0.6, zot_res["K"]))
    if cd_res.get("saturates") is not None:
        # Saturation alone isn't a chaos signature — a periodic limit cycle
        # also saturates (e.g. D2 -> 1.0 for a simple oscillator). The
        # hallmark of chaos specifically is saturation to a FRACTAL
        # (non-integer) dimension, so require both.
        d2_vals = list(cd_res["d2_by_dim"].values())
        tail_d2 = float(np.mean(d2_vals[-2:])) if len(d2_vals) >= 2 else (d2_vals[-1] if d2_vals else np.nan)
        is_fractal = np.isfinite(tail_d2) and abs(tail_d2 - round(tail_d2)) > 0.15
        cd_is_chaos = bool(cd_res["saturates"] and is_fractal)
        signals.append(("Correlation-dim saturation (fractal)", cd_is_chaos, tail_d2))

    if not signals:
        verdict = "Insufficient valid results to classify this series. Provide more data points."
    else:
        chaos_votes = sum(1 for _, is_chaos, _ in signals if is_chaos)
        total = len(signals)
        if chaos_votes == total:
            verdict = (f"All {total} independent test(s) agree: consistent with low-dimensional "
                       f"chaotic dynamics.")
        elif chaos_votes == 0:
            verdict = (f"All {total} independent test(s) agree: no evidence of chaos — dynamics look "
                       f"regular (periodic/quasi-periodic) or the series is dominated by noise "
                       f"without a low-dimensional deterministic structure.")
        else:
            verdict = (f"Tests disagree ({chaos_votes}/{total} indicate chaos) — do not report a single "
                       f"confident label. This commonly happens with short, noisy, or non-stationary "
                       f"real-world data; consider it 'inconclusive' and look at the individual metrics.")

    return ChaosReport(
        n=n, tau=tau, embedding_dim=dim,
        lyapunov=lle_res, zero_one=zot_res, correlation_dim=cd_res, sample_entropy=se_res,
        warnings=warnings, verdict=verdict,
    )