import { CheckCircle, XCircle, Clock } from "lucide-react";

export default function SymbolStatus({ symbols, latestTicks = {} }) {
    return (
        <div className="space-y-4">

            {symbols.map((symbol) => {

                const latestTick = latestTicks[symbol.id];

                return (

                    <div
                        key={symbol.id}
                        className="flex justify-between items-center bg-slate-800 rounded-lg p-4 border border-slate-700"
                    >

                        <div>

                            <h3 className="font-semibold text-white">
                                {symbol.ticker} — {symbol.display_name}
                            </h3>

                            <p className="text-sm text-slate-400">
                                {symbol.asset_type}
                            </p>

                            {latestTick && (

                                <p className="text-sm text-slate-300 mt-1">
                                    {symbol.is_market_open ? "Last: " : "Last session: "}
                                    {latestTick.price}
                                </p>

                            )}

                        </div>

                        <div className="flex items-center gap-2">

                            {!symbol.is_active ? (
                                <>
                                    <XCircle size={18} className="text-slate-500" />
                                    <span className="text-slate-500 font-medium">Inactive</span>
                                </>
                            ) : symbol.is_market_open ? (
                                <>
                                    <CheckCircle size={18} className="text-green-400" />
                                    <span className="text-green-400 font-medium">Live</span>
                                </>
                            ) : (
                                <>
                                    <Clock size={18} className="text-amber-400" />
                                    <span className="text-amber-400 font-medium">Markets Closed</span>
                                </>
                            )}

                        </div>

                    </div>

                );

            })}

        </div>
    );
}
