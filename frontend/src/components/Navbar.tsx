import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Bell, Plus, Menu, Sparkles, User as UserIcon, LogOut } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface NavbarProps {
  unreadAlertsCount?: number;
  onMenuToggle?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ unreadAlertsCount = 0, onMenuToggle }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const firstName = user?.full_name?.split(' ')[0] || 'Chef';

  return (
    <header className="sticky top-0 z-30 bg-white/90 backdrop-blur-md border-b border-slate-200/80 px-4 sm:px-8 py-3.5 flex items-center justify-between">
      {/* Left: Mobile hamburger & Greeting */}
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuToggle}
          className="lg:hidden p-2 rounded-xl text-slate-600 hover:bg-slate-100 transition-colors"
          aria-label="Toggle menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-bold text-slate-800 tracking-tight">
              Hello, {firstName} 👋
            </h2>
          </div>
          <p className="text-xs text-slate-500 hidden sm:block">
            Your smart pantry is monitored and fresh.
          </p>
        </div>
      </div>

      {/* Right: Quick Add + Notification Bell + User Avatar */}
      <div className="flex items-center gap-3">
        {/* Quick Add Food Button */}
        <Link
          to="/add-food"
          className="flex items-center gap-2 bg-gradient-to-r from-emerald-600 to-green-500 hover:from-emerald-700 hover:to-green-600 text-white px-3.5 py-2 rounded-xl text-xs sm:text-sm font-semibold shadow-sm shadow-emerald-500/20 transition-all transform active:scale-95"
        >
          <Plus className="w-4 h-4 stroke-[2.5]" />
          <span className="hidden sm:inline">Add Food</span>
        </Link>

        {/* Notification Bell */}
        <button
          onClick={() => navigate('/alerts')}
          className="relative p-2.5 rounded-xl border border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-all duration-150"
          aria-label="Notifications"
        >
          <Bell className="w-5 h-5" />
          {unreadAlertsCount > 0 && (
            <span className="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-rose-500 text-[10px] font-bold text-white shadow-xs">
              {unreadAlertsCount > 9 ? '9+' : unreadAlertsCount}
            </span>
          )}
        </button>
         {/* Logout Button — ADD THIS */}
        <button
          onClick={() => {
            logout();
            navigate('/');
          }}
          className="flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
        >
          <LogOut size={18} />
          <span>Logout</span>
        </button>
        {/* User Avatar / Profile shortcut */}
        <button
          type="button"
          onClick={() => navigate('/settings#profile')}
          title="Profile settings"
          aria-label="Open profile settings"
          className="flex items-center gap-2 pl-1 rounded-full focus:outline-none focus:ring-2 focus:ring-emerald-500"
        >
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-emerald-100 to-emerald-200 border-2 border-emerald-400 flex items-center justify-center text-emerald-800 font-bold text-sm shadow-xs">
            {firstName.charAt(0)}
          </div>
        </button>
      </div>
    </header>
  );
};
