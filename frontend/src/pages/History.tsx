import React, { useState, useEffect } from 'react';
import {
  History as HistoryIcon,
  TrendingUp,
  TrendingDown,
  DollarSign,
  CheckCircle2,
  Trash2,
  Package,
  Calendar,
  Filter
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';
import { historyApi } from '../services/api';

export const History: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [filterAction, setFilterAction] = useState<string>('');

  const loadHistory = async () => {
    try {
      setLoading(true);
      const res = await historyApi.get(filterAction || undefined);
      setData(res);
    } catch (err) {
      console.error('Failed to load history:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, [filterAction]);

  const stats = data?.stats ?? {
  total_added: 0,
  total_consumed: 0,
  total_wasted: 0,
  waste_rate_percent: 0,
  efficiency_rate_percent: 0,
  money_saved: 0,
  money_wasted: 0
};

const monthlyComparison = Array.isArray(data?.monthly_comparison)
  ? data.monthly_comparison
  : [];

const baselineWaste = Number(monthlyComparison[0]?.wasted ?? 0);
const latestWaste = Number(
  monthlyComparison[monthlyComparison.length - 1]?.wasted ?? 0
);

const wasteChangePercent =
  monthlyComparison.length > 1 && baselineWaste > 0
    ? Math.round(((baselineWaste - latestWaste) / baselineWaste) * 100)
    : null;

const wasteTrendText =
  wasteChangePercent === null
    ? 'Not enough history'
    : wasteChangePercent > 0
      ? `${wasteChangePercent}% less waste`
      : wasteChangePercent < 0
        ? `${Math.abs(wasteChangePercent)}% more waste`
        : 'Waste unchanged';

const wasteTrendClass =
  wasteChangePercent === null
    ? 'bg-slate-100 text-slate-600'
    : wasteChangePercent > 0
      ? 'bg-emerald-50 text-emerald-600'
      : wasteChangePercent < 0
        ? 'bg-rose-50 text-rose-600'
        : 'bg-slate-100 text-slate-600';

const totalResolvedActivities =
  Number(stats.total_consumed ?? 0) +
  Number(stats.total_wasted ?? 0);

  const getActionBadge = (action: string) => {
    switch (action) {
      case 'used':
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-700">Consumed</span>;
      case 'added':
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-100 text-blue-700">Added</span>;
      case 'discarded':
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-700">Discarded</span>;
      case 'expired':
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-700">Expired</span>;
      default:
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-700">Updated</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
          <HistoryIcon className="w-6 h-6 text-emerald-600" />
          Consumption & Waste History
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
          Analytics on food consumption efficiency, financial savings, and waste reduction trends
        </p>
      </div>

      {/* High-Level Metric Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Efficiency Rate */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-soft">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Pantry Efficiency</span>
            <TrendingUp className="w-5 h-5 text-emerald-600" />
          </div>
          <div className="text-2xl sm:text-3xl font-black text-emerald-600">
            {stats.efficiency_rate_percent}%
          </div>
         <p className="text-[11px] text-slate-400 mt-1">Based on recorded consumption and waste</p>
        </div>

        {/* Money Saved */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-soft">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Est. Value Consumed</span>
            <DollarSign className="w-5 h-5 text-emerald-600" />
          </div>
          <div className="text-2xl sm:text-3xl font-black text-slate-900">
            ${stats.money_saved}
          </div>
          <p className="text-[11px] text-emerald-600 font-medium mt-1">Estimated value of consumed food</p>
        </div>

        {/* Total Consumed */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-soft">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Items Consumed</span>
            <CheckCircle2 className="w-5 h-5 text-emerald-600" />
          </div>
          <div className="text-2xl sm:text-3xl font-black text-slate-900">
            {stats.total_consumed}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">Safely cooked & eaten</p>
        </div>

        {/* Food Wasted */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-soft">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Items Discarded</span>
            <Trash2 className="w-5 h-5 text-rose-500" />
          </div>
          <div className="text-2xl sm:text-3xl font-black text-rose-600">
            {stats.total_wasted}
          </div>
          <p className="text-[11px] text-rose-500 font-medium mt-1">Est. loss: ${stats.money_wasted}</p>
        </div>
      </div>

      {/* Monthly Consumed vs Wasted Bar Chart */}
      {monthlyComparison.length > 0 && (
        <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-soft">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-slate-800">Monthly Consumption vs Waste</h3>
              <p className="text-xs text-slate-500"> Recorded consumption and waste over the last 5 calendar months</p>
            </div>
           <span
  className={`text-xs font-semibold px-2.5 py-1 rounded-full ${wasteTrendClass}`}
>
  {wasteTrendText}</span>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={monthlyComparison} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="month" stroke="#94a3b8" fontSize={11} tickLine={false} />
                <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    borderRadius: '12px',
                    boxShadow: '0 4px 15px rgba(0,0,0,0.08)',
                    border: '1px solid #e2e8f0',
                    fontSize: '12px'
                  }}
                />
                <Legend verticalAlign="top" align="right" wrapperStyle={{ fontSize: '11px', paddingBottom: '10px' }} />
                <Bar dataKey="consumed" name="Consumed Items" fill="#22c55e" radius={[6, 6, 0, 0]} />
                <Bar dataKey="wasted" name="Wasted Items" fill="#f43f5e" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )} {totalResolvedActivities === 0 && (
  <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
    <p className="font-semibold">
      No consumption or waste activity recorded yet
    </p>
    <p className="mt-1 text-xs">
      Mark food items as consumed or discarded to build your analytics
      from actual activity records.
    </p>
  </div>
)}

      {/* Activity Timeline Table */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-soft p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-bold text-slate-800">Activity Timeline</h3>
            <p className="text-xs text-slate-500">Log of added, eaten, and disposed items</p>
          </div>

          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={filterAction}
              onChange={(e) => setFilterAction(e.target.value)}
              className="text-xs px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white focus:outline-none"
            >
              <option value="">All Actions</option>
              <option value="added">Added</option>
              <option value="used">Consumed</option>
              <option value="discarded">Discarded</option>
            </select>
          </div>
        </div>

        <div className="space-y-2.5">
          {data?.timeline && data.timeline.length > 0 ? (
            data.timeline.map((act: any) => (
              <div
                key={act.id}
                className="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-100 text-xs hover:bg-slate-100/70 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-white border border-slate-200 flex items-center justify-center font-bold">
                    {act.action === 'used' ? '✅' : act.action === 'added' ? '📥' : '🗑️'}
                  </div>
                  <div>
                    <p className="font-bold text-slate-800">{act.food_item_name}</p>
                    <p className="text-[11px] text-slate-400">
                      {act.quantity} {act.unit} {act.estimated_cost ? `• $${act.estimated_cost}` : ''}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {getActionBadge(act.action)}
                  <span className="text-[11px] text-slate-400 hidden sm:inline">
                    {new Date(act.timestamp).toLocaleDateString()}
                  </span>
                </div>
              </div>
            ))
          ) : (
            <p className="text-xs text-slate-400 text-center py-6 italic">No activity records logged.</p>
          )}
        </div>
      </div>
    </div>
  );
};
