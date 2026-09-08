import { useEffect, useRef, useState } from "react";

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
import TradeSummaryTable from "../components/TradeSummaryTable";
import SymbolInsights from "../components/SymbolInsights";

import {
    getSymbols,
    getTicksCount,
    getSymbolTicks,
    getAlerts,
    getAlertsCount,
    getTodaySummary,
    getSymbolSummaries,
} from "../services/quantpulseService";

export default function Dashboard() {

    const [sidebarOpen, setSidebarOpen] = useState(true);

    const [symbols, setSymbols] = useState([]);
    const [ticksTotal, setTicksTotal] = useState(0);
    const [priceTrends, setPriceTrends] = useState({});
    const [alerts, setAlerts] = useState([]);
    const [alertsTotal, setAlertsTotal] = useState(0);
    const [summary, setSummary] = useState(null);
    const [symbolSummaries, setSymbolSummaries] = useState({});

    const topRef = useRef(null);
    const trendsRef = useRef(null);
    const ticksRef = useRef(null);
    const alertsRef = useRef(null);
    const summaryRef = useRef(null);

    const sectionRefs = {
        top: topRef,
        trends: trendsRef,
        ticks: ticksRef,
        alerts: alertsRef,
        summary: summaryRef,
    };

    function handleNavigate(key) {
        sectionRefs[key]?.current?.scrollIntoView({
            behavior: "smooth",
            block: "start",
        });
    }

    useEffect(() => {

        loadData();

        const interval = setInterval(loadData, 5000);

        return () => clearInterval(interval);

    }, []);

    async function loadData() {

        try {

            // getAlerts returns a capped, latest-first slice -- the counts
            // come from their own /count endpoints so the metric tiles
            // reflect the real totals without ever fetching the whole
            // (ever-growing) table.
            const [
                symbolData,
                ticksCount,
                alertData,
                alertsCount,
                summaryData,
                symbolSummaryData,
            ] = await Promise.all([
                getSymbols(),
                getTicksCount(),
                getAlerts(),
                getAlertsCount(),
                getTodaySummary(),
                getSymbolSummaries(),
            ]);

            const symbolsArr = Array.isArray(symbolData) ? symbolData : [];

            setSymbols(symbolsArr);
            setTicksTotal(ticksCount);
            setAlerts(Array.isArray(alertData) ? alertData : []);
            setAlertsTotal(alertsCount);
            setSummary(summaryData);

            // Keyed by symbol_id for O(1) lookup per tile in SymbolInsights,
            // same pattern as trendsBySymbol below.
            const summariesBySymbol = {};
            (Array.isArray(symbolSummaryData) ? symbolSummaryData : []).forEach((s) => {
                summariesBySymbol[s.symbol_id] = s;
            });
            setSymbolSummaries(summariesBySymbol);

            // Each symbol's own recent tick history -- feeds both its
            // Price Trends chart and its own group in Latest Ticks, so a
            // symbol that trades far more often than the others (BTCUSDT
            // ticking many times a second) can't crowd everyone else out
            // of a single shared list. A symbol with no real ticks yet
            // (e.g. an equity before this session's first Finnhub trade)
            // just gets an empty array.
            const trendResults = await Promise.all(
                symbolsArr.map((s) => getSymbolTicks(s.id, 30).catch(() => []))
            );

            const trendsBySymbol = {};
            symbolsArr.forEach((s, i) => {
                // API returns newest-first; a chart reads left-to-right
                // chronologically, so this is chronological order --
                // Latest Ticks below re-reverses its own slice back to
                // newest-first for display.
                trendsBySymbol[s.id] = trendResults[i].slice().reverse();
            });
            setPriceTrends(trendsBySymbol);

        }

        catch (err) {

            console.error(err);

        }

    }

    // NYSE hours apply uniformly to every equity, so if any one of them
    // is closed right now, they all are -- one banner covers the whole
    // asset class rather than repeating it per symbol.
    const equitiesClosed = symbols.some(
        (s) => s.asset_type === "equity" && !s.is_market_open
    );

    const symbolsWithTicks = symbols.filter(
        (s) => (priceTrends[s.id] || []).length > 0
    );

    function tickerFor(symbolId) {
        const match = symbols.find((s) => s.id === symbolId);
        return match ? match.ticker : `#${symbolId}`;
    }

    return (

        <div className="flex bg-canvas min-h-screen">

            <Sidebar open={sidebarOpen} onNavigate={handleNavigate} />

            <div className="flex-1 min-w-0">

                <Header onToggleSidebar={() => setSidebarOpen((v) => !v)} />

                <div ref={topRef} className="p-8">

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

                    <div ref={trendsRef} className="mb-8 scroll-mt-6">

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

                        <SectionCard title="Current Insights Powered by OpenAI">

                            <SymbolInsights
                                symbols={symbols}
                                summaries={symbolSummaries}
                            />

                        </SectionCard>

                    </div>

                    <div ref={summaryRef} className="mb-8 scroll-mt-6">

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

                    <div className="mb-8">

                        <SectionCard title="Current Trade Summary">

                            <TradeSummaryTable
                                symbols={symbols}
                                priceTrends={priceTrends}
                            />

                        </SectionCard>

                    </div>

                    <div className="grid xl:grid-cols-2 gap-5">

                        <div ref={ticksRef} className="scroll-mt-6">

                            <SectionCard title="Latest Ticks">

                                <div className="max-h-[480px] overflow-y-auto pr-1 space-y-5">

                                    {symbolsWithTicks.map((symbol) => (

                                        <div key={symbol.id}>

                                            <div className="text-sm font-semibold text-ink mb-2">
                                                {symbol.ticker}
                                            </div>

                                            <table className="w-full">

                                                <tbody>

                                                    {priceTrends[symbol.id]
                                                        .slice(-5)
                                                        .reverse()
                                                        .map((tick) => (

                                                            <tr
                                                                key={tick.id}
                                                                className="border-b border-surface-raised text-sm last:border-b-0"
                                                            >

                                                                <td className="py-2 text-muted w-1/3">
                                                                    {new Date(tick.traded_at).toLocaleTimeString()}
                                                                </td>

                                                                <td className="py-2">{tick.price}</td>

                                                                <td className="py-2 text-muted text-right">{tick.volume}</td>

                                                            </tr>

                                                        ))}

                                                </tbody>

                                            </table>

                                        </div>

                                    ))}

                                    {symbolsWithTicks.length === 0 && (
                                        <p className="text-faint text-sm">
                                            No ticks yet.
                                        </p>
                                    )}

                                </div>

                            </SectionCard>

                        </div>

                        <div ref={alertsRef} className="scroll-mt-6">

                            <SectionCard title="Recent Alerts">

                                <div className="max-h-[480px] overflow-y-auto pr-1">

                                    {alerts.map((alert) => (

                                        <div
                                            key={alert.id}
                                            className="flex flex-col gap-2 py-5 border-b border-surface-raised last:border-b-0"
                                        >

                                            <div className="flex justify-between items-start gap-4">

                                                <div className="text-ink font-semibold text-sm leading-snug">
                                                    {alert.message}
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

                                            <div className="text-faint text-xs">
                                                {tickerFor(alert.symbol_id)}
                                            </div>

                                            {/* Filled in by the ai-explainer
                                                CronJob shortly after the alert
                                                is created -- absent here just
                                                means it hasn't run yet, not an
                                                error. */}
                                            {alert.explanation && (

                                                <div className="text-muted text-sm leading-relaxed">
                                                    {alert.explanation}
                                                </div>

                                            )}

                                        </div>

                                    ))}

                                    {alerts.length === 0 && (
                                        <p className="text-faint text-sm">
                                            No alerts yet.
                                        </p>
                                    )}

                                </div>

                            </SectionCard>

                        </div>

                    </div>

                </div>

            </div>

        </div>

    );

}
