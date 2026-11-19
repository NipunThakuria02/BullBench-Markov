"""Read-only saved-bundle API. No training, promotion or upload endpoints."""

import hashlib
import json
import os
import time
from collections import defaultdict, deque
from datetime import date
from pathlib import Path
from threading import Lock

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, field_validator

from nse_forecast.ingest.official import ASSETS
from nse_forecast.experiments.lab import (
    read_snapshots,
    observations,
    FEATURES,
)
from nse_forecast.unit4.hmm import GaussianHMM


class PredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset: str
    as_of_session: date

    @field_validator("as_of_session", mode="before")
    @classmethod
    def iso_session(cls, value):
        if (
            not isinstance(value, str)
            or len(value) != 10
            or date.fromisoformat(value).isoformat() != value
        ):
            raise ValueError("Use ISO YYYY-MM-DD session date")

        if date.fromisoformat(value) > date.today():
            raise ValueError("Future as-of session prohibited")

        return value


def create_app(snapshot_root=None, registry_root=None, evidence_root=None):
    snapshots = Path(
        snapshot_root
        or os.environ.get(
            "BULLBENCH_SNAPSHOTS",
            "data/exploratory_snapshots",
        )
    )

    registry = Path(
        registry_root
        or os.environ.get("BULLBENCH_REGISTRY", "model_registry")
    )

    evidence_path = (
        Path(evidence_root)
        if evidence_root is not None
        else Path(__file__).resolve().parents[2] / "docs"
    )

    app = FastAPI(
        title="BullBench MarkovLab",
        version="0.1.0",
    )

    legacy = Path(
        os.environ.get("BULLBENCH_LEGACY_SITE", "data/legacy_site")
    ).resolve()

    def legacy_file(request, name):
        # Explicit local mode only. Loopback alone must never enable
        # private history serving behind a hosted reverse proxy.
        if os.environ.get("BULLBENCH_LOCAL_LEGACY") != "1":
            raise HTTPException(
                404,
                "Local legacy results are disabled",
            )

        try:
            listing = json.loads(
                (legacy / "manifest.json").read_text()
            )["files_sha256"]

            path = (legacy / name).resolve()

            if not path.is_relative_to(legacy) or name not in listing:
                raise ValueError("Not listed")

            raw = path.read_bytes()

            if hashlib.sha256(raw).hexdigest() != listing[name]:
                raise ValueError("Checksum differs")

            return json.loads(raw)

        except (OSError, ValueError, KeyError):
            raise HTTPException(
                503,
                "Original local results/history missing or failed checksum validation",
            )

    @app.get("/api/results")
    def legacy_results(request: Request):
        return legacy_file(request, "results.json")

    @app.get("/api/history")
    def legacy_history(request: Request, symbol: str):
        allowed = {
            asset + ".NS"
            for asset in ASSETS
            if asset != "NIFTY 50"
        } | {"^NSEI"}

        if symbol not in allowed:
            raise HTTPException(
                400,
                "Unsupported legacy instrument",
            )

        filename = (
            symbol.replace("^", "INDEX_").replace("=", "_")
            + ".json"
        )

        return legacy_file(request, "history/" + filename)

    origins = [
        origin
        for origin in os.environ.get(
            "BULLBENCH_CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    hits = defaultdict(deque)
    lock = Lock()

    @app.middleware("http")
    async def bounds(request: Request, call_next):
        from fastapi.responses import JSONResponse

        if request.method == "POST":
            length = request.headers.get("content-length")

            if length and (
                not length.isdigit() or int(length) > 4096
            ):
                return JSONResponse(
                    {"detail": "Payload too large"},
                    status_code=413,
                )

            body = await request.body()

            if len(body) > 4096:
                return JSONResponse(
                    {"detail": "Payload too large"},
                    status_code=413,
                )

        key = request.client.host if request.client else "unknown"
        now = time.monotonic()

        with lock:
            for old in list(hits):
                if not hits[old] or hits[old][-1] < now - 60:
                    del hits[old]

            queue = hits[key]

            while queue and queue[0] < now - 60:
                queue.popleft()

            if len(queue) >= 120:
                return JSONResponse(
                    {"detail": "Rate limit exceeded"},
                    status_code=429,
                )

            queue.append(now)

        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"

        return response

    def asset_check(asset):
        if asset not in ASSETS:
            raise HTTPException(
                400,
                "Choose one of the six study instruments",
            )

    def load(asset):
        asset_check(asset)

        # Per-asset pointers are written offline, never by HTTP.
        pointer = registry / (asset.replace(" ", "_") + ".json")

        if not pointer.exists():
            raise HTTPException(
                503,
                "No approved saved model bundle for this asset",
            )

        try:
            selected = json.loads(pointer.read_text())
            root = (registry / selected["bundle"]).resolve()

            if (
                not root.is_relative_to(registry.resolve())
                or root == registry.resolve()
            ):
                raise ValueError("Invalid bundle path")

            raw = (root / "manifest.json").read_bytes()

            if (
                hashlib.sha256(raw).hexdigest()
                != selected["manifest_sha256"]
            ):
                raise ValueError("Manifest integrity failure")

            manifest = json.loads(raw)

            if (
                manifest["asset"] != asset
                or selected.get("approved") is not True
            ):
                raise ValueError("Bundle is not approved for asset")

            for name, sha in manifest["files_sha256"].items():
                path = (root / name).resolve()

                if (
                    path.parent != root
                    or hashlib.sha256(path.read_bytes()).hexdigest()
                    != sha
                ):
                    raise ValueError("Bundle integrity failure")

            # Safe numeric arrays only; never deserialize pickle files.
            with np.load(
                root / "hmm.npz",
                allow_pickle=False,
            ) as data:
                arrays = {
                    key: data[key].copy()
                    for key in data.files
                }

            hmm = GaussianHMM(
                n_states=len(arrays["initial"])
            )
            hmm.initial_ = arrays["initial"]
            hmm.transition_ = arrays["transition"]
            hmm.means_ = arrays["means"]
            hmm.variances_ = arrays["variances"]

            bars, current_hashes = read_snapshots(snapshots, asset)
            config = manifest["config"]

            if config.get("calendar_file"):
                calendar = json.loads(
                    Path(config["calendar_file"]).read_text()
                )
            elif config.get("research_track") == "exploratory":
                calendar = [
                    {
                        "session_date": session,
                        "session_type": "unverified_observed",
                    }
                    for session in bars.session_date
                ]
            else:
                raise ValueError("Missing official calendar")

            if manifest.get("features") != FEATURES:
                raise ValueError("Feature schema mismatch")

            if (
                arrays["mean"].shape != (len(FEATURES),)
                or arrays["scale"].shape != (len(FEATURES),)
            ):
                raise ValueError("Scaler dimensions differ")

            if (
                not np.isfinite(arrays["mean"]).all()
                or not np.isfinite(arrays["scale"]).all()
                or (arrays["scale"] <= 0).any()
            ):
                raise ValueError("Invalid scaler")

            hmm.filter(np.zeros((1, hmm.means_.shape[1])))

            frame = observations(
                bars,
                calendar,
                config["price_basis"],
            )
            frame.attrs["source_manifest_sha256"] = current_hashes

            return (
                hmm,
                arrays,
                manifest,
                frame,
                selected["manifest_sha256"],
            )

        except (ValueError, OSError, KeyError, TypeError) as error:
            raise HTTPException(
                503,
                "Saved bundle/data unavailable or failed validation",
            ) from error

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "service": "BullBench MarkovLab",
            "notice": "Research only. Not investment advice.",
        }

    @app.get("/v1/assets")
    def assets():
        return {"assets": list(ASSETS)}

    @app.get("/ready")
    def ready(asset: str):
        load(asset)

        return {
            "status": "ready",
            "asset": asset,
            "notice": (
                "Exploratory approval is not official-data validation."
            ),
        }

    @app.get("/v1/data/status")
    def status():
        items = []

        for asset in ASSETS:
            try:
                bars, hashes = read_snapshots(snapshots, asset)

                items.append(
                    {
                        "asset": asset,
                        "available": True,
                        "last_session": bars.session_date.max(),
                        "rows": len(bars),
                        "source_verified": False,
                        "status": "imported_unverified",
                        "snapshot_hashes": hashes,
                    }
                )

            except (ValueError, OSError, KeyError):
                items.append(
                    {
                        "asset": asset,
                        "available": False,
                        "status": "missing_or_invalid",
                    }
                )

        return {
            "assets": items,
            "g0_passed": False,
            "notice": (
                "Parsed files do not certify source rights, "
                "calendar or corporate actions."
            ),
        }

    @app.get("/v1/data/evidence")
    def data_evidence():
        items = []

        evidence_files = [
            ("NIFTY 50 imports", "NIFTY_IMPORT_AUDIT.json"),
            ("Trading calendar", "CALENDAR_AUDIT.json"),
            ("Corporate actions", "CORPORATE_ACTION_AUDIT.json"),
        ]

        for kind, filename in evidence_files:
            try:
                report = json.loads(
                    (evidence_path / filename).read_text()
                )

                if kind == "NIFTY 50 imports":
                    issues = [
                        (
                            f"{len(report['weekend_sessions_requiring_review'])} "
                            "weekend observations require session-type review."
                        ),
                        (
                            "Download/publication times and data-use "
                            "permission remain unverified."
                        ),
                    ]

                    summary = (
                        f"{report['rows']:,} unique observations, "
                        f"{report['first_session']} to "
                        f"{report['last_session']}. "
                        "Originals retained with checksums."
                    )

                elif kind == "Trading calendar":
                    values = report["comparisons"].get(
                        "NIFTY 50",
                        {},
                    )

                    issues = [
                        (
                            "Calendar amendments are still required. "
                            "Candidate weekdays are not verified sessions."
                        )
                    ]

                    checks = [
                        (
                            "observed_on_annual_closure",
                            "Observed on an annual-notice closure",
                        ),
                        (
                            "absent_from_candidate_weekdays",
                            "Potential later closure amendments",
                        ),
                        (
                            "weekend_observations_without_annual_session_notice",
                            "Special-session notices required",
                        ),
                    ]

                    for key, label in checks:
                        if values.get(key):
                            issues.append(
                                label + ": " + ", ".join(values[key])
                            )

                    years = sorted(
                        item["year"]
                        for item in report["sources"]
                    )

                    summary = (
                        "Annual Capital Market circulars cover "
                        f"{years[0]}–{years[-1]}; "
                        "explicit Muhurat exceptions are retained."
                    )

                else:
                    sources = report["sources"]

                    count = sum(
                        item["in_scope_rows"]
                        for item in sources
                    )

                    summary = (
                        f"{count} in-period event records across "
                        f"five stocks; {len(report['structural_events'])} "
                        "bonus/split/demerger events flagged."
                    )

                    issues = [
                        (
                            "Official previous-close adjustment is not "
                            "verified by event presence. Announcement "
                            "timestamps remain unknown."
                        )
                    ]

                    for item in report["instruments"]:
                        issues.extend(item.get("warnings", []))

                items.append(
                    {
                        "kind": kind,
                        "status": "imported · review pending",
                        "summary": summary,
                        "issues": issues,
                    }
                )

            except (
                OSError,
                ValueError,
                KeyError,
                TypeError,
                IndexError,
            ):
                items.append(
                    {
                        "kind": kind,
                        "status": "unavailable",
                        "summary": "No readable audit record is available.",
                        "issues": [],
                    }
                )

        return {
            "items": items,
            "notice": (
                "Evidence inventory only. G0 and official calendar/"
                "adjustment verification remain pending; "
                "no observations were filled or deleted."
            ),
        }

    @app.get("/v1/assets/{asset}/history")
    def history(asset: str):
        asset_check(asset)

        raise HTTPException(
            403,
            "Public raw OHLC history disabled pending data-display permission (D-007)",
        )

    @app.get("/v1/assets/{asset}/states")
    def states(asset: str, view: str = "filtered"):
        if view not in ("filtered", "smoothed", "viterbi"):
            raise HTTPException(400, "Unknown state view")

        hmm, arrays, manifest, frame, version = load(asset)

        x = (
            (
                frame[FEATURES].to_numpy()
                - arrays["mean"]
            )
            / arrays["scale"]
        )[:, :1]

        if view == "filtered":
            values = hmm.filter(x)
        elif view == "smoothed":
            values = hmm.smooth(x)
        else:
            values = hmm.decode(x)

        return {
            "asset": asset,
            "view": view,
            "retrospective": view != "filtered",
            "model_version": version,
            "trained_through": manifest["trained_through"],
            "scope": (
                "Conditional filtering under this fitted model. "
                "Rows through training cutoff are in-sample state "
                "exploration, not out-of-sample historical forecasts."
            ),
            "rows": [
                {
                    "session_date": session,
                    "value": value.tolist(),
                }
                for session, value in zip(
                    frame.session_date,
                    values,
                )
            ],
        }

    @app.get("/v1/assets/{asset}/transitions")
    def transitions(asset: str):
        hmm, arrays, manifest, frame, version = load(asset)

        dwell = np.divide(
            1,
            1 - np.diag(hmm.transition_),
            out=np.full(hmm.n_states, np.nan),
            where=np.diag(hmm.transition_) < 1,
        )

        return {
            "asset": asset,
            "matrix": hmm.transition_.tolist(),
            "expected_dwell_sessions": [
                float(value) if np.isfinite(value) else None
                for value in dwell
            ],
            "model_version": version,
            "notice": "State IDs have no stable meaning across fits.",
        }

    @app.post("/v1/predict/large-move")
    def risk(payload: PredictionRequest):
        hmm, arrays, manifest, frame, version = load(payload.asset)
        day = payload.as_of_session.isoformat()

        if day <= manifest["trained_through"]:
            raise HTTPException(
                422,
                "As-of must be after training; in-sample forecasts are prohibited",
            )

        frame = frame.loc[frame.session_date <= day]

        if frame.empty or frame.session_date.iloc[-1] != day:
            raise HTTPException(
                422,
                "No complete validated features for requested session",
            )

        x = (
            (
                frame[FEATURES].to_numpy()
                - arrays["mean"]
            )
            / arrays["scale"]
        )[:, :1]

        if not manifest["config"].get("calendar_file"):
            raise HTTPException(
                422,
                "Supply an official target-session calendar before inference",
            )

        calendar = json.loads(
            Path(
                manifest["config"]["calendar_file"]
            ).read_text()
        )

        following = [
            row["session_date"]
            for row in calendar
            if row["session_date"] > day
            and row["session_type"] == "regular"
        ]

        if not following:
            raise HTTPException(
                422,
                "Next session absent from supplied official calendar",
            )

        probability = float(
            hmm.risk(
                x,
                float(arrays["theta"]),
                float(arrays["mean"][0]),
                float(arrays["scale"][0]),
            )[-1]
        )

        return {
            "asset": payload.asset,
            "as_of_session": day,
            "target_session": following[0],
            "target_definition": (
                "Absolute next-session log return > fixed training threshold"
            ),
            "threshold": float(arrays["theta"]),
            "probability": probability,
            "model_version": version,
            "trained_through": manifest["trained_through"],
            "data_freshness": "latest_imported_session_not_verified_current",
            "source_manifest_sha256": frame.attrs[
                "source_manifest_sha256"
            ],
            "training_source_manifest_sha256": manifest[
                "snapshot_manifest_sha256"
            ],
            "research_track": manifest.get(
                "research_track",
                "unverified",
            ),
            "warnings": [
                "Research only. Not investment advice.",
                "Gaussian tails and calibration require review.",
                (
                    "Yahoo/manual-index evidence is exploratory; "
                    "official calendar and source validation remain separate."
                ),
            ],
        }

    @app.post("/v1/predict/next-close")
    def next_close(payload: PredictionRequest):
        hmm, arrays, manifest, frame, version = load(payload.asset)

        if manifest["config"]["price_basis"] not in (
            "exploratory_adjusted_close",
            "exploratory_index_close",
        ):
            raise HTTPException(
                503,
                "Official raw-close inference requires as-of corporate-action reconstruction factors",
            )

        # Reuse all date/session/provenance checks.
        metadata = risk(payload)

        frame = frame.loc[
            frame.session_date
            <= payload.as_of_session.isoformat()
        ]

        x = (
            (
                frame[FEATURES].to_numpy()
                - arrays["mean"]
            )
            / arrays["scale"]
        )[:, :1]

        weights = hmm.filter(x)[-1] @ hmm.transition_

        mu = (
            arrays["mean"][0]
            + arrays["scale"][0] * hmm.means_[:, 0]
        )

        variance = (
            arrays["scale"][0] ** 2
            * hmm.variances_[:, 0]
        )

        expected = float(
            frame.close.iloc[-1]
            * (weights @ np.exp(mu + 0.5 * variance))
        )

        return {
            key: value
            for key, value in metadata.items()
            if key not in (
                "probability",
                "threshold",
                "target_definition",
            )
        } | {
            "predicted_close": expected,
            "model": "HMM expected return",
            "price_basis": "vendor-adjusted or index points",
            "target_definition": (
                "Next-session close on the same exploratory adjusted price basis"
            ),
        }

    @app.get("/v1/experiments")
    def experiments():
        entries = []

        if registry.exists():
            for path in sorted(registry.glob("*/manifest.json")):
                try:
                    manifest = json.loads(path.read_text())

                    if manifest.get("status") == "inference_only":
                        continue

                    entries.append(
                        {
                            "id": path.parent.name,
                            "asset": manifest["asset"],
                            "status": manifest["status"],
                        }
                    )

                except (ValueError, OSError, KeyError):
                    continue

        return {"experiments": entries}

    def experiment_record(run_id):
        if not run_id.replace("-", "").replace("_", "").isalnum():
            raise HTTPException(400, "Invalid run ID")

        root = registry / run_id
        path = root / "manifest.json"

        if not path.exists():
            raise HTTPException(404, "Experiment unavailable")

        try:
            raw = path.read_bytes()
            manifest = json.loads(raw)
            asset_check(manifest["asset"])

            for name, sha in manifest["files_sha256"].items():
                artifact = (root / name).resolve()

                if (
                    artifact.parent != root.resolve()
                    or hashlib.sha256(
                        artifact.read_bytes()
                    ).hexdigest() != sha
                ):
                    raise ValueError("Run integrity failure")

            if not {"predictions.csv", "hmm.npz"}.issubset(
                manifest["files_sha256"]
            ):
                raise ValueError(
                    "Missing required artifact checksum"
                )

            predictions = pd.read_csv(root / "predictions.csv")

            if (
                predictions.empty
                or set(predictions.asset) != {manifest["asset"]}
                or predictions.duplicated(
                    ["target_session", "model"]
                ).any()
            ):
                raise ValueError("Invalid saved pairs")

            if set(predictions.model) != set(manifest["metrics"]):
                raise ValueError("Comparator mismatch")

            if (
                not predictions.actual.isin([0, 1]).all()
                or not np.isfinite(
                    predictions.probability
                ).all()
                or not predictions.probability.between(
                    0,
                    1,
                ).all()
            ):
                raise ValueError("Invalid probabilities/outcomes")

            groups = predictions.groupby("target_session")

            if (
                (groups.actual.nunique() != 1).any()
                or (
                    groups.model.nunique()
                    != len(manifest["metrics"])
                ).any()
            ):
                raise ValueError("Unpaired outcomes")

            from nse_forecast.experiments.lab import scoring

            recomputed_metrics = {}

            for name, part in predictions.groupby("model"):
                recorded = manifest["metrics"][name]

                computed = scoring(
                    part.actual.to_numpy(),
                    part.probability.to_numpy(),
                    recorded["decision_threshold"],
                )

                for key in (
                    "n",
                    "events",
                    "brier",
                    "log_loss",
                    "pr_auc",
                ):
                    if computed[key] is None:
                        if recorded[key] is not None:
                            raise ValueError(
                                "Undefined classification metric must remain null"
                            )
                        continue

                    # Older XGBoost metrics used float32 reduction.
                    # Permit four float32 ULPs, not arbitrary drift.
                    tolerance = (
                        0
                        if key in ("n", "events")
                        else 4
                        * abs(
                            float(
                                np.spacing(
                                    np.float32(recorded[key])
                                )
                            )
                        )
                    )

                    if not np.isclose(
                        computed[key],
                        recorded[key],
                        rtol=0,
                        atol=tolerance,
                    ):
                        raise ValueError(
                            "Metric differs from saved predictions"
                        )

                recomputed_metrics[name] = computed

            baseline = recomputed_metrics.get(
                "Prevalence",
                {},
            ).get("brier", 0)

            for metric in recomputed_metrics.values():
                if baseline > 0:
                    metric["brier_skill"] = (
                        1 - metric["brier"] / baseline
                    )

            if manifest["price_metrics"]:
                if "price_predictions.csv" not in manifest[
                    "files_sha256"
                ]:
                    raise ValueError("Missing price checksum")

                prices = pd.read_csv(
                    root / "price_predictions.csv"
                )

                if (
                    prices.duplicated(
                        ["target_session", "model"]
                    ).any()
                    or set(prices.model)
                    != set(manifest["price_metrics"])
                ):
                    raise ValueError("Price comparator mismatch")

                if not np.isfinite(
                    prices[["actual", "predicted"]].to_numpy()
                ).all():
                    raise ValueError("Invalid saved prices")

                if (
                    prices.groupby(
                        "target_session"
                    ).actual.nunique() != 1
                ).any():
                    raise ValueError("Price outcomes disagree")

                for name, part in prices.groupby("model"):
                    if set(part.target_session) != set(
                        predictions.target_session
                    ):
                        raise ValueError(
                            "Unpaired price target dates"
                        )

                    error = (
                        part.predicted.to_numpy()
                        - part.actual.to_numpy()
                    )

                    computed = {
                        "mae": float(np.abs(error).mean()),
                        "rmse": float(
                            np.sqrt((error ** 2).mean())
                        ),
                    }

                    if any(
                        not np.isclose(
                            computed[key],
                            manifest["price_metrics"][name][key],
                            rtol=1e-10,
                            atol=1e-10,
                        )
                        for key in computed
                    ):
                        raise ValueError(
                            "Price metric differs from saved predictions"
                        )

            train_end = manifest["config"]["train_end"]

            if predictions.origin_session.min() <= train_end:
                raise ValueError("Validation overlaps training")

            with np.load(
                root / "hmm.npz",
                allow_pickle=False,
            ) as arrays:
                threshold = float(arrays["theta"])

            if not np.isfinite(threshold) or threshold <= 0:
                raise ValueError("Invalid threshold")

            from nse_forecast.experiments.diagnostics import (
                probability_diagnostics,
            )

            reliability, intervals = probability_diagnostics(
                predictions
            )

            result = {
                key: manifest[key]
                for key in (
                    "asset",
                    "status",
                    "metrics",
                    "price_metrics",
                    "failed_models",
                    "hmm_runs",
                    "calibration",
                    "caveat",
                    "final_test_evaluated",
                )
            }

            if (
                predictions.actual.nunique() == 1
                and not manifest["final_test_evaluated"]
            ):
                result["caveat"] = (
                    "HMM state/seed selected on validation; "
                    "classification threshold fixed at 0.5 because "
                    "validation has one outcome class. Probability "
                    "scores do not establish event-detection ability. "
                    "All scores are exploratory."
                )

            result["metrics"] = recomputed_metrics

            result.update(
                model_version=hashlib.sha256(raw).hexdigest(),
                research_track=manifest.get(
                    "research_track",
                    "unverified",
                ),
                evaluation={
                    "train_end": train_end,
                    "validation_start": (
                        predictions.target_session.min()
                    ),
                    "validation_end": (
                        predictions.target_session.max()
                    ),
                    "threshold": threshold,
                    "kind": (
                        "locked_historical_test"
                        if manifest["final_test_evaluated"]
                        else "development_validation"
                    ),
                    "selection_validation": manifest.get(
                        "validation_period"
                    ),
                },
                reliability=reliability,
                uncertainty=intervals,
            )

            if manifest["final_test_evaluated"]:
                if (
                    predictions.origin_session.min()
                    < manifest["config"]["test_start"]
                    or predictions.target_session.max()
                    > manifest["config"]["test_end"]
                ):
                    raise ValueError(
                        "Historical prediction outside locked test"
                    )

                result["protocol_sha256"] = manifest[
                    "protocol_sha256"
                ]

                result["uncertainty"] = [
                    {
                        **row,
                        "limitation": (
                            "Conditional on frozen fitted predictions; "
                            "no refitting; no cross-asset multiplicity "
                            "correction."
                        ),
                    }
                    for row in intervals
                ]

            return result, predictions

        except (ValueError, OSError, KeyError, TypeError) as error:
            raise HTTPException(
                503,
                "Saved experiment failed integrity or metric verification",
            ) from error

    @app.get("/v1/experiments/{run_id}")
    def experiment(run_id: str):
        return experiment_record(run_id)[0]

    @app.get("/v1/experiments/{run_id}/risk-predictions")
    def historical_risk_predictions(run_id: str):
        result, predictions = experiment_record(run_id)

        # Read existing checksum/metric-verified predictions only.
        # No training, new inference or raw price history is generated.
        if (
            predictions.groupby(
                "target_session"
            ).origin_session.nunique() != 1
        ).any():
            raise HTTPException(
                503,
                "Saved prediction origins disagree",
            )

        if (
            predictions.origin_session
            >= predictions.target_session
        ).any():
            raise HTTPException(
                503,
                "Saved origin must precede target session",
            )

        models = sorted(
            result["metrics"],
            key=lambda name: (
                name != "HMM",
                name != "Prevalence",
                name,
            ),
        )

        rows = []

        for target, part in predictions.groupby(
            "target_session",
            sort=True,
        ):
            rows.append(
                {
                    "origin_session": str(
                        part.origin_session.iloc[0]
                    ),
                    "target_session": str(target),
                    "actual_event": int(
                        part.actual.iloc[0]
                    ),
                    "probabilities": {
                        str(row.model): float(row.probability)
                        for row in part.itertuples()
                    },
                }
            )

        return {
            "asset": result["asset"],
            "run_id": run_id,
            "model_version": result["model_version"],
            "evaluation": result["evaluation"],
            "evaluation_kind": result["evaluation"]["kind"],
            "target_definition": (
                "Next observed-session absolute log return exceeds "
                "the fixed training threshold."
            ),
            "notice": (
                "Saved historical predictions and later observed "
                "outcomes. This view does not generate a new forecast "
                "or prospective evidence."
            ),
            "models": models,
            "decision_thresholds": {
                name: result["metrics"][name]["decision_threshold"]
                for name in models
            },
            "rows": rows,
        }

    @app.get("/v1/experiments/{run_id}/predictions")
    def experiment_predictions(run_id: str):
        from fastapi.responses import Response

        _, predictions = experiment_record(run_id)

        columns = [
            "asset",
            "origin_session",
            "target_session",
            "model",
            "actual",
            "probability",
        ]

        return Response(
            predictions[columns].to_csv(index=False),
            media_type="text/csv",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{run_id}-predictions.csv"'
                )
            },
        )

    return app


app = create_app()