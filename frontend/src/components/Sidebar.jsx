import {
    Activity,
    LayoutDashboard,
    Cpu,
    Bell,
    Database,
    BarChart3,
    LogOut,
} from "lucide-react";

import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Sidebar({ open, onNavigate }) {

    const navigate = useNavigate();
    const { signOut } = useAuth();

    const menu = [
        {
            key: "top",
            icon: <LayoutDashboard size={18} />,
            label: "Dashboard",
        },
        {
            key: "trends",
            icon: <Cpu size={18} />,
            label: "Symbols",
        },
        {
            key: "ticks",
            icon: <Database size={18} />,
            label: "Ticks",
        },
        {
            key: "alerts",
            icon: <Bell size={18} />,
            label: "Alerts",
        },
        {
            key: "summary",
            icon: <BarChart3 size={18} />,
            label: "Analytics",
        },
    ];

    function handleLogout() {
        signOut();
        navigate("/login");
    }

    return (
        <aside
            className={`bg-canvas border-line min-h-screen flex flex-col overflow-hidden transition-all duration-200 ${
                open ? "w-64 border-r p-5" : "w-0 border-r-0 p-0"
            }`}
        >

            <div className="flex items-center gap-2.5 px-2 pb-6 border-b border-line mb-5 whitespace-nowrap">

                <Activity className="text-accent" size={26} />

                <span className="font-display text-lg font-bold text-accent">
                    QuantPulse
                </span>

            </div>

            <nav className="flex flex-col gap-1 whitespace-nowrap">

                {menu.map((item, i) => (

                    <button
                        key={item.label}
                        onClick={() => onNavigate?.(item.key)}
                        className={`flex items-center gap-3 w-full px-4 py-2.5 rounded-full text-sm font-medium transition ${
                            i === 0
                                ? "bg-surface-raised text-ink"
                                : "text-muted hover:bg-surface hover:text-ink"
                        }`}
                    >

                        {item.icon}

                        {item.label}

                    </button>

                ))}

            </nav>

            <div className="flex-1" />

            <button
                onClick={handleLogout}
                className="flex items-center justify-center gap-2 w-full py-3 rounded-full bg-accent hover:bg-accent-hover transition text-canvas font-semibold text-sm mb-5 whitespace-nowrap"
            >

                <LogOut size={16} />

                Logout

            </button>

            <div className="border-t border-line pt-4 flex flex-col gap-2.5 whitespace-nowrap">

                <div className="flex items-center gap-2 mb-1">

                    <div className="w-1.5 h-1.5 rounded-full bg-good" />

                    <span className="text-good text-xs font-semibold">
                        System Healthy
                    </span>

                </div>

                <div className="flex justify-between text-xs">
                    <span className="text-faint">Backend</span>
                    <span className="text-muted">Online</span>
                </div>

                <div className="flex justify-between text-xs">
                    <span className="text-faint">Database</span>
                    <span className="text-muted">Online</span>
                </div>

                <div className="flex justify-between text-xs">
                    <span className="text-faint">Prometheus</span>
                    <span className="text-muted">Online</span>
                </div>

                <div className="flex justify-between text-xs">
                    <span className="text-faint">Grafana</span>
                    <span className="text-muted">Online</span>
                </div>

            </div>

        </aside>
    );
}
