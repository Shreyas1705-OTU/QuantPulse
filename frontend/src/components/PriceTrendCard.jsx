import { ResponsiveContainer, LineChart, Line, YAxis } from "recharts";

import StatusBadge from "./StatusBadge";

// Change is computed over whatever window of ticks was fetched (see
// getSymbolTicks in quantpulseService.js), not a real session-open price --
// there's no market-hours-aware "open" tracked yet. Close enough for an
// at-a-glance trend indicator; a real "day change" is future work.
function computeChange(ticks) {
    if (ticks.length < 2) return null;
    const first = ticks[0].price;
    const last = ticks[ticks.length - 1].price;
    if (first === 0) return null;
    return ((last - first) / first) * 100;
}

export default function PriceTrendCard({ symbol, ticks }) {
    const hasData = ticks.length > 0;
    const rawChange = computeChange(ticks);
    // Round first, then re-derive sign/color from the ROUNDED value -- a
    // tiny negative change that rounds to 0.00 would otherwise still
    // carry a "-" from toFixed (e.g. (-0.0001).toFixed(2) === "-0.00"),
    // displaying as the confusing "-0.00%". Number(...) collapses that
    // back to a clean -0, and -0's own toFixed drops the sign.
    const change = rawChange === null ? null : Number(rawChange.toFixed(2));
    // change > 0 / < 0 rather than >= 0, so a value that rounds to exactly
    // zero reads as flat (gray, no sign) instead of a misleading "+0.00%".
    const trend = change === null || change === 0 ? "flat" : change > 0 ? "up" : "down";
    const lineColor = trend === "up" ? "#8FAE74" : trend === "down" ? "#C24A38" : "#6F6559";

    return (
        <div className="bg-surface-raised rounded-2xl p-3.5">

            <div className="flex justify-between items-start mb-2">

                <div>
                    <div className="font-bold text-sm text-ink">
                        {symbol.ticker}
                    </div>
                    <div className="text-[10.5px] text-faint mt-0.5">
                        {symbol.asset_type}
                    </div>
                </div>

                <StatusBadge symbol={symbol} />

            </div>

            {hasData ? (

                <>
                    <div className="h-[34px] -mx-1">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={ticks} margin={{ top: 2, right: 4, bottom: 2, left: 4 }}>
                                {/* recharts defaults an unspecified YAxis to
                                    domain [0, auto] -- every price plots
                                    against a scale starting at zero, so a
                                    real $1-2 move on a ~$300 stock is
                                    invisible (it's <1% of the plotted
                                    range). Fitting the domain tightly to
                                    the actual min/max is what makes small,
                                    real moves show up at all. */}
                                <YAxis domain={["dataMin", "dataMax"]} hide />
                                <Line
                                    type="monotone"
                                    dataKey="price"
                                    stroke={lineColor}
                                    strokeWidth={2}
                                    dot={false}
                                    isAnimationActive={false}
                                />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>

                    <div className="flex justify-between items-baseline mt-2">
                        <span className="font-display text-base font-bold text-ink">
                            {ticks[ticks.length - 1].price.toLocaleString(undefined, { maximumFractionDigits: 5 })}
                        </span>
                        {change !== null && (
                            <span
                                className="text-[11px] font-semibold"
                                style={{ color: lineColor }}
                            >
                                {trend === "up" ? "+" : ""}{change.toFixed(2)}%
                            </span>
                        )}
                    </div>
                </>

            ) : (

                <div className="h-[34px] flex items-center">
                    <span className="text-xs text-faint">No data yet</span>
                </div>

            )}

        </div>
    );
}
