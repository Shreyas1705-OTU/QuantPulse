import {
    Activity,
    LayoutDashboard,
    Cpu,
    Bell,
    Database,
    BarChart3,
    ShieldCheck,
    LogOut,
} from "lucide-react";

import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Sidebar() {

    const navigate = useNavigate();
    const { signOut } = useAuth();

    const menu = [
        {
            icon: <LayoutDashboard size={18} />,
            label: "Dashboard",
        },
        {
            icon: <Cpu size={18} />,
            label: "Symbols",
        },
        {
            icon: <Database size={18} />,
            label: "Ticks",
        },
        {
            icon: <Bell size={18} />,
            label: "Alerts",
        },
        {
            icon: <BarChart3 size={18} />,
            label: "Analytics",
        },
    ];

    function handleLogout() {
        signOut();
        navigate("/login");
    }

    return (
        <aside className="w-72 bg-slate-900 border-r border-slate-800 min-h-screen flex flex-col">

            <div className="p-8 border-b border-slate-800">

                <div className="flex items-center gap-3">

                    <Activity
                        className="text-cyan-400"
                        size={36}
                    />

                    <div>

                        <h1 className="text-2xl font-bold text-white">
                            QuantPulse
                        </h1>

                        <p className="text-xs text-slate-400">
                            Market Monitoring Platform
                        </p>

                    </div>

                </div>

            </div>

            <nav className="flex-1 p-5">

                {menu.map((item) => (

                    <button
                        key={item.label}
                        className="flex items-center gap-3 w-full mb-2 px-4 py-3 rounded-lg text-slate-300 hover:bg-cyan-600 hover:text-white transition"
                    >

                        {item.icon}

                        {item.label}

                    </button>

                ))}

            </nav>

            <div className="px-6">

                <button
                    onClick={handleLogout}
                    className="flex items-center justify-center gap-2 w-full py-3 rounded-lg bg-red-600 hover:bg-red-700 transition text-white font-semibold"
                >

                    <LogOut size={18} />

                    Logout

                </button>

            </div>

            <div className="p-6 border-t border-slate-800 mt-6">

                <div className="flex items-center gap-2 mb-3">

                    <ShieldCheck
                        className="text-green-400"
                        size={18}
                    />

                    <span className="text-green-400 text-sm font-medium">
                        System Healthy
                    </span>

                </div>

                <div className="space-y-2 text-sm">

                    <div className="flex justify-between">

                        <span className="text-slate-400">
                            Backend
                        </span>

                        <span className="text-green-400">
                            Online
                        </span>

                    </div>

                    <div className="flex justify-between">

                        <span className="text-slate-400">
                            Database
                        </span>

                        <span className="text-green-400">
                            Online
                        </span>

                    </div>

                    <div className="flex justify-between">

                        <span className="text-slate-400">
                            Prometheus
                        </span>

                        <span className="text-green-400">
                            Online
                        </span>

                    </div>

                    <div className="flex justify-between">

                        <span className="text-slate-400">
                            Grafana
                        </span>

                        <span className="text-green-400">
                            Online
                        </span>

                    </div>

                </div>

            </div>

        </aside>
    );
}