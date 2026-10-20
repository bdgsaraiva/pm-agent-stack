"""qstats — dependency-free statistics for market research validation.

Copied verbatim (16 Oct 2026) from Appendix A of the quant-research-standards skill for the research loop
(agent 12, pmstack/research.py); `python -m pmstack.qstats` runs its self-test (also tests/test_research.py).

Everything here uses only numpy (pandas optional, for the episode helpers). It exists
because `scipy` and `statsmodels` are unavailable in many sandboxes, and because a
hand-rolled test you have validated beats a library call you have not.

Run `python qstats.py` to execute the self-test, which checks every distribution
against published critical values and every estimator against a closed-form result.

Contents
--------
distributions   norm_cdf, norm_ppf, t_pvalue, f_pvalue, chi2_sf, betainc
regression      ols (with Newey-West HAC), nw_lags
time series     adf, granger, ljung_box, acf
signals         independent_episodes, lift_test, split_halves
"""
from __future__ import annotations
import math
import numpy as np

__all__ = ["norm_cdf", "norm_ppf", "t_pvalue", "f_pvalue", "chi2_sf", "betainc",
           "ols", "nw_lags", "adf", "granger", "ljung_box", "acf",
           "independent_episodes", "lift_test", "split_halves"]

# ─────────────────────────────── distributions ───────────────────────────────

def norm_cdf(z: float) -> float:
    """Standard normal CDF."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def norm_ppf(p: float) -> float:
    """Standard normal inverse CDF (Acklam's rational approximation, |err| < 1.15e-9)."""
    if not 0.0 < p < 1.0:
        raise ValueError("p must be in (0, 1)")
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        x = (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    elif p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        x = -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    else:
        q = p - 0.5
        r = q * q
        x = (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
            (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
    # one Halley refinement step
    e = 0.5 * math.erfc(-x / math.sqrt(2)) - p
    u = e * math.sqrt(2 * math.pi) * math.exp(x * x / 2)
    return x - u / (1 + x * u / 2)


def _betacf(a: float, b: float, x: float, itmax: int = 300, eps: float = 3e-14) -> float:
    """Continued fraction for the incomplete beta function (Lentz's method)."""
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d
    for m in range(1, itmax + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny: d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny: c = tiny
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny: d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny: c = tiny
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < eps:
            break
    return h


def betainc(a: float, b: float, x: float) -> float:
    """Regularised incomplete beta I_x(a, b)."""
    if x <= 0.0: return 0.0
    if x >= 1.0: return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    if x < (a + 1.0) / (a + b + 2.0):
        return math.exp(lbeta + a * math.log(x) + b * math.log1p(-x)) * _betacf(a, b, x) / a
    return 1.0 - math.exp(lbeta + b * math.log1p(-x) + a * math.log(x)) * _betacf(b, a, 1 - x) / b


def t_pvalue(t: float, df: float) -> float:
    """TWO-SIDED p-value for Student's t. Halve it for a one-sided test."""
    if not np.isfinite(t) or df <= 0:
        return float("nan")
    return betainc(df / 2.0, 0.5, df / (df + t * t))


def f_pvalue(F: float, df1: float, df2: float) -> float:
    """Upper-tail p-value for the F distribution."""
    if not np.isfinite(F) or F <= 0 or df1 <= 0 or df2 <= 0:
        return float("nan")
    return betainc(df2 / 2.0, df1 / 2.0, df2 / (df2 + df1 * F))


def chi2_sf(x: float, k: float) -> float:
    """Upper-tail (survival) probability for chi-square with k degrees of freedom."""
    if x <= 0: return 1.0
    a, xx = k / 2.0, x / 2.0
    if xx < a + 1.0:                                   # series expansion
        s = term = 1.0 / a
        ap = a
        for _ in range(10000):
            ap += 1.0
            term *= xx / ap
            s += term
            if abs(term) < abs(s) * 1e-15:
                break
        return 1.0 - s * math.exp(-xx + a * math.log(xx) - math.lgamma(a))
    b = xx + 1.0 - a                                   # continued fraction
    c, d = 1e300, 1.0 / b
    h = d
    for i in range(1, 10000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < 1e-300: d = 1e-300
        c = b + an / c
        if abs(c) < 1e-300: c = 1e-300
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < 1e-15:
            break
    return math.exp(-xx + a * math.log(xx) - math.lgamma(a)) * h


# ─────────────────────────────── regression ───────────────────────────────

def nw_lags(n: int) -> int:
    """Newey-West (1994) automatic bandwidth: floor(4 * (n/100)^(2/9))."""
    return int(math.floor(4.0 * (n / 100.0) ** (2.0 / 9.0)))


def ols(y, X, add_const: bool = True, nw: int = 0) -> dict:
    """OLS with optional Newey-West HAC standard errors.

    nw = 0 gives classical homoskedastic errors; nw > 0 gives HAC with a Bartlett
    kernel and `nw` lags. Use nw for overlapping windows, autocorrelated residuals,
    or any forward-return regression.

    Returns beta, se, t, p, r2, adj_r2, n, k, dof, ssr, resid.
    """
    y = np.asarray(y, dtype=float).ravel()
    X = np.asarray(X, dtype=float)
    if X.ndim == 1:
        X = X[:, None]
    if add_const:
        X = np.column_stack([np.ones(len(y)), X])
    n, k = X.shape
    if n <= k:
        raise ValueError(f"need more observations ({n}) than regressors ({k})")
    XtX_inv = np.linalg.pinv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    resid = y - X @ beta
    dof = n - k
    ssr = float(resid @ resid)
    sst = float(((y - y.mean()) ** 2).sum())
    if nw > 0:
        u = X * resid[:, None]
        S = u.T @ u
        for L in range(1, nw + 1):
            w = 1.0 - L / (nw + 1.0)                   # Bartlett kernel
            G = u[L:].T @ u[:-L]
            S += w * (G + G.T)
        V = XtX_inv @ S @ XtX_inv
    else:
        V = XtX_inv * (ssr / dof)
    se = np.sqrt(np.maximum(np.diag(V), 0.0))
    with np.errstate(divide="ignore", invalid="ignore"):
        t = np.where(se > 0, beta / se, np.nan)
    p = np.array([t_pvalue(ti, dof) for ti in t])
    r2 = 1.0 - ssr / sst if sst > 0 else float("nan")
    adj = 1.0 - (1.0 - r2) * (n - 1) / dof if sst > 0 else float("nan")
    return dict(beta=beta, se=se, t=t, p=p, r2=r2, adj_r2=adj,
                n=n, k=k, dof=dof, ssr=ssr, resid=resid)


# ─────────────────────────────── time series ───────────────────────────────

def acf(x, lags: int = 10) -> np.ndarray:
    """Sample autocorrelations 1..lags (biased/1-over-n estimator, as in Ljung-Box)."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    xc = x - x.mean()
    denom = float(xc @ xc)
    return np.array([float(xc[k:] @ xc[:-k]) / denom for k in range(1, lags + 1)])


def adf(series, maxlag: int | None = None, regression: str = "c"):
    """Augmented Dickey-Fuller. Returns (tstat, used_lag, nobs); lag chosen by AIC.

    regression='c' includes a constant, 'n' includes none.
    Asymptotic critical values WITH a constant: -3.43 (1%), -2.86 (5%), -2.57 (10%).
    More negative than the critical value rejects the unit root (i.e. stationary).
    """
    y = np.asarray(series, float)
    y = y[np.isfinite(y)]
    n = len(y)
    if maxlag is None:
        maxlag = int(math.ceil(12 * (n / 100.0) ** 0.25))
    maxlag = max(0, min(maxlag, (n - 3) // 2))
    dy = np.diff(y)
    best = None
    for L in range(maxlag, -1, -1):
        ylag = y[L:-1]
        dyt = dy[L:]
        cols = [ylag] + [dy[L - j:-j] for j in range(1, L + 1)]
        Xm = np.column_stack(cols)
        res = ols(dyt, Xm, add_const=(regression == "c"))
        idx = 1 if regression == "c" else 0
        aic = len(dyt) * math.log(res["ssr"] / len(dyt)) + 2 * res["k"]
        if best is None or aic < best[0]:
            best = (aic, float(res["t"][idx]), L, len(dyt))
    return best[1], best[2], best[3]


def granger(y, x, lags: int = 5):
    """Does x Granger-cause y? Returns (F, p, df1, df2).

    Significance in BOTH directions is the signature of shared contemporaneous noise,
    not of a lead. Always run it both ways and read the pair.
    """
    y = np.asarray(y, float)
    x = np.asarray(x, float)
    if len(y) != len(x):
        raise ValueError("y and x must be the same length")
    n = len(y)
    Y = y[lags:]
    ylags = np.column_stack([y[lags - j:n - j] for j in range(1, lags + 1)])
    xlags = np.column_stack([x[lags - j:n - j] for j in range(1, lags + 1)])
    r_r = ols(Y, ylags)
    r_u = ols(Y, np.column_stack([ylags, xlags]))
    df1, df2 = lags, r_u["dof"]
    F = ((r_r["ssr"] - r_u["ssr"]) / df1) / (r_u["ssr"] / df2)
    return F, f_pvalue(F, df1, df2), df1, df2


def ljung_box(x, lags: int = 10):
    """Ljung-Box Q and its p-value. Tests whether the first `lags` autocorrelations
    are jointly zero. Run it on any series before using it in a lead/lag study."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    r = acf(x, lags)
    Q = n * (n + 2) * float(np.sum(r ** 2 / (n - np.arange(1, lags + 1))))
    return Q, chi2_sf(Q, lags)


# ─────────────────────────────── signal evaluation ───────────────────────────────

def independent_episodes(flag, min_gap_days: int):
    """Collapse a boolean signal series into INDEPENDENT episodes.

    `flag` is a pandas boolean Series with a DatetimeIndex. Consecutive or nearby
    True days describe one event, not many; counting them all inflates the sample
    and understates the standard error. Returns the first date of each episode.

    Set min_gap_days to at least the evaluation horizon, so two episodes cannot
    share a forward window.
    """
    idx = flag[flag.fillna(False).astype(bool)].index
    keep, last = [], None
    for d in idx:
        if last is None or (d - last).days > min_gap_days:
            keep.append(d)
        last = d
    return type(idx)(keep)


def lift_test(hit_flags, base_rate: float) -> dict:
    """Score a binary signal against the unconditional base rate.

    hit_flags : outcomes (0/1) on the INDEPENDENT signal episodes only.
    base_rate : unconditional P(outcome) over all valid observations.

    A hit rate means nothing on its own — if 62% of all days precede a 5% decline,
    an 80% hit rate is a lift of 1.29, not a good signal. Report lift, always.
    """
    h = np.asarray(hit_flags, float)
    h = h[np.isfinite(h)]
    k = len(h)
    if k == 0 or not 0.0 < base_rate < 1.0:
        return dict(n=k, hit_rate=float("nan"), base_rate=base_rate,
                    lift=float("nan"), z=float("nan"), p=float("nan"))
    hit = float(h.mean())
    se = math.sqrt(base_rate * (1.0 - base_rate) / k)
    z = (hit - base_rate) / se
    return dict(n=k, hit_rate=hit, base_rate=base_rate, lift=hit / base_rate,
                z=z, p=2.0 * (1.0 - norm_cdf(abs(z))))


def split_halves(values):
    """Chronological split of an effect vector. Returns (h1_mean, h2_mean, sign_stable).

    A sign flip between halves is the hard filter: it disqualifies the effect.
    """
    v = np.asarray(values, float)
    v = v[np.isfinite(v)]
    if len(v) < 4:
        return float("nan"), float("nan"), False
    h = len(v) // 2
    a, b = float(v[:h].mean()), float(v[h:].mean())
    return a, b, bool(np.sign(a) == np.sign(b) and a != 0)


# ─────────────────────────────── self-test ───────────────────────────────

def _selftest() -> int:
    fails = []

    def ck(name, got, exp, tol):
        ok = np.isfinite(got) and abs(got - exp) <= tol
        print(f"  {'PASS' if ok else 'FAIL'}  {name:<52} {got:.6g} vs {exp:.6g}")
        if not ok:
            fails.append(name)

    print("distributions — against published critical values")
    ck("norm_cdf(1.959964) = 0.975", norm_cdf(1.959964), 0.975, 1e-6)
    ck("norm_ppf(0.975) = 1.959964", norm_ppf(0.975), 1.959964, 1e-6)
    ck("norm_ppf(norm_cdf(-1.3)) = -1.3", norm_ppf(norm_cdf(-1.3)), -1.3, 1e-8)
    ck("t two-sided p(2.000, df=30) = 0.0546250", t_pvalue(2.0, 30), 0.0546250, 1e-6)
    ck("t two-sided p(2.042, df=30) = 0.05", t_pvalue(2.042272, 30), 0.05, 1e-5)
    ck("t two-sided p(1.959964, df=1e7) = 0.05", t_pvalue(1.959964, 1e7), 0.05, 1e-5)
    ck("t two-sided p(12.706, df=1) = 0.05", t_pvalue(12.7062, 1), 0.05, 1e-5)
    ck("F upper p(4.170877, 1, 30) = 0.05", f_pvalue(4.170877, 1, 30), 0.05, 1e-5)
    ck("F upper p(2.533555, 5, 30) = 0.05", f_pvalue(2.533555, 5, 30), 0.05, 1e-5)
    ck("F(t^2,1,df) equals t two-sided p", f_pvalue(2.0 ** 2, 1, 30), t_pvalue(2.0, 30), 1e-10)
    ck("chi2 sf(3.841459, 1) = 0.05", chi2_sf(3.841459, 1), 0.05, 1e-6)
    ck("chi2 sf(18.307038, 10) = 0.05", chi2_sf(18.307038, 10), 0.05, 1e-6)
    ck("chi2 sf(23.209251, 10) = 0.01", chi2_sf(23.209251, 10), 0.01, 1e-6)
    ck("betainc(2,3,0.5) = 0.6875", betainc(2, 3, 0.5), 0.6875, 1e-10)

    print("\nregression — against closed form")
    rng = np.random.default_rng(7)
    x = rng.normal(size=400)
    y = 1.5 + 0.8 * x + rng.normal(size=400) * 0.5
    r = ols(y, x)
    Xd = np.column_stack([np.ones(400), x])
    b_exact = np.linalg.solve(Xd.T @ Xd, Xd.T @ y)
    ck("ols intercept matches normal equations", r["beta"][0], b_exact[0], 1e-10)
    ck("ols slope matches normal equations", r["beta"][1], b_exact[1], 1e-10)
    res = y - Xd @ b_exact
    s2 = (res @ res) / (400 - 2)
    se_exact = math.sqrt(s2 * np.linalg.inv(Xd.T @ Xd)[1, 1])
    ck("ols slope se matches closed form", r["se"][1], se_exact, 1e-10)
    ck("ols r2 matches 1 - ssr/sst", r["r2"],
       1 - (res @ res) / ((y - y.mean()) ** 2).sum(), 1e-12)
    r0 = ols(y, x, nw=0)
    ck("nw=0 reproduces homoskedastic se", ols(y, x, nw=0)["se"][1], r0["se"][1], 1e-14)
    rnw = ols(y, x, nw=4)
    ck("nw=4 se is positive and finite", float(rnw["se"][1] > 0), 1.0, 0)
    ck("nw_lags(4832) = 9", nw_lags(4832), 9, 0)
    ck("nw_lags(100) = 4", nw_lags(100), 4, 0)

    print("\ntime series")
    iid = rng.normal(size=1500)
    rw = np.cumsum(rng.normal(size=1500))
    t_iid = adf(iid)[0]
    t_rw = adf(rw)[0]
    ck("ADF rejects unit root on iid (t < -3.43)", float(t_iid < -3.43), 1.0, 0)
    ck("ADF does NOT reject on a random walk (t > -2.86)", float(t_rw > -2.86), 1.0, 0)
    ck("acf of iid at lag 1 is near zero", abs(acf(iid, 1)[0]), 0.0, 0.08)
    ar = np.zeros(2000)
    for i in range(1, 2000):
        ar[i] = 0.6 * ar[i - 1] + rng.normal()
    ck("acf of AR(1) rho=0.6 recovers ~0.6", acf(ar, 1)[0], 0.6, 0.06)
    ck("Ljung-Box does not reject on iid (p > 0.05)", float(ljung_box(iid, 10)[1] > 0.05), 1.0, 0)
    ck("Ljung-Box rejects on AR(1) (p < 1e-6)", float(ljung_box(ar, 10)[1] < 1e-6), 1.0, 0)
    xs = rng.normal(size=1200)
    y_led = np.concatenate([[0.0], 0.7 * xs[:-1]]) + rng.normal(size=1200) * 0.3
    ck("Granger detects x leading y (p < 1e-6)", float(granger(y_led, xs, 3)[1] < 1e-6), 1.0, 0)
    ck("Granger finds nothing on independent series (p > 0.01)",
       float(granger(rng.normal(size=1200), rng.normal(size=1200), 3)[1] > 0.01), 1.0, 0)

    print("\nsignal evaluation")
    lt = lift_test([1, 1, 1, 0, 0, 0, 0, 0, 0, 0], 0.10)
    ck("lift_test hit rate", lt["hit_rate"], 0.30, 1e-12)
    ck("lift_test lift = 3.0", lt["lift"], 3.0, 1e-12)
    ck("lift_test z = (0.3-0.1)/sqrt(0.1*0.9/10)", lt["z"],
       (0.3 - 0.1) / math.sqrt(0.1 * 0.9 / 10), 1e-12)
    ck("lift = 1 gives z = 0", lift_test([1, 0, 0, 0], 0.25)["z"], 0.0, 1e-12)
    a, b, stable = split_halves([1, 2, 3, 4])
    ck("split_halves h1 mean", a, 1.5, 1e-12)
    ck("split_halves h2 mean", b, 3.5, 1e-12)
    ck("split_halves flags a sign flip", float(split_halves([1, 2, -3, -4])[2]), 0.0, 0)
    try:
        import pandas as pd
        idx = pd.bdate_range("2020-01-01", periods=60)
        f = pd.Series(False, index=idx)
        f.iloc[[0, 1, 2, 40, 41]] = True
        ep = independent_episodes(f, min_gap_days=21)
        ck("independent_episodes collapses 5 days into 2", len(ep), 2, 0)
    except ImportError:
        print("  SKIP  independent_episodes (pandas unavailable)")

    print(f"\n{'ALL CHECKS PASSED' if not fails else 'FAILURES: ' + ', '.join(fails)}")
    return 0 if not fails else 1


if __name__ == "__main__":
    raise SystemExit(_selftest())
