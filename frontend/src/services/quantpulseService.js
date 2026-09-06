import api from "./api";

export async function getSymbols() {
    const response = await api.get("/symbols/");
    return response.data;
}

export async function getTicks() {
    const response = await api.get("/ticks");
    return response.data;
}

export async function getAlerts() {
    const response = await api.get("/alerts");
    return response.data;
}
