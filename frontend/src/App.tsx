import React, { useState, useEffect, Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { NotificationProvider } from './context/NotificationContext';
import { Sidebar } from './components/Sidebar';
import { Navbar } from './components/Navbar';
import { Dashboard } from './pages/Dashboard';
import { Login } from './pages/login';
import { alertsApi, setConnectionErrorListener, checkBackendHealth } from './services/api';
import { AlertTriangle, RefreshCw } from 'lucide-react';

// Lazy-load secondary routes to split the production JS bundle
const Zones = lazy(() => import('./pages/Zones').then((m) => ({ default: m.Zones })));
const FoodManagement = lazy(() => import('./pages/FoodManagement').then((m) => ({ default: m.FoodManagement })));
const AddFood = lazy(() => import('./pages/AddFood').then((m) => ({ default: m.AddFood })));
const WeeklyAudit = lazy(() => import('./pages/WeeklyAudit').then((m) => ({ default: m.WeeklyAudit })));
const Alerts = lazy(() => import('./pages/Alerts').then((m) => ({ default: m.Alerts })));
const History = lazy(() => import('./pages/History').then((m) => ({ default: m.History })));
const DatasetReview = lazy(() => import('./pages/DatasetReview').then((m) => ({ default: m.DatasetReview })));
const Settings = lazy(() => import('./pages/Settings').then((m) => ({ default: m.Settings })));
const DairyRecognition = lazy(() => import('./pages/DairyRecognition').then((m) => ({ default: m.DairyRecognition })));
const Recipes = lazy(() => import('./pages/Recipes').then((m) => ({ default: m.Recipes })));
const ShoppingList = lazy(() => import('./pages/ShoppingList').then((m) => ({ default: m.ShoppingList })));
const WebcamRecognition = lazy(() => import('./pages/WebcamRecognition'));

const AppContent: React.FC = () => {
  const [unreadAlerts, setUnreadAlerts] = useState<number>(0);
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(false);
  const [isBackendOffline, setIsBackendOffline] = useState<boolean>(false);
  const { user, loading } = useAuth();

  const [isDarkMode, setIsDarkMode] = useState<boolean>(() => {
    try {
      return window.localStorage.getItem('smart-fridge-theme') === 'dark';
    } catch {
      return false;
    }
  });

  useEffect(() => {
    const applyDark = isDarkMode && Boolean(user);
    document.documentElement.classList.toggle('dark', applyDark);
    document.documentElement.style.colorScheme = applyDark ? 'dark' : 'light';

    try {
      window.localStorage.setItem(
        'smart-fridge-theme',
        isDarkMode ? 'dark' : 'light',
      );
    } catch {
      // The selected theme still works for the current session.
    }
  }, [isDarkMode, user]);

  const fetchUnreadAlerts = async () => {
    try {
      const all = await alertsApi.getAll({ is_read: false });
      setUnreadAlerts(all.length);
      setIsBackendOffline(false);
    } catch (err: any) {
      if (!err.response || err.code === 'ERR_NETWORK' || (err.response && err.response.status >= 502)) {
        setIsBackendOffline(true);
      }
    }
  };

  useEffect(() => {
    setConnectionErrorListener((isDown) => {
      setIsBackendOffline(isDown);
    });

    fetchUnreadAlerts();
    const interval = setInterval(() => {
      if (isBackendOffline) {
        checkBackendHealth().then((healthy) => {
          if (healthy) {
            setIsBackendOffline(false);
            fetchUnreadAlerts();
          }
        });
      } else {
        fetchUnreadAlerts();
      }
    }, isBackendOffline ? 45000 : 20000);

    return () => clearInterval(interval);
  }, [isBackendOffline]);

  if (loading) {
    return <div className="p-8">Loading Smart Fridge AI...</div>;
  }

  if (!user) {
    return <Login />;
  }

  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-900 font-sans antialiased">
      <Sidebar
        unreadAlertsCount={unreadAlerts}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {isBackendOffline && (
          <div className="bg-amber-600 text-white px-4 py-2 text-xs sm:text-sm font-medium flex items-center justify-between shadow-md transition-all sticky top-0 z-50">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 animate-pulse text-amber-200" />
              <span>
                <strong>Backend Server Offline:</strong> Cannot communicate with FastAPI backend on <code className="bg-amber-700/80 px-1 py-0.5 rounded font-mono">http://127.0.0.1:8000</code>. Start it with <code className="bg-amber-700/80 px-1 py-0.5 rounded font-mono">.\start-dev.ps1</code> or <code className="bg-amber-700/80 px-1 py-0.5 rounded font-mono">npm run dev</code>.
              </span>
            </div>
            <button
              onClick={() => {
                checkBackendHealth().then((ok) => {
                  if (ok) {
                    setIsBackendOffline(false);
                    fetchUnreadAlerts();
                  }
                });
              }}
              className="ml-3 px-2.5 py-1 bg-white text-amber-900 rounded font-semibold text-xs hover:bg-amber-50 transition-colors shadow-sm flex items-center gap-1.5 flex-shrink-0"
            >
              <RefreshCw className="w-3 h-3" />
              Retry Connection
            </button>
          </div>
        )}

        <Navbar
          unreadAlertsCount={unreadAlerts}
          onMenuToggle={() => setSidebarOpen(!sidebarOpen)}
          isDarkMode={isDarkMode}
          onThemeToggle={() => setIsDarkMode((current) => !current)}
        />

        <main className="flex-1 p-4 sm:p-8 max-w-7xl w-full mx-auto overflow-y-auto">
          <Suspense fallback={<div className="p-8 text-sm text-slate-500">Loading page...</div>}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/zones" element={<Zones />} />
              <Route path="/foods" element={<FoodManagement />} />
              <Route path="/add-food" element={<AddFood />} />
              <Route path="/recipes" element={<Recipes />} />
              <Route path="/shopping-list" element={<ShoppingList />} />
              <Route path="/dairy-ai" element={<DairyRecognition />} />
              <Route path="/audit" element={<WeeklyAudit />} />
              <Route path="/alerts" element={<Alerts />} />
              <Route path="/history" element={<History />} />
              <Route path="/dataset" element={<DatasetReview />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/webcam" element={<WebcamRecognition />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </main>
      </div>
    </div>
  );
};

export const App: React.FC = () => (
  <Router>
    <AuthProvider>
      <NotificationProvider>
        <AppContent />
      </NotificationProvider>
    </AuthProvider>
  </Router>
);

export default App;