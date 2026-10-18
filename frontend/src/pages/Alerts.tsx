import React, { useState, useEffect } from 'react';
import {
  Bell,
  CheckCheck,
  Trash2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  Thermometer,
  Sparkles,
  Send,
  RefreshCw,
  Clock,
  CheckCircle2,
  MessageSquare,
  ShieldCheck,
  Check,
  Smartphone,
  AlertOctagon,
  History,
  X,
  PackageX,
  Radio
} from 'lucide-react';
import { alertsApi, settingsApi } from '../services/api';
import { AlertItem, NotificationLog, SchedulerStatus } from '../types';
import { useNotification } from '../context/NotificationContext';
import { subscribeToWebPush } from '../services/pwa';

export const Alerts: React.FC = () => {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'resolved'>('all');
  const [evaluating, setEvaluating] = useState(false);
  const [sendingTest, setSendingTest] = useState(false);
  const [resolvingId, setResolvingId] = useState<number | null>(null);
  const [removingId, setRemovingId] = useState<number | null>(null);
  const [confirmRemoveAlert, setConfirmRemoveAlert] = useState<AlertItem | null>(null);

  // Push Permission State
  const [pushSupported, setPushSupported] = useState(false);
  const [pushPermission, setPushPermission] = useState<string>('default');
  const [enablingPush, setEnablingPush] = useState(false);

  // Notification History State
  const [showLogs, setShowLogs] = useState(false);
  const [logs, setLogs] = useState<NotificationLog[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);

  // Scheduler Status State
  const [schedulerStatus, setSchedulerStatus] = useState<SchedulerStatus | null>(null);

  const { showToast } = useNotification();

  useEffect(() => {
    if ('Notification' in window && 'serviceWorker' in navigator) {
      setPushSupported(true);
      setPushPermission(Notification.permission);
    }
  }, []);

  const loadAlerts = async () => {
    try {
      setLoading(true);
      const params: any = {};
      if (filterType) params.alert_type = filterType;
      if (statusFilter === 'active') params.is_resolved = false;
      if (statusFilter === 'resolved') params.is_resolved = true;
      const data = await alertsApi.getAll(params);
      setAlerts(data);
    } catch (err) {
      console.error('Failed to load alerts:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadLogs = async () => {
    try {
      setLogsLoading(true);
      const data = await settingsApi.getNotificationLogs(50);
      setLogs(data);
    } catch (err) {
      console.error('Failed to load notification logs:', err);
    } finally {
      setLogsLoading(false);
    }
  };

  const loadSchedulerStatus = async () => {
    try {
      const s = await alertsApi.getSchedulerStatus();
      setSchedulerStatus(s);
    } catch (err) {
      console.error('Failed to load scheduler status:', err);
    }
  };

  useEffect(() => {
    loadAlerts();
    loadSchedulerStatus();
    loadLogs();
  }, [filterType, statusFilter]);

  const handleResolveAlert = async (id: number) => {
    try {
      setResolvingId(id);
      await alertsApi.resolve(id);
      setAlerts((prev) =>
        prev.map((a) =>
          a.id === id
            ? {
                ...a,
                is_resolved: true,
                status: 'RESOLVED',
                is_read: true,
                resolved_at: new Date().toISOString(),
                next_reminder_at: undefined,
                next_sms_scheduled_at: undefined
              }
            : a
        )
      );
      showToast('success', 'Alert resolved. Recurring reminders have been silenced.', 'Alert Resolved');
    } catch (err) {
      showToast('error', 'Failed to resolve alert');
    } finally {
      setResolvingId(null);
    }
  };

  const handleConfirmRemoveFood = async () => {
    if (!confirmRemoveAlert) return;
    const alertId = confirmRemoveAlert.id;
    const foodName = confirmRemoveAlert.food_item_name || 'Food item';

    try {
      setRemovingId(alertId);
      await alertsApi.removeFood(alertId);
      setAlerts((prev) =>
        prev.map((a) =>
          a.id === alertId
            ? {
                ...a,
                is_resolved: true,
                status: 'REMOVED',
                is_read: true,
                resolved_at: new Date().toISOString(),
                next_reminder_at: undefined,
                next_sms_scheduled_at: undefined
              }
            : a
        )
      );
      setConfirmRemoveAlert(null);
      showToast(
        'success',
        `"${foodName}" was removed from fridge inventory and recurring reminders have been cancelled.`,
        'Food Removed'
      );
      await loadAlerts();
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to remove food item';
      showToast('error', msg);
    } finally {
      setRemovingId(null);
    }
  };

  const handleMarkRead = async (id: number) => {
    try {
      await alertsApi.markRead(id);
      setAlerts((prev) =>
        prev.map((a) =>
          a.id === id
            ? {
                ...a,
                is_read: true
              }
            : a
        )
      );
      showToast('info', 'Alert marked as read.');
    } catch (err) {
      showToast('error', 'Failed to update alert');
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await alertsApi.markAllRead();
      setAlerts((prev) =>
        prev.map((a) => ({
          ...a,
          is_read: true
        }))
      );
      showToast('success', 'All alerts marked as read');
    } catch (err) {
      showToast('error', 'Failed to update alerts');
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await alertsApi.delete(id);
      setAlerts((prev) => prev.filter((a) => a.id !== id));
      showToast('info', 'Alert dismissed');
    } catch (err) {
      showToast('error', 'Failed to delete alert');
    }
  };

  const handleTriggerEvaluation = async () => {
    setEvaluating(true);
    try {
      const res = await alertsApi.evaluate();
      showToast('success', res.message, 'Rules Evaluated');
      loadAlerts();
    } catch (err) {
      showToast('error', 'Evaluation failed');
    } finally {
      setEvaluating(false);
    }
  };

  const handleTestAlert = async () => {
    try {
      setSendingTest(true);
      const res = await alertsApi.testNotification('all');
      const tg = res.results?.telegram;
      const isTgSuccess = tg ? tg.success : (res.status === 'success');
      const summary = res.summary || 'Test alert processed';
      if (!isTgSuccess || res.status === 'partial_failure' || res.status === 'failed') {
        const errorDetail = tg?.error || tg?.detail || summary;
        showToast('error', errorDetail, 'Telegram Delivery Incomplete');
      } else {
        showToast('success', summary, 'Telegram Alert Confirmed');
      }
      await loadLogs();
      await loadSchedulerStatus();
    } catch (err: any) {
      let msg = err.response?.data?.detail;
      if (!msg) {
        if (err.response?.status === 502 || err.code === 'ERR_NETWORK') {
          msg = 'Backend API server is offline or unreachable on http://127.0.0.1:8000 (502 Bad Gateway). Please ensure the FastAPI backend is running.';
        } else {
          msg = err.message || 'Failed to dispatch test notification';
        }
      }
      showToast('error', msg, 'Dispatch Failure');
    } finally {
      setSendingTest(false);
    }
  };

  const handleEnablePush = async () => {
    setEnablingPush(true);
    try {
      const res = await subscribeToWebPush();
      if (res.success) {
        setPushPermission('granted');
        showToast('success', res.message, 'Mobile Push Enabled');
      } else {
        showToast('warning', res.message, 'Notification Notice');
      }
    } catch (err: any) {
      showToast('error', err.message || 'Failed to enable Web Push');
    } finally {
      setEnablingPush(false);
    }
  };

  const formatCountdown = (isoString?: string) => {
    if (!isoString) return null;
    const target = new Date(isoString).getTime();
    const now = new Date().getTime();
    const diffMs = target - now;
    if (diffMs <= 0) return 'Due now (processing reminder)';
    const minutes = Math.floor(diffMs / 60000);
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    if (hours > 0) {
      return `in ${hours}h ${remainingMinutes}m`;
    }
    return `in ${minutes}m`;
  };

  const activeSpoilageAlerts = alerts.filter(
    (a) => !a.is_resolved && (a.alert_type === 'Food Spoilage Alert' || a.status === 'ACTIVE')
  );
  const activeAlertsCount = alerts.filter((a) => !a.is_resolved).length;

  const getAlertIcon = (type: string) => {
    switch (type) {
      case 'Food Spoilage Alert':
        return <AlertOctagon className="w-5 h-5 text-rose-600 animate-pulse" />;
      case 'Expired / Remove Now':
        return <XCircle className="w-5 h-5 text-rose-600" />;
      case 'Expiring Soon':
        return <Clock className="w-5 h-5 text-amber-600" />;
      case 'Compatibility Warning':
        return <AlertTriangle className="w-5 h-5 text-orange-600" />;
      case 'Temperature Warning':
        return <Thermometer className="w-5 h-5 text-purple-600" />;
      case 'Item Not Seen':
        return <HelpCircle className="w-5 h-5 text-blue-600" />;
      default:
        return <Sparkles className="w-5 h-5 text-emerald-600" />;
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
              <Bell className="w-6 h-6 text-emerald-600" />
              Alerts & Notifications
            </h1>
            {activeSpoilageAlerts.length > 0 && (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-black bg-rose-600 text-white animate-pulse shadow-sm flex items-center gap-1">
                <AlertOctagon className="w-3.5 h-3.5" />
                {activeSpoilageAlerts.length} Spoilage Alert{activeSpoilageAlerts.length > 1 ? 's' : ''}
              </span>
            )}
          </div>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Real-time food spoilage detection with persistent 2-hour recurring reminders, inventory removal, and mobile push notifications.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={handleTriggerEvaluation}
            disabled={evaluating}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-all shadow-xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-slate-500 ${evaluating ? 'animate-spin' : ''}`} />
            Evaluate Rules Now
          </button>

          <button
            onClick={() => {
              setShowLogs(!showLogs);
              if (!showLogs) loadLogs();
            }}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold transition-all shadow-xs border ${
              showLogs
                ? 'bg-slate-900 text-white border-slate-900'
                : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50'
            }`}
          >
            <History className="w-3.5 h-3.5 text-slate-500" />
            {showLogs ? 'Hide History' : 'Notification History'}
          </button>

          <button
            onClick={handleTestAlert}
            disabled={sendingTest}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-emerald-600 text-white text-xs font-bold hover:bg-emerald-700 transition-all shadow-xs disabled:opacity-50"
          >
            <Send className={`w-3.5 h-3.5 ${sendingTest ? 'animate-spin' : ''}`} />
            {sendingTest ? 'Sending...' : 'Send Test Alert'}
          </button>

          <button
            onClick={handleMarkAllRead}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-all shadow-xs"
          >
            <CheckCheck className="w-3.5 h-3.5 text-emerald-600" />
            Mark All Read
          </button>
        </div>
      </div>

      {/* Web Push Permission Prompt Callout (if permission not yet granted or denied) */}
      {pushSupported && pushPermission === 'denied' && (
        <div className="bg-rose-50 border border-rose-200 p-4 rounded-2xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-xs">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-rose-600 text-white shadow-xs">
              <Smartphone className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-rose-950">Mobile Notification Permission Denied in Browser</h2>
              <p className="text-xs text-rose-800 mt-0.5">
                Your browser is currently blocking push notifications for this site. To receive mobile reminders, click the padlock/settings icon in your browser address bar, set Notifications to "Allow", and reload this page.
              </p>
            </div>
          </div>
        </div>
      )}

      {pushSupported && pushPermission === 'default' && (
        <div className="bg-gradient-to-r from-blue-500/10 via-indigo-500/10 to-purple-500/10 border border-blue-200/80 p-4 rounded-2xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-xs">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-blue-600 text-white shadow-xs">
              <Smartphone className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900">Enable Mobile Spoilage Push Notifications</h2>
              <p className="text-xs text-slate-600 mt-0.5">
                Receive urgent mobile reminders on your phone every 2 hours when spoiled food is detected, even with the app closed.
              </p>
            </div>
          </div>
          <button
            onClick={handleEnablePush}
            disabled={enablingPush}
            className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold transition-all shadow-sm flex items-center gap-1.5 shrink-0"
          >
            <Sparkles className="w-3.5 h-3.5" />
            {enablingPush ? 'Enabling...' : 'Enable Mobile Push'}
          </button>
        </div>
      )}

      {/* Spoilage Urgent Summary Banner (if active spoilage exists) */}
      {activeSpoilageAlerts.length > 0 && (
        <div className="p-4 rounded-2xl bg-rose-50 border-2 border-rose-300 shadow-soft space-y-3">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <div className="flex items-center gap-2 text-rose-900 font-black text-sm">
              <AlertOctagon className="w-5 h-5 text-rose-600" />
              <span>URGENT ATTENTION: {activeSpoilageAlerts.length} Food Item{activeSpoilageAlerts.length > 1 ? 's' : ''} Spoiled in Refrigerator</span>
            </div>
            {schedulerStatus?.scheduler_running ? (
              <span className="text-[11px] font-semibold text-emerald-800 bg-emerald-100 px-2.5 py-1 rounded-full border border-emerald-200 flex items-center gap-1.5 shadow-2xs">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                Recurring 2-Hour Reminders Active (Scheduler Online)
              </span>
            ) : (
              <span className="text-[11px] font-semibold text-amber-800 bg-amber-100 px-2.5 py-1 rounded-full border border-amber-300 flex items-center gap-1.5 shadow-2xs">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                Backend Scheduler Stopped (Reminders Paused)
              </span>
            )}
          </div>
          <p className="text-xs text-rose-800">
            Spoiled produce or dairy emits bacteria and ethylene gas that accelerates spoilage of adjacent items. Please tap <strong>"Remove Food"</strong> on the alert card below once the item is taken out of your fridge.
          </p>
        </div>
      )}

      {/* Filter Tabs & Status Pills */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-3 rounded-2xl border border-slate-200 shadow-xs">
        {/* Status Filter */}
        <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl">
          {[
            { label: `All (${alerts.length})`, val: 'all' },
            { label: `Active (${activeAlertsCount})`, val: 'active' },
            { label: 'Resolved / Removed', val: 'resolved' }
          ].map((s) => (
            <button
              key={s.val}
              onClick={() => setStatusFilter(s.val as any)}
              className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                statusFilter === s.val
                  ? 'bg-white text-slate-900 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>

        {/* Type Filter */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          {[
            { label: 'All Types', val: '' },
            { label: '🚨 Spoilage Alerts', val: 'Food Spoilage Alert' },
            { label: 'Expired / Remove', val: 'Expired / Remove Now' },
            { label: 'Expiring Soon', val: 'Expiring Soon' },
            { label: 'Temperature', val: 'Temperature Warning' },
            { label: 'Compatibility', val: 'Compatibility Warning' },
            { label: 'Audit Missing', val: 'Item Not Seen' }
          ].map((f) => (
            <button
              key={f.val}
              onClick={() => setFilterType(f.val)}
              className={`px-2.5 py-1 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
                filterType === f.val
                  ? 'bg-slate-900 text-white shadow-xs'
                  : 'bg-slate-50 border border-slate-200/80 text-slate-600 hover:bg-slate-100'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Notification Dispatch History Drawer */}
      {showLogs && (
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-soft space-y-3">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <History className="w-5 h-5 text-slate-700" />
              <h3 className="text-sm font-bold text-slate-900">Notification Dispatch History</h3>
            </div>
            <button
              onClick={loadLogs}
              disabled={logsLoading}
              className="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1 font-semibold"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${logsLoading ? 'animate-spin' : ''}`} />
              Refresh Logs
            </button>
          </div>

          {logsLoading ? (
            <div className="py-6 text-center text-xs text-slate-400">Loading history...</div>
          ) : logs.length === 0 ? (
            <div className="py-6 text-center text-xs text-slate-400">No notification logs recorded yet.</div>
          ) : (
            <div className="space-y-2.5 max-h-96 overflow-y-auto pr-1">
              {logs.map((log) => {
                const normStatus = log.status?.toLowerCase() || 'pending';
                const isDelivered = normStatus === 'delivered';
                const isAccepted = ['accepted', 'sent', 'success'].includes(normStatus);
                const isSimulated = normStatus === 'simulated';
                const isFailed = normStatus === 'failed';

                return (
                  <div
                    key={log.id}
                    className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/80 text-xs flex flex-col gap-2 transition-all hover:bg-white hover:shadow-xs"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        {log.alert_id ? (
                          <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded-md bg-slate-200 text-slate-800">
                            Incident #{log.alert_id}
                          </span>
                        ) : (
                          <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded-md bg-slate-100 text-slate-600">
                            Test Dispatch
                          </span>
                        )}
                        {log.food_name && (
                          <span className="font-semibold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200/60 flex items-center gap-1">
                            🍱 {log.food_name}
                          </span>
                        )}
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-black uppercase tracking-wider bg-slate-200 text-slate-700">
                          {log.channel}
                        </span>
                        {isDelivered && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300" title="Handset receipt confirmed">
                            Delivered
                          </span>
                        )}
                        {isAccepted && !isDelivered && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800 border border-blue-200" title="Accepted by carrier/provider gateway">
                            Accepted by Gateway
                          </span>
                        )}
                        {isSimulated && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-800 border border-purple-200" title="Simulated mode (dev environment)">
                            Simulated Mode
                          </span>
                        )}
                        {isFailed && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-200" title="Delivery attempt failed">
                            Failed
                          </span>
                        )}
                        {log.provider_message_id && (
                          <span className="font-mono text-[10px] text-slate-500 bg-white px-2 py-0.5 rounded border border-slate-200" title="Provider Message ID">
                            ID: {log.provider_message_id}
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-slate-400 shrink-0">
                        {new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} •{' '}
                        {new Date(log.created_at).toLocaleDateString()}
                      </div>
                    </div>

                    <div className="text-slate-700 leading-relaxed font-normal">
                      <strong>{log.title}</strong> — {log.message}
                    </div>

                    {(log.error_message || log.next_reminder_at) && (
                      <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-slate-200/60 text-[11px]">
                        {log.error_message ? (
                          <div className="text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
                            Failure reason: {log.error_message}
                          </div>
                        ) : <div />}
                        {log.next_reminder_at && (
                          <div className="text-amber-800 bg-amber-50 px-2 py-0.5 rounded border border-amber-200 flex items-center gap-1 font-semibold">
                            <Clock className="w-3 h-3 text-amber-600" />
                            Next scheduled reminder: {formatCountdown(log.next_reminder_at)}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          <div className="text-[11px] text-slate-500 bg-slate-50 p-2.5 rounded-xl border border-slate-200/60 flex items-center gap-1.5 flex-wrap">
            <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>
              <strong>Delivery Evidence Standard:</strong> "Accepted by Gateway" confirms provider acceptance (Telegram, Web Push, SMTP). "Delivered" requires live handset delivery confirmation.
            </span>
          </div>
        </div>
      )}

      {/* Alerts List */}
      <div className="space-y-4">
        {loading ? (
          <div className="text-center py-16 text-slate-400">
            <div className="w-8 h-8 border-3 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
            Loading active alerts and reminders...
          </div>
        ) : alerts.length === 0 ? (
          <div className="bg-white p-12 rounded-3xl border border-slate-200/80 text-center text-slate-400 shadow-soft">
            <ShieldCheck className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
            <h3 className="text-base font-bold text-slate-800">All Clear! No Alerts Found</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              {statusFilter === 'active'
                ? 'Your smart refrigerator has zero active food spoilage or temperature warnings. Everything is safe and fresh!'
                : 'No alerts match your selected filter criteria.'}
            </p>
          </div>
        ) : (
          alerts.map((alert) => {
            const isSpoilage = alert.alert_type === 'Food Spoilage Alert' || alert.status === 'ACTIVE';
            const isResolved = alert.is_resolved || alert.status === 'RESOLVED' || alert.status === 'REMOVED';
            const isRemoved = alert.status === 'REMOVED';

            return (
              <div
                key={alert.id}
                className={`p-4 sm:p-5 rounded-3xl border transition-all duration-200 flex flex-col gap-4 shadow-soft ${
                  isResolved
                    ? 'bg-slate-50/70 border-slate-200 text-slate-600 opacity-80'
                    : isSpoilage
                    ? 'bg-white border-rose-300 ring-2 ring-rose-500/15 text-slate-900 shadow-md'
                    : !alert.is_read
                    ? 'bg-white border-amber-300 ring-1 ring-amber-500/20 text-slate-900'
                    : 'bg-white border-slate-200 text-slate-800'
                }`}
              >
                <div className="flex items-start gap-3.5 flex-1 min-w-0">
                  <div
                    className={`p-3 rounded-2xl flex-shrink-0 mt-0.5 border ${
                      isSpoilage
                        ? 'bg-rose-50 border-rose-200 text-rose-600'
                        : 'bg-slate-50 border-slate-100 text-slate-600'
                    }`}
                  >
                    {getAlertIcon(alert.alert_type)}
                  </div>

                  <div className="space-y-2 min-w-0 flex-1">
                    {/* Header Row */}
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="text-sm sm:text-base font-bold text-slate-900 truncate">
                        {alert.title}
                      </h3>

                      {!alert.is_read && !isResolved && (
                        <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-pulse" title="Unread alert"></span>
                      )}

                      {/* Status Badges */}
                      {isRemoved ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-slate-200 text-slate-800 border border-slate-300">
                          <PackageX className="w-3 h-3 text-slate-600" />
                          Removed from Fridge
                        </span>
                      ) : isResolved ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200">
                          <Check className="w-3 h-3 text-emerald-600" />
                          Resolved & Silenced
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-rose-100 text-rose-800 border border-rose-200">
                          Active Warning
                        </span>
                      )}

                      {/* Zone Location Badge */}
                      {alert.zone_name && (
                        <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                          📍 {alert.zone_name}
                        </span>
                      )}

                      {/* Reminder Sent Counter */}
                      {alert.reminder_count !== undefined && alert.reminder_count > 0 && (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-purple-100 text-purple-800 border border-purple-200">
                          <MessageSquare className="w-3 h-3 text-purple-600" />
                          Reminders Sent: {alert.reminder_count}x
                        </span>
                      )}

                      {/* Next Scheduled Reminder Countdown */}
                      {!isResolved && alert.next_reminder_at && (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-300">
                          <Clock className="w-3 h-3 text-amber-600" />
                          Next 2-Hour Reminder: {formatCountdown(alert.next_reminder_at)}
                        </span>
                      )}
                    </div>

                    {/* Alert Message */}
                    <p className="text-xs sm:text-sm text-slate-700 leading-relaxed">
                      {alert.message}
                    </p>

                    {/* Recommended Action Callout */}
                    {alert.action_recommended && !isResolved && (
                      <div className="p-2.5 rounded-xl bg-amber-50/70 border border-amber-200/70 text-xs text-amber-900 font-medium flex items-center gap-2">
                        <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                        <span>Recommended action: <strong>{alert.action_recommended}</strong></span>
                      </div>
                    )}

                    {/* Metadata Footer */}
                    <div className="flex items-center gap-4 text-[11px] text-slate-400 flex-wrap pt-1">
                      <span>
                        Detected: {new Date(alert.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} •{' '}
                        {new Date(alert.created_at).toLocaleDateString()}
                      </span>
                      {alert.confidence_score !== undefined && alert.confidence_score !== null && (
                        <span>Model Confidence: {Math.round(alert.confidence_score * 100)}%</span>
                      )}
                      {alert.last_notification_at && (
                        <span>
                          Last Notified: {new Date(alert.last_notification_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      )}
                      {isResolved && alert.resolved_at && (
                        <span className="text-emerald-600 font-semibold">
                          Resolved at: {new Date(alert.resolved_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Mobile-Friendly Action Buttons */}
                <div className="flex items-center gap-2 pt-3 border-t border-slate-100 flex-wrap justify-end">
                  {!isResolved && (
                    <>
                      {/* 1. Remove Food Button (Prominent Action for Spoilage) */}
                      <button
                        onClick={() => setConfirmRemoveAlert(alert)}
                        disabled={removingId === alert.id}
                        className="flex-1 sm:flex-initial flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold transition-all shadow-xs disabled:opacity-50 min-h-[42px]"
                      >
                        <Trash2 className="w-4 h-4" />
                        {removingId === alert.id ? 'Removing Food...' : 'Remove Food'}
                      </button>

                      {/* 2. Mark as Resolved Button */}
                      <button
                        onClick={() => handleResolveAlert(alert.id)}
                        disabled={resolvingId === alert.id}
                        className="flex-1 sm:flex-initial flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold transition-all shadow-xs disabled:opacity-50 min-h-[42px]"
                      >
                        <CheckCircle2 className="w-4 h-4" />
                        {resolvingId === alert.id ? 'Resolving...' : 'Mark as Resolved'}
                      </button>
                    </>
                  )}

                  {!alert.is_read && !isResolved && (
                    <button
                      onClick={() => handleMarkRead(alert.id)}
                      className="px-3 py-2 rounded-xl border border-slate-200 text-slate-700 hover:bg-slate-50 text-xs font-semibold min-h-[42px]"
                    >
                      Mark Read
                    </button>
                  )}

                  <button
                    onClick={() => handleDelete(alert.id)}
                    className="p-2.5 rounded-xl border border-slate-200 text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors shrink-0 min-h-[42px] min-w-[42px] flex items-center justify-center"
                    title="Dismiss alert"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Confirmation Modal for "Remove Food" */}
      {confirmRemoveAlert && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4 animate-scaleUp">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-2xl bg-rose-100 text-rose-600">
                <Trash2 className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900">Confirm Food Removal</h3>
                <p className="text-xs text-slate-500">Action cannot be undone</p>
              </div>
            </div>

            <p className="text-xs sm:text-sm text-slate-700 leading-relaxed">
              Are you sure you want to remove <strong>{confirmRemoveAlert.food_item_name || 'this food item'}</strong> from your refrigerator?
              <br /><br />
              This will update your live fridge inventory, mark the item as discarded, and cancel all subsequent 2-hour mobile reminder notifications.
            </p>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setConfirmRemoveAlert(null)}
                className="px-4 py-2.5 rounded-xl border border-slate-200 text-slate-700 font-semibold text-xs hover:bg-slate-50 transition-all min-h-[42px]"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmRemoveFood}
                disabled={removingId === confirmRemoveAlert.id}
                className="px-5 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs transition-all shadow-sm flex items-center gap-1.5 min-h-[42px]"
              >
                <Trash2 className="w-4 h-4" />
                {removingId === confirmRemoveAlert.id ? 'Discarding...' : 'Yes, Remove Food'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
