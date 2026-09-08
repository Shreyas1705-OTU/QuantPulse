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

export async function getAlerts() {
    const response = await api.get("/alerts");
    return response.data;
}

export async function getAlertsCount() {
    const response = await api.get("/alerts/count");
    return response.data.count;
}
