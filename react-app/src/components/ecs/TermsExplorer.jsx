import React, { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import { AlertCircle, ChartNoAxesColumn, ChartScatter, ExternalLink, Loader2, Table2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { makeBfileLink } from "@/lib/ecs";

const bfileCache = new Map();
const PLOT_WIDTH = 640;
const PLOT_HEIGHT = 300;
const PLOT_LEFT = 58;
const PLOT_RIGHT = 624;
const PLOT_TOP = 18;
const PLOT_BOTTOM = 268;
const TABLE_MAX_INDEX = 50;
const PLOT_MAX_INDEX = 100;

TermsExplorer.propTypes = {
  structure: PropTypes.object.isRequired,
};

export function TermsExplorer({ structure }) {
  const [display, setDisplay] = useState("table");
  const [state, setState] = useState({ status: "loading", terms: [], error: "" });

  useEffect(() => {
    const url = makeBfileLink(structure.id);
    const cached = bfileCache.get(url);
    if (cached) {
      setState({ status: "ready", terms: cached, error: "" });
      return undefined;
    }

    const controller = new AbortController();
    setState({ status: "loading", terms: [], error: "" });
    fetch(url, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.text();
      })
      .then((text) => {
        const terms = parseBfile(text);
        bfileCache.set(url, terms);
        setState({ status: "ready", terms, error: "" });
      })
      .catch((error) => {
        if (error.name === "AbortError") return;
        setState({ status: "error", terms: [], error: error.message });
      });
    return () => controller.abort();
  }, [structure.id]);

  const tableTerms = useMemo(() => state.terms.slice(0, TABLE_MAX_INDEX + 1), [state.terms]);
  const plotTerms = useMemo(() => state.terms.slice(0, PLOT_MAX_INDEX + 1), [state.terms]);
  const plot = useMemo(() => analyzeTerms(plotTerms), [plotTerms]);

  return (
    <Card className="shadow-sm">
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle className="text-lg">Sequence terms</CardTitle>
          {state.status === "ready" && (
            <Badge variant="secondary">{state.terms.length.toLocaleString()} terms</Badge>
          )}
        </div>
        <p className="text-sm text-slate-600">
          #{structure.id}: {structure.name}
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-3 gap-2" aria-label="Term display">
          <ViewButton active={display === "table"} onClick={() => setDisplay("table")} icon={Table2}>
            Table
          </ViewButton>
          <ViewButton active={display === "pin"} onClick={() => setDisplay("pin")} icon={ChartNoAxesColumn}>
            Pin plot
          </ViewButton>
          <ViewButton active={display === "scatter"} onClick={() => setDisplay("scatter")} icon={ChartScatter}>
            Scatter
          </ViewButton>
        </div>

        {state.status === "loading" && (
          <div className="flex items-center justify-center py-12 text-sm text-slate-600">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading b-file…
          </div>
        )}
        {state.status === "error" && (
          <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>Could not load the b-file: {state.error}</span>
          </div>
        )}
        {state.status === "ready" && display === "table" && (
          <TermsTable terms={tableTerms} totalTerms={state.terms.length} />
        )}
        {state.status === "ready" && display !== "table" && (
          <SequencePlot
            terms={plotTerms}
            totalTerms={state.terms.length}
            analysis={plot}
            mode={display}
          />
        )}

        <a
          href={makeBfileLink(structure.id)}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 text-sm underline"
        >
          Open b{String(structure.id).padStart(6, "0")}.txt
          <ExternalLink className="h-3.5 w-3.5" />
        </a>
      </CardContent>
    </Card>
  );
}

ViewButton.propTypes = {
  active: PropTypes.bool.isRequired,
  children: PropTypes.string.isRequired,
  icon: PropTypes.elementType.isRequired,
  onClick: PropTypes.func.isRequired,
};

function ViewButton({ active, children, icon: Icon, onClick }) {
  return (
    <Button
      type="button"
      size="sm"
      variant={active ? "secondary" : "outline"}
      aria-label={children}
      aria-pressed={active}
      onClick={onClick}
      className="px-2"
    >
      <Icon className="h-4 w-4" />
      <span className="hidden sm:inline">{children}</span>
    </Button>
  );
}

TermsTable.propTypes = {
  terms: PropTypes.array.isRequired,
  totalTerms: PropTypes.number.isRequired,
};

function TermsTable({ terms, totalTerms }) {
  return (
    <div className="space-y-2">
      <p className="text-xs text-slate-500">
        Showing a({terms.at(0)?.index ?? 0})–a({terms.at(-1)?.index ?? 0}), {terms.length.toLocaleString()} of{" "}
        {totalTerms.toLocaleString()} terms.
      </p>
      <div className="overflow-auto rounded-lg border">
        <table className="w-full table-fixed text-left text-sm">
          <thead className="bg-slate-100 text-xs uppercase tracking-wide text-slate-600">
            <tr>
              <th className="w-16 px-3 py-1.5 font-medium">n</th>
              <th className="px-3 py-1.5 font-medium">a(n)</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {terms.map((term) => (
              <tr key={term.index} className="align-top odd:bg-slate-50/60">
                <td className="px-3 py-1 font-mono text-xs leading-4 text-slate-500">{term.index}</td>
                <td className="break-all px-3 py-1 font-mono text-xs leading-4">{term.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

SequencePlot.propTypes = {
  analysis: PropTypes.object.isRequired,
  mode: PropTypes.oneOf(["pin", "scatter"]).isRequired,
  terms: PropTypes.array.isRequired,
  totalTerms: PropTypes.number.isRequired,
};

function SequencePlot({ analysis, mode, terms, totalTerms }) {
  const logarithmic = mode === "scatter" && analysis.useLogarithmicScale;
  const label = mode === "pin" ? "Pin plot" : "Scatter plot";
  const plotted = terms.map((term, position) => ({
    ...term,
    x: xCoordinate(position, terms.length),
    y: yCoordinate(analysis.logs[position], analysis, logarithmic),
  }));

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-600">
        <span>
          {label} of the first {terms.length.toLocaleString()} of {totalTerms.toLocaleString()} terms
          (n = 0…{terms.at(-1)?.index ?? 0})
        </span>
        {logarithmic && <Badge variant="outline">logarithmic y-axis</Badge>}
      </div>
      <div className="overflow-hidden rounded-lg border bg-white p-2">
        <svg
          viewBox={`0 0 ${PLOT_WIDTH} ${PLOT_HEIGHT}`}
          className="h-auto w-full"
          role="img"
          aria-label={`${label} for ${terms.length} sequence terms${logarithmic ? " with a logarithmic y-axis" : ""}`}
        >
          <PlotAxes analysis={analysis} logarithmic={logarithmic} lastIndex={terms.at(-1)?.index ?? 0} />
          {mode === "pin" &&
            plotted.map((point) => (
              <g key={point.index}>
                <line
                  x1={point.x}
                  x2={point.x}
                  y1={PLOT_BOTTOM}
                  y2={point.y}
                  stroke="currentColor"
                  className="text-slate-400"
                  strokeWidth="0.7"
                />
                <circle cx={point.x} cy={point.y} r="1.2" className="fill-slate-800" />
              </g>
            ))}
          {mode === "scatter" &&
            plotted.map((point) => (
              <circle key={point.index} cx={point.x} cy={point.y} r="1.7" className="fill-sky-700">
                <title>{`a(${point.index}) = ${point.value}`}</title>
              </circle>
            ))}
        </svg>
      </div>
      {logarithmic && analysis.hasZero && (
        <p className="text-xs text-slate-500">Zero terms are shown on the baseline.</p>
      )}
    </div>
  );
}

PlotAxes.propTypes = {
  analysis: PropTypes.object.isRequired,
  lastIndex: PropTypes.number.isRequired,
  logarithmic: PropTypes.bool.isRequired,
};

function PlotAxes({ analysis, lastIndex, logarithmic }) {
  const topLabel = logarithmic
    ? powerOfTenLabel(analysis.maxLog)
    : compactDecimal(analysis.maxValue);
  const bottomLabel = logarithmic && !analysis.hasZero ? powerOfTenLabel(analysis.minLog) : "0";
  return (
    <>
      {[0, 0.25, 0.5, 0.75, 1].map((fraction) => {
        const y = PLOT_TOP + fraction * (PLOT_BOTTOM - PLOT_TOP);
        return (
          <line
            key={fraction}
            x1={PLOT_LEFT}
            x2={PLOT_RIGHT}
            y1={y}
            y2={y}
            stroke="currentColor"
            className="text-slate-200"
            strokeWidth="1"
          />
        );
      })}
      <line x1={PLOT_LEFT} x2={PLOT_LEFT} y1={PLOT_TOP} y2={PLOT_BOTTOM} className="stroke-slate-500" />
      <line x1={PLOT_LEFT} x2={PLOT_RIGHT} y1={PLOT_BOTTOM} y2={PLOT_BOTTOM} className="stroke-slate-500" />
      <text x={PLOT_LEFT - 7} y={PLOT_TOP + 4} textAnchor="end" className="fill-slate-500 text-[10px]">
        {topLabel}
      </text>
      <text x={PLOT_LEFT - 7} y={PLOT_BOTTOM + 4} textAnchor="end" className="fill-slate-500 text-[10px]">
        {bottomLabel}
      </text>
      <text x={PLOT_LEFT} y={PLOT_BOTTOM + 18} textAnchor="middle" className="fill-slate-500 text-[10px]">
        0
      </text>
      <text x={PLOT_RIGHT} y={PLOT_BOTTOM + 18} textAnchor="middle" className="fill-slate-500 text-[10px]">
        {lastIndex}
      </text>
      <text x={(PLOT_LEFT + PLOT_RIGHT) / 2} y={PLOT_HEIGHT - 2} textAnchor="middle" className="fill-slate-500 text-[10px]">
        n
      </text>
    </>
  );
}

export function parseBfile(text) {
  return text
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => {
      const separator = line.indexOf(" ");
      if (separator === -1) throw new Error("Invalid b-file row");
      return {
        index: Number(line.slice(0, separator)),
        value: line.slice(separator + 1).trim(),
      };
    });
}

function analyzeTerms(terms) {
  const logs = terms.map((term) => decimalLog10(term.value));
  const positiveLogs = logs.filter((value) => value !== null);
  const maxLog = positiveLogs.length ? Math.max(...positiveLogs) : 0;
  const minLog = positiveLogs.length ? Math.min(...positiveLogs) : 0;
  let maxValue = "0";
  for (const term of terms) {
    if (compareNonnegativeDecimals(term.value, maxValue) > 0) maxValue = term.value;
  }
  return {
    logs,
    maxLog,
    minLog,
    maxValue,
    hasZero: logs.some((value) => value === null),
    useLogarithmicScale: maxLog >= 12 || maxLog - minLog >= 6,
  };
}

function decimalLog10(value) {
  const digits = value.replace(/^[+-]/, "").replace(/^0+/, "");
  if (!digits) return null;
  const leading = digits.slice(0, 15);
  const mantissa = Number(leading) / 10 ** (leading.length - 1);
  return digits.length - 1 + Math.log10(mantissa);
}

function compareNonnegativeDecimals(left, right) {
  const normalizedLeft = left.replace(/^\+/, "").replace(/^0+(?=\d)/, "");
  const normalizedRight = right.replace(/^\+/, "").replace(/^0+(?=\d)/, "");
  if (normalizedLeft.length !== normalizedRight.length) {
    return normalizedLeft.length - normalizedRight.length;
  }
  return normalizedLeft.localeCompare(normalizedRight);
}

function xCoordinate(position, count) {
  if (count <= 1) return PLOT_LEFT;
  return PLOT_LEFT + (position / (count - 1)) * (PLOT_RIGHT - PLOT_LEFT);
}

function yCoordinate(logarithm, analysis, logarithmic) {
  if (logarithm === null) return PLOT_BOTTOM;
  let ratio;
  if (logarithmic) {
    const range = analysis.maxLog - analysis.minLog;
    ratio = range ? (logarithm - analysis.minLog) / range : 1;
  } else {
    ratio = 10 ** Math.max(-324, logarithm - analysis.maxLog);
  }
  return PLOT_BOTTOM - ratio * (PLOT_BOTTOM - PLOT_TOP);
}

function powerOfTenLabel(logarithm) {
  return `10^${Math.floor(logarithm)}`;
}

function compactDecimal(value) {
  const digits = value.replace(/^\+/, "").replace(/^0+(?=\d)/, "");
  if (digits.length <= 8) return digits;
  return `${digits.slice(0, 4)}e${digits.length - 1}`;
}
