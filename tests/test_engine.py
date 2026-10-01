import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "py"))
import engine  # noqa: E402

IMPUTING = ["mean", "median", "most_frequent", "constant", "knn", "regression", "iterative",
            "random_forest", "gradient_boosting", "em", "multiple"]


def correlated(n=300, seed=1):
    rng = np.random.RandomState(seed)
    x = rng.normal(50, 10, n)
    y = 2 * x + rng.normal(0, 5, n)
    z = rng.normal(0, 1, n)
    return pd.DataFrame({"x": x, "y": y, "z": z})


def call(**request):
    return json.loads(engine.run(json.dumps(request)))


def csv_request(df, **extra):
    return dict(dataset={"kind": "csv", "csv": df.to_csv(index=False)}, **extra)


# ---- missingness mechanisms

@pytest.mark.parametrize("mechanism", engine.MECHANISMS)
@pytest.mark.parametrize("rate", [0.1, 0.3, 0.6])
def test_inject_hits_rate(mechanism, rate):
    df = correlated(2000)
    out, mask = engine.inject_missing(df, mechanism, rate, "y", "x", seed=3)
    assert abs(mask.mean() - rate) < 0.04
    assert out["y"].isna().sum() == mask.sum()
    assert out[["x", "z"]].notna().all().all()


def test_mar_depends_on_driver_and_mnar_on_target():
    df = correlated(3000)
    df["x"] = np.random.RandomState(5).normal(size=len(df))  # driver independent of y
    _, mar = engine.inject_missing(df, "MAR", 0.3, "y", "x", seed=1)
    _, mnar = engine.inject_missing(df, "MNAR", 0.3, "y", "x", seed=1)
    _, mcar = engine.inject_missing(df, "MCAR", 0.3, "y", "x", seed=1)
    assert df.loc[mar, "x"].mean() - df.loc[~mar, "x"].mean() > 0.5
    assert abs(df.loc[mar, "y"].mean() - df.loc[~mar, "y"].mean()) < 2.5
    assert df.loc[mnar, "y"].mean() - df.loc[~mnar, "y"].mean() > 5
    assert abs(df.loc[mcar, "y"].mean() - df.loc[~mcar, "y"].mean()) < 2.5


def test_inject_is_deterministic_and_validates():
    df = correlated()
    a = engine.inject_missing(df, "MCAR", 0.3, "y", None, seed=7)[1]
    b = engine.inject_missing(df, "MCAR", 0.3, "y", None, seed=7)[1]
    assert (a == b).all()
    for kwargs, code in [
        (dict(mechanism="XXX", rate=0.3, target="y", driver="x"), "bad_mechanism"),
        (dict(mechanism="MCAR", rate=1.5, target="y", driver="x"), "bad_rate"),
        (dict(mechanism="MCAR", rate=0.3, target="nope", driver="x"), "bad_target"),
        (dict(mechanism="MAR", rate=0.3, target="y", driver="y"), "bad_driver"),
        (dict(mechanism="MAR", rate=0.3, target="y", driver=None), "bad_driver"),
    ]:
        with pytest.raises(engine.EngineError) as err:
            engine.inject_missing(df, seed=0, **kwargs)
        assert err.value.code == code
    holes = df.copy()
    holes.loc[0, "x"] = np.nan
    with pytest.raises(engine.EngineError) as err:
        engine.inject_missing(holes, "MCAR", 0.3, "y", None, 0)
    assert err.value.code == "not_complete"


# ---- imputation methods

@pytest.mark.parametrize("method", IMPUTING)
def test_methods_fill_numeric_and_keep_shape(method):
    df, _ = engine.inject_missing(correlated(150), "MCAR", 0.3, "y", None, seed=2)
    df.loc[[3, 4, 5], "z"] = np.nan
    out = engine.impute(df, method, {}, seed=0)["frame"]
    assert out.shape == df.shape
    assert out.notna().all().all()
    observed = df.notna()
    pd.testing.assert_frame_equal(out.where(observed), df.where(observed))


def test_mean_shrinks_std_and_model_methods_beat_mean():
    truth = correlated(400)
    df, mask = engine.inject_missing(truth, "MCAR", 0.4, "y", None, seed=4)
    rmse = {}
    for method in ["mean", "knn", "regression", "iterative", "random_forest", "gradient_boosting", "em"]:
        out = engine.impute(df, method, {}, seed=0)["frame"]
        rmse[method] = float(np.sqrt(((out.loc[mask, "y"] - truth.loc[mask, "y"]) ** 2).mean()))
        if method == "mean":
            assert out["y"].std() < 0.85 * truth["y"].std()
    for method in ["knn", "regression", "iterative", "random_forest", "gradient_boosting", "em"]:
        assert rmse[method] < 0.6 * rmse["mean"], rmse


def test_em_recovers_parameters():
    rng = np.random.RandomState(0)
    cov = np.array([[4.0, 3.0], [3.0, 9.0]])
    X = rng.multivariate_normal([10, -5], cov, size=4000)
    holes = X.copy()
    holes[rng.uniform(size=4000) < 0.3, 1] = np.nan
    filled, mu, sigma, iterations = engine.em_impute(holes)
    assert not np.isnan(filled).any()
    assert np.allclose(mu, [10, -5], atol=0.2)
    assert np.allclose(sigma, cov, atol=0.5)
    assert iterations < 100


def test_listwise_and_zero_rows():
    df = correlated(50)
    df.loc[:9, "y"] = np.nan
    assert len(engine.impute(df, "listwise", {})["frame"]) == 40
    df["z"] = np.nan
    result = engine.impute(df, "listwise", {})
    assert result["frame"].empty and result["notes"]


def test_all_nan_column_is_kept_and_reported():
    df = correlated(60)
    df.loc[:5, "y"] = np.nan
    df["empty"] = np.nan
    for method in ["knn", "iterative", "em", "mean"]:
        result = engine.impute(df, method, {})
        assert list(result["frame"].columns) == list(df.columns)
        assert result["frame"]["empty"].isna().all()
        assert result["frame"]["y"].notna().all()
        assert any("komplett leer" in n for n in result["notes"])


def test_constant_column_with_scaling_and_single_numeric():
    df = correlated(60)
    df["const"] = 1.0
    df.loc[:5, "y"] = np.nan
    assert engine.impute(df, "knn", {"scale": True})["frame"].notna().all().all()
    single = df[["y"]]
    for method in ["regression", "iterative", "em", "knn"]:
        assert engine.impute(single, method, {})["frame"]["y"].notna().all()


def test_categoricals_are_left_alone_but_mode_fills_them():
    df = correlated(40)
    df["cat"] = ["a", "b"] * 20
    df.loc[[1, 2], "cat"] = None
    df.loc[[3], "y"] = np.nan
    result = engine.impute(df, "iterative", {})
    assert result["frame"]["cat"].isna().sum() == 2 and result["notes"]
    assert engine.impute(df, "most_frequent", {})["frame"].notna().all().all()


def test_indicator_drop_columns_pairwise_multiple():
    df = correlated(80)
    df.loc[:19, "y"] = np.nan
    ind = engine.impute(df, "mean", {"add_indicator": True})["frame"]
    assert ind["y_missing"].sum() == 20
    assert list(engine.impute(df, "drop_columns", {"max_missing_pct": 10})["frame"].columns) == ["x", "z"]
    with pytest.raises(engine.EngineError):
        engine.impute(pd.DataFrame({"a": [np.nan, np.nan, 1.0]}), "drop_columns", {"max_missing_pct": 10})
    pair = engine.impute(df, "pairwise", {})
    assert pair["frame"].equals(df) and "corr_pairwise" in pair["extras"]
    multi = engine.impute(df, "multiple", {"m": 4})
    assert multi["extras"]["spread"].shape == (80, 3)
    assert multi["extras"]["spread"][:20, 1].min() > 0
    assert multi["extras"]["spread"][20:, 1].max() == 0


def test_bad_method_and_params():
    df = correlated(30)
    df.loc[0, "y"] = np.nan
    for method, params in [("nope", {}), ("knn", {"weights": "x"}), ("knn", {"n_neighbors": "abc"}),
                           ("constant", {"fill_value": "abc"})]:
        with pytest.raises(engine.EngineError):
            engine.impute(df, method, params)


# ---- CSV validation

@pytest.mark.parametrize("text,code", [
    ("", "empty_file"),
    ("   \n", "empty_file"),
    ("a,b\n", "empty_table"),
    ("a,a\n1,2\n", "duplicate_columns"),
    ("name,city\nx,y\n", "no_numeric_column"),
    (",".join(f"c{i}" for i in range(60)) + "\n" + ",".join("1" for _ in range(60)) + "\n", "too_many_columns"),
    ("a,b\n" + "1,2\n" * 10001, "too_many_rows"),
], ids=["empty", "blank", "header_only", "duplicates", "no_numeric", "too_wide", "too_long"])
def test_csv_rejections(text, code):
    with pytest.raises(engine.EngineError) as err:
        engine.parse_csv(text)
    assert err.value.code == code


def test_csv_tokens_and_delimiters():
    df = engine.parse_csv("a;b;c\n1;NA;x\n?;2.5;y\n3;null;\n")
    assert df["a"].isna().sum() == 1 and df["b"].isna().sum() == 2 and df["c"].isna().sum() == 1
    assert engine.numeric_columns(df) == ["a", "b"]
    assert engine.parse_csv("a\tb\n1\t2\n3\t4\n").shape == (2, 2)


# ---- run(): the JSON contract used by the UI

def test_run_full_response_is_valid_json_with_truth():
    r = call(dataset={"kind": "generated", "name": "notebook_survey"},
             missing={"mechanism": "MAR", "rate": 0.3, "target": "Income", "driver": "Age"},
             method={"id": "knn", "params": {"n_neighbors": 3}}, seed=1)
    assert r["ok"] and r["has_truth"] and not r["has_native_missing"]
    assert r["column"] == "Income" and r["missing_cells_after"] == 0
    assert len(r["imputed_cells"]) == r["missing_cells_before"]
    assert all("truth" in c for c in r["imputed_cells"])
    income = next(s for s in r["stats"] if s["column"] == "Income")
    assert income["rmse"] > 0 and income["truth"]["n"] == 100
    assert set(r["histogram"]["counts"]) == {"before", "after", "truth"}
    assert "KNNImputer(n_neighbors=3" in r["code"]


def test_run_native_missing_listwise_and_errors():
    r = call(dataset={"kind": "generated", "name": "notebook_mar"},
             missing={"mechanism": "MCAR", "rate": 0.3, "target": "Age"},
             method={"id": "listwise"})
    assert r["ok"] and r["has_native_missing"] and not r["has_truth"]
    assert r["shape_after"][0] < r["shape_before"][0] and len(r["dropped_rows"]) > 0
    assert r["notes"]
    assert call(dataset={"kind": "generated", "name": "x"})["code"] == "unknown_dataset"
    assert call(dataset={"kind": "csv", "csv": ""})["code"] == "empty_file"
    assert json.loads(engine.run("not json"))["code"] == "internal_error"


@pytest.mark.parametrize("method", ["none", "listwise", "drop_columns", "pairwise"] + IMPUTING)
def test_run_every_method_on_every_generated_dataset(method):
    for name in engine.GENERATED:
        missing = {"mechanism": "MCAR", "rate": 0.3, "target": "Income"} if name == "notebook_survey" else None
        r = call(dataset={"kind": "generated", "name": name}, missing=missing, method={"id": method})
        assert r["ok"], (name, method, r)


def test_run_all_rows_dropped_and_multiple_sd():
    df = correlated(30)
    df["z"] = np.nan
    df.loc[0, "z"] = 1.0
    df.loc[0, "x"] = np.nan
    r = call(**csv_request(df, method={"id": "listwise"}))
    assert r["ok"] and r["shape_after"][0] == 0
    df = correlated(60)
    df.loc[:9, "y"] = np.nan
    r = call(**csv_request(df, method={"id": "multiple", "params": {"m": 3}}))
    assert r["ok"] and all(c["sd"] > 0 for c in r["imputed_cells"])
    assert "y" in r["extras"]["pooled_mean"]
