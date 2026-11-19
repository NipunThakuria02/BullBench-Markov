import { useEffect, useState } from 'react';
import type { Asset } from './assets';
import { InteractiveChart } from './charts';
import { assetValue, displayDate, percent } from './data';
import {
    labAsset,
    labStatus,
    labRuns,
    labStates,
    labTransitions,
    labExperiment,
    labEvidence,
    labDownload,
    type StateView,
    type StateData,
    type TransitionData,
    type StatusData,
    type Run,
    type Experiment,
    type Evidence,
} from './markov-api';
import { HistoricalRiskPredictions } from './HistoricalRiskPredictions';
import './markov-sections.css';

export const LAB_SECTIONS = [
    ['experiments', 'Results'],
    ['states', 'Hidden states'],
    ['transitions', 'Transitions'],
    ['forecasts', 'Historical risk predictions'],
    ['data-quality', 'Data quality'],
] as const;

const palette = ['#6355ff', '#168b65', '#bf8447', '#be6655'];

function dataSource(name: string) {
    if (name === 'NIFTY 50') {
        return {
            name: 'NSE Indices · manual CSV export',
            url: 'https://www.niftyindices.com/reports/historical-data',
        };
    }

    if (
        ['HDFCBANK', 'ICICIBANK', 'TCS', 'RELIANCE', 'TATASTEEL'].includes(name)
    ) {
        return {
            name: 'Yahoo Finance · adjusted prices',
            url: `https://finance.yahoo.com/quote/${encodeURIComponent(
                name + '.NS',
            )}/history/`,
        };
    }

    return {
        name: 'Source not specified',
        url: '',
    };
}

function SourceLink({ instrument }: { instrument: string }) {
    const source = dataSource(instrument);

    return source.url ? (
        <a
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
        >
            {source.name}
        </a>
    ) : (
        <span>{source.name}</span>
    );
}

function Unavailable({ error }: { error?: string }) {
    return error ? (
        <div className="results-error" role="alert">
            <strong>Unavailable</strong>
            <p>{error}</p>
            <p>No replacement values generated.</p>
        </div>
    ) : null;
}

export function MarkovSections({
    asset,
    activeSection,
}: {
    asset: Asset;
    activeSection: string;
}) {
    const instrument = labAsset(asset.symbol);

    const [status, setStatus] = useState<StatusData | null>(null);
    const [runs, setRuns] = useState<Run[]>([]);
    const [run, setRun] = useState('');
    const [view, setView] = useState<StateView>('filtered');

    const [states, setStates] = useState<StateData | null>(null);
    const [transitions, setTransitions] =
        useState<TransitionData | null>(null);
    const [experiment, setExperiment] =
        useState<Experiment | null>(null);
    const [evidence, setEvidence] = useState<Evidence | null>(null);

    const [errors, setErrors] = useState<Record<string, string>>({});
    const [loading, setLoading] = useState('');
    const [refresh, setRefresh] = useState(0);

    useEffect(() => {
        const controller = new AbortController();

        labStatus(controller.signal)
            .then(setStatus)
            .catch(e => {
                if (!controller.signal.aborted) {
                    setErrors(previous => ({
                        ...previous,
                        status: e.message,
                    }));
                }
            });

        labRuns(controller.signal)
            .then(value => {
                const list = value.experiments
                    .filter(item => item.asset === instrument)
                    .sort(
                        (a, b) =>
                            Number(b.status === 'locked_historical_test') -
                            Number(a.status === 'locked_historical_test'),
                    );

                setRuns(list);

                setRun(previous =>
                    list.some(item => item.id === previous)
                        ? previous
                        : list[0]?.id || '',
                );
            })
            .catch(e => {
                if (!controller.signal.aborted) {
                    setErrors(previous => ({
                        ...previous,
                        runs: e.message,
                    }));
                }
            });

        return () => controller.abort();
    }, [instrument, refresh]);

    useEffect(() => {
        const controller = new AbortController();
        let request: Promise<unknown> | undefined;

        setErrors(previous => ({
            ...previous,
            [activeSection]: '',
        }));

        if (activeSection === 'states') {
            setStates(null);
            request = labStates(
                instrument,
                view,
                controller.signal,
            ).then(setStates);
        }

        if (activeSection === 'transitions') {
            setTransitions(null);
            request = labTransitions(
                instrument,
                controller.signal,
            ).then(setTransitions);
        }

        if (activeSection === 'experiments' && run) {
            setExperiment(null);
            request = labExperiment(
                run,
                instrument,
                controller.signal,
            ).then(setExperiment);
        }

        if (activeSection === 'data-quality') {
            request = labEvidence(controller.signal).then(setEvidence);
        }

        setLoading(request ? activeSection : '');

        request
            ?.catch(e => {
                if (!controller.signal.aborted) {
                    setErrors(previous => ({
                        ...previous,
                        [activeSection]: e.message,
                    }));
                }
            })
            .finally(() => {
                if (!controller.signal.aborted) {
                    setLoading('');
                }
            });

        return () => controller.abort();
    }, [activeSection, instrument, view, run, refresh]);

    const current = status?.assets.find(
        item => item.asset === instrument,
    );

    const label = experiment?.final_test_evaluated
        ? 'Historical test'
        : 'Validation';

    const hmm = experiment?.metrics.HMM;
    const prevalence = experiment?.metrics.Prevalence;

    const ranking = experiment
        ? Object.entries(experiment.metrics).sort(
            (a, b) => a[1].brier - b[1].brier,
        )
        : [];

    const hmmSkill =
        hmm && prevalence && prevalence.brier > 0
            ? 1 - hmm.brier / prevalence.brier
            : null;

    async function download() {
        try {
            await labDownload(run);
        } catch (e) {
            setErrors(previous => ({
                ...previous,
                experiments: (e as Error).message,
            }));
        }
    }

    function prompt(id: string) {
        return activeSection !== id ? (
            <p className="subtle-note">
                <a href={`#/markovlab/${asset.slug}/${id}`}>
                    Open this section
                </a>{' '}
                to load saved evidence for {asset.short}.
            </p>
        ) : null;
    }

    function pending(id: string) {
        return loading === id ? (
            <p role="status" className="subtle-note">
                Loading saved evidence…
            </p>
        ) : null;
    }

    function reload() {
        setRefresh(value => value + 1);
    }

    return (
        <>
            <section id="states" className="panel lab-section">
                <div className="section-title">
                    <div>
                        <h2>Hidden states</h2>
                        <p>
                            Causal probabilities and retrospective decoding for{' '}
                            {asset.short}.
                        </p>
                    </div>

                    <div className="filter-controls">
                        <label>
                            State view
                            <select
                                value={view}
                                onChange={e =>
                                    setView(e.target.value as StateView)
                                }
                            >
                                <option value="filtered">Causal filtering</option>
                                <option value="smoothed">
                                    Retrospective smoothing
                                </option>
                                <option value="viterbi">
                                    Retrospective Viterbi path
                                </option>
                            </select>
                        </label>
                    </div>
                </div>

                {view !== 'filtered' && (
                    <p className="lab-warning">
                        Retrospective: uses future observations within the
                        displayed sequence. Never a historical forecasting feature.
                    </p>
                )}

                {prompt('states')}
                {pending('states')}
                <Unavailable error={errors.states} />

                {states && (
                    <>
                        <p className="subtle-note">
                            State IDs have no stable meaning across fits. Model{' '}
                            {states.model_version}
                            {states.trained_through
                                ? ` · trained through ${displayDate(
                                    states.trained_through,
                                )}`
                                : ''}
                            . {states.scope}
                        </p>

                        {view !== 'viterbi' && (
                            <>
                                <InteractiveChart
                                    dates={states.rows.map(row => row.session_date)}
                                    series={(states.rows[0].value as number[]).map(
                                        (_, index) => ({
                                            name: `State ${index}`,
                                            color: palette[index % palette.length],
                                            values: states.rows.map(
                                                row => (row.value as number[])[index],
                                            ),
                                        }),
                                    )}
                                    symbol={asset.symbol}
                                    returns
                                    label={`${asset.short} ${view} state probabilities`}
                                />

                                <div className="model-legend">
                                    {(states.rows[0].value as number[]).map(
                                        (_, index) => (
                                            <span key={index}>
                                                <i
                                                    style={{
                                                        background:
                                                            palette[index % palette.length],
                                                    }}
                                                />
                                                State {index}
                                            </span>
                                        ),
                                    )}
                                </div>
                            </>
                        )}

                        <details className="lab-details">
                            <summary>
                                Inspect state observations ({states.rows.length}{' '}
                                sessions)
                            </summary>

                            <div className="table-scroll">
                                <table>
                                    <thead>
                                        <tr>
                                            <th>Session</th>
                                            <th>
                                                {view === 'viterbi'
                                                    ? 'State ID'
                                                    : 'State probabilities'}
                                            </th>
                                        </tr>
                                    </thead>

                                    <tbody>
                                        {states.rows.slice(-100).map(row => (
                                            <tr key={row.session_date}>
                                                <td>{displayDate(row.session_date)}</td>
                                                <td>
                                                    {Array.isArray(row.value)
                                                        ? row.value
                                                            .map(
                                                                (probability, index) =>
                                                                    `S${index}: ${percent(probability)}`,
                                                            )
                                                            .join(' · ')
                                                        : `S${row.value}`}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>

                            <p className="subtle-note">
                                Showing the latest{' '}
                                {Math.min(100, states.rows.length)} observations.
                            </p>
                        </details>
                    </>
                )}
            </section>

            <section id="transitions" className="panel lab-section">
                <div className="section-title">
                    <div>
                        <h2>Transitions</h2>
                        <p>How the fitted model moves between hidden states.</p>
                    </div>

                    <button className="outline-button" onClick={reload}>
                        REFRESH EVIDENCE
                    </button>
                </div>

                {prompt('transitions')}
                {pending('transitions')}
                <Unavailable error={errors.transitions} />

                {transitions && (
                    <>
                        <div className="table-scroll">
                            <table className="lab-transition">
                                <caption>Conditional next-state probabilities</caption>

                                <thead>
                                    <tr>
                                        <th>From / To</th>
                                        {transitions.matrix.map((_, index) => (
                                            <th key={index}>State {index}</th>
                                        ))}
                                        <th>Expected dwell sessions</th>
                                    </tr>
                                </thead>

                                <tbody>
                                    {transitions.matrix.map((row, index) => (
                                        <tr key={index}>
                                            <th>State {index}</th>

                                            {row.map((probability, column) => (
                                                <td
                                                    key={column}
                                                    style={{
                                                        background: `rgba(99,85,255,${0.04 + probability * 0.2
                                                            })`,
                                                    }}
                                                >
                                                    {percent(probability)}
                                                </td>
                                            ))}

                                            <td>
                                                {transitions.expected_dwell_sessions[
                                                    index
                                                ]?.toFixed(1) ?? 'Unbounded'}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>

                        <p className="subtle-note">
                            {transitions.notice} Transition probabilities are not
                            event-risk forecasts.
                        </p>
                    </>
                )}
            </section>

            <section id="forecasts" className="panel lab-section">
                {activeSection === 'forecasts' ? (
                    <HistoricalRiskPredictions
                        key={`${instrument}:${run}`}
                        asset={asset}
                        runId={run}
                        runs={runs}
                        runError={errors.runs}
                        onRunChange={setRun}
                    />
                ) : (
                    prompt('forecasts')
                )}
            </section>

            <section id="experiments" className="panel lab-section">
                <div className="section-title">
                    <div>
                        <h2>MarkovLab results</h2>
                        <p>
                            Saved development and locked historical comparisons for{' '}
                            {asset.short}. Select a run to inspect its evaluation
                            period.
                        </p>
                    </div>

                    <div className="filter-controls">
                        <label>
                            Evaluation period
                            <select
                                value={run}
                                onChange={e => setRun(e.target.value)}
                            >
                                <option value="">Select an evaluation</option>

                                {runs.map(item => (
                                    <option key={item.id} value={item.id}>
                                        {item.status === 'locked_historical_test'
                                            ? 'Historical Benchmark · 2026'
                                            : item.status === 'development_candidate'
                                                ? 'Development Validation · 2023'
                                                : item.id}
                                    </option>
                                ))}
                            </select>
                        </label>
                    </div>
                </div>

                {prompt('experiments')}
                {pending('experiments')}
                <Unavailable error={errors.experiments || errors.runs} />

                {!runs.length && !errors.runs && (
                    <p className="empty-message">
                        No saved development results for this instrument. Select
                        an instrument with a saved run; no scores are generated
                        to fill this view.
                    </p>
                )}

                {experiment && (
                    <>
                        {hmm &&
                            (hmm.events === 0 || hmm.events === hmm.n) && (
                                <p className="lab-warning">
                                    <strong>
                                        Only one outcome class occurred in this{' '}
                                        {experiment.final_test_evaluated
                                            ? 'historical test'
                                            : 'validation'}{' '}
                                        window.
                                    </strong>{' '}
                                    PR-AUC, balanced accuracy and macro-F1 are not
                                    estimable. Brier/log-loss comparisons describe
                                    probability error for the observed class only and
                                    do not establish large-move detection ability.
                                    The training threshold and dates were not changed
                                    to create events.
                                </p>
                            )}

                        <div className="lab-result-meta">
                            <span>
                                Trained through{' '}
                                <strong>
                                    {displayDate(experiment.evaluation.train_end)}
                                </strong>
                            </span>

                            <span>
                                {label} targets{' '}
                                <strong>
                                    {displayDate(
                                        experiment.evaluation.validation_start,
                                    )}
                                    {' – '}
                                    {displayDate(
                                        experiment.evaluation.validation_end,
                                    )}
                                </strong>
                            </span>

                            <span>
                                Event threshold |log return| &gt;{' '}
                                <strong>
                                    {percent(experiment.evaluation.threshold)}
                                </strong>
                            </span>
                        </div>

                        {hmm && (
                            <div className="lab-results-summary">
                                <div>
                                    <span>HMM Brier score · lower is better</span>
                                    <strong>{hmm.brier.toFixed(4)}</strong>
                                    <small>
                                        {hmm.events} large-move events across {hmm.n}{' '}
                                        {label.toLowerCase()} sessions
                                    </small>
                                </div>

                                <div>
                                    <span>HMM Brier skill vs prevalence</span>
                                    <strong>
                                        {hmmSkill === null
                                            ? 'Unavailable'
                                            : percent(hmmSkill)}
                                    </strong>
                                    <small>
                                        {hmmSkill === null
                                            ? 'Reference score unavailable'
                                            : hmmSkill > 0
                                                ? 'Lower Brier error than the prevalence baseline.'
                                                : hmmSkill < 0
                                                    ? 'Higher Brier error than the prevalence baseline.'
                                                    : 'Same Brier error as the prevalence baseline.'}
                                    </small>
                                </div>

                                <div>
                                    <span>Lowest {label.toLowerCase()} Brier</span>
                                    <strong>
                                        {ranking[0]?.[0] ?? 'Unavailable'}
                                    </strong>
                                    <small>
                                        {ranking[0]
                                            ? `Brier ${ranking[0][1].brier.toFixed(
                                                4,
                                            )} · descriptive comparison, not a profitability claim.`
                                            : 'No paired comparison available.'}
                                    </small>
                                </div>
                            </div>
                        )}

                        {hmm && (
                            <p className="lab-result-finding">
                                The HMM ranks{' '}
                                <strong>
                                    {1 +
                                        ranking.filter(
                                            ([, metric]) => metric.brier < hmm.brier,
                                        ).length}{' '}
                                    of {ranking.length}
                                </strong>{' '}
                                on {label.toLowerCase()} Brier score. Base event
                                rate: <strong>{percent(hmm.base_rate)}</strong>.
                                This result applies to {asset.short} and this{' '}
                                {label.toLowerCase()} window only.
                            </p>
                        )}

                        <div className="table-scroll">
                            <table>
                                <thead>
                                    <tr>
                                        <th>Model</th>
                                        <th>Brier</th>
                                        <th>Log loss</th>
                                        <th>PR-AUC</th>
                                        <th>Balanced accuracy</th>
                                        <th>Events / sessions</th>
                                    </tr>
                                </thead>

                                <tbody>
                                    {ranking.map(([name, metric]) => (
                                        <tr
                                            key={name}
                                            className={
                                                name === 'HMM'
                                                    ? 'lab-score-hmm'
                                                    : undefined
                                            }
                                        >
                                            <td>
                                                {name}
                                                {name === 'HMM' ? ' · Unit 4' : ''}
                                            </td>

                                            <td
                                                className={
                                                    ranking[0]?.[0] === name
                                                        ? 'lab-score-best'
                                                        : undefined
                                                }
                                            >
                                                {metric.brier.toFixed(4)}
                                            </td>

                                            <td>{metric.log_loss.toFixed(4)}</td>

                                            <td>
                                                {metric.pr_auc === null
                                                    ? 'Not estimable'
                                                    : metric.pr_auc.toFixed(4)}
                                            </td>

                                            <td>
                                                {metric.balanced_accuracy === null
                                                    ? 'Not estimable'
                                                    : percent(metric.balanced_accuracy)}
                                            </td>

                                            <td>
                                                {metric.events} / {metric.n}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>

                        <p className="subtle-note">
                            Brier and log loss: lower is better. PR-AUC: higher
                            is better; interpret with the event base rate. All
                            models use the same {label.toLowerCase()} target dates.
                        </p>

                        <button
                            className="outline-button lab-results-export"
                            onClick={() => void download()}
                        >
                            {experiment.final_test_evaluated
                                ? 'EXPORT HISTORICAL TEST PREDICTIONS'
                                : 'EXPORT VALIDATION PREDICTIONS'}
                        </button>

                        <p className="subtle-note">
                            {experiment.calibration}
                        </p>

                        <details className="lab-details">
                            <summary>Research notes</summary>
                            <p>
                                <strong>Research track:</strong>{' '}
                                {experiment.research_track}
                            </p>
                            <p>{experiment.caveat}</p>
                        </details>

                        <details className="lab-details">
                            <summary>
                                HMM calibration bins · raw probabilities
                            </summary>

                            <div className="table-scroll">
                                <table>
                                    <thead>
                                        <tr>
                                            <th>Bin</th>
                                            <th>Sessions</th>
                                            <th>Mean forecast probability</th>
                                            <th>Observed event rate</th>
                                        </tr>
                                    </thead>

                                    <tbody>
                                        {experiment.reliability
                                            .filter(item => item.model === 'HMM')
                                            .map(item => (
                                                <tr key={item.bin}>
                                                    <td>{item.bin + 1}</td>
                                                    <td>{item.n}</td>
                                                    <td>
                                                        {item.mean_probability === null
                                                            ? 'No observations'
                                                            : percent(item.mean_probability)}
                                                    </td>
                                                    <td>
                                                        {item.event_rate === null
                                                            ? 'No observations'
                                                            : percent(item.event_rate)}
                                                    </td>
                                                </tr>
                                            ))}
                                    </tbody>
                                </table>
                            </div>
                        </details>

                        <details className="lab-details">
                            <summary>
                                Paired uncertainty · {label.toLowerCase()} Brier
                                difference
                            </summary>

                            <p>
                                Difference versus prevalence; negative values
                                favour the model. Circular date-block bootstrap,
                                conditional on these saved predictions. Models are
                                not refitted and cross-asset multiplicity is not
                                corrected.
                            </p>

                            {experiment.uncertainty.length ? (
                                <div className="table-scroll">
                                    <table>
                                        <thead>
                                            <tr>
                                                <th>Model</th>
                                                <th>Loss difference</th>
                                                <th>Pointwise 95% interval</th>
                                            </tr>
                                        </thead>

                                        <tbody>
                                            {experiment.uncertainty.map(item => (
                                                <tr key={item.model}>
                                                    <td>{item.model}</td>
                                                    <td>{item.estimate.toFixed(4)}</td>
                                                    <td>
                                                        {item.low_95.toFixed(4)} to{' '}
                                                        {item.high_95.toFixed(4)}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            ) : (
                                <p>
                                    Insufficient saved dates for these block-bootstrap
                                    intervals.
                                </p>
                            )}
                        </details>

                        {Object.keys(experiment.price_metrics).length > 0 && (
                            <>
                                <h3>SECONDARY PRICE COMPARISON</h3>

                                <div className="table-scroll">
                                    <table>
                                        <thead>
                                            <tr>
                                                <th>Model</th>
                                                <th>Close MAE</th>
                                                <th>Close RMSE</th>
                                            </tr>
                                        </thead>

                                        <tbody>
                                            {Object.entries(
                                                experiment.price_metrics,
                                            ).map(([name, metric]) => (
                                                <tr key={name}>
                                                    <td>{name}</td>
                                                    <td>
                                                        {assetValue(
                                                            metric.mae,
                                                            asset.symbol,
                                                        )}
                                                    </td>
                                                    <td>
                                                        {assetValue(
                                                            metric.rmse,
                                                            asset.symbol,
                                                        )}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </>
                        )}

                        <details className="lab-details">
                            <summary>
                                HMM learning and convergence (
                                {experiment.hmm_runs.length} candidates)
                            </summary>

                            <div className="table-scroll">
                                <table>
                                    <thead>
                                        <tr>
                                            <th>States</th>
                                            <th>Seed</th>
                                            <th>Status</th>
                                            <th>EM steps</th>
                                            <th>Final log likelihood</th>
                                        </tr>
                                    </thead>

                                    <tbody>
                                        {experiment.hmm_runs.map((item, index) => (
                                            <tr key={index}>
                                                <td>{item.states}</td>
                                                <td>{item.seed}</td>
                                                <td>
                                                    {item.error ||
                                                        (item.converged
                                                            ? 'Converged'
                                                            : 'Not converged')}
                                                </td>
                                                <td>{item.trace?.length ?? '—'}</td>
                                                <td>
                                                    {item.trace?.at(-1)?.toFixed(3) ?? '—'}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </details>

                        {Object.keys(experiment.failed_models).length > 0 && (
                            <>
                                <h3>FAILED OR BLOCKED MODELS</h3>

                                <ul>
                                    {Object.entries(
                                        experiment.failed_models,
                                    ).map(([name, reason]) => (
                                        <li key={name}>
                                            {name}: {reason}
                                        </li>
                                    ))}
                                </ul>
                            </>
                        )}
                    </>
                )}
            </section>

            <section id="data-quality" className="panel lab-section">
                <div className="section-title">
                    <div>
                        <h2>Data quality</h2>
                        <p>
                            Data sources, imported observations and supporting
                            evidence.
                        </p>
                    </div>

                    <button className="outline-button" onClick={reload}>
                        REFRESH EVIDENCE
                    </button>
                </div>

                <Unavailable error={errors.status} />

                {current && (
                    <div className="lab-source-summary">
                        <span>
                            Instrument <strong>{instrument}</strong>
                        </span>

                        <span>
                            Data source{' '}
                            <strong>
                                <SourceLink instrument={current.asset} />
                            </strong>
                        </span>

                        <span>
                            Last imported session{' '}
                            <strong>
                                {current.last_session
                                    ? displayDate(current.last_session)
                                    : 'Not imported'}
                            </strong>
                        </span>

                        <span>
                            Observations <strong>{current.rows ?? '—'}</strong>
                        </span>

                        <span>
                            Data availability{' '}
                            <strong>
                                {current.available ? 'Loaded' : 'Unavailable'}
                            </strong>
                        </span>
                    </div>
                )}

                {status && (
                    <div className="table-scroll">
                        <table>
                            <thead>
                                <tr>
                                    <th>Instrument</th>
                                    <th>Data source</th>
                                    <th>Last imported session</th>
                                    <th>Rows</th>
                                    <th>Data availability</th>
                                </tr>
                            </thead>

                            <tbody>
                                {status.assets.map(item => (
                                    <tr key={item.asset}>
                                        <td>{item.asset}</td>

                                        <td>
                                            <SourceLink instrument={item.asset} />
                                        </td>

                                        <td>
                                            {item.last_session
                                                ? displayDate(item.last_session)
                                                : '—'}
                                        </td>

                                        <td>{item.rows ?? '—'}</td>

                                        <td>
                                            {item.available ? 'Loaded' : 'Unavailable'}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                <details className="lab-details" open>
                    <summary>Data sources and collection methods</summary>

                    <ul>
                        <li>
                            <a
                                href="https://finance.yahoo.com/"
                                target="_blank"
                                rel="noopener noreferrer"
                            >
                                Yahoo Finance
                            </a>{' '}
                            — HDFC Bank, ICICI Bank, TCS, Reliance and Tata Steel
                            historical equity prices, downloaded through the
                            yfinance Python library with automatic price
                            adjustment. These are vendor-adjusted observations,
                            not official NSE equity exports.
                        </li>

                        <li>
                            <a
                                href="https://www.niftyindices.com/reports/historical-data"
                                target="_blank"
                                rel="noopener noreferrer"
                            >
                                NSE Indices historical data
                            </a>{' '}
                            — owner-supplied NIFTY 50 daily historical CSV exports.
                            Values are index points, not equity prices or a Total
                            Return Index.
                        </li>

                        <li>
                            <a
                                href="https://www.nseindia.com/resources/exchange-communication-circulars"
                                target="_blank"
                                rel="noopener noreferrer"
                            >
                                NSE Capital Market circulars
                            </a>{' '}
                            — owner-supplied annual trading-holiday PDFs for
                            2021–2026, used as supporting calendar evidence.
                            Later amendments and special-session details remain
                            under review.
                        </li>

                        <li>
                            <a
                                href="https://www.nseindia.com/companies-listing/corporate-filings-actions"
                                target="_blank"
                                rel="noopener noreferrer"
                            >
                                NSE corporate-action records
                            </a>{' '}
                            — owner-supplied equity CSV exports covering dividends,
                            bonuses, splits, buybacks and other recorded actions.
                            These support event checks; they do not independently
                            verify historical price adjustments.
                        </li>
                    </ul>
                </details>

                <details className="lab-details">
                    <summary>Verification notes</summary>

                    <p>
                        {status?.notice ||
                            'Verification details are unavailable until the source API responds.'}
                    </p>

                    <p>
                        Loaded means that the imported snapshot passed the
                        current loader and checksum checks. Source attribution
                        does not certify complete trading-calendar
                        reconciliation, corporate-action adjustments or
                        redistribution rights.
                    </p>
                </details>

                {prompt('data-quality')}
                {pending('data-quality')}
                <Unavailable error={errors['data-quality']} />

                {evidence && (
                    <>
                        <p className="subtle-note">{evidence.notice}</p>

                        {evidence.items.map(item => (
                            <details className="lab-details" key={item.kind}>
                                <summary>
                                    {item.kind} · {item.status}
                                </summary>

                                <p>{item.summary}</p>

                                {item.issues.length > 0 && (
                                    <ul>
                                        {item.issues.map(issue => (
                                            <li key={issue}>{issue}</li>
                                        ))}
                                    </ul>
                                )}
                            </details>
                        ))}
                    </>
                )}

                <p className="subtle-note">
                    Raw-price display remains restricted pending source rights.
                    Not investment advice. No buy/sell recommendations.
                </p>
            </section>
        </>
    );
}