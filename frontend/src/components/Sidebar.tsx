import React, { useState, useEffect, useCallback } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Layers,
  UtensilsCrossed,
  Sparkles,
  Milk,
  Camera,
  Bell,
  History,
  Settings,
  Database,
  Wifi,
  ShieldAlert,
  CookingPot,
  ShoppingCart,
  ClipboardCheck,
  Droplets,
  Thermometer,
  RefreshCw,
  X,
  ArrowRight,
  ChevronDown,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { dashboardApi } from '../services/api';

interface SidebarProps {
  unreadAlertsCount?: number;
  isOpen?: boolean;
  onClose?: () => void;
}

interface NavItem {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
  count?: number;
}

interface SensorPoint {
  time: string;
  top_shelf?: number;
  middle_shelf?: number;
  bottom_shelf?: number;
  veg_drawer?: number;
  top_hum?: number;
  middle_hum?: number;
  bottom_hum?: number;
  veg_hum?: number;
  avg_humidity?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({ unreadAlertsCount = 0, isOpen = true, onClose }) => {
  const navigate = useNavigate();

  // Live Climate Popover state
  const [climateOpen, setClimateOpen] = useState(false);
  const [climateTab, setClimateTab] = useState<'humidity' | 'temperature'>('humidity');
  const [climateLoading, setClimateLoading] = useState(false);
  const [sensorHistory, setSensorHistory] = useState<SensorPoint[]>([]);
  const [avgHumidity, setAvgHumidity] = useState<number>(72);
  const [avgTemp, setAvgTemp] = useState<number | null>(null);
  const [latestPoint, setLatestPoint] = useState<SensorPoint | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string>('');

  const fetchClimateData = useCallback(async () => {
    try {
      setClimateLoading(true);
      const summary = await dashboardApi.getSummary();
      const rawHistory: SensorPoint[] = Array.isArray(summary?.temperature_history_24h)
        ? summary.temperature_history_24h
        : [];

      const enriched = rawHistory.map((pt) => {
        const hums = [pt.top_hum, pt.middle_hum, pt.bottom_hum, pt.veg_hum].filter(
          (v): v is number => typeof v === 'number' && Number.isFinite(v)
        );
        const avgHum = hums.length ? Math.round(hums.reduce((a, b) => a + b, 0) / hums.length) : undefined;
        return { ...pt, avg_humidity: avgHum };
      });

      setSensorHistory(enriched);

      const latest = enriched.at(-1) || null;
      setLatestPoint(latest);

      if (latest) {
        if (typeof latest.avg_humidity === 'number') {
          setAvgHumidity(latest.avg_humidity);
        }
        const temps = [latest.top_shelf, latest.middle_shelf, latest.bottom_shelf, latest.veg_drawer].filter(
          (v): v is number => typeof v === 'number' && Number.isFinite(v)
        );
        if (temps.length) {
          setAvgTemp(Number((temps.reduce((a, b) => a + b, 0) / temps.length).toFixed(1)));
        }
      }

      setLastUpdated(
        new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      );
    } catch (err) {
      console.error('Failed to load live climate data:', err);
    } finally {
      setClimateLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!climateOpen) return;
    fetchClimateData();
    const timer = window.setInterval(fetchClimateData, 15000);
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setClimateOpen(false);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [climateOpen, fetchClimateData]);

  const clampedHumidity = Math.max(0, Math.min(100, Math.round(avgHumidity)));
  const gaugeData = [
    { name: 'Humidity', value: clampedHumidity, color: '#059669' },
    { name: 'Remaining', value: Math.max(0, 100 - clampedHumidity), color: '#e2e8f0' },
  ];

  const humidityStatus =
    clampedHumidity >= 85
      ? { label: 'High', cls: 'bg-amber-100 text-amber-800' }
      : clampedHumidity <= 40
      ? { label: 'Dry', cls: 'bg-sky-100 text-sky-800' }
      : { label: 'Optimal', cls: 'bg-emerald-100 text-emerald-800' };

  const navGroups: { heading: string; items: NavItem[] }[] = [
    {
      heading: 'My Kitchen',
      items: [
        { to: '/', label: 'Dashboard', icon: LayoutDashboard },
        { to: '/zones', label: 'Refrigerator Zones', icon: Layers },
        { to: '/foods', label: 'Food Inventory', icon: UtensilsCrossed },
        { to: '/recipes', label: 'Meal Ideas', icon: CookingPot },
        { to: '/shopping-list', label: 'Shopping List', icon: ShoppingCart },
      ],
    },
    {
      heading: 'AI Vision',
      items: [
        { to: '/add-food', label: 'Add Food & Scan', icon: Sparkles, badge: 'AI' },
        { to: '/webcam', label: 'Live Webcam Scan', icon: Camera, badge: 'LIVE' },
        { to: '/dairy-ai', label: 'Dairy Label AI', icon: Milk },
        { to: '/audit', label: 'Weekly Fridge Audit', icon: ClipboardCheck },
      ],
    },
    {
      heading: 'Insights & System',
      items: [
        { to: '/alerts', label: 'Alerts', icon: Bell, count: unreadAlertsCount },
        { to: '/history', label: 'History & Impact', icon: History },
        { to: '/dataset', label: 'AI Accuracy', icon: Database },
        { to: '/settings', label: 'Settings', icon: Settings },
      ],
    },
  ];

  return (
    <>
      <aside
        className={`fixed lg:static inset-y-0 left-0 z-40 w-72 bg-white border-r border-slate-200/80 flex flex-col h-screen transition-transform duration-300 ease-in-out shadow-sm ${
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Interactive Brand Header — Click to open Live Fridge Climate */}
        <div className="px-4 py-3.5 border-b border-slate-100 flex items-center justify-between shrink-0">
          <button
            type="button"
            onClick={() => setClimateOpen((prev) => !prev)}
            title="Click to view live fridge humidity & temperature"
            className={`flex items-center gap-3 w-full text-left p-1.5 -m-1 rounded-2xl transition-all group ${
              climateOpen ? 'bg-emerald-50/80 ring-1 ring-emerald-200' : 'hover:bg-slate-50'
            }`}
          >
            <div className="relative w-11 h-11 rounded-2xl bg-gradient-to-br from-[#1b4332] via-[#059669] to-[#34d399] flex items-center justify-center shadow-lg shadow-emerald-600/25 ring-1 ring-inset ring-white/25 shrink-0 transition-transform group-hover:scale-105">
              <svg
                viewBox="0 0 40 40"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                className="w-7 h-7"
                aria-hidden="true"
              >
                <rect
                  x="10"
                  y="7"
                  width="17"
                  height="26"
                  rx="4.5"
                  fill="white"
                  fillOpacity="0.18"
                  stroke="white"
                  strokeWidth="2"
                />
                <line x1="10.5" y1="16.5" x2="26.5" y2="16.5" stroke="white" strokeWidth="1.8" />
                <line x1="22.5" y1="11.2" x2="22.5" y2="14" stroke="white" strokeWidth="2" strokeLinecap="round" />
                <line x1="22.5" y1="19.5" x2="22.5" y2="24" stroke="white" strokeWidth="2" strokeLinecap="round" />
                <path
                  d="M14.2 26.2C14.2 22.8 17.1 20.8 19.6 21C19.6 23.9 17.6 26.4 14.2 26.2Z"
                  fill="#A7F3D0"
                />
                <path
                  d="M31 7.5L32.1 10.6L35.2 11.7L32.1 12.8L31 15.9L29.9 12.8L26.8 11.7L29.9 10.6L31 7.5Z"
                  fill="#FEF08A"
                />
              </svg>
              <span className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full bg-emerald-400 border-2 border-white animate-pulse" />
            </div>

            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-1.5">
                <h1 className="text-[16px] font-extrabold tracking-tight text-slate-900 leading-none">
                  Smart Fridge
                </h1>
                <span className="text-[9px] font-black uppercase tracking-wider px-1.5 py-0.5 rounded-md bg-emerald-600 text-white">
                  AI
                </span>
              </div>
              <p className="text-[11px] font-medium text-emerald-700/90 tracking-wide mt-1 flex items-center gap-1">
                <span>Live Climate &amp; Status</span>
                <ChevronDown
                  className={`w-3 h-3 transition-transform duration-200 ${climateOpen ? 'rotate-180' : ''}`}
                />
              </p>
            </div>
          </button>

          {onClose && (
            <button
              onClick={onClose}
              aria-label="Close navigation"
              className="lg:hidden ml-2 p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
            >
              ✕
            </button>
          )}
        </div>

        {/* Grouped Navigation */}
        <nav aria-label="Main navigation" className="flex-1 overflow-y-auto px-3.5 py-3 space-y-4">
          {navGroups.map((group) => (
            <div key={group.heading}>
              <p className="px-3 mb-1.5 text-[10px] font-bold uppercase tracking-widest text-slate-400">
                {group.heading}
              </p>
              <div className="space-y-0.5">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      end={item.to === '/'}
                      onClick={onClose}
                      className={({ isActive }) =>
                        `flex items-center justify-between px-3 py-2 rounded-xl text-[13px] font-medium transition-all duration-150 group ${
                          isActive
                            ? 'bg-emerald-50 text-emerald-700 font-semibold shadow-xs'
                            : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                        }`
                      }
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <Icon className="w-4 h-4 shrink-0" />
                        <span className="truncate">{item.label}</span>
                      </div>
                      {item.badge && (
                        <span className="text-[9px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 tracking-wider shrink-0">
                          {item.badge}
                        </span>
                      )}
                      {item.count !== undefined && item.count > 0 && (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-500 text-white shadow-xs shrink-0">
                          {item.count > 99 ? '99+' : item.count}
                        </span>
                      )}
                    </NavLink>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        {/* Footer Status — Also clickable to open Live Climate */}
        <div className="p-3.5 border-t border-slate-100 space-y-2.5 bg-slate-50/50 shrink-0">
          <button
            type="button"
            onClick={() => setClimateOpen((prev) => !prev)}
            className="w-full text-left bg-white p-3 rounded-xl border border-slate-200/70 hover:border-emerald-300 shadow-xs flex items-center justify-between transition-colors"
          >
            <div className="flex items-center gap-2.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
              <div>
                <p className="text-xs font-semibold text-slate-800">Online – Fridge synced</p>
                <p className="text-[10px] text-slate-500">Click for live humidity &amp; temp</p>
              </div>
            </div>
            <Wifi className="w-4 h-4 text-emerald-600" />
          </button>

          <div className="flex items-start gap-1.5 px-1 text-[10px] text-slate-400 leading-tight">
            <ShieldAlert className="w-3.5 h-3.5 flex-shrink-0 text-slate-400 mt-0.5" />
            <span>Freshness predictions are assistive and not a food safety guarantee.</span>
          </div>
        </div>
      </aside>

      {/* Floating Live Fridge Climate Popover */}
      {climateOpen && (
        <>
          <div
            className="fixed inset-0 z-50 bg-slate-900/20 backdrop-blur-[1px]"
            onClick={() => setClimateOpen(false)}
          />
          <div
            role="dialog"
            aria-label="Live Fridge Climate"
            className="fixed z-50 left-3 right-3 top-20 lg:left-[296px] lg:right-auto lg:top-4 lg:w-[410px] bg-white rounded-3xl border border-slate-200 shadow-2xl shadow-slate-900/15 overflow-hidden animate-in fade-in zoom-in-95 duration-200"
          >
            {/* Popover Header */}
            <div className="px-5 py-4 bg-gradient-to-r from-[#1b4332] via-[#059669] to-[#10b981] text-white flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-200 animate-pulse" />
                <div>
                  <h2 className="text-sm font-bold leading-tight">Live Fridge Climate</h2>
                  <p className="text-[11px] text-emerald-100">
                    {lastUpdated ? `Synced at ${lastUpdated}` : 'Connecting to sensors...'}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={fetchClimateData}
                  title="Refresh live readings"
                  className="p-1.5 rounded-lg bg-white/15 hover:bg-white/25 transition-colors"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${climateLoading ? 'animate-spin' : ''}`} />
                </button>
                <button
                  type="button"
                  onClick={() => setClimateOpen(false)}
                  title="Close"
                  className="p-1.5 rounded-lg bg-white/15 hover:bg-white/25 transition-colors"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            <div className="p-5 space-y-4">
              {/* Top Row: Humidity Arc Gauge + Quick Zone Metrics */}
              <div className="grid grid-cols-12 gap-3 items-center">
                <div className="col-span-5 flex flex-col items-center justify-center p-2.5 rounded-2xl bg-slate-50 border border-slate-100">
                  <div className="relative w-28 h-24">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={gaugeData}
                          cx="50%"
                          cy="58%"
                          innerRadius={32}
                          outerRadius={44}
                          startAngle={215}
                          endAngle={-35}
                          paddingAngle={0}
                          dataKey="value"
                          stroke="none"
                        >
                          {gaugeData.map((entry, idx) => (
                            <Cell key={`gauge-${idx}`} fill={entry.color} />
                          ))}
                        </Pie>
                      </PieChart>
                    </ResponsiveContainer>
                    <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center pt-2">
                      <span className="text-xl font-black text-slate-900 leading-none">{clampedHumidity}%</span>
                      <span className="text-[9px] font-bold uppercase tracking-wider text-slate-400 mt-0.5">
                        Humidity
                      </span>
                    </div>
                  </div>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${humidityStatus.cls}`}>
                    {humidityStatus.label}
                  </span>
                </div>

                <div className="col-span-7 space-y-2">
                  <div className="p-3 rounded-2xl bg-emerald-50/70 border border-emerald-100 flex items-center justify-between">
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-wider text-emerald-700">Avg. Cooling</p>
                      <p className="text-xl font-black text-slate-900 leading-tight mt-0.5">
                        {avgTemp !== null ? `${avgTemp}°C` : '3.8°C'}
                      </p>
                    </div>
                    <div className="w-9 h-9 rounded-xl bg-emerald-600 text-white flex items-center justify-center">
                      <Thermometer className="w-4 h-4" />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-1.5 text-[11px]">
                    <div className="px-2.5 py-1.5 rounded-xl bg-slate-50 border border-slate-100 flex justify-between">
                      <span className="text-slate-500">Top</span>
                      <span className="font-bold text-slate-800">
                        {latestPoint?.top_shelf !== undefined ? `${latestPoint.top_shelf}°C` : '4.0°C'}
                      </span>
                    </div>
                    <div className="px-2.5 py-1.5 rounded-xl bg-slate-50 border border-slate-100 flex justify-between">
                      <span className="text-slate-500">Middle</span>
                      <span className="font-bold text-slate-800">
                        {latestPoint?.middle_shelf !== undefined ? `${latestPoint.middle_shelf}°C` : '3.2°C'}
                      </span>
                    </div>
                    <div className="px-2.5 py-1.5 rounded-xl bg-slate-50 border border-slate-100 flex justify-between">
                      <span className="text-slate-500">Bottom</span>
                      <span className="font-bold text-slate-800">
                        {latestPoint?.bottom_shelf !== undefined ? `${latestPoint.bottom_shelf}°C` : '2.1°C'}
                      </span>
                    </div>
                    <div className="px-2.5 py-1.5 rounded-xl bg-slate-50 border border-slate-100 flex justify-between">
                      <span className="text-slate-500">Veg Box</span>
                      <span className="font-bold text-slate-800">
                        {latestPoint?.veg_hum !== undefined ? `${latestPoint.veg_hum}%` : `${clampedHumidity}%`}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Chart Mode Switcher */}
              <div className="flex items-center justify-between gap-2">
                <div className="inline-flex p-1 rounded-xl bg-slate-100 border border-slate-200/70">
                  <button
                    type="button"
                    onClick={() => setClimateTab('humidity')}
                    className={`px-3 py-1 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all ${
                      climateTab === 'humidity'
                        ? 'bg-white text-emerald-700 shadow-xs'
                        : 'text-slate-500 hover:text-slate-800'
                    }`}
                  >
                    <Droplets className="w-3.5 h-3.5" />
                    Humidity (%)
                  </button>
                  <button
                    type="button"
                    onClick={() => setClimateTab('temperature')}
                    className={`px-3 py-1 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all ${
                      climateTab === 'temperature'
                        ? 'bg-white text-emerald-700 shadow-xs'
                        : 'text-slate-500 hover:text-slate-800'
                    }`}
                  >
                    <Thermometer className="w-3.5 h-3.5" />
                    Temp (°C)
                  </button>
                </div>
                <span className="text-[11px] font-medium text-slate-400">Last 24 hours</span>
              </div>

              {/* Live Chart */}
              <div className="h-44 w-full rounded-2xl border border-slate-100 bg-slate-50/50 p-2">
                {sensorHistory.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    {climateTab === 'humidity' ? (
                      <AreaChart data={sensorHistory} margin={{ top: 8, right: 8, left: -24, bottom: 0 }}>
                        <defs>
                          <linearGradient id="humidityFill" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#10b981" stopOpacity={0.35} />
                            <stop offset="95%" stopColor="#10b981" stopOpacity={0.02} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                        <XAxis dataKey="time" stroke="#94a3b8" fontSize={10} tickLine={false} />
                        <YAxis stroke="#94a3b8" fontSize={10} tickLine={false} unit="%" domain={['auto', 'auto']} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#ffffff',
                            borderRadius: '10px',
                            border: '1px solid #e2e8f0',
                            fontSize: '11px',
                          }}
                        />
                        <Area
                          type="monotone"
                          dataKey="avg_humidity"
                          name="Avg. Humidity (%)"
                          stroke="#059669"
                          strokeWidth={2.5}
                          fill="url(#humidityFill)"
                          connectNulls
                        />
                      </AreaChart>
                    ) : (
                      <LineChart data={sensorHistory} margin={{ top: 8, right: 8, left: -24, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                        <XAxis dataKey="time" stroke="#94a3b8" fontSize={10} tickLine={false} />
                        <YAxis stroke="#94a3b8" fontSize={10} tickLine={false} unit="°C" domain={['auto', 'auto']} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#ffffff',
                            borderRadius: '10px',
                            border: '1px solid #e2e8f0',
                            fontSize: '11px',
                          }}
                        />
                        <Line type="monotone" dataKey="top_shelf" name="Top shelf" stroke="#059669" strokeWidth={2.2} dot={false} connectNulls />
                        <Line type="monotone" dataKey="middle_shelf" name="Middle shelf" stroke="#34d399" strokeWidth={2.2} dot={false} connectNulls />
                        <Line type="monotone" dataKey="bottom_shelf" name="Bottom shelf" stroke="#d97706" strokeWidth={2.2} dot={false} connectNulls />
                      </LineChart>
                    )}
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-xs text-slate-400">
                    {climateLoading ? 'Loading live sensor trends...' : 'No 24h sensor readings yet'}
                  </div>
                )}
              </div>

              {/* Footer Action */}
              <div className="pt-1 flex items-center justify-between">
                <span className="text-[11px] text-slate-400">Auto-refreshes every 15s</span>
                <button
                  type="button"
                  onClick={() => {
                    setClimateOpen(false);
                    navigate('/zones');
                    onClose?.();
                  }}
                  className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-700 hover:text-emerald-800 hover:underline"
                >
                  Open Refrigerator Zones
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
};