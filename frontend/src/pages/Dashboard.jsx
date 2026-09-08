import { useEffect, useState } from "react";

import {
    TrendingUp,
    Bell,
    Database,
    Clock,
} from "lucide-react";

import Sidebar from "../components/Sidebar";
import Header from "../components/Header";
import MetricCard from "../components/MetricCard";
import SectionCard from "../components/SectionCard";
import PriceTrendCard from "../components/PriceTrendCard";

import {
    getSymbols,
    getTicks,
    getTicksCount,
    getSymbolTicks,
    getAlerts,
    getAlertsCount,
    getTodaySummary,
} from "../services/quantpulseService";

export default function Dashboard() {

    const [symbols, setSymbols] = useState([]);
    const [ticks, setTicks] = useState([]);
    const [ticksTotal, setTicksTotal] = useState(0);
    const [priceTrends, setPriceTrends] = useState({});
    const [alerts, setAlerts] = useState([]);
    const [alertsTotal, setAlertsTotal] = useState(0);
    const [summary, setSummary] = useState(null);

    useEffect(() => {

        loadData();

        const interval = setInterval(loadData, 5000);

        return () => clearInterval(interval);

    }, []);

    async function loadData() {

        try {

            // getTicks/getAlerts return a capped, latest-first slice (for
            // the tables below) -- the counts come from their own /count
            // endpoints so the metric tiles reflect the real totals
            // without ever fetching the whole (ever-growing) table.
            const [
                symbolData,
                tickData,
                ticksCount,
                alertData,
                alertsCount,
                summaryData,
            ] = await Promise.all([
                getSymbols(),
                getTicks(),
                getTicksCount(),
                getAlerts(),
                getAlertsCount(),
                getTodaySummary(),
            ]);

            const symbolsArr = Array.isArray(symbolData) ? symbolData : [];

            setSymbols(symbolsArr);
            setTicks(Array.isArray(tickData) ? tickData : []);
            setTicksTotal(ticksCount);
            setAlerts(Array.isArray(alertData) ? alertData : []);
            setAlertsTotal(alertsCount);
            setSummary(summaryData);

            // Each symbol's own recent tick history, for its Price Trends
            // card -- a symbol with no real ticks yet (e.g. an equity
            // before this session's first Finnhub trade) just gets an
            // empty array, which PriceTrendCard renders as "No data yet"
            // rather than a fabricated chart.
            const trendResults = await Promise.all(
                symbolsArr.map((s) => getSymbolTicks(s.id, 30).catch(() => []))
            );

            const trendsBySymbol = {};
            symbolsArr.forEach((s, i) => {
                // API returns newest-first; a chart reads left-to-right
                // chronologically.
                trendsBySymbol[s.id] = trendResults[i].slice().reverse();
            });
            setPriceTrends(trendsBySymbol);

        }

        catch (err) {

            console.error(err);

        }

    }

    function tickerFor(symbolId) {
        const match = symbols.find((s) => s.id === symbolId);
        return match ? match.ticker : `#${symbolId}`;
    }

    // NYSE hours apply uniformly to every equity, so if any one of them
    // is closed right now, they all are -- one banner covers the whole
    // asset class rather than repeating it per symbol.
    const equitiesClosed = symbols.some(
        (s) => s.asset_type === "equity" && !s.is_market_open
    );

    return (

        <div className="flex bg-canvas min-h-screen">

            <Sidebar />

            <div className="flex-1">

                <Header />

                <div className="p-8">

                    {equitiesClosed && (

                        <div className="flex items-center gap-3 bg-warn-soft border border-line rounded-2xl px-6 py-4 mb-8">

                            <Clock size={18} className="text-warn shrink-0" />

                            <p className="text-warn text-sm">
                                US equity markets are currently closed.
                                Equity prices below are from the last
                                session. Forex and crypto continue trading.
                            </p>

                        </div>

                    )}

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-8">

                        <MetricCard
                            title="Symbols Tracked"
                            value={symbols.length}
                            unit=""
                            icon={<TrendingUp className="text-accent" size={20} />}
                        />

                        <MetricCard
                            title="Ticks Ingested"
                            value={ticksTotal}
                            unit=""
                            icon={<Database className="text-accent" size={20} />}
                        />

                        <MetricCard
                            title="Alerts"
                            value={alertsTotal}
                            unit=""
                            icon={<Bell className="text-accent" size={20} />}
                        />

                    </div>

                    <div className="mb-8">

                        <SectionCard title="Price Trends">

                            <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-3.5">

                                {symbols.map((symbol) => (

                                    <PriceTrendCard
                                        key={symbol.id}
                                        symbol={symbol}
                                        ticks={priceTrends[symbol.id] || []}
                                    />

                                ))}

                            </div>

                        </SectionCard>

                    </div>

                    <div className="mb-8">

                        <SectionCard title="Today's Summary">

                            {summary ? (

                                <p className="text-muted leading-relaxed">
                                    {summary.summary_text}
                                </p>

                            ) : (

                                <p className="text-faint text-sm">
                                    No summary generated yet -- the daily
                                    summary runs once a day, after market
                                    close.
                                </p>

                            )}

                        </SectionCard>

                    </div>

                    <div className="grid xl:grid-cols-2 gap-5">

                        <SectionCard title="Latest Ticks">

                            <table className="w-full">

                                <thead>

                                    <tr className="border-b border-line text-muted text-xs">

                                        <th className="text-left py-3 font-normal">Symbol</th>
                                        <th className="text-left font-normal">Price</th>
                                        <th className="text-left font-normal">Volume</th>

                                    </tr>

                                </thead>

                                <tbody>

                                    {ticks.slice(0, 8).map((tick) => (

                                        <tr
                                            key={tick.id}
                                            className="border-b border-surface-raised text-sm"
                                        >

                                            <td className="py-3">
                                                {tickerFor(tick.symbol_id)}
                                            </td>

                                            <td>{tick.price}</td>

                                            <td className="text-muted">{tick.volume}</td>

                                        </tr>

                                    ))}

                                </tbody>

                            </table>

                        </SectionCard>

                        <SectionCard title="Recent Alerts">

                            {alerts.slice(0, 8).map((alert) => (

                                <div
                                    key={alert.id}
                                    className="flex justify-between gap-4 py-4 border-b border-surface-raised last:border-b-0"
                                >

                                    <div>

                                        <div className="text-ink font-semibold text-sm">
                                            {alert.message}
                                        </div>

                                        <div className="text-faint text-xs mt-1">
                                            {tickerFor(alert.symbol_id)}
                                        </div>

                                        {/* Filled in by the ai-explainer
                                            CronJob shortly after the alert
                                            is created -- absent here just
                                            means it hasn't run yet, not an
                                            error. */}
                                        {alert.explanation && (

                                            <div className="text-muted text-sm mt-2 italic leading-relaxed">
                                                {alert.explanation}
                                            </div>

                                        )}

                                    </div>

                                    <span
                                        className={`h-fit px-3 py-1 rounded-full text-xs font-semibold shrink-0 ${
                                            alert.severity === "HIGH"
                                                ? "bg-accent text-canvas"
                                                : "bg-warn-soft text-warn"
                                        }`}
                                    >

                                        {alert.severity}

                                    </span>

                                </div>

                            ))}

                            {alerts.length === 0 && (
                                <p className="text-faint text-sm">
                                    No alerts yet.
                                </p>
                            )}

                        </SectionCard>

                    </div>

                </div>

            </div>

        </div>

    );

}
