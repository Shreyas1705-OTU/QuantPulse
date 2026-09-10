// Live push client for WS /api/v1/stream (backend/app/routers/stream.py).
// Ingestion publishes a tick/alert to Redis the moment it happens; this
// relays straight through the backend to here -- what lets Dashboard.jsx
// react to real trade activity instead of polling on a flat timer.

function streamUrl() {
    // Same host the page itself was loaded from, upgraded to ws:/wss: to
    // match the page's own http:/https: -- works unchanged through
    // nginx's /api/ proxy (frontend/nginx.conf) or an ingress routing
    // /api straight to the backend service, since it's a relative path
    // either way, not a hardcoded host.
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${window.location.host}/api/v1/stream`;
}

// Opens the connection and keeps it alive; calls onEvent(payload) for
// every real tick/alert message (the server's own keepalive pings are
// swallowed here, never passed through). Returns an unsubscribe function
// that closes the connection and stops reconnecting.
export function subscribeToEvents(onEvent) {
    let socket = null;
    let reconnectTimer = null;
    let stopped = false;

    function connect() {
        const token = localStorage.getItem("token");
        if (!token) {
            // Not signed in -- nothing to authenticate the socket with.
            // AuthContext's own sign-in flow will trigger a fresh
            // Dashboard mount (and so a fresh connect()) once it is.
            return;
        }

        socket = new WebSocket(streamUrl());

        socket.onopen = () => {
            // First frame is the auth handshake the server's
            // _authenticate() is waiting for -- browsers can't set an
            // Authorization header on a WS handshake, so the token goes
            // here instead.
            socket.send(JSON.stringify({ token }));
        };

        socket.onmessage = (event) => {
            let payload;
            try {
                payload = JSON.parse(event.data);
            } catch {
                return;
            }

            if (payload.type === "ping") return;

            onEvent(payload);
        };

        socket.onclose = (event) => {
            if (stopped) return;

            if (event.code === 4401) {
                // Server rejected the token -- missing, expired, or
                // revoked (see backend/app/routers/stream.py's
                // _authenticate/REAUTH_INTERVAL_SECONDS). Retrying with
                // the exact same stored token would just get rejected
                // again every time, forever -- reconnecting here would
                // mean hammering the backend with a fresh handshake + DB
                // lookup every 3s indefinitely. Stop until a fresh
                // sign-in replaces the token; AuthContext's sign-in flow
                // re-mounts Dashboard (and so calls connect() fresh)
                // once that happens.
                return;
            }

            // Reconnect on any other close -- a network blip or a
            // backend pod restart shouldn't permanently strand the
            // dashboard on "no live updates" until a manual page refresh.
            reconnectTimer = setTimeout(connect, 3000);
        };

        socket.onerror = () => {
            socket.close();
        };
    }

    connect();

    return function unsubscribe() {
        stopped = true;

        if (reconnectTimer) clearTimeout(reconnectTimer);
        if (socket) socket.close();
    };
}
