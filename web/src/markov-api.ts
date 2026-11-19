/** Runtime-checked contracts for the saved-model API. */

const base = (import.meta.env.VITE_API_BASE_URL || '')
  .replace(/\/$/, '');

const obj = (
  value: unknown,
): value is Record<string, unknown> =>
  !!value &&
  typeof value === 'object' &&
  !Array.isArray(value);

const num = (value: unknown): value is number =>
  typeof value === 'number' && Number.isFinite(value);

const str = (value: unknown): value is string =>
  typeof value === 'string';

const date = (value: unknown): value is string =>
  str(value) &&
  /^\d{4}-\d{2}-\d{2}$/.test(value) &&
  !Number.isNaN(Date.parse(value)) &&
  new Date(value).toISOString().slice(0, 10) === value;

const strings = (value: unknown): value is string[] =>
  Array.isArray(value) && value.every(str);

const probability = (value: unknown): value is number =>
  num(value) && value >= 0 && value <= 1;

export type StateView = 'filtered' | 'smoothed' | 'viterbi';

export interface StateData {
  trained_through?: string;
  scope?: string;
  asset: string;
  view: StateView;
  retrospective: boolean;
  model_version: string;
  rows: {
    session_date: string;
    value: number[] | number;
  }[];
}

export interface TransitionData {
  asset: string;
  model_version: string;
  matrix: number[][];
  expected_dwell_sessions: (number | null)[];
  notice: string;
}

export interface SourceStatus {
  asset: string;
  available: boolean;
  status: string;
  last_session?: string;
  rows?: number;
  snapshot_hashes?: string[];
}

export interface StatusData {
  assets: SourceStatus[];
  g0_passed: boolean;
  notice: string;
}

export interface Run {
  id: string;
  asset: string;
  status: string;
}

export interface Metric {
  n: number;
  events: number;
  base_rate: number;
  brier: number;
  log_loss: number;
  pr_auc: number | null;
  balanced_accuracy: number | null;
  macro_f1: number | null;
  brier_skill?: number;
}

export interface Experiment {
  asset: string;
  status: string;
  metrics: Record<string, Metric>;
  price_metrics: Record<string, {
    mae: number;
    rmse: number;
  }>;
  failed_models: Record<string, string>;
  hmm_runs: {
    states: number;
    seed: number;
    converged?: boolean;
    trace?: number[];
    error?: string;
  }[];
  calibration: string;
  caveat: string;
  final_test_evaluated: boolean;
  model_version: string;
  research_track: string;
  evaluation: {
    train_end: string;
    validation_start: string;
    validation_end: string;
    threshold: number;
  };
  reliability: {
    model: string;
    bin: number;
    n: number;
    mean_probability: number | null;
    event_rate: number | null;
  }[];
  uncertainty: {
    model: string;
    estimate: number;
    low_95: number;
    high_95: number;
    limitation: string;
  }[];
}

export interface Forecast {
  asset: string;
  as_of_session: string;
  target_session: string;
  target_definition: string;
  model_version: string;
  data_freshness: string;
  warnings: string[];
  probability?: number;
  threshold?: number;
  predicted_close?: number;
  price_basis?: string;
  research_track?: string;
}

export interface Evidence {
  items: {
    kind: string;
    status: string;
    summary: string;
    issues: string[];
  }[];
  notice: string;
}

export interface HistoricalRiskRow {
  origin_session: string;
  target_session: string;
  actual_event: 0 | 1;
  probabilities: Record<string, number>;
}

export interface HistoricalRiskData {
  asset: string;
  run_id: string;
  model_version: string;
  evaluation: {
    train_end: string;
    validation_start: string;
    validation_end: string;
    threshold: number;
  };
  evaluation_kind:
  | 'development_validation'
  | 'locked_historical_test';
  target_definition: string;
  notice: string;
  models: string[];
  decision_thresholds: Record<string, number>;
  rows: HistoricalRiskRow[];
}

async function checked<T>(
  path: string,
  guard: (value: unknown) => boolean,
  signal: AbortSignal,
  body?: unknown,
): Promise<T> {
  const response = await fetch(base + path, {
    method: body ? 'POST' : 'GET',
    headers: body
      ? { 'Content-Type': 'application/json' }
      : undefined,
    body: body ? JSON.stringify(body) : undefined,
    signal,
    cache: 'no-store',
  });

  let value: unknown;

  try {
    value = await response.json();
  } catch {
    throw Error('The API returned an unreadable response.');
  }

  if (!response.ok) {
    throw Error(
      obj(value) && str(value.detail)
        ? value.detail
        : `Request failed (${response.status}).`,
    );
  }

  if (!guard(value)) {
    throw Error(
      'Saved evidence failed response validation. No values were loaded.',
    );
  }

  return value as T;
}

export const labAsset = (symbol: string) =>
  symbol === '^NSEI'
    ? 'NIFTY 50'
    : symbol.replace(/\.NS$/, '');

export const labStatus = (signal: AbortSignal) =>
  checked<StatusData>(
    '/v1/data/status',
    value =>
      obj(value) &&
      typeof value.g0_passed === 'boolean' &&
      str(value.notice) &&
      Array.isArray(value.assets) &&
      value.assets.every(
        asset =>
          obj(asset) &&
          str(asset.asset) &&
          typeof asset.available === 'boolean' &&
          str(asset.status) &&
          (
            !asset.available ||
            (
              date(asset.last_session) &&
              num(asset.rows) &&
              asset.rows > 0
            )
          ),
      ),
    signal,
  );

export const labRuns = (signal: AbortSignal) =>
  checked<{ experiments: Run[] }>(
    '/v1/experiments',
    value =>
      obj(value) &&
      Array.isArray(value.experiments) &&
      value.experiments.every(
        run =>
          obj(run) &&
          str(run.id) &&
          str(run.asset) &&
          str(run.status),
      ),
    signal,
  );

export const labEvidence = (signal: AbortSignal) =>
  checked<Evidence>(
    '/v1/data/evidence',
    value =>
      obj(value) &&
      str(value.notice) &&
      Array.isArray(value.items) &&
      value.items.every(
        item =>
          obj(item) &&
          str(item.kind) &&
          str(item.status) &&
          str(item.summary) &&
          strings(item.issues),
      ),
    signal,
  );

export const labStates = (
  asset: string,
  view: StateView,
  signal: AbortSignal,
) =>
  checked<StateData>(
    `/v1/assets/${encodeURIComponent(asset)}/states?view=${view}`,
    value =>
      obj(value) &&
      value.asset === asset &&
      value.view === view &&
      value.retrospective === (view !== 'filtered') &&
      str(value.model_version) &&
      Array.isArray(value.rows) &&
      value.rows.length > 0 &&
      value.rows.every(
        row =>
          obj(row) &&
          date(row.session_date) &&
          (
            view === 'viterbi'
              ? (
                num(row.value) &&
                Number.isInteger(row.value) &&
                row.value >= 0
              )
              : (
                Array.isArray(row.value) &&
                row.value.length >= 2 &&
                row.value.every(probability) &&
                Math.abs(
                  row.value.reduce(
                    (sum: number, p: number) => sum + p,
                    0,
                  ) - 1,
                ) < 1e-6
              )
          ),
      ),
    signal,
  );

export const labTransitions = (
  asset: string,
  signal: AbortSignal,
) =>
  checked<TransitionData>(
    `/v1/assets/${encodeURIComponent(asset)}/transitions`,
    value =>
      obj(value) &&
      value.asset === asset &&
      str(value.model_version) &&
      str(value.notice) &&
      Array.isArray(value.matrix) &&
      value.matrix.length >= 2 &&
      value.matrix.every(
        (row: unknown) =>
          Array.isArray(row) &&
          row.length === (value.matrix as unknown[]).length &&
          row.every(probability) &&
          Math.abs(
            row.reduce(
              (sum: number, p: number) => sum + p,
              0,
            ) - 1,
          ) < 1e-6,
      ) &&
      Array.isArray(value.expected_dwell_sessions) &&
      value.expected_dwell_sessions.length === value.matrix.length &&
      value.expected_dwell_sessions.every(
        item => item === null || (num(item) && item >= 1),
      ),
    signal,
  );

export const labExperiment = (
  id: string,
  asset: string,
  signal: AbortSignal,
) =>
  checked<Experiment>(
    `/v1/experiments/${encodeURIComponent(id)}`,
    value =>
      obj(value) &&
      value.asset === asset &&
      str(value.status) &&
      str(value.caveat) &&
      str(value.calibration) &&
      typeof value.final_test_evaluated === 'boolean' &&
      str(value.model_version) &&
      str(value.research_track) &&
      obj(value.evaluation) &&
      date(value.evaluation.train_end) &&
      date(value.evaluation.validation_start) &&
      date(value.evaluation.validation_end) &&
      num(value.evaluation.threshold) &&
      Array.isArray(value.reliability) &&
      value.reliability.every(
        row =>
          obj(row) &&
          str(row.model) &&
          num(row.bin) &&
          num(row.n) &&
          (
            row.mean_probability === null ||
            probability(row.mean_probability)
          ) &&
          (
            row.event_rate === null ||
            probability(row.event_rate)
          ),
      ) &&
      Array.isArray(value.uncertainty) &&
      value.uncertainty.every(
        row =>
          obj(row) &&
          str(row.model) &&
          num(row.estimate) &&
          num(row.low_95) &&
          num(row.high_95) &&
          str(row.limitation),
      ) &&
      obj(value.metrics) &&
      Object.values(value.metrics).every(
        metric =>
          obj(metric) &&
          ['n', 'events', 'base_rate', 'brier', 'log_loss'].every(
            key => num(metric[key]),
          ) &&
          ['pr_auc', 'balanced_accuracy', 'macro_f1'].every(
            key => metric[key] === null || num(metric[key]),
          ),
      ) &&
      obj(value.price_metrics) &&
      Object.values(value.price_metrics).every(
        metric =>
          obj(metric) &&
          num(metric.mae) &&
          num(metric.rmse),
      ) &&
      obj(value.failed_models) &&
      Object.values(value.failed_models).every(str) &&
      Array.isArray(value.hmm_runs) &&
      value.hmm_runs.every(
        run =>
          obj(run) &&
          num(run.states) &&
          num(run.seed) &&
          (
            run.trace === undefined ||
            (
              Array.isArray(run.trace) &&
              run.trace.every(num)
            )
          ),
      ),
    signal,
  );

export const labPredict = (
  asset: string,
  day: string,
  kind: 'large-move' | 'next-close',
  signal: AbortSignal,
) =>
  checked<Forecast>(
    `/v1/predict/${kind}`,
    value =>
      obj(value) &&
      value.asset === asset &&
      value.as_of_session === day &&
      date(value.target_session) &&
      value.target_session > day &&
      str(value.target_definition) &&
      str(value.model_version) &&
      str(value.data_freshness) &&
      strings(value.warnings) &&
      (
        kind === 'large-move'
          ? (
            probability(value.probability) &&
            num(value.threshold) &&
            value.threshold > 0
          )
          : (
            num(value.predicted_close) &&
            value.predicted_close > 0 &&
            str(value.price_basis)
          )
      ),
    signal,
    {
      asset,
      as_of_session: day,
    },
  );

function validHistoricalRisk(
  value: unknown,
  asset: string,
  id: string,
): boolean {
  if (
    !obj(value) ||
    value.asset !== asset ||
    value.run_id !== id ||
    !str(value.model_version) ||
    !str(value.target_definition) ||
    !str(value.notice)
  ) {
    return false;
  }

  if (
    ![
      'development_validation',
      'locked_historical_test',
    ].includes(String(value.evaluation_kind))
  ) {
    return false;
  }

  const evaluation = value.evaluation;

  if (
    !obj(evaluation) ||
    !date(evaluation.train_end) ||
    !date(evaluation.validation_start) ||
    !date(evaluation.validation_end) ||
    evaluation.validation_start > evaluation.validation_end ||
    !num(evaluation.threshold) ||
    evaluation.threshold <= 0
  ) {
    return false;
  }

  if (
    !strings(value.models) ||
    value.models.length < 2 ||
    new Set(value.models).size !== value.models.length ||
    !value.models.includes('HMM') ||
    !value.models.includes('Prevalence')
  ) {
    return false;
  }

  const models = value.models;
  const cutoffs = value.decision_thresholds;

  if (
    !obj(cutoffs) ||
    !models.every(model => probability(cutoffs[model]))
  ) {
    return false;
  }

  if (!Array.isArray(value.rows) || !value.rows.length) {
    return false;
  }

  let previous = '';

  for (const row of value.rows) {
    if (
      !obj(row) ||
      !date(row.origin_session) ||
      !date(row.target_session) ||
      row.origin_session >= row.target_session ||
      row.origin_session <= evaluation.train_end ||
      row.target_session <= previous ||
      row.target_session < evaluation.validation_start ||
      row.target_session > evaluation.validation_end ||
      ![0, 1].includes(Number(row.actual_event)) ||
      typeof row.actual_event !== 'number'
    ) {
      return false;
    }

    const probabilities = row.probabilities;

    if (
      !obj(probabilities) ||
      Object.keys(probabilities).length !== models.length ||
      !models.every(
        model => probability(probabilities[model]),
      )
    ) {
      return false;
    }

    previous = row.target_session;
  }

  return true;
}

export const labHistoricalRisk = (
  id: string,
  asset: string,
  signal: AbortSignal,
) =>
  checked<HistoricalRiskData>(
    `/v1/experiments/${encodeURIComponent(id)}/risk-predictions`,
    value => validHistoricalRisk(value, asset, id),
    signal,
  );

export async function labDownload(id: string): Promise<void> {
  const response = await fetch(
    `${base}/v1/experiments/${encodeURIComponent(id)}/predictions`,
    {
      signal: AbortSignal.timeout(15000),
      cache: 'no-store',
    },
  );

  if (
    !response.ok ||
    !response.headers
      .get('content-type')
      ?.startsWith('text/csv')
  ) {
    throw Error(
      'Verified saved predictions could not be downloaded.',
    );
  }

  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement('a');

  link.href = url;
  link.download = `${id}-predictions.csv`;
  link.click();

  setTimeout(() => URL.revokeObjectURL(url), 1000);
}