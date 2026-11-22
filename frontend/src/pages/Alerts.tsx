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
  ShieldCheck,
  Check,
  Smartphone,
  AlertOctagon,
  History,
  X,
  PackageX
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
    } catch {
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
      setAlerts((prev) => prev.map((a) => (a.id === id ? { ...a, is_read: true } : a)));
      showToast('info', 'Alert marked as read.');
    } catch {
      showToast('error', 'Failed to update alert');
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await alertsApi.markAllRead();
      setAlerts((prev) => prev.map((a) => ({ ...a, is_read: true })));
      showToast('success', 'All alerts marked as read');
    } catch {
      showToast('error', 'Failed to update alerts');
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await alertsApi.delete(id);
      setAlerts((prev) => prev.filter((a) => a.id !== id));
      showToast('info', 'Alert dismissed');
    } catch {
      showToast('error', 'Failed to delete alert');
    }
  };

  const handleTriggerEvaluation = async () => {
    setEvaluating(true);
    try {
      const res = await alertsApi.evaluate();
      showToast('success', res.message, 'Rules Evaluated');
      loadAlerts();
    } catch {
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
      const isTgSuccess = tg ? tg.success : res.status === 'success';
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
      const msg = err.response?.data?.detail || err.message || 'Failed to dispatch test notification';
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
    const diffMs = new Date(isoString).getTime() - Date.now();
    if (diffMs <= 0) return 'Due soon';
    const minutes = Math.floor(diffMs / 60000);
    const hours = Math.floor(minutes / 60);
    const rem = minutes % 60;
    return hours > 0 ? `in ${hours}h ${rem}m` : `in ${minutes}m`;
  };

  const isFoodSpoilageType = (a: AlertItem) =>
    a.alert_type === 'Food Spoilage Alert' || a.alert_type === 'Expired / Remove Now';

  const activeSpoilageAlerts = alerts.filter((a) => !a.is_resolved && isFoodSpoilageType(a));
  const activeAlertsCount = alerts.filter((a) => !a.is_resolved).length;

  const getAlertIconMeta = (type: string) => {
    switch (type) {
      case 'Food Spoilage Alert':
        return { icon: <AlertOctagon className="w-4 h-4" />, box: 'bg-rose-50 text-rose-600 border-rose-200' };
      case 'Expired / Remove Now':
        return { icon: <XCircle className="w-4 h-4" />, box: 'bg-rose-50 text-rose-600 border-rose-200' };
      case 'Expiring Soon':
        return { icon: <Clock className="w-4 h-4" />, box: 'bg-amber-50 text-amber-600 border-amber-200' };
      case 'Compatibility Warning':
        return { icon: <AlertTriangle className="w-4 h-4" />, box: 'bg-orange-50 text-orange-600 border-orange-200' };
      case 'Temperature Warning':
        return { icon: <Thermometer className="w-4 h-4" />, box: 'bg-purple-50 text-purple-600 border-purple-200' };
      case 'Item Not Seen':
        return { icon: <HelpCircle className="w-4 h-4" />, box: 'bg-sky-50 text-sky-600 border-sky-200' };
      default:
        return { icon: <Sparkles className="w-4 h-4" />, box: 'bg-emerald-50 text-emerald-600 border-emerald-200' };
    }
  };

  return (
    <div className="space-y-5 pb-12">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
              <Bell className="w-6 h-6 text-emerald-600" />
              Alerts &amp; Notifications
            </h1>
            {activeAlertsCount > 0 && (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-100 text-rose-700">
                {activeAlertsCount} active
              </span>
            )}
          </div>
          <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
            Track food spoilage, temperature warnings, recurring reminders, and delivery history
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={handleTriggerEvaluation}
            disabled={evaluating}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-slate-500 ${evaluating ? 'animate-spin' : ''}`} />
            Evaluate Rules
          </button>

          <button
            onClick={() => {
              setShowLogs(!showLogs);
              if (!showLogs) loadLogs();
            }}
            className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold transition-colors border ${
              showLogs
                ? 'bg-slate-900 text-white border-slate-900'
                : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50'
            }`}
          >
            <History className="w-3.5 h-3.5" />
            {showLogs ? 'Hide History' : 'History'}
          </button>

          <button
            onClick={handleMarkAllRead}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
          >
            <CheckCheck className="w-3.5 h-3.5 text-emerald-600" />
            Mark All Read
          </button>

          <button
            onClick={handleTestAlert}
            disabled={sendingTest}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-emerald-600 text-white text-xs font-bold hover:bg-emerald-700 transition-colors disabled:opacity-50"
          >
            <Send className={`w-3.5 h-3.5 ${sendingTest ? 'animate-spin' : ''}`} />
            {sendingTest ? 'Sending...' : 'Send Test Alert'}
          </button>
        </div>
      </div>

      {/* Web Push Permission Prompts */}
      {pushSupported && pushPermission === 'denied' && (
        <div className="bg-rose-50 border border-rose-200 px-4 py-3 rounded-2xl flex items-center gap-3 text-xs text-rose-900">
          <Smartphone className="w-4 h-4 text-rose-600 shrink-0" />
          <span>
            <strong>Browser notifications are blocked.</strong> Allow notifications in your browser address bar settings and reload to enable push alerts.
          </span>
        </div>
      )}

      {pushSupported && pushPermission === 'default' && (
        <div className="bg-slate-50 border border-slate-200 px-4 py-3 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2.5 text-xs text-slate-700">
            <Smartphone className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>
              <strong>Enable Browser Push Alerts</strong> to get instant spoilage reminders even when the tab is closed.
            </span>
          </div>
          <button
            onClick={handleEnablePush}
            disabled={enablingPush}
            className="px-3.5 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold transition-colors shrink-0 self-start sm:self-auto"
          >
            {enablingPush ? 'Enabling...' : 'Enable Push'}
          </button>
        </div>
      )}

      {/* Urgent Attention Summary Banner */}
      {activeAlertsCount > 0 && (
        <div className="px-4 py-3.5 rounded-2xl bg-rose-50/80 border border-rose-200 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
          <div className="flex items-start gap-2.5">
            <AlertOctagon className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
            <div className="text-xs text-rose-900">
              <span className="font-bold">
                {activeSpoilageAlerts.length > 0
                  ? `${activeSpoilageAlerts.length} food item${activeSpoilageAlerts.length > 1 ? 's' : ''} spoiled or expired`
                  : `${activeAlertsCount} active fridge alert${activeAlertsCount > 1 ? 's' : ''} need attention`}
              </span>
              <span className="text-rose-800/90 ml-1">
                — Spoiled food releases bacteria and ethylene gas that speeds up spoilage of nearby items.
              </span>
            </div>
          </div>

          {schedulerStatus?.scheduler_running ? (
            <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-emerald-800 bg-emerald-100 px-2.5 py-1 rounded-full border border-emerald-200 shrink-0 self-start sm:self-auto">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              Reminders Active
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-amber-800 bg-amber-100 px-2.5 py-1 rounded-full border border-amber-200 shrink-0 self-start sm:self-auto">
              <AlertTriangle className="w-3 h-3 text-amber-600" />
              Scheduler Paused
            </span>
          )}
        </div>
      )}

      {/* Filter Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 bg-white p-2.5 rounded-2xl border border-slate-200/80 shadow-xs">
        <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl self-start">
          {[
            { label: `All (${alerts.length})`, val: 'all' },
            { label: `Active (${activeAlertsCount})`, val: 'active' },
            { label: 'Resolved', val: 'resolved' }
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

        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0">
          {[
            { label: 'All Types', val: '' },
            { label: 'Spoilage', val: 'Food Spoilage Alert' },
            { label: 'Expired', val: 'Expired / Remove Now' },
            { label: 'Expiring Soon', val: 'Expiring Soon' },
            { label: 'Temperature', val: 'Temperature Warning' },
            { label: 'Compatibility', val: 'Compatibility Warning' },
            { label: 'Audit Missing', val: 'Item Not Seen' }
          ].map((f) => (
            <button
              key={f.val}
              onClick={() => setFilterType(f.val)}
              className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
                filterType === f.val
                  ? 'bg-slate-900 text-white'
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
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-soft overflow-hidden">
          <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <History className="w-4 h-4 text-slate-700" />
              <h3 className="text-sm font-bold text-slate-900">Notification Dispatch History</h3>
            </div>
            <button
              onClick={loadLogs}
              disabled={logsLoading}
              className="text-xs text-slate-500 hover:text-slate-800 inline-flex items-center gap-1 font-semibold"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${logsLoading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>

          {logsLoading ? (
            <div className="py-8 text-center text-xs text-slate-400">Loading history...</div>
          ) : logs.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-400">No notification logs recorded yet.</div>
          ) : (
            <div className="divide-y divide-slate-100 max-h-80 overflow-y-auto">
              {logs.map((log) => {
                const normStatus = log.status?.toLowerCase() || 'pending';
                const statusBadge =
                  normStatus === 'delivered'
                    ? 'bg-emerald-100 text-emerald-800'
                    : ['accepted', 'sent', 'success'].includes(normStatus)
                    ? 'bg-blue-100 text-blue-800'
                    : normStatus === 'failed'
                    ? 'bg-rose-100 text-rose-800'
                    : 'bg-slate-100 text-slate-700';

                return (
                  <div key={log.id} className="px-5 py-3 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="min-w-0 space-y-0.5">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase bg-slate-100 text-slate-700">
                          {log.channel}
                        </span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold capitalize ${statusBadge}`}>
                          {normStatus}
                        </span>
                        <span className="font-semibold text-slate-800 truncate">{log.title}</span>
                      </div>
                      <p className="text-[11px] text-slate-500 line-clamp-1">{log.message}</p>
                      {log.error_message && (
                        <p className="text-[11px] text-rose-600">Error: {log.error_message}</p>
                      )}
                    </div>
                    <span className="text-[11px] text-slate-400 shrink-0">
                      {new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} ·{' '}
                      {new Date(log.created_at).toLocaleDateString()}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Clean Unified Alerts List */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-soft overflow-hidden">
        {loading ? (
          <div className="text-center py-14 text-xs text-slate-400">
            <div className="w-7 h-7 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            Loading alerts...
          </div>
        ) : alerts.length === 0 ? (
          <div className="p-12 text-center text-slate-400">
            <ShieldCheck className="w-10 h-10 text-emerald-500 mx-auto mb-2.5" />
            <h3 className="text-sm font-bold text-slate-800">All Clear — No Alerts</h3>
            <p className="text-xs text-slate-500 mt-1">
              {statusFilter === 'active'
                ? 'Zero active spoilage or temperature warnings right now.'
                : 'No alerts match your current filter.'}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {alerts.map((alert) => {
              const isResolved = alert.is_resolved || alert.status === 'RESOLVED' || alert.status === 'REMOVED';
              const isRemoved = alert.status === 'REMOVED';
              const isFoodAlert = Boolean(alert.food_item_id) || isFoodSpoilageType(alert);
              const iconMeta = getAlertIconMeta(alert.alert_type);
              const nextRem = !isResolved && alert.next_reminder_at ? formatCountdown(alert.next_reminder_at) : null;

              return (
                <div
                  key={alert.id}
                  className={`px-5 py-4 transition-colors flex flex-col lg:flex-row lg:items-center justify-between gap-3.5 ${
                    isResolved ? 'bg-slate-50/50 opacity-75' : 'hover:bg-slate-50/70'
                  }`}
                >
                  {/* Left: Icon + Readable Content */}
                  <div className="flex items-start gap-3.5 min-w-0 flex-1">
                    <div className={`w-9 h-9 rounded-xl border flex items-center justify-center shrink-0 mt-0.5 ${iconMeta.box}`}>
                      {iconMeta.icon}
                    </div>

                    <div className="min-w-0 flex-1 space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        {!alert.is_read && !isResolved && (
                          <span className="w-2 h-2 rounded-full bg-rose-500 shrink-0" title="Unread" />
                        )}
                        <h3 className="text-sm font-bold text-slate-900 leading-snug">{alert.title}</h3>

                        {alert.zone_name && (
                          <span className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-slate-100 text-slate-600">
                            {alert.zone_name}
                          </span>
                        )}

                        {isRemoved ? (
                          <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-200 text-slate-700">
                            <PackageX className="w-3 h-3" /> Removed
                          </span>
                        ) : isResolved ? (
                          <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700">
                            <Check className="w-3 h-3" /> Resolved
                          </span>
                        ) : (
                          alert.reminder_count !== undefined && alert.reminder_count > 0 && (
                            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-50 text-rose-700 border border-rose-200">
                              Reminder #{alert.reminder_count}
                            </span>
                          )
                        )}
                      </div>

                      <p className="text-xs text-slate-600 leading-relaxed">{alert.message}</p>

                      {alert.action_recommended && !isResolved && isFoodAlert && (
                        <p className="text-xs text-amber-800 font-medium">
                          Action: {alert.action_recommended}
                        </p>
                      )}

                      <div className="flex items-center gap-3 flex-wrap text-[11px] text-slate-400 pt-0.5">
                        <span>
                          {new Date(alert.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} ·{' '}
                          {new Date(alert.created_at).toLocaleDateString()}
                        </span>
                        {alert.last_notification_at && (
                          <span>
                            Notified {new Date(alert.last_notification_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        )}
                        {nextRem && (
                          <span className="text-amber-700 font-medium">Next reminder: {nextRem}</span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Right: Compact Aligned Actions */}
                  <div className="flex items-center gap-2 shrink-0 pl-12 lg:pl-0">
                    {!isResolved && isFoodAlert && (
                      <button
                        onClick={() => setConfirmRemoveAlert(alert)}
                        disabled={removingId === alert.id}
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold transition-colors disabled:opacity-50"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        {removingId === alert.id ? 'Removing...' : 'Remove'}
                      </button>
                    )}

                    {!isResolved && (
                      <button
                        onClick={() => handleResolveAlert(alert.id)}
                        disabled={resolvingId === alert.id}
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-emerald-200 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 text-xs font-semibold transition-colors disabled:opacity-50"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        {resolvingId === alert.id ? 'Saving...' : 'Resolve'}
                      </button>
                    )}

                    {!alert.is_read && !isResolved && (
                      <button
                        onClick={() => handleMarkRead(alert.id)}
                        className="px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 text-xs font-semibold transition-colors"
                      >
                        Read
                      </button>
                    )}

                    <button
                      onClick={() => handleDelete(alert.id)}
                      className="p-1.5 rounded-lg border border-slate-200 text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                      title="Dismiss alert"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Confirmation Modal for "Remove Food" */}
      {confirmRemoveAlert && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-2xl bg-rose-100 text-rose-600">
                <Trash2 className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900">Confirm Food Removal</h3>
                <p className="text-xs text-slate-500">This updates your fridge inventory</p>
              </div>
            </div>

            <p className="text-xs sm:text-sm text-slate-700 leading-relaxed">
              Remove <strong>{confirmRemoveAlert.food_item_name || 'this food item'}</strong> from your refrigerator? It will be marked as discarded and recurring reminders will stop.
            </p>

            <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setConfirmRemoveAlert(null)}
                className="px-4 py-2 rounded-xl border border-slate-200 text-slate-700 font-semibold text-xs hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmRemoveFood}
                disabled={removingId === confirmRemoveAlert.id}
                className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs inline-flex items-center gap-1.5"
              >
                <Trash2 className="w-3.5 h-3.5" />
                {removingId === confirmRemoveAlert.id ? 'Removing...' : 'Yes, Remove Food'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};