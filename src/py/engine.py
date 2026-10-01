"""Imputation Lab engine.

Pure pandas / scikit-learn logic. The same file runs in the browser (Pyodide)
and under CPython for the tests. The only entry point used by the UI is
``run(request_json) -> response_json``.
"""

from __future__ import annotations

import io
import json
import math
import time

import numpy as np
import pandas as pd
from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import IterativeImputer, KNNImputer, SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

MAX_ROWS = 10_000
MAX_COLS = 50
DISPLAY_ROWS = 200
NA_TOKENS = ["", "NA", "N/A", "NaN", "nan", "null", "NULL", "?"]

MECHANISMS = ("MCAR", "MAR", "MNAR")


class EngineError(Exception):
    """An error the user can act on. ``code`` is stable, ``message`` is shown in the UI."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


# --------------------------------------------------------------------------- datasets


def _notebook_survey(n: int = 100) -> pd.DataFrame:
    """Complete survey data following the notebook's sample dataset (seed 0)."""
    rng = np.random.RandomState(0)
    return pd.DataFrame(
        {
            "Age": rng.randint(18, 60, n).astype(float),
            "Income": rng.randint(20000, 100000, n).astype(float),
            "Satisfaction": rng.choice([1, 2, 3, 4, 5], n).astype(float),
        }
    )


def _notebook_mar(m: int = 23) -> pd.DataFrame:
    """Notebook MAR example: Job_Satisfaction is missing where Stress_Level == 'Low'."""
    rng = np.random.RandomState(0)
    df = pd.DataFrame(
        {
            "Age": rng.randint(20, 60, m).astype(float),
            "Stress_Level": rng.choice(["Low", "Medium", "High"], m),
            "Job_Satisfaction": rng.choice([1, 2, 3, 4, 5], m).astype(float),
        }
    )
    df.loc[df["Stress_Level"] == "Low", "Job_Satisfaction"] = np.nan
    return df


def _notebook_debt(m: int = 23) -> pd.DataFrame:
    """Notebook 'MNAR' example: Savings is missing where Debt > 30000."""
    rng = np.random.RandomState(0)
    df = pd.DataFrame(
        {
            "Debt": rng.randint(0, 50000, m).astype(float),
            "Savings": rng.randint(0, 50000, m).astype(float),
        }
    )
    df.loc[df["Debt"] > 30000, "Savings"] = np.nan
    return df


GENERATED = {
    "notebook_survey": _notebook_survey,
    "notebook_mar": _notebook_mar,
    "notebook_debt": _notebook_debt,
}


def parse_csv(text: str) -> pd.DataFrame:
    """Parse and validate an uploaded or bundled CSV/TSV file."""
    if not isinstance(text, str) or not text.strip():
        raise EngineError("empty_file", "Die Datei ist leer.")
    try:
        header = pd.read_csv(
            io.StringIO(text), sep=None, engine="python", header=None, nrows=1, dtype=str, keep_default_na=False
        ).iloc[0]
        names = [str(h).strip() for h in header]
        if len(set(names)) != len(names):  # pandas would silently rename duplicates to "a.1"
            raise EngineError("duplicate_columns", "Spaltennamen müssen eindeutig sein.")
        df = pd.read_csv(
            io.StringIO(text),
            sep=None,
            engine="python",
            na_values=NA_TOKENS,
            keep_default_na=True,
            skipinitialspace=True,
        )
    except EngineError:
        raise
    except Exception as exc:  # pandas raises several unrelated error types here
        raise EngineError("parse_error", f"Die Datei konnte nicht als CSV gelesen werden: {exc}") from exc
    return validate_frame(df)


def validate_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.shape[1] == 0 or df.shape[0] == 0:
        raise EngineError("empty_table", "Die Tabelle enthält keine Datenzeilen.")
    if df.shape[1] > MAX_COLS:
        raise EngineError("too_many_columns", f"Zu viele Spalten: {df.shape[1]} (erlaubt sind {MAX_COLS}).")
    if df.shape[0] > MAX_ROWS:
        raise EngineError("too_many_rows", f"Zu viele Zeilen: {df.shape[0]} (erlaubt sind {MAX_ROWS}).")
    names = [str(c) for c in df.columns]
    if len(set(names)) != len(names):
        raise EngineError("duplicate_columns", "Spaltennamen müssen eindeutig sein.")
    if any(n.startswith("Unnamed:") for n in names):
        raise EngineError("missing_header", "Die Datei braucht eine Kopfzeile mit Spaltennamen.")
    df = df.copy()
    df.columns = names
    for col in df.columns:
        if df[col].dtype == bool:
            df[col] = df[col].astype(object)
    if not numeric_columns(df):
        raise EngineError("no_numeric_column", "Es wird mindestens eine numerische Spalte benötigt.")
    return df.reset_index(drop=True)


def numeric_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]


def load_dataset(spec: dict) -> pd.DataFrame:
    kind = spec.get("kind")
    if kind == "generated":
        name = spec.get("name")
        if name not in GENERATED:
            raise EngineError("unknown_dataset", f"Unbekannter Datensatz: {name}")
        return validate_frame(GENERATED[name]())
    if kind == "csv":
        return parse_csv(spec.get("csv", ""))
    raise EngineError("unknown_dataset", f"Unbekannte Datensatz-Art: {kind}")


# --------------------------------------------------------------------------- missingness


def _zscore(values: np.ndarray) -> np.ndarray:
    std = values.std()
    if not np.isfinite(std) or std == 0:
        return np.zeros_like(values, dtype=float)
    return (values - values.mean()) / std


def _calibrated_probabilities(z: np.ndarray, rate: float, strength: float = 2.5) -> np.ndarray:
    """Logistic missingness probabilities whose mean equals ``rate`` (bisection on the intercept)."""
    lo, hi = -30.0, 30.0
    for _ in range(60):
        mid = (lo + hi) / 2
        mean = float((1 / (1 + np.exp(-(mid + strength * z)))).mean())
        if mean < rate:
            lo = mid
        else:
            hi = mid
    return 1 / (1 + np.exp(-((lo + hi) / 2 + strength * z)))


def inject_missing(df: pd.DataFrame, mechanism: str, rate: float, target: str, driver: str | None, seed: int):
    """Return (df_with_missing, mask). Only allowed on complete data so that a ground truth exists."""
    if mechanism not in MECHANISMS:
        raise EngineError("bad_mechanism", f"Unbekannter Mechanismus: {mechanism}")
    if not 0 < rate < 1:
        raise EngineError("bad_rate", "Die Missing-Rate muss zwischen 0 und 1 liegen.")
    if df.isna().any().any():
        raise EngineError("not_complete", "Fehlende Werte lassen sich nur in vollständige Daten einstreuen.")
    if target not in numeric_columns(df):
        raise EngineError("bad_target", f"Zielspalte '{target}' ist nicht numerisch oder existiert nicht.")

    rng = np.random.RandomState(seed)
    n = len(df)
    if mechanism == "MCAR":
        prob = np.full(n, rate)
    elif mechanism == "MAR":
        if driver is None or driver == target or driver not in numeric_columns(df):
            raise EngineError("bad_driver", "MAR braucht eine zweite numerische Spalte als Auslöser.")
        prob = _calibrated_probabilities(_zscore(df[driver].to_numpy(dtype=float)), rate)
    else:  # MNAR: depends on the value that goes missing
        prob = _calibrated_probabilities(_zscore(df[target].to_numpy(dtype=float)), rate)

    mask = rng.uniform(size=n) < prob
    if mask.all():  # keep at least one observed value so that every method has something to learn from
        mask[int(np.argmin(prob))] = False
    out = df.copy()
    out.loc[mask, target] = np.nan
    return out, mask


# --------------------------------------------------------------------------- imputation


def _usable_numeric(df: pd.DataFrame, notes: list[str]) -> list[str]:
    """Numeric columns that have at least one observed value."""
    cols = []
    for c in numeric_columns(df):
        if df[c].notna().any():
            cols.append(c)
        else:
            notes.append(f"Spalte '{c}' ist komplett leer und wird nicht imputiert.")
    return cols


def _note_categoricals(df: pd.DataFrame, notes: list[str]) -> None:
    cats = [c for c in df.columns if c not in numeric_columns(df) and df[c].isna().any()]
    if cats:
        notes.append(
            "Dieses Verfahren arbeitet nur auf numerischen Spalten; fehlende Werte in "
            + ", ".join(f"'{c}'" for c in cats)
            + " bleiben bestehen."
        )


def em_impute(X: np.ndarray, max_iter: int = 100, tol: float = 1e-6):
    """EM for a multivariate normal model; missing cells get their conditional mean.

    Returns (imputed array, mean vector, covariance matrix, iterations used);
    iterations is ``max_iter + 1`` if the algorithm did not converge.
    """
    X = np.asarray(X, dtype=float)
    n, p = X.shape
    miss = np.isnan(X)
    mu = np.nanmean(X, axis=0)
    filled = np.where(miss, mu, X)
    sigma = np.cov(filled, rowvar=False, bias=True).reshape(p, p) + 1e-8 * np.eye(p)
    patterns = {}
    for i in range(n):
        patterns.setdefault(miss[i].tobytes(), []).append(i)

    iterations = 0
    converged = False
    for iterations in range(1, max_iter + 1):
        filled = X.copy()
        c_sum = np.zeros((p, p))
        for key, rows in patterns.items():
            m = np.frombuffer(key, dtype=bool)
            if not m.any():
                continue
            o = ~m
            rows = np.asarray(rows)
            if not o.any():
                filled[np.ix_(rows, m)] = mu[m]
                c_sum[np.ix_(m, m)] += len(rows) * sigma[np.ix_(m, m)]
                continue
            beta = sigma[np.ix_(m, o)] @ np.linalg.pinv(sigma[np.ix_(o, o)])
            filled[np.ix_(rows, m)] = mu[m] + (X[np.ix_(rows, o)] - mu[o]) @ beta.T
            c_sum[np.ix_(m, m)] += len(rows) * (sigma[np.ix_(m, m)] - beta @ sigma[np.ix_(o, m)])
        mu_new = filled.mean(axis=0)
        centered = filled - mu_new
        sigma_new = (centered.T @ centered + c_sum) / n
        change = max(float(np.abs(mu_new - mu).max()), float(np.abs(sigma_new - sigma).max()))
        scale = max(1.0, float(np.abs(sigma).max()))
        mu, sigma = mu_new, sigma_new
        if change / scale < tol:
            converged = True
            break
    return filled, mu, sigma, iterations if converged else max_iter + 1


def _regression_impute(df: pd.DataFrame, cols: list[str], stochastic: bool, seed: int) -> pd.DataFrame:
    """Regression imputation as in the notebook: predictors are mean-imputed, one model per column."""
    out = df.copy()
    rng = np.random.RandomState(seed)
    helper = pd.DataFrame(SimpleImputer(strategy="mean").fit_transform(df[cols]), columns=cols, index=df.index)
    for col in cols:
        missing = df[col].isna()
        predictors = [c for c in cols if c != col]
        if not missing.any():
            continue
        if not predictors or (~missing).sum() < 2:
            out.loc[missing, col] = df[col].mean()
            continue
        model = LinearRegression().fit(helper.loc[~missing, predictors], df.loc[~missing, col])
        pred = model.predict(helper.loc[missing, predictors])
        if stochastic:
            resid = df.loc[~missing, col] - model.predict(helper.loc[~missing, predictors])
            pred = pred + rng.normal(0, float(resid.std(ddof=0)), size=len(pred))
        out.loc[missing, col] = pred
    return out


def _iterative(df, cols, estimator, max_iter, seed, sample_posterior=False):
    imputer = IterativeImputer(
        estimator=estimator,
        max_iter=max_iter,
        random_state=seed,
        sample_posterior=sample_posterior,
    )
    out = df.copy()
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # ConvergenceWarning is reported through max_iter in the UI
        out[cols] = imputer.fit_transform(df[cols])
    return out


def _int(params: dict, key: str, default: int, lo: int, hi: int) -> int:
    try:
        value = int(params.get(key, default))
    except (TypeError, ValueError):
        raise EngineError("bad_param", f"Parameter '{key}' muss eine ganze Zahl sein.") from None
    return max(lo, min(hi, value))


def impute(df: pd.DataFrame, method: str, params: dict, seed: int = 0):
    """Apply one method. Returns a dict with ``frame``, ``code``, ``notes`` and method-specific extras."""
    notes: list[str] = []
    extras: dict = {}
    params = params or {}

    if method == "none":
        return {"frame": df.copy(), "code": "df", "notes": notes, "extras": extras}

    if method == "listwise":
        out = df.dropna()
        if out.empty:
            notes.append("Nach Listwise Deletion bleibt keine Zeile übrig.")
        return {"frame": out, "code": "df_out = df.dropna()", "notes": notes, "extras": extras}

    if method == "drop_columns":
        threshold = _int(params, "max_missing_pct", 30, 0, 100)
        share = df.isna().mean() * 100
        keep = [c for c in df.columns if share[c] <= threshold]
        if not keep:
            raise EngineError("no_columns_left", "Bei diesem Schwellwert bleibt keine Spalte übrig.")
        code = f"share = df.isna().mean() * 100\ndf_out = df.loc[:, share <= {threshold}]"
        return {"frame": df[keep].copy(), "code": code, "notes": notes, "extras": extras}

    if method == "pairwise":
        num = numeric_columns(df)
        extras["corr_pairwise"] = _matrix(df[num].corr(method="pearson", min_periods=1))
        extras["corr_listwise"] = _matrix(df[num].dropna().corr(method="pearson"))
        extras["n_pairwise"] = _matrix(df[num].notna().astype(int).T.dot(df[num].notna().astype(int)))
        notes.append("Pairwise Deletion verändert die Daten nicht – jede Korrelation nutzt alle verfügbaren Paare.")
        code = "corr = df.corr(method='pearson', min_periods=1, numeric_only=True)"
        return {"frame": df.copy(), "code": code, "notes": notes, "extras": extras}

    cols = _usable_numeric(df, notes)

    if method in ("mean", "median", "most_frequent", "constant"):
        out = df.copy()
        indicator = bool(params.get("add_indicator", False))
        if method in ("mean", "median"):
            target_cols = [c for c in cols if df[c].isna().any()]
            kwargs = ""
            _note_categoricals(df, notes)
        elif method == "most_frequent":
            target_cols = [c for c in df.columns if df[c].isna().any() and df[c].notna().any()]
            kwargs = ""
        else:
            target_cols = [c for c in cols if df[c].isna().any()]
            try:
                fill = float(params.get("fill_value", 0))
            except (TypeError, ValueError):
                raise EngineError("bad_param", "Der Füllwert muss eine Zahl sein.") from None
            kwargs = f", fill_value={fill:g}"
            _note_categoricals(df, notes)
        for c in target_cols:
            options = {"strategy": method}
            if method == "constant":
                options["fill_value"] = fill
            column = df[[c]]
            if not pd.api.types.is_numeric_dtype(df[c]):  # None -> np.nan so that SimpleImputer sees the gaps
                column = column.astype(object).where(column.notna(), np.nan)
            out[c] = SimpleImputer(**options).fit_transform(column).ravel()
            if indicator:
                out[f"{c}_missing"] = df[c].isna().astype(int)
        code = (
            "from sklearn.impute import SimpleImputer\n\n"
            f"imputer = SimpleImputer(strategy='{method}'{kwargs}"
            + (", add_indicator=True" if indicator else "")
            + ")\n"
            f"df[cols] = imputer.fit_transform(df[cols])"
        )
        if indicator:
            code = code.replace("df[cols] = imputer", "values = imputer") + "  # Werte + Indikator-Spalten"
        return {"frame": out, "code": code, "notes": notes, "extras": extras}

    if not cols:
        raise EngineError("no_numeric_column", "Keine numerische Spalte mit beobachteten Werten vorhanden.")
    _note_categoricals(df, notes)

    if method == "knn":
        k = _int(params, "n_neighbors", 5, 1, 50)
        weights = params.get("weights", "uniform")
        if weights not in ("uniform", "distance"):
            raise EngineError("bad_param", "weights muss 'uniform' oder 'distance' sein.")
        scale = bool(params.get("scale", True))
        out = df.copy()
        imputer = KNNImputer(n_neighbors=k, weights=weights)
        if scale:
            scaler = StandardScaler()
            out[cols] = scaler.inverse_transform(imputer.fit_transform(scaler.fit_transform(df[cols])))
            code = (
                "from sklearn.impute import KNNImputer\nfrom sklearn.preprocessing import StandardScaler\n\n"
                "scaler = StandardScaler()\n"
                f"imputer = KNNImputer(n_neighbors={k}, weights='{weights}')\n"
                "X = imputer.fit_transform(scaler.fit_transform(df[cols]))\n"
                "df[cols] = scaler.inverse_transform(X)"
            )
        else:
            out[cols] = imputer.fit_transform(df[cols])
            code = (
                "from sklearn.impute import KNNImputer\n\n"
                f"imputer = KNNImputer(n_neighbors={k}, weights='{weights}')\n"
                "df[cols] = imputer.fit_transform(df[cols])"
            )
        return {"frame": out, "code": code, "notes": notes, "extras": extras}

    if method == "regression":
        stochastic = bool(params.get("stochastic", False))
        out = _regression_impute(df, cols, stochastic, seed)
        if len(cols) < 2:
            notes.append("Nur eine numerische Spalte: Regression fällt auf den Mittelwert zurück.")
        code = (
            "from sklearn.impute import SimpleImputer\nfrom sklearn.linear_model import LinearRegression\n\n"
            "X = SimpleImputer(strategy='mean').fit_transform(df[predictors])\n"
            "known = df[target].notna()\n"
            "model = LinearRegression().fit(X[known], df.loc[known, target])\n"
            "df.loc[~known, target] = model.predict(X[~known])"
            + ("  # + Zufallsrauschen aus den Residuen" if stochastic else "")
        )
        return {"frame": out, "code": code, "notes": notes, "extras": extras}

    if method == "iterative":
        max_iter = _int(params, "max_iter", 10, 1, 50)
        out = _iterative(df, cols, None, max_iter, seed)
        code = (
            "from sklearn.experimental import enable_iterative_imputer\nfrom sklearn.impute import IterativeImputer\n\n"
            f"imputer = IterativeImputer(max_iter={max_iter}, random_state={seed})\n"
            "df[cols] = imputer.fit_transform(df[cols])"
        )
        return {"frame": out, "code": code, "notes": notes, "extras": extras}

    if method == "random_forest":
        trees = _int(params, "n_estimators", 30, 5, 100)
        max_iter = _int(params, "max_iter", 5, 1, 10)
        estimator = RandomForestRegressor(n_estimators=trees, random_state=seed, n_jobs=1)
        out = _iterative(df, cols, estimator, max_iter, seed)
        code = (
            "from sklearn.experimental import enable_iterative_imputer\n"
            "from sklearn.impute import IterativeImputer\nfrom sklearn.ensemble import RandomForestRegressor\n\n"
            f"forest = RandomForestRegressor(n_estimators={trees}, random_state={seed})\n"
            f"imputer = IterativeImputer(estimator=forest, max_iter={max_iter}, random_state={seed})\n"
            "df[cols] = imputer.fit_transform(df[cols])"
        )
        return {"frame": out, "code": code, "notes": notes, "extras": extras}

    if method == "gradient_boosting":
        max_iter = _int(params, "max_iter", 5, 1, 10)
        estimator = HistGradientBoostingRegressor(max_iter=50, random_state=seed)
        out = _iterative(df, cols, estimator, max_iter, seed)
        code = (
            "from sklearn.experimental import enable_iterative_imputer\n"
            "from sklearn.impute import IterativeImputer\nfrom sklearn.ensemble import HistGradientBoostingRegressor\n\n"
            f"boosting = HistGradientBoostingRegressor(max_iter=50, random_state={seed})\n"
            f"imputer = IterativeImputer(estimator=boosting, max_iter={max_iter}, random_state={seed})\n"
            "df[cols] = imputer.fit_transform(df[cols])"
        )
        return {"frame": out, "code": code, "notes": notes, "extras": extras}

    if method == "em":
        max_iter = _int(params, "max_iter", 100, 1, 500)
        out = df.copy()
        filled, _mu, _sigma, used = em_impute(df[cols].to_numpy(dtype=float), max_iter=max_iter)
        out[cols] = filled
        extras["em_iterations"] = used
        if used > max_iter:
            notes.append(f"EM hat nach {max_iter} Iterationen noch nicht konvergiert.")
        code = (
            "# EM für ein multivariat normalverteiltes Modell (eigene numpy-Implementierung,\n"
            "# siehe src/py/engine.py: em_impute)\n"
            f"X_filled, mu, sigma, n_iter = em_impute(df[cols].to_numpy(), max_iter={max_iter})\n"
            "df[cols] = X_filled"
        )
        return {"frame": out, "code": code, "notes": notes, "extras": extras}

    if method == "multiple":
        m = _int(params, "m", 5, 2, 20)
        max_iter = _int(params, "max_iter", 10, 1, 30)
        runs = [
            _iterative(df, cols, None, max_iter, seed + i, sample_posterior=True)[cols].to_numpy(dtype=float)
            for i in range(m)
        ]
        stack = np.stack(runs)
        out = df.copy()
        out[cols] = runs[0]
        extras["m"] = m
        extras["spread_cols"] = cols
        extras["spread"] = stack.std(axis=0)
        extras["pooled_mean"] = {c: float(stack[:, :, j].mean()) for j, c in enumerate(cols)}
        extras["between_sd"] = {c: float(stack[:, :, j].mean(axis=1).std(ddof=1)) for j, c in enumerate(cols)}
        notes.append(f"Angezeigt wird der erste von {m} imputierten Datensätzen; die Streuung je Zelle steht im Tooltip.")
        code = (
            "from sklearn.experimental import enable_iterative_imputer\nfrom sklearn.impute import IterativeImputer\n\n"
            "imputed = [\n"
            f"    IterativeImputer(max_iter={max_iter}, sample_posterior=True, random_state={seed} + i)\n"
            "    .fit_transform(df[cols])\n"
            f"    for i in range({m})\n"
            "]  # m Datensätze: getrennt auswerten, Ergebnisse zusammenführen"
        )
        return {"frame": out, "code": code, "notes": notes, "extras": extras}

    raise EngineError("unknown_method", f"Unbekanntes Verfahren: {method}")


# --------------------------------------------------------------------------- reporting


def _num(value):
    """JSON-safe scalar: NaN/inf become None, numpy types become Python types."""
    if value is None:
        return None
    if isinstance(value, (np.floating, float)):
        value = float(value)
        return value if math.isfinite(value) else None
    if isinstance(value, (np.integer, int)) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if pd.isna(value):
        return None
    return str(value)


def _matrix(frame: pd.DataFrame) -> dict:
    return {
        "labels": [str(c) for c in frame.columns],
        "values": [[_num(v) for v in row] for row in frame.to_numpy()],
    }


def _table(frame: pd.DataFrame, limit: int = DISPLAY_ROWS) -> dict:
    head = frame.head(limit)
    return {
        "columns": [str(c) for c in head.columns],
        "dtypes": [str(t) for t in head.dtypes],
        "index": [_num(i) for i in head.index],
        "rows": [[_num(v) for v in row] for row in head.to_numpy(dtype=object)],
        "total_rows": int(len(frame)),
    }


def _describe(series: pd.Series) -> dict:
    s = pd.to_numeric(series, errors="coerce").dropna()
    return {
        "n": int(len(s)),
        "mean": _num(s.mean()) if len(s) else None,
        "std": _num(s.std(ddof=1)) if len(s) > 1 else None,
        "min": _num(s.min()) if len(s) else None,
        "max": _num(s.max()) if len(s) else None,
    }


def _histogram(series_by_name: dict, bins: int = 20) -> dict | None:
    arrays = {k: pd.to_numeric(v, errors="coerce").dropna().to_numpy(dtype=float) for k, v in series_by_name.items()}
    arrays = {k: v for k, v in arrays.items() if len(v)}
    if not arrays:
        return None
    lo = min(float(a.min()) for a in arrays.values())
    hi = max(float(a.max()) for a in arrays.values())
    if lo == hi:
        lo, hi = lo - 0.5, hi + 0.5
    edges = np.linspace(lo, hi, bins + 1)
    return {
        "edges": [float(e) for e in edges],
        "counts": {k: [int(c) for c in np.histogram(v, bins=edges)[0]] for k, v in arrays.items()},
    }


def _resolve_missing(df: pd.DataFrame, missing: dict) -> dict:
    """Fill in sensible defaults: last numeric column as target, its strongest correlate as driver."""
    numeric = numeric_columns(df)
    target = missing.get("target")
    if target not in numeric:
        target = numeric[-1]
    driver = missing.get("driver")
    if driver not in numeric or driver == target:
        others = [c for c in numeric if c != target]
        driver = None
        if others:
            corr = df[others].corrwith(df[target]).abs().fillna(0)
            driver = str(corr.idxmax())
    try:
        rate = float(missing.get("rate", 0.3))
    except (TypeError, ValueError):
        raise EngineError("bad_rate", "Die Missing-Rate muss eine Zahl sein.") from None
    return {"mechanism": missing.get("mechanism", "MCAR"), "rate": rate, "target": target, "driver": driver}


def run(request_json: str) -> str:
    """Single entry point for the UI. Never raises: errors are returned as ``{"ok": false, ...}``."""
    started = time.perf_counter()
    try:
        request = json.loads(request_json)
        response = _run(request)
        response["ok"] = True
        response["elapsed_ms"] = round((time.perf_counter() - started) * 1000)
        return json.dumps(response, allow_nan=False)
    except EngineError as exc:
        return json.dumps({"ok": False, "code": exc.code, "message": exc.message})
    except Exception as exc:  # last line of defence: the UI must always get valid JSON
        return json.dumps({"ok": False, "code": "internal_error", "message": f"{type(exc).__name__}: {exc}"})


def _run(request: dict) -> dict:
    truth = load_dataset(request.get("dataset") or {})
    notes: list[str] = []
    try:
        seed = int(request.get("seed") or 0)
    except (TypeError, ValueError):
        raise EngineError("bad_param", "Der Seed muss eine ganze Zahl sein.") from None
    has_native_missing = bool(truth.isna().any().any())

    mask = None
    before = truth
    missing = request.get("missing")
    applied = None
    if missing and not has_native_missing:
        applied = _resolve_missing(truth, missing)
        before, mask = inject_missing(
            truth, applied["mechanism"], applied["rate"], applied["target"], applied["driver"], seed
        )
    elif missing and has_native_missing:
        notes.append("Der Datensatz hat bereits fehlende Werte – es werden keine weiteren eingestreut.")

    method = request.get("method") or {}
    result = impute(before, method.get("id", "none"), method.get("params") or {}, seed)
    after = result["frame"]
    notes += result["notes"]
    extras = result["extras"]

    numeric = numeric_columns(before)
    column = request.get("column")
    if column not in numeric:
        column = applied["target"] if applied else None
    if column is None:
        with_gaps = [c for c in numeric if before[c].isna().any()]
        column = (with_gaps or numeric)[0]

    kept = after.index
    kept_set = set(kept)
    imputed_cells = []
    display_index = list(after.index[:DISPLAY_ROWS])
    shared = [c for c in after.columns if c in before.columns]
    was_missing = before.loc[display_index, shared].isna().to_numpy()
    now_present = after.loc[display_index, shared].notna().to_numpy()
    col_pos = {c: j for j, c in enumerate(after.columns)}
    for r, c in zip(*np.nonzero(was_missing & now_present)):
        cell = {"row": int(r), "col": col_pos[shared[c]]}
        if mask is not None:
            cell["truth"] = _num(truth.loc[display_index[r], shared[c]])
        imputed_cells.append(cell)
    if "spread" in extras:
        spread, spread_cols = extras.pop("spread"), extras.pop("spread_cols")
        position = {c: j for j, c in enumerate(spread_cols)}
        for cell in imputed_cells:
            name = after.columns[cell["col"]]
            if name in position:
                cell["sd"] = _num(spread[after.index.get_loc(display_index[cell["row"]]), position[name]])

    stats = []
    for c in numeric:
        entry = {
            "column": c,
            "missing": int(before[c].isna().sum()),
            "before": _describe(before[c]),
            "after": _describe(after[c]) if c in after.columns else None,
            "truth": _describe(truth[c]) if mask is not None else None,
            "rmse": None,
        }
        if mask is not None and c in after.columns:
            gaps = before[c].isna() & before.index.isin(kept)
            filled = after.loc[gaps[gaps].index, c]
            if len(filled) and filled.notna().all():
                entry["rmse"] = _num(np.sqrt(((filled - truth.loc[filled.index, c]) ** 2).mean()))
        stats.append(entry)

    hist_input = {"before": before[column]}
    if column in after.columns:
        hist_input["after"] = after[column]
    if mask is not None:
        hist_input["truth"] = truth[column]

    num_after = [c for c in numeric if c in after.columns]
    return {
        "before": _table(before),
        "after": _table(after),
        "dropped_rows": [_num(i) for i in before.index[:DISPLAY_ROWS] if i not in kept_set],
        "imputed_cells": imputed_cells,
        "has_truth": mask is not None,
        "missing_applied": applied,
        "has_native_missing": has_native_missing,
        "numeric_columns": numeric,
        "column": column,
        "stats": stats,
        "histogram": _histogram(hist_input),
        "corr_before": _matrix(before[numeric].corr(min_periods=2)) if len(numeric) > 1 else None,
        "corr_after": _matrix(after[num_after].corr(min_periods=2)) if len(num_after) > 1 and len(after) > 1 else None,
        "corr_truth": _matrix(truth[numeric].corr()) if mask is not None and len(numeric) > 1 else None,
        "extras": extras,
        "code": result["code"],
        "notes": notes,
        "shape_before": [int(before.shape[0]), int(before.shape[1])],
        "shape_after": [int(after.shape[0]), int(after.shape[1])],
        "missing_cells_before": int(before.isna().sum().sum()),
        "missing_cells_after": int(after.isna().sum().sum()),
    }
