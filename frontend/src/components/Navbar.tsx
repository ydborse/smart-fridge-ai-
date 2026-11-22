import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Bell,
  ChevronDown,
  History,
  LogOut,
  Menu,
  Moon,
  Settings,
  Sun,
  UserRound,
} from 'lucide-react';
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
  const [profileOpen, setProfileOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const fullName = user?.full_name || 'Smart Chef';
  const firstName = fullName.split(' ')[0] || 'Chef';
  const email = user?.email || '';

  useEffect(() => {
    if (!profileOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setProfileOpen(false);
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setProfileOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [profileOpen]);

  const goTo = (path: string) => {
    setProfileOpen(false);
    navigate(path);
  };

  return (
    <header className="sticky top-0 z-30 bg-white/90 backdrop-blur-md border-b border-slate-200/80 px-4 sm:px-8 py-3 flex items-center justify-between">
      {/* Left: Mobile hamburger and kitchen brand greeting */}
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuToggle}
          className="lg:hidden p-2 rounded-full text-slate-600 hover:bg-slate-100 transition-colors"
          aria-label="Toggle menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div>
          <div className="flex items-center gap-2.5">
            <h2 className="kitchen-heading text-xl sm:text-[22px] tracking-tight">
              {firstName}&rsquo;s Kitchen
            </h2>
            <span className="hidden sm:inline-flex items-center gap-1.5 rounded-full bg-emerald-50 border border-emerald-200/80 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-700">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Live
            </span>
          </div>

          <p className="text-xs text-slate-500 hidden sm:block mt-0.5">
            Smart pantry &amp; freshness assistant
          </p>
        </div>
      </div>

      {/* Right: Unified pill controls (Theme · Notifications · Profile chip) */}
      <div className="flex items-center gap-2.5">
        {/* Theme toggle pill */}
        <button
          type="button"
          onClick={onThemeToggle}
          disabled={!onThemeToggle}
          aria-label={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
          title={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
          className="inline-flex items-center gap-2 h-10 rounded-full border border-slate-200/90 bg-white px-3.5 text-xs font-semibold text-slate-700 shadow-xs hover:shadow-sm hover:bg-slate-50 transition-all"
        >
          {isDarkMode ? (
            <Sun className="h-4 w-4 text-amber-400" />
          ) : (
            <Moon className="h-4 w-4 text-slate-600" />
          )}
          <span className="hidden md:inline">
            {isDarkMode ? 'Light' : 'Dark'}
          </span>
        </button>

        {/* Circular notification bell */}
        <button
          type="button"
          onClick={() => navigate('/alerts')}
          className="relative inline-flex items-center justify-center w-10 h-10 rounded-full border border-slate-200/90 bg-white text-slate-700 shadow-xs hover:shadow-sm hover:bg-slate-50 transition-all"
          aria-label="Notifications"
          title="View alerts"
        >
          <Bell className="w-[18px] h-[18px]" />
          {unreadAlertsCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 flex h-5 min-w-[20px] px-1 items-center justify-center rounded-full bg-rose-500 text-[10px] font-bold text-white ring-2 ring-white">
              {unreadAlertsCount > 9 ? '9+' : unreadAlertsCount}
            </span>
          )}
        </button>

        {/* Profile pill chip + dropdown */}
        <div className="relative" ref={menuRef}>
          <button
            type="button"
            onClick={() => setProfileOpen((open) => !open)}
            title="Account & Profile"
            aria-label="Open profile menu"
            aria-expanded={profileOpen}
            className="inline-flex items-center gap-2 h-10 pl-1.5 pr-3 rounded-full border border-slate-200/90 bg-white shadow-xs hover:shadow-sm hover:bg-slate-50 transition-all focus:outline-none focus:ring-2 focus:ring-emerald-500/60"
          >
            <div className="w-7 h-7 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center text-white font-bold text-xs shadow-xs">
              {firstName.charAt(0).toUpperCase()}
            </div>
            <span className="hidden sm:inline text-xs font-semibold text-slate-800">
              {firstName}
            </span>
            <ChevronDown
              className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-200 ${
                profileOpen ? 'rotate-180' : ''
              }`}
            />
          </button>

          {profileOpen && (
            <div className="absolute right-0 mt-2.5 w-64 rounded-2xl border border-slate-200 bg-white shadow-xl overflow-hidden z-50">
              <div className="px-4 py-3.5 border-b border-slate-100 flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center text-white font-bold text-sm shrink-0">
                  {firstName.charAt(0).toUpperCase()}
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-bold text-slate-900 truncate">
                    {fullName}
                  </p>
                  {email && (
                    <p className="text-xs text-slate-500 truncate">{email}</p>
                  )}
                </div>
              </div>

              <div className="p-1.5 space-y-0.5">
                <button
                  type="button"
                  onClick={() => goTo('/settings#profile')}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors text-left"
                >
                  <UserRound className="w-4 h-4 text-emerald-600" />
                  Profile &amp; Contact
                </button>

                <button
                  type="button"
                  onClick={() => goTo('/settings')}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors text-left"
                >
                  <Settings className="w-4 h-4 text-emerald-600" />
                  Alerts &amp; Notification Settings
                </button>

                <button
                  type="button"
                  onClick={() => goTo('/history')}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors text-left"
                >
                  <History className="w-4 h-4 text-emerald-600" />
                  Consumption &amp; Waste History
                </button>

                {onThemeToggle && (
                  <button
                    type="button"
                    onClick={() => {
                      onThemeToggle();
                      setProfileOpen(false);
                    }}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors text-left"
                  >
                    {isDarkMode ? (
                      <Sun className="w-4 h-4 text-amber-500" />
                    ) : (
                      <Moon className="w-4 h-4 text-slate-500" />
                    )}
                    Switch to {isDarkMode ? 'Light mode' : 'Dark mode'}
                  </button>
                )}
              </div>

              <div className="p-1.5 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => {
                    setProfileOpen(false);
                    logout();
                    navigate('/');
                  }}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-semibold text-rose-600 hover:bg-rose-50 transition-colors text-left"
                >
                  <LogOut className="w-4 h-4" />
                  Sign out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};