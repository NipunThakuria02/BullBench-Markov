import { useEffect, useState } from 'react';
import type { Asset } from './assets';
import { InteractiveChart } from './charts';
import { displayDate, percent } from './data';
import {
    labAsset,
    labHistoricalRisk,
    labDownload,
    type HistoricalRiskData,
    type Run,
} from './markov-api';

type Props = {
    asset: Asset;
    runId: string;
    runs: Run[];
    runError?: string;
    onRunChange: (id: string) => void;
};

const PAGE_SIZE = 25;

export function HistoricalRiskPredictions({
    asset,
    runId,
    runs,
    runError,
    onRunChange,
}: Props) {
    const [data, setData] = useState<HistoricalRiskData | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const [model, setModel] = useState('HMM');
    const [baseline, setBaseline] = useState('Prevalence');

    const [start, setStart] = useState('');
    const [end, setEnd] = useState('');
    const [selected, setSelected] = useState('');
    const [page, setPage] = useState(0);

    const instrument = labAsset(asset.symbol);

    useEffect(() => {
        const controller = new AbortController();

        setData(null);
        setError('');

        if (!runId) {
            setLoading(false);
            return () => controller.abort();
        }

        setLoading(true);

        labHistoricalRisk(runId, instrument, controller.signal)
            .then(value => {
                if (controller.signal.aborted) return;

                setData(value);
                setSelected(value.rows.at(-1)!.target_session);
            })
            .catch(e => {
                if (!controller.signal.aborted) {
                    setError((e as Error).message);
                }
            })
            .finally(() => {
                if (!controller.signal.aborted) {
                    setLoading(false);
                }
            });

        return () => controller.abort();
    }, [runId, instrument]);

    const invalidRange = !!start && !!end && start > end;

    const rows =
        data && !invalidRange
            ? data.rows.filter(
                row =>
                    (!start || row.target_session >= start) &&
                    (!end || row.target_session <= end),
            )
            : [];

    const selectedRow =
        rows.find(row => row.target_session === selected) ||
        rows.at(-1);

    const pageCount = Math.max(
        1,
        Math.ceil(rows.length / PAGE_SIZE),
    );

    const currentPage = Math.min(page, pageCount - 1);

    const visible = rows.slice(
        currentPage * PAGE_SIZE,
        (currentPage + 1) * PAGE_SIZE,
    );

    const cutoff = data?.decision_thresholds[model];

    const brier = rows.length
        ? rows.reduce(
            (sum, row) =>
                sum +
                (row.probabilities[model] - row.actual_event) ** 2,
            0,
        ) / rows.length
        : null;

    const baselineBrier = rows.length
        ? rows.reduce(
            (sum, row) =>
                sum +
                (row.probabilities[baseline] - row.actual_event) ** 2,
            0,
        ) / rows.length
        : null;

    const events = rows.reduce(
        (sum, row) => sum + row.actual_event,
        0,
    );

    async function download() {
        try {
            await labDownload(runId);
        } catch (e) {
            setError((e as Error).message);
        }
    }

    return (
        <>
            <div className="section-title">
                <div>
                    <h2>Historical risk predictions</h2>
                    <p>
                        Saved probabilities and the outcomes observed in later
                        sessions for {asset.short}.
                    </p>
                </div>

                <div className="filter-controls">
                    <label>
                        Evaluation period
                        <select
                            value={runId}
                            onChange={e => onRunChange(e.target.value)}
                        >
                            <option value="">Select an evaluation</option>

                            {runs.map(run => (
                                <option key={run.id} value={run.id}>
                                    {run.status === 'locked_historical_test'
                                        ? 'Historical Benchmark · 2026'
                                        : run.status === 'development_candidate'
                                            ? 'Development Validation · 2023'
                                            : run.id}
                                </option>
                            ))}
                        </select>
                    </label>
                </div>
            </div>

            <p className="subtle-note">
                Historical evaluation only. Predictions use an earlier fitted
                model; later observed outcomes are shown for comparison. This
                page does not generate a future forecast.
            </p>

            {loading && (
                <p role="status">Loading verified saved predictions…</p>
            )}

            {(error || runError) && (
                <div className="results-error" role="alert">
                    <strong>Unavailable</strong>
                    <p>{error || runError}</p>
                    <p>No replacement predictions generated.</p>
                </div>
            )}

            {!runId && !runError && (
                <p className="empty-message">
                    No evaluation is selected. Choose an instrument with a
                    saved run.
                </p>
            )}

            {data && (
                <>
                    <div className="lab-result-meta">
                        <span>
                            Trained through{' '}
                            <strong>
                                {displayDate(data.evaluation.train_end)}
                            </strong>
                        </span>

                        <span>
                            {data.evaluation_kind === 'locked_historical_test'
                                ? 'Historical test'
                                : 'Validation'}{' '}
                            targets{' '}
                            <strong>
                                {displayDate(data.evaluation.validation_start)}
                                {' – '}
                                {displayDate(data.evaluation.validation_end)}
                            </strong>
                        </span>

                        <span>
                            Large-move threshold |log return| &gt;{' '}
                            <strong>
                                {percent(data.evaluation.threshold)}
                            </strong>
                        </span>
                    </div>

                    <div
                        className="filter-controls lab-forecast-controls"
                        style={{
                            display: 'grid',
                            gridTemplateColumns:
                                'repeat(auto-fit, minmax(min(100%, 180px), 1fr))',
                        }}
                    >
                        <label>
                            Prediction model
                            <select
                                value={model}
                                onChange={e => setModel(e.target.value)}
                            >
                                {data.models.map(name => (
                                    <option key={name} value={name}>
                                        {name}
                                    </option>
                                ))}
                            </select>
                        </label>

                        <label>
                            Comparison model
                            <select
                                value={baseline}
                                onChange={e => setBaseline(e.target.value)}
                            >
                                {data.models.map(name => (
                                    <option key={name} value={name}>
                                        {name}
                                    </option>
                                ))}
                            </select>
                        </label>

                        <label>
                            From target session
                            <input
                                type="date"
                                value={start}
                                min={data.evaluation.validation_start}
                                max={data.evaluation.validation_end}
                                onChange={e => {
                                    setStart(e.target.value);
                                    setPage(0);
                                }}
                            />
                        </label>

                        <label>
                            To target session
                            <input
                                type="date"
                                value={end}
                                min={data.evaluation.validation_start}
                                max={data.evaluation.validation_end}
                                onChange={e => {
                                    setEnd(e.target.value);
                                    setPage(0);
                                }}
                            />
                        </label>

                        <button
                            className="outline-button"
                            onClick={() => {
                                setStart('');
                                setEnd('');
                                setPage(0);
                            }}
                        >
                            RESET DATES
                        </button>
                    </div>

                    {invalidRange && (
                        <p role="alert" className="subtle-note">
                            The start date must be on or before the end date.
                        </p>
                    )}

                    {!rows.length && !invalidRange && (
                        <p className="empty-message">
                            No saved predictions fall within this date range.
                        </p>
                    )}

                    {rows.length > 0 && (
                        <>
                            <div className="lab-results-summary">
                                <div>
                                    <span>Saved target sessions in selection</span>
                                    <strong>{rows.length}</strong>
                                    <small>
                                        {events} observed large-move events · base rate{' '}
                                        {percent(events / rows.length)}
                                    </small>
                                </div>

                                <div>
                                    <span>
                                        {model} Brier score · selected dates
                                    </span>
                                    <strong>{brier!.toFixed(4)}</strong>
                                    <small>
                                        Lower probability error is better.
                                    </small>
                                </div>

                                <div>
                                    <span>
                                        {baseline} Brier score · same dates
                                    </span>
                                    <strong>{baselineBrier!.toFixed(4)}</strong>
                                    <small>
                                        All displayed models use the same observed
                                        outcomes.
                                    </small>
                                </div>
                            </div>

                            <InteractiveChart
                                dates={rows.map(row => row.target_session)}
                                series={[
                                    {
                                        name: model,
                                        color: '#6355ff',
                                        values: rows.map(
                                            row => row.probabilities[model],
                                        ),
                                    },
                                    ...(model !== baseline
                                        ? [
                                            {
                                                name: baseline,
                                                color: '#168b65',
                                                values: rows.map(
                                                    row => row.probabilities[baseline],
                                                ),
                                                dashed: true,
                                            },
                                        ]
                                        : []),
                                ]}
                                symbol={asset.symbol}
                                returns
                                label={`${asset.short} saved large-move probabilities`}
                            />

                            <div className="model-legend">
                                <span>
                                    <i style={{ background: '#6355ff' }} />
                                    {model}
                                </span>

                                {model !== baseline && (
                                    <span>
                                        <i style={{ background: '#168b65' }} />
                                        {baseline}
                                    </span>
                                )}
                            </div>

                            <p className="subtle-note">
                                Chart values are probabilities of a large absolute
                                next-session move, not predicted returns or closing
                                prices.
                            </p>

                            <div className="filter-controls">
                                <label>
                                    Inspect target session
                                    <select
                                        value={selectedRow?.target_session || ''}
                                        onChange={e => setSelected(e.target.value)}
                                    >
                                        {rows.map(row => (
                                            <option
                                                key={row.target_session}
                                                value={row.target_session}
                                            >
                                                {displayDate(row.target_session)}
                                            </option>
                                        ))}
                                    </select>
                                </label>
                            </div>

                            {selectedRow && (
                                <div className="lab-results-summary">
                                    <div>
                                        <span>Prediction origin → target</span>
                                        <strong>
                                            {displayDate(selectedRow.target_session)}
                                        </strong>
                                        <small>
                                            Information through{' '}
                                            {displayDate(selectedRow.origin_session)}
                                        </small>
                                    </div>

                                    <div>
                                        <span>
                                            {model} predicted large-move probability
                                        </span>
                                        <strong>
                                            {percent(
                                                selectedRow.probabilities[model],
                                            )}
                                        </strong>
                                        <small>
                                            Saved decision cutoff: {percent(cutoff!)}
                                        </small>
                                    </div>

                                    <div>
                                        <span>Actual observed outcome</span>
                                        <strong>
                                            {selectedRow.actual_event
                                                ? 'Large move'
                                                : 'No large move'}
                                        </strong>
                                        <small>
                                            {model} classification:{' '}
                                            {selectedRow.probabilities[model] >= cutoff!
                                                ? 'Large move'
                                                : 'No large move'}
                                        </small>
                                    </div>
                                </div>
                            )}

                            <div className="table-scroll">
                                <table>
                                    <thead>
                                        <tr>
                                            <th>Prediction origin</th>
                                            <th>Target session</th>
                                            <th>{model} probability</th>
                                            <th>{baseline} probability</th>
                                            <th>Actual outcome</th>
                                            <th>{model} classification</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {visible.map(row => (
                                            <tr key={row.target_session}>
                                                <td>
                                                    {displayDate(row.origin_session)}
                                                </td>
                                                <td>
                                                    {displayDate(row.target_session)}
                                                </td>
                                                <td>
                                                    {percent(row.probabilities[model])}
                                                </td>
                                                <td>
                                                    {percent(row.probabilities[baseline])}
                                                </td>
                                                <td>
                                                    {row.actual_event
                                                        ? 'Large move'
                                                        : 'No large move'}
                                                </td>
                                                <td>
                                                    {row.probabilities[model] >= cutoff!
                                                        ? 'Large move'
                                                        : 'No large move'}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>

                            <div
                                className="filter-controls"
                                style={{ flexWrap: 'wrap' }}
                            >
                                <button
                                    className="outline-button"
                                    disabled={currentPage === 0}
                                    onClick={() => setPage(currentPage - 1)}
                                >
                                    PREVIOUS
                                </button>

                                <span>
                                    Page {currentPage + 1} of {pageCount}
                                </span>

                                <button
                                    className="outline-button"
                                    disabled={currentPage + 1 >= pageCount}
                                    onClick={() => setPage(currentPage + 1)}
                                >
                                    NEXT
                                </button>
                            </div>

                            <p className="subtle-note">
                                A probability is not a guaranteed outcome.
                                Classification uses the stored validation-selected
                                cutoff. Changing models or dates here does not
                                retrain a model or tune its cutoff.
                            </p>
                        </>
                    )}

                    <button
                        className="outline-button lab-results-export"
                        onClick={() => void download()}
                    >
                        EXPORT ALL SAVED PREDICTIONS
                    </button>

                    <p className="subtle-note">
                        Export includes the complete selected run across all
                        models and dates, including dates outside the current
                        display filter.
                    </p>

                    <details className="lab-details">
                        <summary>Research notes and model version</summary>
                        <p>{data.target_definition}</p>
                        <p>{data.notice}</p>
                        <p>Model version: {data.model_version}</p>
                        <p>
                            The historical period was inspected for the original
                            price task. These comparisons are exploratory, not
                            untouched, prospective or official-data certification.
                            The separately fitted latest state-exploration model
                            is not used to generate these historical predictions.
                        </p>
                    </details>
                </>
            )}
        </>
    );
}