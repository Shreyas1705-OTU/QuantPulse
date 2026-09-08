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

        <div className="min-h-screen flex items-center justify-center bg-canvas">

            <form
                onSubmit={handleSubmit}
                className="w-full max-w-md bg-surface rounded-2xl border border-line p-8"
            >

                <div className="flex items-center gap-3 mb-8">

                    <Activity
                        className="text-accent"
                        size={32}
                    />

                    <div>

                        <h1 className="font-display text-2xl font-bold text-ink">
                            QuantPulse
                        </h1>

                        <p className="text-muted text-sm">
                            Sign in to continue
                        </p>

                    </div>

                </div>

                <input
                    className="w-full rounded-xl bg-surface-raised border border-line p-3 text-ink mb-4 placeholder:text-faint focus:outline-none focus:border-accent"
                    placeholder="Username"
                    value={username}
                    onChange={(e)=>setUsername(e.target.value)}
                />

                <input
                    type="password"
                    className="w-full rounded-xl bg-surface-raised border border-line p-3 text-ink mb-6 placeholder:text-faint focus:outline-none focus:border-accent"
                    placeholder="Password"
                    value={password}
                    onChange={(e)=>setPassword(e.target.value)}
                />

                {error && (

                    <p className="text-bad mb-4 text-sm">

                        {error}

                    </p>

                )}

                <button
                    disabled={loading}
                    className="w-full bg-accent hover:bg-accent-hover disabled:opacity-60 rounded-full py-3 font-semibold text-canvas transition"
                >

                    {loading ? "Signing In..." : "Login"}

                </button>

            </form>

        </div>

    );

}
