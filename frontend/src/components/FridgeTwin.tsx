import React, { useState } from 'react';
import { Zone } from '../types';
import {
  Thermometer,
  Droplets,
  HeartPulse,
  AlertTriangle,
  CheckCircle2,
  Package,
  Sparkles,
  Info
} from 'lucide-react';

interface FridgeTwinProps {
  zones: Zone[];
  selectedZoneId?: number;
  onSelectZone?: (zone: Zone) => void;
}

export const FridgeTwin: React.FC<FridgeTwinProps> = ({
  zones,
  selectedZoneId,
  onSelectZone
}) => {
  const [internalSelectedId, setInternalSelectedId] = useState<number>(
    selectedZoneId || (zones[0]?.id ?? 1)
  );

  const activeZoneId = selectedZoneId || internalSelectedId;
  const activeZone = zones.find((z) => z.id === activeZoneId) || zones[0];

  const handleSelect = (zone: Zone) => {
    setInternalSelectedId(zone.id);
    if (onSelectZone) onSelectZone(zone);
  };

  // Helper for status colors
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'critical':
        return 'border-rose-400 bg-rose-50/80 text-rose-800';
      case 'warning':
        return 'border-amber-400 bg-amber-50/80 text-amber-800';
      default:
        return 'border-emerald-300 bg-emerald-50/70 text-emerald-800';
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'critical':
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-700">Critical</span>;
      case 'warning':
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-700">Warning</span>;
      default:
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-700">Normal</span>;
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
      {/* Visual Refrigerator Graphic (7 cols) */}
      <div className="lg:col-span-6 bg-white p-6 rounded-2xl border border-slate-200/80 shadow-soft">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-bold text-slate-800">Fridge Digital Twin</h3>
            <p className="text-xs text-slate-500">Interactive live sensor & item layout</p>
          </div>
          <span className="flex items-center gap-1.5 text-xs text-emerald-600 font-semibold bg-emerald-50 px-2.5 py-1 rounded-full">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            Sensors Active
          </span>
        </div>

        {/* Physical Fridge Outer Frame */}
        <div className="relative border-4 border-slate-300 rounded-3xl p-3 bg-gradient-to-b from-slate-100 to-slate-200 shadow-inner">
          {/* Refrigerator Interior Cavity */}
          <div className="bg-slate-50 rounded-2xl p-2.5 border border-slate-300/70 space-y-2.5">
            {zones.map((zone) => {
              const isSelected = zone.id === activeZone?.id;
              const isFreezer = zone.code === 'freezer';

              return (
                <div
                  key={zone.id}
                  onClick={() => handleSelect(zone)}
                  className={`cursor-pointer rounded-xl p-3 border-2 transition-all duration-200 relative overflow-hidden group ${
                    isSelected
                      ? 'ring-2 ring-emerald-500 ring-offset-2 border-emerald-500 bg-white shadow-md'
                      : 'border-slate-200/80 bg-white/90 hover:border-slate-300 hover:bg-white'
                  }`}
                >
                  {/* Shelf Glass Divider Line */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div
                        className={`w-3 h-3 rounded-full ${
                          zone.status === 'critical'
                            ? 'bg-rose-500'
                            : zone.status === 'warning'
                            ? 'bg-amber-500'
                            : 'bg-emerald-500'
                        }`}
                      />
                      <span className="text-xs font-bold text-slate-800">
                        {zone.name}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 text-xs">
                      <span className="font-semibold text-slate-700 bg-slate-100 px-2 py-0.5 rounded-md">
                        {zone.current_temp}°C
                      </span>
                      <span className="text-slate-500">
                        {zone.current_humidity}% RH
                      </span>
                      {getStatusBadge(zone.status)}
                    </div>
                  </div>

                  {/* Items peek preview */}
                  <div className="mt-2 flex items-center justify-between text-[11px] text-slate-500">
                    <div className="flex items-center gap-1.5 truncate max-w-[220px]">
                      <Package className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                      <span>{zone.item_count || 0} items stored</span>
                    </div>

                    {zone.compatibility_conflict && (
                      <span className="flex items-center gap-1 text-[10px] font-bold text-amber-700 bg-amber-100 px-2 py-0.5 rounded-full">
                        <AlertTriangle className="w-3 h-3" /> Ethylene Conflict
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Selected Shelf Details Panel (5 cols) */}
      <div className="lg:col-span-6 space-y-4">
        {activeZone && (
          <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-soft">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div>
                <span className="text-[11px] font-semibold text-emerald-600 uppercase tracking-wider">
                  Zone Telemetry
                </span>
                <h3 className="text-lg font-bold text-slate-900">{activeZone.name}</h3>
                <p className="text-xs text-slate-500 mt-0.5">{activeZone.description}</p>
              </div>
              <div className="text-right">
                <span className="text-xs text-slate-500 block">Health Index</span>
                <span className="text-2xl font-black text-slate-800">
                  {activeZone.health_score}
                  <span className="text-xs font-normal text-slate-500">/100</span>
                </span>
              </div>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-2 gap-3 my-4">
              {/* Temperature card */}
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100">
                <div className="flex items-center gap-1.5 text-slate-500 text-xs mb-1">
                  <Thermometer className="w-4 h-4 text-emerald-600" />
                  <span>Temperature</span>
                </div>
                <div className="text-xl font-bold text-slate-800">
                  {activeZone.current_temp}°C
                </div>
                <div className="text-[10px] text-slate-500 mt-0.5">
                  Target: {activeZone.target_temp_min}°C – {activeZone.target_temp_max}°C
                </div>
              </div>

              {/* Humidity card */}
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100">
                <div className="flex items-center gap-1.5 text-slate-500 text-xs mb-1">
                  <Droplets className="w-4 h-4 text-blue-500" />
                  <span>Humidity</span>
                </div>
                <div className="text-xl font-bold text-slate-800">
                  {activeZone.current_humidity}%
                </div>
                <div className="text-[10px] text-slate-500 mt-0.5">
                  Target: {activeZone.target_humidity_min}% – {activeZone.target_humidity_max}%
                </div>
              </div>
            </div>

            {/* Ethylene Gas Compatibility Warning Banner */}
            {activeZone.compatibility_conflict ? (
              <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 mb-4 flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-xs font-bold text-amber-800">
                    Ethylene Incompatibility Detected!
                  </h4>
                  <p className="text-xs text-amber-700 leading-relaxed mt-1">
                    Ethylene producer (<strong>{activeZone.producers?.join(', ')}</strong>) is stored
                    next to gas-sensitive items (<strong>{activeZone.sensitive?.join(', ')}</strong>).
                    This causes premature ripening and yellowing! Move them to separate shelves.
                  </p>
                </div>
              </div>
            ) : (
              <div className="p-3 rounded-xl bg-emerald-50/80 border border-emerald-100 text-emerald-800 text-xs flex items-center gap-2 mb-4">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                <span>Gas balance safe: No incompatible ethylene gas producers paired with sensitive greens.</span>
              </div>
            )}

            {/* Stored Items in this shelf */}
            <div>
              <h4 className="text-xs font-bold text-slate-700 mb-2 flex items-center justify-between">
                <span>Stored Foods in {activeZone.name}</span>
                <span className="text-[11px] font-normal text-slate-500">
                  {activeZone.items?.length || 0} items
                </span>
              </h4>

              <div className="max-h-52 overflow-y-auto space-y-1.5 pr-1">
                {activeZone.items && activeZone.items.length > 0 ? (
                  activeZone.items.map((it) => (
                    <div
                      key={it.id}
                      className="flex items-center justify-between p-2.5 rounded-lg bg-slate-50 border border-slate-100 text-xs"
                    >
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                        <span className="font-semibold text-slate-800">{it.name}</span>
                        <span className="text-[10px] text-slate-400">({it.category})</span>
                      </div>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                          it.freshness_status === 'Rotten' || it.freshness_status === 'Expired'
                            ? 'bg-rose-100 text-rose-700'
                            : it.freshness_status === 'Ripe' || it.freshness_status === 'Expiring Soon'
                            ? 'bg-amber-100 text-amber-700'
                            : 'bg-emerald-100 text-emerald-700'
                        }`}
                      >
                        {it.freshness_status}
                      </span>
                    </div>
                  ))
                ) : (
                  <div className="p-4 text-center text-xs text-slate-400 italic bg-slate-50 rounded-xl">
                    No items currently assigned to this shelf.
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
