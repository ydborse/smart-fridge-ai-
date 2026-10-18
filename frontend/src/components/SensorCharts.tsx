import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  PieChart,
  Pie,
  Cell
} from 'recharts';
import { Thermometer, Droplets } from 'lucide-react';

interface SensorChartsProps {
  temperatureHistory: Array<{
    time: string;
    top_shelf?: number;
    middle_shelf?: number;
    bottom_shelf?: number;
    veg_drawer?: number;
    freezer?: number;
  }>;
  averageHumidity?: number;
}

export const SensorCharts: React.FC<SensorChartsProps> = ({
  temperatureHistory,
  averageHumidity = 71
}) => {
  // Data for humidity donut gauge
  const gaugeData = [
    { name: 'Current Humidity', value: averageHumidity, color: '#0ea5e9' },
    { name: 'Remaining', value: Math.max(0, 100 - averageHumidity), color: '#e2e8f0' },
  ];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      {/* 24-Hour Temperature Line Chart (8 cols) */}
      <div className="lg:col-span-8 bg-white p-6 rounded-2xl border border-slate-200/80 shadow-soft">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <Thermometer className="w-4 h-4 stroke-[2.5]" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-800">
                24-Hour Shelf Temperature Trends
              </h3>
              <p className="text-[11px] text-slate-500">
                Hourly telemetry per refrigerator zone (°C)
              </p>
            </div>
          </div>
          <span className="text-[11px] font-semibold text-slate-500 bg-slate-100 px-2.5 py-1 rounded-full">
            24h Window
          </span>
        </div>

        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={temperatureHistory} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis dataKey="time" stroke="#94a3b8" fontSize={11} tickLine={false} />
              <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} unit="°C" domain={['auto', 'auto']} />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(255, 255, 255, 0.95)',
                  borderRadius: '12px',
                  boxShadow: '0 4px 15px rgba(0,0,0,0.08)',
                  border: '1px solid #e2e8f0',
                  fontSize: '12px'
                }}
              />
              <Legend
                verticalAlign="top"
                align="right"
                iconType="circle"
                wrapperStyle={{ fontSize: '11px', paddingBottom: '10px' }}
              />
              <Line
                type="monotone"
                dataKey="top_shelf"
                name="Top Shelf"
                stroke="#10b981"
                strokeWidth={2.5}
                dot={false}
                activeDot={{ r: 5 }}
              />
              <Line
                type="monotone"
                dataKey="middle_shelf"
                name="Middle Shelf"
                stroke="#3b82f6"
                strokeWidth={2.5}
                dot={false}
                activeDot={{ r: 5 }}
              />
              <Line
                type="monotone"
                dataKey="bottom_shelf"
                name="Bottom Shelf"
                stroke="#6366f1"
                strokeWidth={2.5}
                dot={false}
                activeDot={{ r: 5 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Humidity Donut Gauge (4 cols) */}
      <div className="lg:col-span-4 bg-white p-6 rounded-2xl border border-slate-200/80 shadow-soft flex flex-col justify-between">
        <div className="flex items-center gap-2.5 mb-2">
          <div className="w-8 h-8 rounded-lg bg-sky-50 text-sky-600 flex items-center justify-center">
            <Droplets className="w-4 h-4 stroke-[2.5]" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-800">Humidity Gauge</h3>
            <p className="text-[11px] text-slate-500">Overall Cabinet Humidity</p>
          </div>
        </div>

        {/* Circular Gauge */}
        <div className="relative h-44 w-full flex items-center justify-center my-auto">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={gaugeData}
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={75}
                startAngle={220}
                endAngle={-40}
                paddingAngle={0}
                dataKey="value"
              >
                {gaugeData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          {/* Centered Number */}
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none mt-2">
            <span className="text-2xl font-black text-slate-800 tracking-tight">
              {averageHumidity}%
            </span>
            <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
              Relative Hum.
            </span>
          </div>
        </div>

        {/* Gauge bottom note */}
        <div className="p-2.5 rounded-xl bg-sky-50/70 border border-sky-100 text-sky-800 text-[11px] flex items-center justify-between">
          <span>Crisper Target: 80-95%</span>
          <span className="font-bold text-sky-700">Optimal</span>
        </div>
      </div>
    </div>
  );
};
