
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, Menu, LogOut, Moon, Sun } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface NavbarProps {
  unreadAlertsCount?: number;
  onMenuToggle?: () => void;
  isDarkMode?: boolean;
  onThemeToggle?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  unreadAlertsCount = 0,
  onMenuToggle,
  isDarkMode = false,
  onThemeToggle,
}) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const firstName = user?.full_name?.split(' ')[0] || 'Chef';

  return (
    <header className="sticky top-0 z-30 bg-white/90 backdrop-blur-md border-b border-slate-200/80 px-4 sm:px-8 py-3.5 flex items-center justify-between">
      {/* Left: Mobile hamburger and greeting */}
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
              Hello, {firstName} {String.fromCodePoint(0x1F44B)}
            </h2>
          </div>

          <p className="text-xs text-slate-500 hidden sm:block">
            Your smart pantry is monitored and fresh.
          </p>
        </div>
      </div>

      {/* Right: Theme toggle, notifications, logout and profile */}
      <div className="flex items-center gap-3">
        {/* Theme toggle */}
        <button
          type="button"
          onClick={onThemeToggle}
          disabled={!onThemeToggle}
          aria-label={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
          title={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
          className="flex items-center justify-center gap-2 theme-toggle-button rounded-xl border border-slate-200 px-3 py-2 text-slate-600 transition-colors hover:bg-slate-50"
        >
          {isDarkMode ? (
            <Sun className="h-4 w-4 theme-toggle-icon" />
          ) : (
            <Moon className="h-4 w-4 theme-toggle-icon" />
          )}

          <span className="hidden xl:inline text-xs font-medium">
            {isDarkMode ? 'Light mode' : 'Dark mode'}
          </span>
        </button>

        {/* Notification bell */}
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

        {/* Logout button */}
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

        {/* User avatar / profile shortcut */}
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
