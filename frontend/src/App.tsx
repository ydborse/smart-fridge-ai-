import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { NotificationProvider } from './context/NotificationContext';
import { Sidebar } from './components/Sidebar';
import { Navbar } from './components/Navbar';
import { Dashboard } from './pages/Dashboard';
import { Zones } from './pages/Zones';
import { FoodManagement } from './pages/FoodManagement';
import { AddFood } from './pages/AddFood';
import { WeeklyAudit } from './pages/WeeklyAudit';
import { Alerts } from './pages/Alerts';
import { History } from './pages/History';
import { DatasetReview } from './pages/DatasetReview';
import { Settings } from './pages/Settings';
import { DairyRecognition } from './pages/DairyRecognition';
import { alertsApi, setConnectionErrorListener, checkBackendHealth } from './services/api';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Login } from './pages/login';

const AppContent: React.FC = () => {
  const [unreadAlerts, setUnreadAlerts] = useState<number>(0);
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(false);
  const [isBackendOffline, setIsBackendOffline] = useState<boolean>(false);
  const { user, loading } = useAuth();
  
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
    // Use dynamic polling: normal interval 20s if connected, slower 45s health probe if disconnected
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

      {/* Sidebar Navigation */}
      <Sidebar
        unreadAlertsCount={unreadAlerts}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Backend Disconnected Alert Banner */}
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
        />

        <main className="flex-1 p-4 sm:p-8 max-w-7xl w-full mx-auto overflow-y-auto">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/zones" element={<Zones />} />
            <Route path="/foods" element={<FoodManagement />} />
            <Route path="/add-food" element={<AddFood />} />
            <Route path="/dairy-ai" element={<DairyRecognition />} />
            <Route path="/audit" element={<WeeklyAudit />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/history" element={<History />} />
            <Route path="/dataset" element={<DatasetReview />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <Router>
      <AuthProvider>
        <NotificationProvider>
          <AppContent />
        </NotificationProvider>
      </AuthProvider>
    </Router>
  );
};

export default App;
