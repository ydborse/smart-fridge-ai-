import React from 'react';
import { NavLink } from 'react-router-dom';
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
  Refrigerator,
  Wifi,
  ShieldAlert
} from 'lucide-react';

interface SidebarProps {
  unreadAlertsCount?: number;
  isOpen?: boolean;
  onClose?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ unreadAlertsCount = 0, isOpen = true, onClose }) => {
  const navItems = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/zones', label: 'Refrigerator Zones', icon: Layers },
    { to: '/foods', label: 'Food Management', icon: UtensilsCrossed },
    { to: '/add-food', label: 'AI Recognition', icon: Sparkles, badge: 'AI' },
    { to: '/webcam', label: 'Webcam Recognition', icon: Camera, badge: 'NEW' },
    { to: '/dairy-ai', label: 'Dairy Packaging AI', icon: Milk, badge: 'NEW' },
    { to: '/audit', label: 'Weekly Fridge Audit', icon: Camera },
    { to: '/alerts', label: 'Alerts', icon: Bell, count: unreadAlertsCount },
    { to: '/history', label: 'History & Waste', icon: History },
    { to: '/dataset', label: 'Dataset & AI Retrain', icon: Database },
    { to: '/settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside
      className={`fixed lg:static inset-y-0 left-0 z-40 w-72 bg-white border-r border-slate-200/80 flex flex-col justify-between transition-transform duration-300 ease-in-out shadow-sm ${
        isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
      }`}
    >
      {/* Top Branding */}
      <div>
        <div className="p-6 pb-5 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-emerald-600 to-green-400 flex items-center justify-center text-white shadow-md shadow-emerald-500/20">
              <Refrigerator className="w-6 h-6 stroke-[2.2]" />
            </div>
            <div>
              <h1 className="text-base font-bold tracking-tight text-slate-900 leading-tight">
                Smart Fridge
              </h1>
              <p className="text-[11px] font-medium text-emerald-600 tracking-wide">
                Smart Food. Healthy You.
              </p>
            </div>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
            >
              ✕
            </button>
          )}
        </div>

        {/* Navigation Items */}
        <nav className="p-4 space-y-1.5 overflow-y-auto max-h-[calc(100vh-270px)]">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={onClose}
                className={({ isActive }) =>
                  `flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 group ${
                    isActive
                      ? 'bg-emerald-50 text-emerald-700 font-semibold shadow-xs'
                      : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                  }`
                }
              >
                <div className="flex items-center gap-3">
                  <Icon className="w-5 h-5 transition-transform duration-200 group-hover:scale-110" />
                  <span>{item.label}</span>
                </div>

                {item.badge && (
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 tracking-wider">
                    {item.badge}
                  </span>
                )}

                {item.count !== undefined && item.count > 0 && (
                  <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-rose-500 text-white shadow-xs animate-pulse">
                    {item.count}
                  </span>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Bottom Status Card & Disclaimer */}
      <div className="p-4 border-t border-slate-100 space-y-3 bg-slate-50/50">
        {/* Sync Status Card */}
        <div className="bg-white p-3.5 rounded-xl border border-slate-200/70 shadow-xs flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="relative flex items-center justify-center">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
              <span className="absolute w-4 h-4 rounded-full bg-emerald-400 animate-ping opacity-75"></span>
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-800 flex items-center gap-1.5">
                Online – Fridge synced
              </p>
              <p className="text-[10px] text-slate-500">ESP32 & Sensors live</p>
            </div>
          </div>
          <Wifi className="w-4 h-4 text-emerald-600" />
        </div>

        {/* Safety Disclaimer */}
        <div className="flex items-start gap-1.5 px-1 text-[10px] text-slate-400 leading-tight">
          <ShieldAlert className="w-3.5 h-3.5 flex-shrink-0 text-slate-400 mt-0.5" />
          <span>Freshness predictions are assistive and not a food safety guarantee.</span>
        </div>
      </div>
    </aside>
  );
};
