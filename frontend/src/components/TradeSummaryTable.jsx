import StatusBadge from "./StatusBadge";

// Same window of ticks Price Trends already fetches per symbol (see
// getSymbolTicks in quantpulseService.js) -- this table is just a denser,
// scannable read of the same data: one row per symbol instead of one
// mini-chart, with high/low/volume rolled up across the window too.
function computeStats(ticks) {
    if (ticks.length === 0) return null;

    const prices = ticks.map((t) => t.price);
    const first = prices[0];
    const last = prices[prices.length - 1];

    // Round first, then re-derive sign/trend from the ROUNDED value -- see
    // PriceTrendCard's computeChange for why (a tiny negative change that
    // rounds to 0.00 must read as flat, not "-0.00%").
    const rawChange = first === 0 ? null : ((last - first) / first) * 100;
    const change = rawChange === null ? null : Number(rawChange.toFixed(2));

    return {
        price: last,
        change,
        high: Math.max(...prices),
        low: Math.min(...prices),
        volume: ticks.reduce((sum, t) => sum + (t.volume || 0), 0),
        lastTradeAt: ticks[ticks.length - 1].traded_at,
    };
}

function fmt(n) {
    return n.toLocaleString(undefined, { maximumFractionDigits: 5 });
}

export default function TradeSummaryTable({ symbols, priceTrends }) {
    return (
        <div className="overflow-x-auto">

            <table className="w-full text-sm">

                <thead>
                    <tr className="text-left text-faint text-xs uppercase tracking-wide">
                        <th className="pb-3 font-medium">Symbol</th>
                        <th className="pb-3 font-medium">Status</th>
                        <th className="pb-3 font-medium text-right">Price</th>
                        <th className="pb-3 font-medium text-right">Change</th>
                        <th className="pb-3 font-medium text-right">High</th>
                        <th className="pb-3 font-medium text-right">Low</th>
                        <th className="pb-3 font-medium text-right">Volume</th>
                        <th className="pb-3 font-medium text-right">Last Trade</th>
                    </tr>
                </thead>

                <tbody>

                    {symbols.map((symbol) => {
                        const stats = computeStats(priceTrends[symbol.id] || []);
                        const trend =
                            !stats || stats.change === null || stats.change === 0
                                ? "flat"
                                : stats.change > 0
                                ? "up"
                                : "down";
                        const changeColor =
                            trend === "up"
                                ? "text-good"
                                : trend === "down"
                                ? "text-bad"
                                : "text-faint";

                        return (
                            <tr
                                key={symbol.id}
                                className="border-t border-surface-raised"
                            >
                                <td className="py-3">
                                    <div className="font-semibold text-ink">
                                        {symbol.ticker}
                                    </div>
                                    <div className="text-[10.5px] text-faint">
                                        {symbol.asset_type}
                                    </div>
                                </td>

                                <td className="py-3">
                                    <StatusBadge symbol={symbol} />
                                </td>

                                {stats ? (
                                    <>
                                        <td className="py-3 text-right font-display font-semibold text-ink">
                                            {fmt(stats.price)}
                                        </td>
                                        <td className={`py-3 text-right font-semibold ${changeColor}`}>
                                            {stats.change === null
                                                ? "--"
                                                : `${trend === "up" ? "+" : ""}${stats.change.toFixed(2)}%`}
                                        </td>
                                        <td className="py-3 text-right text-muted">
                                            {fmt(stats.high)}
                                        </td>
                                        <td className="py-3 text-right text-muted">
                                            {fmt(stats.low)}
                                        </td>
                                        <td className="py-3 text-right text-muted">
                                            {fmt(stats.volume)}
                                        </td>
                                        <td className="py-3 text-right text-faint text-xs">
                                            {new Date(stats.lastTradeAt).toLocaleTimeString()}
                                        </td>
                                    </>
                                ) : (
                                    <td colSpan={6} className="py-3 text-right text-faint text-xs">
                                        No ticks yet
                                    </td>
                                )}

                            </tr>
                        );
                    })}

                </tbody>

            </table>

        </div>
    );
}
