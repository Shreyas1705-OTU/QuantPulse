import { ResponsiveContainer, LineChart, Line } from "recharts";
import { CheckCircle, XCircle, Clock } from "lucide-react";

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

                {!symbol.is_active ? (
                    <span className="flex items-center gap-1 text-[10px] font-semibold text-faint bg-canvas px-2 py-0.5 rounded-full">
                        <XCircle size={10} />
                        Inactive
                    </span>
                ) : symbol.is_market_open ? (
                    <span className="flex items-center gap-1 text-[10px] font-semibold text-accent bg-accent-soft px-2 py-0.5 rounded-full">
                        <CheckCircle size={10} />
                        Live
                    </span>
                ) : (
                    <span className="flex items-center gap-1 text-[10px] font-semibold text-warn bg-warn-soft px-2 py-0.5 rounded-full">
                        <Clock size={10} />
                        Closed
                    </span>
                )}

            </div>

            {hasData ? (

                <>
                    <div className="h-[34px] -mx-1">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={ticks} margin={{ top: 2, right: 4, bottom: 2, left: 4 }}>
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
