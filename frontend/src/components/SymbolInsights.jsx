import StatusBadge from "./StatusBadge";

// One card per symbol, each with a text box holding the AI's running read
// of that symbol's session (see ai/symbol_summary.py -- refreshes every
// 15 minutes while the CronJob has new ticks to work with, unlike Today's
// Summary which only ever writes once a day). `summaries` is keyed by
// symbol_id, built once in Dashboard.jsx from the flat list the API
// returns.
export default function SymbolInsights({ symbols, summaries }) {
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3.5">

            {symbols.map((symbol) => {
                const entry = summaries[symbol.id];

                return (
                    <div
                        key={symbol.id}
                        className="bg-surface-raised rounded-2xl p-4 flex flex-col gap-3"
                    >

                        <div className="flex justify-between items-start">

                            <div>
                                <div className="font-bold text-sm text-ink">
                                    {symbol.ticker}
                                </div>
                                <div className="text-[10.5px] text-faint mt-0.5">
                                    {symbol.display_name}
                                </div>
                            </div>

                            <StatusBadge symbol={symbol} />

                        </div>

                        <div className="bg-canvas rounded-xl px-3.5 py-3 min-h-[72px]">

                            {entry ? (

                                <p className="text-muted text-xs leading-relaxed">
                                    {entry.summary_text}
                                </p>

                            ) : (

                                <p className="text-faint text-xs italic">
                                    No AI summary yet -- generated shortly
                                    after this symbol's first trades come in.
                                </p>

                            )}

                        </div>

                        {entry && (
                            <div className="text-faint text-[10px]">
                                Updated {new Date(entry.updated_at).toLocaleTimeString()}
                            </div>
                        )}

                    </div>
                );
            })}

        </div>
    );
}
