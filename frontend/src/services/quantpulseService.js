import api from "./api";

export async function getSymbols() {
    const response = await api.get("/symbols/");
    return response.data;
}

export async function getTicks() {
    const response = await api.get("/ticks");
    return response.data;
}

export async function getTicksCount() {
    const response = await api.get("/ticks/count");
    return response.data.count;
}

export async function getLatestTicks() {
    const response = await api.get("/ticks/latest");
    return response.data;
}

export async function getAlerts() {
    const response = await api.get("/alerts");
    return response.data;
}

export async function getAlertsCount() {
    const response = await api.get("/alerts/count");
    return response.data.count;
}

export async function getTodaySummary() {
    try {
        const response = await api.get("/summary/today");
        return response.data;
    } catch (err) {
        // 404 means "not generated yet" (e.g. before the daily CronJob's
        // first run) -- a normal, expected state, not a load failure.
        if (err.response && err.response.status === 404) {
            return null;
        }
        throw err;
    }
}
