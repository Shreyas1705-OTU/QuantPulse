import { Menu } from "lucide-react";

export default function Header({ onToggleSidebar }) {
    return (
        <header className="relative flex items-center justify-between bg-canvas border-b border-line px-10 py-7 overflow-hidden">

            {/* subtle dot-grid texture, top-right */}
            <div
                className="absolute -top-14 -right-10 w-[340px] h-[220px] opacity-50 pointer-events-none"
                style={{
                    backgroundImage: "radial-gradient(#3A3530 1.4px, transparent 1.4px)",
                    backgroundSize: "16px 16px",
                    WebkitMaskImage: "radial-gradient(ellipse at center, black 10%, transparent 70%)",
                    maskImage: "radial-gradient(ellipse at center, black 10%, transparent 70%)",
                }}
            />

            <div className="relative flex items-center gap-4">

                <button
                    onClick={onToggleSidebar}
                    className="p-2 rounded-full text-muted hover:bg-surface hover:text-ink transition shrink-0"
                    aria-label="Toggle sidebar"
                >
                    <Menu size={20} />
                </button>

                <div>
                    <span className="font-display text-3xl font-bold tracking-tight text-accent">
                        QuantPulse
                    </span>

                    <p className="text-muted text-sm mt-1">
                        Real-Time Market Monitoring Platform
                    </p>
                </div>

            </div>

            <div className="relative flex items-center gap-2 bg-surface border border-line px-4 py-2 rounded-full">
                <div className="w-1.5 h-1.5 rounded-full bg-good" />
                <span className="text-good text-sm font-semibold">
                    System Online
                </span>
            </div>

        </header>
    );
}
