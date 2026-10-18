import React, { useState, useEffect } from 'react';
import { zonesApi } from '../services/api';
import { Zone } from '../types';
import { FridgeTwin } from '../components/FridgeTwin';
import { useNotification } from '../context/NotificationContext';
import {
  Layers,
  Thermometer,
  Droplets,
  AlertTriangle,
  RefreshCw,
  Cpu,
  ShieldCheck,
  Zap
} from 'lucide-react';

export const Zones: React.FC = () => {
  const [zones, setZones] = useState<Zone[]>([]);
  const [loading, setLoading] = useState(true);
  const [simulating, setSimulating] = useState(false);
  const { showToast } = useNotification();

  const loadZones = async () => {
    try {
      const data = await zonesApi.getAll();
      setZones(data);
    } catch (err) {
      console.error('Failed to load zones:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadZones();
    const interval = setInterval(loadZones, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleSimulateSensorReading = async (zoneCode: string, temp: number, hum: number) => {
    try {
      setSimulating(true);
      await zonesApi.postSensorReading({
        zone_code: zoneCode,
        temperature: temp,
        humidity: hum
      });
      showToast('success', `Sensor reading posted for ${zoneCode}`, 'IoT Packet Received');
      await loadZones();
    } catch (err) {
      showToast('error', 'Failed to push simulated sensor reading');
    } finally {
      setSimulating(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <Layers className="w-6 h-6 text-emerald-600" />
            Refrigerator Zones & Digital Twin
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
            Real-time telemetry, shelf health scores, and ethylene gas compatibility monitoring
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadZones}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-slate-200 bg-white text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-xs transition-all"
          >
            <RefreshCw className="w-3.5 h-3.5 text-slate-500" />
            Refresh Telemetry
          </button>
        </div>
      </div>

      {/* Interactive Fridge Digital Twin */}
      <FridgeTwin zones={zones} />

      {/* Per-Zone Detail Cards Grid */}
      <div>
        <h2 className="text-base font-bold text-slate-900 mb-4">
          All Refrigerator Shelves & Crispers
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {zones.map((zone) => (
            <div
              key={zone.id}
              className={`p-5 rounded-2xl border transition-all duration-200 bg-white shadow-soft ${
                zone.status === 'critical'
                  ? 'border-rose-300'
                  : zone.status === 'warning'
                  ? 'border-amber-300'
                  : 'border-slate-200/80'
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-bold text-slate-800 text-sm flex items-center gap-2">
                  <span
                    className={`w-2.5 h-2.5 rounded-full ${
                      zone.status === 'critical'
                        ? 'bg-rose-500'
                        : zone.status === 'warning'
                        ? 'bg-amber-500'
                        : 'bg-emerald-500'
                    }`}
                  />
                  {zone.name}
                </h3>
                <span className="text-xs font-extrabold text-slate-800 bg-slate-100 px-2 py-0.5 rounded-full">
                  Health: {zone.health_score}/100
                </span>
              </div>

              <p className="text-xs text-slate-500 mb-4 min-h-[32px] line-clamp-2">
                {zone.description}
              </p>

              {/* Temp and Humidity */}
              <div className="grid grid-cols-2 gap-2 mb-4">
                <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                  <div className="flex items-center gap-1 text-slate-400 text-[10px]">
                    <Thermometer className="w-3 h-3 text-emerald-600" />
                    <span>Temperature</span>
                  </div>
                  <div className="text-base font-bold text-slate-800 mt-0.5">
                    {zone.current_temp}°C
                  </div>
                  <div className="text-[10px] text-slate-400">
                    Safe: {zone.target_temp_min}-{zone.target_temp_max}°C
                  </div>
                </div>

                <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                  <div className="flex items-center gap-1 text-slate-400 text-[10px]">
                    <Droplets className="w-3 h-3 text-blue-500" />
                    <span>Humidity</span>
                  </div>
                  <div className="text-base font-bold text-slate-800 mt-0.5">
                    {zone.current_humidity}%
                  </div>
                  <div className="text-[10px] text-slate-400">
                    Safe: {zone.target_humidity_min}-{zone.target_humidity_max}%
                  </div>
                </div>
              </div>

              {/* Compatibility Status */}
              {zone.compatibility_conflict ? (
                <div className="p-2.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-center gap-2 mb-3">
                  <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0" />
                  <span className="text-[11px] font-medium leading-tight">
                    Gas conflict: {zone.producers?.join(', ')} emitting ethylene!
                  </span>
                </div>
              ) : (
                <div className="p-2 rounded-xl bg-emerald-50/70 border border-emerald-100 text-emerald-800 text-[11px] flex items-center gap-1.5 mb-3">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Ethylene levels balanced</span>
                </div>
              )}

              {/* Items Stored Count */}
              <div className="flex items-center justify-between text-xs text-slate-500 pt-2 border-t border-slate-100">
                <span>Items Stored</span>
                <span className="font-bold text-slate-800">{zone.item_count || 0} items</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Hardware / IoT Simulator Card */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-soft">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <Cpu className="w-5 h-5 stroke-[2.2]" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-800">
                Hardware Sensor Endpoint (ESP32 / MQTT / Arduino)
              </h3>
              <p className="text-xs text-slate-500">
                Real IoT hardware posts JSON to <code className="bg-slate-100 px-1 py-0.5 rounded text-emerald-600 font-mono">POST /api/sensors</code>
              </p>
            </div>
          </div>
          <span className="text-xs font-semibold text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full">
            REST Ready
          </span>
        </div>

        <p className="text-xs text-slate-600 mb-4 leading-relaxed">
          Simulate an external physical probe sending readings to the Smart Fridge backend:
        </p>

        <div className="flex flex-wrap gap-2.5">
          <button
            disabled={simulating}
            onClick={() => handleSimulateSensorReading('top_shelf', 3.6, 65.0)}
            className="px-3.5 py-2 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200 text-xs font-semibold text-slate-700 transition-all active:scale-95"
          >
            Send Normal Reading (Top Shelf: 3.6°C)
          </button>
          <button
            disabled={simulating}
            onClick={() => handleSimulateSensorReading('top_shelf', 7.5, 50.0)}
            className="px-3.5 py-2 rounded-xl bg-amber-50 hover:bg-amber-100 border border-amber-200 text-xs font-semibold text-amber-800 transition-all active:scale-95"
          >
            Simulate Door Ajar Spike (Top Shelf: 7.5°C)
          </button>
          <button
            disabled={simulating}
            onClick={() => handleSimulateSensorReading('vegetable_drawer', 5.1, 92.0)}
            className="px-3.5 py-2 rounded-xl bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 text-xs font-semibold text-emerald-800 transition-all active:scale-95"
          >
            Simulate Fresh Crisper (Veg Drawer: 5.1°C, 92% RH)
          </button>
        </div>
      </div>
    </div>
  );
};
