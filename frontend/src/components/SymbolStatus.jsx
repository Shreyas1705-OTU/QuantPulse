import { CheckCircle, XCircle } from "lucide-react";

export default function SymbolStatus({ symbols }) {
    return (
        <div className="space-y-4">

            {symbols.map((symbol) => (

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

                    </div>

                    <div className="flex items-center gap-2">

                        {symbol.is_active ? (
                            <>
                                <CheckCircle size={18} className="text-green-400" />
                                <span className="text-green-400 font-medium">Active</span>
                            </>
                        ) : (
                            <>
                                <XCircle size={18} className="text-slate-500" />
                                <span className="text-slate-500 font-medium">Inactive</span>
                            </>
                        )}

                    </div>

                </div>

            ))}

        </div>
    );
}
