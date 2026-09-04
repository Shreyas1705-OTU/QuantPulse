import { useState } from "react";
import { Navigate } from "react-router-dom";
import { Activity } from "lucide-react";

import { useAuth } from "../context/AuthContext";

export default function Login() {

    const { user, signIn } = useAuth();

    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");

    const [error, setError] = useState("");

    const [loading, setLoading] = useState(false);

    if (user) {
        return <Navigate to="/" replace />;
    }

    async function handleSubmit(e) {

        e.preventDefault();

        setError("");
        setLoading(true);

        try {

            await signIn(username, password);

        }

        catch {

            setError("Invalid username or password");

        }

        setLoading(false);

    }

    return (

        <div className="min-h-screen flex items-center justify-center bg-slate-950">

            <form
                onSubmit={handleSubmit}
                className="w-full max-w-md bg-slate-900 rounded-xl border border-slate-700 p-8 shadow-xl"
            >

                <div className="flex items-center gap-3 mb-8">

                    <Activity
                        className="text-cyan-400"
                        size={36}
                    />

                    <div>

                        <h1 className="text-3xl font-bold text-white">
                            QuantPulse
                        </h1>

                        <p className="text-slate-400">
                            Sign in to continue
                        </p>

                    </div>

                </div>

                <input
                    className="w-full rounded-lg bg-slate-800 border border-slate-700 p-3 text-white mb-4"
                    placeholder="Username"
                    value={username}
                    onChange={(e)=>setUsername(e.target.value)}
                />

                <input
                    type="password"
                    className="w-full rounded-lg bg-slate-800 border border-slate-700 p-3 text-white mb-6"
                    placeholder="Password"
                    value={password}
                    onChange={(e)=>setPassword(e.target.value)}
                />

                {error && (

                    <p className="text-red-400 mb-4">

                        {error}

                    </p>

                )}

                <button
                    disabled={loading}
                    className="w-full bg-cyan-500 hover:bg-cyan-600 rounded-lg py-3 font-semibold transition"
                >

                    {loading ? "Signing In..." : "Login"}

                </button>

            </form>

        </div>

    );

}