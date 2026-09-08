export default function Header() {
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

            <div className="relative">
                <div className="relative inline-block">
                    <span className="font-display text-3xl font-bold tracking-tight text-ink">
                        QuantPulse
                    </span>
                    <div
                        className="absolute -left-1 -right-1 bottom-1.5 h-2.5 bg-accent opacity-85 -z-10"
                        style={{ transform: "skewX(-8deg) rotate(-1.5deg)" }}
                    />
                </div>

                <p className="text-muted text-sm mt-1">
                    Real-Time Market Monitoring Platform
                </p>
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
