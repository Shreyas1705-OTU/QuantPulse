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

import SymbolStatus from "../components/SymbolStatus";

import {
    getSymbols,
    getTicks,
    getTicksCount,
    getLatestTicks,
    getAlerts,
    getAlertsCount,
    getTodaySummary,
} from "../services/quantpulseService";

export default function Dashboard() {

    const [symbols, setSymbols] = useState([]);
    const [ticks, setTicks] = useState([]);
    const [ticksTotal, setTicksTotal] = useState(0);
    const [latestTicks, setLatestTicks] = useState({});
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
                latestTickData,
                alertData,
                alertsCount,
                summaryData,
            ] = await Promise.all([
                getSymbols(),
                getTicks(),
                getTicksCount(),
                getLatestTicks(),
                getAlerts(),
                getAlertsCount(),
                getTodaySummary(),
            ]);

            setSymbols(Array.isArray(symbolData) ? symbolData : []);
            setTicks(Array.isArray(tickData) ? tickData : []);
            setTicksTotal(ticksCount);

            const latestBySymbol = {};
            if (Array.isArray(latestTickData)) {
                for (const tick of latestTickData) {
                    latestBySymbol[tick.symbol_id] = tick;
                }
            }
            setLatestTicks(latestBySymbol);

            setAlerts(Array.isArray(alertData) ? alertData : []);
            setAlertsTotal(alertsCount);
            setSummary(summaryData);

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

        <div className="flex bg-slate-950 min-h-screen">

            <Sidebar />

            <div className="flex-1">

                <Header />

                <div className="p-8">

                    {equitiesClosed && (

                        <div className="flex items-center gap-3 bg-amber-500/10 border border-amber-500/30 rounded-xl px-6 py-4 mb-8">

                            <Clock size={20} className="text-amber-400 shrink-0" />

                            <p className="text-amber-300 text-sm">
                                US equity markets are currently closed.
                                Equity prices below are from the last
                                session. Forex and crypto continue trading.
                            </p>

                        </div>

                    )}

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">

                        <MetricCard
                            title="Symbols Tracked"
                            value={symbols.length}
                            unit=""
                            color="bg-cyan-500/20"
                            icon={<TrendingUp className="text-cyan-400" />}
                        />

                        <MetricCard
                            title="Ticks Ingested"
                            value={ticksTotal}
                            unit=""
                            color="bg-purple-500/20"
                            icon={<Database className="text-purple-400" />}
                        />

                        <MetricCard
                            title="Alerts"
                            value={alertsTotal}
                            unit=""
                            color="bg-yellow-500/20"
                            icon={<Bell className="text-yellow-400" />}
                        />

                    </div>

                    <div className="mb-8">

                        <SectionCard title="Tracked Symbols">
                            <SymbolStatus symbols={symbols} latestTicks={latestTicks} />
                        </SectionCard>

                    </div>

                    <div className="mb-8">

                        <SectionCard title="Today's Summary">

                            {summary ? (

                                <p className="text-slate-300 leading-relaxed">
                                    {summary.summary_text}
                                </p>

                            ) : (

                                <p className="text-slate-500 text-sm">
                                    No summary generated yet -- the daily
                                    summary runs once a day, after market
                                    close.
                                </p>

                            )}

                        </SectionCard>

                    </div>

                    <div className="grid xl:grid-cols-2 gap-6">

                        <SectionCard title="Latest Ticks">

                            <table className="w-full">

                                <thead>

                                    <tr className="border-b border-slate-700">

                                        <th className="text-left py-3">Symbol</th>
                                        <th className="text-left">Price</th>
                                        <th className="text-left">Volume</th>

                                    </tr>

                                </thead>

                                <tbody>

                                    {ticks.slice(0, 8).map((tick) => (

                                        <tr
                                            key={tick.id}
                                            className="border-b border-slate-800"
                                        >

                                            <td className="py-3">
                                                {tickerFor(tick.symbol_id)}
                                            </td>

                                            <td>{tick.price}</td>

                                            <td>{tick.volume}</td>

                                        </tr>

                                    ))}

                                </tbody>

                            </table>

                        </SectionCard>

                        <SectionCard title="Recent Alerts">

                            {alerts.slice(0, 8).map((alert) => (

                                <div
                                    key={alert.id}
                                    className="flex justify-between py-4 border-b border-slate-700"
                                >

                                    <div>

                                        <div className="text-white font-semibold">
                                            {alert.message}
                                        </div>

                                        <div className="text-slate-400 text-sm">
                                            {tickerFor(alert.symbol_id)}
                                        </div>

                                        {/* Filled in by the ai-explainer
                                            CronJob shortly after the alert
                                            is created -- absent here just
                                            means it hasn't run yet, not an
                                            error. */}
                                        {alert.explanation && (

                                            <div className="text-slate-300 text-sm mt-2 italic">
                                                {alert.explanation}
                                            </div>

                                        )}

                                    </div>

                                    <span
                                        className={`px-3 py-1 rounded-full text-sm ${
                                            alert.severity === "HIGH"
                                                ? "bg-red-600"
                                                : "bg-yellow-600"
                                        }`}
                                    >

                                        {alert.severity}

                                    </span>

                                </div>

                            ))}

                            {alerts.length === 0 && (
                                <p className="text-slate-500 text-sm">
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
