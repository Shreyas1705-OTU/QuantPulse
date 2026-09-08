import { CheckCircle, XCircle, Clock } from "lucide-react";

// Same three states everywhere a symbol's live-ness is shown (Price Trends
// cards, Current Trade Summary table): a deactivated symbol (is_active is
// set false in the DB, e.g. SPY's old slot) always reads "Inactive"
// regardless of market hours; an active symbol then reads "Live" or
// "Closed" from is_market_open (see backend/app/core/market_hours.py).
export default function StatusBadge({ symbol }) {
    if (!symbol.is_active) {
        return (
            <span className="flex items-center gap-1 text-[10px] font-semibold text-faint bg-canvas px-2 py-0.5 rounded-full">
                <XCircle size={10} />
                Inactive
            </span>
        );
    }

    if (symbol.is_market_open) {
        return (
            <span className="flex items-center gap-1 text-[10px] font-semibold text-accent bg-accent-soft px-2 py-0.5 rounded-full">
                <CheckCircle size={10} />
                Live
            </span>
        );
    }

    return (
        <span className="flex items-center gap-1 text-[10px] font-semibold text-warn bg-warn-soft px-2 py-0.5 rounded-full">
            <Clock size={10} />
            Closed
        </span>
    );
}
