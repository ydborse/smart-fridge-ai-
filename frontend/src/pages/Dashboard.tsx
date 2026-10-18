import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Package,
  Sparkles,
  AlertTriangle,
  XCircle,
  ArrowRight,
  Clock,
  Plus,
  Layers,
  ChevronRight,
  TrendingDown,
  Info
} from 'lucide-react';
import { dashboardApi } from '../services/api';
import { DashboardSummary } from '../types';
import { SensorCharts } from '../components/SensorCharts';
import { getFoodEmoji } from '../utils/foodIcons';

export const Dashboard: React.FC = () => {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const loadData = async () => {
    try {
      setLoading(true);
      const res = await dashboardApi.getSummary();
      setData(res);
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 20000); // refresh every 20s
    return () => clearInterval(interval);
  }, []);

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-sm font-medium text-slate-500">Syncing with smart fridge...</p>
        </div>
      </div>
    );
  }

  const stats = data?.stats || { total_items: 24, fresh_items: 14, expiring_soon_items: 6, expired_items: 4 };

  return (
    <div className="space-y-6">
      {/* 1. Hero Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-emerald-600 via-emerald-500 to-green-500 p-6 sm:p-8 text-white shadow-lg shadow-emerald-500/15">
        <div className="relative z-10 max-w-xl">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-white/20 backdrop-blur-md mb-3">
            <Sparkles className="w-3.5 h-3.5" />
            AI Freshness Assistant
          </span>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white mb-2">
            Eat Fresh, Stay Healthy.
          </h1>
          <p className="text-sm text-emerald-50 leading-relaxed mb-5">
            Your refrigerator is keeping your pantry safe. Scan groceries with your phone camera,
            prevent food waste, and receive instant alerts before spoilage occurs.
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <Link
              to="/foods"
              className="inline-flex items-center gap-2 bg-white text-emerald-800 hover:bg-emerald-50 px-5 py-2.5 rounded-xl font-bold text-sm shadow-md transition-all active:scale-95"
            >
              View Food Items
              <ArrowRight className="w-4 h-4 stroke-[2.5]" />
            </Link>
            <Link
              to="/add-food"
              className="inline-flex items-center gap-2 bg-emerald-700/60 hover:bg-emerald-700/80 text-white px-4 py-2.5 rounded-xl font-semibold text-sm backdrop-blur-md border border-white/20 transition-all"
            >
              <Plus className="w-4 h-4" />
              Quick Scan
            </Link>
          </div>
        </div>

        {/* Decorative background circle */}
        <div className="absolute -right-12 -bottom-12 w-64 h-64 rounded-full bg-white/10 blur-2xl pointer-events-none" />
      </div>

      {/* 2. Stat Cards Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
        {/* Total Items */}
        <div
          onClick={() => navigate('/foods')}
          className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-soft hover:shadow-card cursor-pointer transition-all duration-200 group"
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
              Total Items
            </span>
            <div className="w-9 h-9 rounded-xl bg-slate-100 group-hover:bg-slate-200/80 flex items-center justify-center text-slate-700 transition-colors">
              <Package className="w-5 h-5 stroke-[2.2]" />
            </div>
          </div>
          <div className="text-3xl font-black text-slate-900 tracking-tight">
            {stats.total_items}
          </div>
          <p className="text-[11px] text-slate-400 mt-1 flex items-center gap-1">
            Across 5 shelves
          </p>
        </div>

        {/* Fresh Items */}
        <div
          onClick={() => navigate('/foods?status=Fresh')}
          className="bg-white p-5 rounded-2xl border border-emerald-100 shadow-soft hover:shadow-card cursor-pointer transition-all duration-200 group"
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold text-emerald-700 uppercase tracking-wider">
              Fresh Items
            </span>
            <div className="w-9 h-9 rounded-xl bg-emerald-50 group-hover:bg-emerald-100 flex items-center justify-center text-emerald-600 transition-colors">
              <Sparkles className="w-5 h-5 stroke-[2.2]" />
            </div>
          </div>
          <div className="text-3xl font-black text-emerald-600 tracking-tight">
            {stats.fresh_items}
          </div>
          <p className="text-[11px] text-emerald-600 font-medium mt-1">
            Safe & optimal state
          </p>
        </div>

        {/* Expiring Soon */}
        <div
          onClick={() => navigate('/foods?status=Expiring')}
          className="bg-white p-5 rounded-2xl border border-amber-100 shadow-soft hover:shadow-card cursor-pointer transition-all duration-200 group"
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold text-amber-700 uppercase tracking-wider">
              Expiring Soon
            </span>
            <div className="w-9 h-9 rounded-xl bg-amber-50 group-hover:bg-amber-100 flex items-center justify-center text-amber-600 transition-colors">
              <Clock className="w-5 h-5 stroke-[2.2]" />
            </div>
          </div>
          <div className="text-3xl font-black text-amber-600 tracking-tight">
            {stats.expiring_soon_items}
          </div>
          <p className="text-[11px] text-amber-600 font-medium mt-1">
            ≤ 3 days left
          </p>
        </div>

        {/* Expired / Attention */}
        <div
          onClick={() => navigate('/foods?status=Expired')}
          className="bg-white p-5 rounded-2xl border border-rose-100 shadow-soft hover:shadow-card cursor-pointer transition-all duration-200 group"
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold text-rose-700 uppercase tracking-wider">
              Expired
            </span>
            <div className="w-9 h-9 rounded-xl bg-rose-50 group-hover:bg-rose-100 flex items-center justify-center text-rose-600 transition-colors">
              <XCircle className="w-5 h-5 stroke-[2.2]" />
            </div>
          </div>
          <div className="text-3xl font-black text-rose-600 tracking-tight">
            {stats.expired_items}
          </div>
          <p className="text-[11px] text-rose-600 font-medium mt-1">
            Immediate action needed
          </p>
        </div>
      </div>

      {/* 3. Today's Insights Panel */}
      {data?.insights && data.insights.length > 0 && (
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-soft">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-7 h-7 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <Info className="w-4 h-4 stroke-[2.5]" />
            </div>
            <h3 className="text-sm font-bold text-slate-800">Today's Smart Insights</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
            {data.insights.map((insight, idx) => (
              <div
                key={idx}
                className="flex items-start gap-2.5 p-3 rounded-xl bg-slate-50 border border-slate-100 text-xs text-slate-700"
              >
                <span className="text-sm flex-shrink-0">{insight.slice(0, 2)}</span>
                <span className="leading-relaxed">{insight.slice(2).trim()}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 4. Temperature & Humidity Telemetry Charts */}
      {data?.temperature_history_24h && (
        <SensorCharts
          temperatureHistory={data.temperature_history_24h}
          averageHumidity={72}
        />
      )}

      {/* 5. Two Columns: Items Expiring Soon + Recently Added */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Items Expiring Soon List */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-soft">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-slate-800">Items Expiring Soon</h3>
              <p className="text-xs text-slate-500">Eat or cook these first to eliminate waste</p>
            </div>
            <Link
              to="/foods?status=Expiring"
              className="text-xs font-semibold text-emerald-600 hover:text-emerald-700 flex items-center gap-1"
            >
              See All <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="space-y-2.5">
            {data?.expiring_soon && data.expiring_soon.length > 0 ? (
              data.expiring_soon.map((food) => (
                <div
                  key={food.id}
                  className="flex items-center justify-between p-3 rounded-xl bg-slate-50 hover:bg-slate-100/80 border border-slate-100 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-white border border-slate-200 flex items-center justify-center text-slate-700 font-bold text-base shadow-xs">
                      {getFoodEmoji(food.name, food.category)}
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-800">{food.name}</h4>
                      <p className="text-[11px] text-slate-400">
                        {food.zone_name} • {food.quantity} {food.unit}
                      </p>
                    </div>
                  </div>

                  <div className="text-right">
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        (food.days_until_expiry ?? 0) <= 0
                          ? 'bg-rose-100 text-rose-700'
                          : (food.days_until_expiry ?? 0) === 1
                          ? 'bg-amber-100 text-amber-700'
                          : 'bg-emerald-100 text-emerald-700'
                      }`}
                    >
                      {(food.days_until_expiry ?? 0) <= 0
                        ? 'Expired'
                        : `${food.days_until_expiry}d left`}
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-400 text-center py-6 italic">
                No items currently expiring soon. Everything is fresh!
              </p>
            )}
          </div>
        </div>

        {/* Recently Added List */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-soft">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-slate-800">Recently Added</h3>
              <p className="text-xs text-slate-500">Latest groceries placed in the fridge</p>
            </div>
            <Link
              to="/foods"
              className="text-xs font-semibold text-emerald-600 hover:text-emerald-700 flex items-center gap-1"
            >
              See All <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="space-y-2.5">
            {data?.recently_added && data.recently_added.length > 0 ? (
              data.recently_added.map((food) => (
                <div
                  key={food.id}
                  className="flex items-center justify-between p-3 rounded-xl bg-slate-50 hover:bg-slate-100/80 border border-slate-100 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-white border border-slate-200 flex items-center justify-center text-slate-700 font-bold text-base shadow-xs">
                      {getFoodEmoji(food.name, food.category)}
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-800">{food.name}</h4>
                      <p className="text-[11px] text-slate-400">
                        {food.zone_name} • via {food.source.replace('_', ' ')}
                      </p>
                    </div>
                  </div>

                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700">
                    {food.freshness_status}
                  </span>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-400 text-center py-6 italic">
                No recent items logged.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
