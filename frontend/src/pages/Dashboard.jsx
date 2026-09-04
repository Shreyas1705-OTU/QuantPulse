import { useEffect, useState } from "react";

import {
    Thermometer,
    Droplets,
    Battery,
    Bell,
    Cpu,
    Database,
} from "lucide-react";

import Sidebar from "../components/Sidebar";
import Header from "../components/Header";
import MetricCard from "../components/MetricCard";
import SectionCard from "../components/SectionCard";

import DeviceStatus from "../components/DeviceStatus";
import TemperatureChart from "../components/TemperatureChart";
import HumidityChart from "../components/HumidityChart";
import BatteryChart from "../components/BatteryChart";

import {
    getDevices,
    getReadings,
    getAlerts,
} from "../services/quantpulseService";

export default function Dashboard() {

    const [devices, setDevices] = useState([]);
    const [readings, setReadings] = useState([]);
    const [alerts, setAlerts] = useState([]);

    useEffect(() => {

        loadData();

        const interval = setInterval(loadData, 5000);

        return () => clearInterval(interval);

    }, []);

    async function loadData() {

        try {

            const deviceData = await getDevices();
            const readingData = await getReadings();
            const alertData = await getAlerts();

            console.log("Devices:", deviceData);
            console.log("Readings:", readingData);
            console.log("Alerts:", alertData);

            setDevices(Array.isArray(deviceData) ? deviceData : []);
            setReadings(Array.isArray(readingData) ? readingData : []);
            setAlerts(Array.isArray(alertData) ? alertData : []);

        }

        catch (err) {

            console.error(err);

        }

    }

    const latest = readings.length ? readings[0] : null;

    return (

        <div className="flex bg-slate-950 min-h-screen">

            <Sidebar />

            <div className="flex-1">

                <Header />

                <div className="p-8">

                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6 mb-8">

                        <MetricCard
                            title="Temperature"
                            value={latest?.temperature ?? "--"}
                            unit="°C"
                            color="bg-red-500/20"
                            icon={<Thermometer className="text-red-400" />}
                        />

                        <MetricCard
                            title="Humidity"
                            value={latest?.humidity ?? "--"}
                            unit="%"
                            color="bg-blue-500/20"
                            icon={<Droplets className="text-blue-400" />}
                        />

                        <MetricCard
                            title="Battery"
                            value={latest?.battery ?? "--"}
                            unit="%"
                            color="bg-green-500/20"
                            icon={<Battery className="text-green-400" />}
                        />

                        <MetricCard
                            title="Devices"
                            value={devices.length}
                            unit=""
                            color="bg-cyan-500/20"
                            icon={<Cpu className="text-cyan-400" />}
                        />

                        <MetricCard
                            title="Readings"
                            value={readings.length}
                            unit=""
                            color="bg-purple-500/20"
                            icon={<Database className="text-purple-400" />}
                        />

                        <MetricCard
                            title="Alerts"
                            value={alerts.length}
                            unit=""
                            color="bg-yellow-500/20"
                            icon={<Bell className="text-yellow-400" />}
                        />

                    </div>

                    <div className="grid xl:grid-cols-2 gap-6 mb-8">

                        <SectionCard title="Temperature Trend">
                            <TemperatureChart readings={readings} />
                        </SectionCard>

                        <SectionCard title="Humidity Trend">
                            <HumidityChart readings={readings} />
                        </SectionCard>

                    </div>

                    <div className="mb-8">

                        <SectionCard title="Battery Trend">
                            <BatteryChart readings={readings} />
                        </SectionCard>

                    </div>

                    <div className="mb-8">

                        <SectionCard title="Device Status">
                            <DeviceStatus devices={devices} />
                        </SectionCard>

                    </div>

                    <div className="grid xl:grid-cols-2 gap-6">

                        <SectionCard title="Latest Readings">

                            <table className="w-full">

                                <thead>

                                    <tr className="border-b border-slate-700">

                                        <th className="text-left py-3">Device</th>
                                        <th className="text-left">Temp</th>
                                        <th className="text-left">Humidity</th>
                                        <th className="text-left">Battery</th>

                                    </tr>

                                </thead>

                                <tbody>

                                    {readings.slice(0,8).map((reading)=>(

                                        <tr
                                            key={reading.id}
                                            className="border-b border-slate-800"
                                        >

                                            <td className="py-3">
                                                Device {reading.device_id}
                                            </td>

                                            <td>{reading.temperature}°C</td>

                                            <td>{reading.humidity}%</td>

                                            <td>{reading.battery}%</td>

                                        </tr>

                                    ))}

                                </tbody>

                            </table>

                        </SectionCard>

                        <SectionCard title="Recent Alerts">

                            {alerts.slice(0,8).map((alert)=>(

                                <div
                                    key={alert.id}
                                    className="flex justify-between py-4 border-b border-slate-700"
                                >

                                    <div>

                                        <div className="text-white font-semibold">
                                            {alert.message}
                                        </div>

                                        <div className="text-slate-400 text-sm">
                                            Device {alert.device_id}
                                        </div>

                                    </div>

                                    <span
                                        className={`px-3 py-1 rounded-full text-sm ${
                                            alert.severity === "HIGH"
                                                ? "bg-red-600"
                                                : "bg-yellow-600"
                                        }`}
                                    >

                                        {alert.severity}

                                    </span>

                                </div>

                            ))}

                        </SectionCard>

                    </div>

                </div>

            </div>

        </div>

    );

}