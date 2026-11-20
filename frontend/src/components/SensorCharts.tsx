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
  Cell,
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
  /** Average of the latest available humidity sensor readings. Omit when unavailable. */
  averageHumidity?: number;
}

export const SensorCharts: React.FC<SensorChartsProps> = ({ temperatureHistory, averageHumidity }) => {
  const hasHumidityReading = typeof averageHumidity === 'number' && Number.isFinite(averageHumidity);
  const humidity = hasHumidityReading ? Math.max(0, Math.min(100, averageHumidity)) : 0;
  const gaugeData = [
    { name: 'Measured humidity', value: humidity, color: '#54744e' },
    { name: 'Remaining', value: Math.max(0, 100 - humidity), color: '#e7e9df' },
  ];

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
      <section className={`${hasHumidityReading ? 'lg:col-span-8' : 'lg:col-span-12'} rounded-xl border border-[#e4e6dc] bg-white p-4 sm:p-6`}>
        <div className="mb-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#edf2e8] text-[#356247]"><Thermometer className="h-4 w-4" /></div>
            <div>
              <h3 className="text-sm font-semibold text-[#26372d]">Temperature history</h3>
              <p className="text-xs text-[#69736b]">Recorded fridge-zone readings (°C)</p>
            </div>
          </div>
          <span className="rounded-full bg-[#f2f3ec] px-2.5 py-1 text-xs font-medium text-[#5e6c60]">Last 24 hours</span>
        </div>

        {temperatureHistory.length > 0 ? (
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={temperatureHistory} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eceee6" />
                <XAxis dataKey="time" stroke="#7b867d" fontSize={11} tickLine={false} />
                <YAxis stroke="#7b867d" fontSize={11} tickLine={false} unit="°C" domain={['auto', 'auto']} />
                <Tooltip contentStyle={{ backgroundColor: '#fffefa', borderRadius: '10px', border: '1px solid #e1e2d8', fontSize: '12px' }} />
                <Legend verticalAlign="top" align="right" iconType="circle" wrapperStyle={{ fontSize: '11px', paddingBottom: '10px' }} />
                <Line type="monotone" dataKey="top_shelf" name="Top shelf" stroke="#54744e" strokeWidth={2.5} dot={false} activeDot={{ r: 5 }} connectNulls />
                <Line type="monotone" dataKey="middle_shelf" name="Middle shelf" stroke="#7c9a78" strokeWidth={2.5} dot={false} activeDot={{ r: 5 }} connectNulls />
                <Line type="monotone" dataKey="bottom_shelf" name="Bottom shelf" stroke="#b5813c" strokeWidth={2.5} dot={false} activeDot={{ r: 5 }} connectNulls />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="py-10 text-center text-sm text-[#69736b]">No temperature readings are available yet.</p>
        )}
      </section>

      {hasHumidityReading && (
        <section className="flex flex-col rounded-xl border border-[#e4e6dc] bg-white p-4 sm:p-6 lg:col-span-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#edf2e8] text-[#356247]"><Droplets className="h-4 w-4" /></div>
            <div>
              <h3 className="text-sm font-semibold text-[#26372d]">Relative humidity</h3>
              <p className="text-xs text-[#69736b]">Average of latest available readings</p>
            </div>
          </div>
          <div className="relative my-auto flex h-44 w-full items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={gaugeData} cx="50%" cy="50%" innerRadius={54} outerRadius={72} startAngle={220} endAngle={-40} paddingAngle={0} dataKey="value">
                  {gaugeData.map((entry, index) => <Cell key={`cell-${index}`} fill={entry.color} />)}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <div className="pointer-events-none absolute inset-0 mt-2 flex flex-col items-center justify-center">
              <span className="text-2xl font-semibold tracking-tight text-[#26372d]">{Math.round(humidity)}%</span>
              <span className="text-[10px] font-medium uppercase tracking-wider text-[#788378]">Measured</span>
            </div>
          </div>
          <p className="rounded-lg border border-[#e5e8dc] bg-[#f7f8f1] px-3 py-2 text-xs leading-5 text-[#5c6b5e]">
            Sensor reading only. Use your storage guidance and food labels when deciding where to keep each item.
          </p>
        </section>
      )}
    </div>
  );
};
