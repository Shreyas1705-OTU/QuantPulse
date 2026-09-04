import { Activity } from "lucide-react";

export default function Header() {
    return (
        <header className="flex items-center justify-between bg-slate-900 border-b border-slate-700 px-8 py-5">
            <div>
                <div className="flex items-center gap-3">
                    <Activity size={34} className="text-cyan-400" />

                    <div>
                        <h1 className="text-3xl font-bold text-white">
                            QuantPulse
                        </h1>

                        <p className="text-slate-400 text-sm">
                            Cloud Native IoT Monitoring Platform
                        </p>
                    </div>
                </div>
            </div>

            <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-green-500 animate-pulse"></div>

                <span className="text-green-400 font-medium">
                    System Online
                </span>
            </div>
        </header>
    );
}