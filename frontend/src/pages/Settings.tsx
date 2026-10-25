import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import {
  Settings as SettingsIcon,
  Save,
  Bell,
  Clock,
  Phone,
  Mail,
  Smartphone,
  MessageSquare,
  CheckCircle2,
  XCircle,
  AlertCircle,
  RefreshCw,
  Send,
  Shield,
  Zap,
  Sparkles,
  ExternalLink,
  ChevronRight,
  AlertOctagon,
  Trash2,
  CheckCheck,
  Check
} from 'lucide-react';
import { settingsApi, alertsApi } from '../services/api';
import { subscribeToWebPush, unsubscribeFromWebPush } from '../services/pwa';
import { useNotification } from '../context/NotificationContext';
import { NotificationLog, AlertItem } from '../types';

export const Settings: React.FC = () => {const location = useLocation();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [logsLoading, setLogsLoading] = useState(false);

  // Active Spoilage Incidents State
  const [spoilageIncidents, setSpoilageIncidents] = useState<AlertItem[]>([]);
  const [loadingIncidents, setLoadingIncidents] = useState(false);
  const [resolvingIncidentId, setResolvingIncidentId] = useState<number | null>(null);
  const [removingIncidentId, setRemovingIncidentId] = useState<number | null>(null);
  const [pushPermission, setPushPermission] = useState<string>('default');

  // Testing states
  const [testingEmail, setTestingEmail] = useState(false);
  const [testingPush, setTestingPush] = useState(false);
  const [testingSms, setTestingSms] = useState(false);
  const [testingAll, setTestingAll] = useState(false);
  const [enablingPush, setEnablingPush] = useState(false);

  // Form fields: Profile & Contact
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');

  // Channel Master Toggles
  const [emailEnabled, setEmailEnabled] = useState(true);
  const [pushEnabled, setPushEnabled] = useState(true);
  const [smsEnabled, setSmsEnabled] = useState(false);
  const [hasPushSubscription, setHasPushSubscription] = useState(false);

  // Alert Category Toggles
  const [emailForExpiring, setEmailForExpiring] = useState(true);
  const [emailForExpired, setEmailForExpired] = useState(true);
  const [emailDailyDigest, setEmailDailyDigest] = useState(true);

  const [pushForExpiring, setPushForExpiring] = useState(true);
  const [pushForExpired, setPushForExpired] = useState(true);
  const [pushForTemperature, setPushForTemperature] = useState(true);
  const [pushForSpoilage, setPushForSpoilage] = useState(true);
  const [spoilageReminderEnabled, setSpoilageReminderEnabled] = useState(true);
  const [spoilageReminderInterval, setSpoilageReminderInterval] = useState(120);
  const [unsubscribingPush, setUnsubscribingPush] = useState(false);

  const [smsForCritical, setSmsForCritical] = useState(false);
  const [smsForExpiring, setSmsForExpiring] = useState(false);
  const [smsForExpired, setSmsForExpired] = useState(true);
  const [smsForTemperature, setSmsForTemperature] = useState(true);
  const [smsForDairy, setSmsForDairy] = useState(true);
  const [smsRepeatInterval, setSmsRepeatInterval] = useState(15);
  const [smsMaxDuration, setSmsMaxDuration] = useState(120);
  const [smsSystemStatus, setSmsSystemStatus] = useState<any>(null);
  const [telegramSystemStatus, setTelegramSystemStatus] = useState<any>(null);
  const [testTelegramChatId, setTestTelegramChatId] = useState('');
  const [testingTelegram, setTestingTelegram] = useState(false);
  const [testTelegramResult, setTestTelegramResult] = useState<any>(null);
  const [testSmsPhone, setTestSmsPhone] = useState('');
  const [testSmsResult, setTestSmsResult] = useState<any>(null);
  const [channelFilter, setChannelFilter] = useState<string>('all');

  // Rules & Scheduling
  const [alertLeadDays, setAlertLeadDays] = useState(2);
  const [quietHoursStart, setQuietHoursStart] = useState('22:00');
  const [quietHoursEnd, setQuietHoursEnd] = useState('07:00');
  const [auditDay, setAuditDay] = useState('Sunday');
  const [auditTime, setAuditTime] = useState('10:00');

  // Zones & Logs
  const [zones, setZones] = useState<any[]>([]);
  const [logs, setLogs] = useState<NotificationLog[]>([]);

  const { showToast } = useNotification();

  const loadSettings = async () => {
    try {
      setLoading(true);
      const data = await settingsApi.get();
      if (data.user) {
        setFullName(data.user.full_name || '');
        setEmail(data.user.email || '');
        setPhoneNumber(data.user.phone_number || '');
        setTestSmsPhone(data.user.phone_number || '');

        setEmailEnabled(data.user.email_notifications_enabled ?? true);
        setPushEnabled(data.user.push_notifications_enabled ?? true);
        setSmsEnabled(data.user.sms_notifications_enabled ?? false);
        setHasPushSubscription(!!data.user.has_push_subscription);

        setEmailForExpiring(data.user.email_for_expiring ?? true);
        setEmailForExpired(data.user.email_for_expired ?? true);
        setEmailDailyDigest(data.user.email_daily_digest ?? true);

        pushForExpiring !== undefined && setPushForExpiring(data.user.push_for_expiring ?? true);
        pushForExpired !== undefined && setPushForExpired(data.user.push_for_expired ?? true);
        pushForTemperature !== undefined && setPushForTemperature(data.user.push_for_temperature ?? true);
        setPushForSpoilage(data.user.push_for_spoilage ?? true);
        setSpoilageReminderEnabled(data.user.spoilage_reminder_enabled ?? true);
        setSpoilageReminderInterval(data.user.spoilage_reminder_interval_minutes || 120);

        setSmsForCritical(data.user.sms_for_critical ?? false);
        setSmsForExpiring(data.user.sms_for_expiring ?? false);
        setSmsForExpired(data.user.sms_for_expired ?? true);
        setSmsForTemperature(data.user.sms_for_temperature ?? true);
        setSmsForDairy(data.user.sms_for_dairy ?? true);
        setSmsRepeatInterval(data.user.sms_repeat_interval_minutes || 15);
        setSmsMaxDuration(data.user.sms_max_duration_minutes || 120);

        setAlertLeadDays(data.user.alert_lead_days || 2);
        setQuietHoursStart(data.user.quiet_hours_start || '22:00');
        setQuietHoursEnd(data.user.quiet_hours_end || '07:00');
        setAuditDay(data.user.audit_day || 'Sunday');
        setAuditTime(data.user.audit_time || '10:00');
      }
      if (data.telegram_system_status) {
        setTelegramSystemStatus(data.telegram_system_status);
        if (data.telegram_system_status.chat_id && data.telegram_system_status.chat_id !== 'Not Configured') {
          setTestTelegramChatId(data.telegram_system_status.chat_id);
        }
      }
      if (data.sms_system_status) {
        setSmsSystemStatus(data.sms_system_status);
      }
      if (data.zones) {
        setZones(data.zones);
      }
    } catch (err) {
      console.error(err);
      showToast('error', 'Failed to load user settings');
    } finally {
      setLoading(false);
    }
  };


  const loadLogs = async () => {
    try {
      setLogsLoading(true);
      const data = await settingsApi.getNotificationLogs(20);
      setLogs(data);
    } catch (err) {
      console.error('Failed to load notification logs:', err);
    } finally {
      setLogsLoading(false);
    }
  };

  const loadIncidents = async () => {
    try {
      setLoadingIncidents(true);
      const incidents = await alertsApi.getActiveSpoilage();
      setSpoilageIncidents(incidents);
    } catch (err) {
      console.error('Failed to load active spoilage incidents:', err);
    } finally {
      setLoadingIncidents(false);
    }
  };

  useEffect(() => {
    if (typeof window !== 'undefined' && 'Notification' in window) {
      setPushPermission(Notification.permission);
    }
    loadSettings();
    loadLogs();
    loadIncidents();
  }, []);
  useEffect(() => {
  if (location.hash !== '#profile') return;

  const timer = window.setTimeout(() => {
    document.getElementById('profile')?.scrollIntoView({
      behavior: 'smooth',
      block: 'start',
    });
  }, 150);

  return () => window.clearTimeout(timer);
}, [location.pathname, location.hash]);

  const formatCountdown = (isoString?: string) => {
    if (!isoString) return null;
    const diffMs = new Date(isoString).getTime() - new Date().getTime();
    if (diffMs <= 0) return 'Due now (sending reminder)';
    const minutes = Math.floor(diffMs / 60000);
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    if (hours > 0) {
      return `in ${hours}h ${remainingMinutes}m`;
    }
    return `in ${minutes}m`;
  };

  const handleResolveIncident = async (id: number) => {
    try {
      setResolvingIncidentId(id);
      await alertsApi.resolve(id);
      showToast('success', 'Spoilage incident resolved. Recurring reminders stopped.', 'Incident Resolved');
      await loadIncidents();
      await loadLogs();
    } catch (err) {
      showToast('error', 'Failed to resolve incident');
    } finally {
      setResolvingIncidentId(null);
    }
  };

  const handleAcknowledgeIncident = async (id: number) => {
    try {
      await alertsApi.markRead(id);
      showToast('info', 'Spoilage incident acknowledged.');
      await loadIncidents();
    } catch (err) {
      showToast('error', 'Failed to acknowledge incident');
    }
  };

  const handleRemoveFoodIncident = async (alertId: number, foodName: string) => {
    try {
      setRemovingIncidentId(alertId);
      await alertsApi.removeFood(alertId);
      showToast('success', `"${foodName}" removed from fridge inventory. Incident resolved and reminders cancelled.`, 'Food Removed');
      await loadIncidents();
      await loadLogs();
    } catch (err: any) {
      showToast('error', err.response?.data?.detail || 'Failed to remove food item');
    } finally {
      setRemovingIncidentId(null);
    }
  };

  const handleTestAllNotification = async () => {
    setTestingAll(true);
    try {
      const res = await alertsApi.testNotification('all');
      const tg = res.results?.telegram;
      const isTgSuccess = tg ? tg.success : (res.status === 'success');
      if (!isTgSuccess || res.status === 'partial_failure') {
        showToast('error', tg?.error || tg?.detail || res.summary || 'Failed to send Telegram test notification', 'Delivery Incomplete');
      } else {
        showToast('success', res.summary || 'Telegram message confirmed delivered to your chat!', 'Telegram Alert Sent');
      }
      await loadLogs();
    } catch (err: any) {
      let msg = err.response?.data?.detail;
      if (!msg) {
        if (err.response?.status === 502 || err.code === 'ERR_NETWORK') {
          msg = 'Backend API server is offline or unreachable on http://127.0.0.1:8000 (502 Bad Gateway). Please ensure the FastAPI backend is running.';
        } else {
          msg = err.message || 'Failed to send test notification';
        }
      }
      showToast('error', msg, 'Dispatch Failure');
    } finally {
      setTestingAll(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await settingsApi.update({
        full_name: fullName,
        phone_number: phoneNumber,
        email_notifications_enabled: emailEnabled,
        push_notifications_enabled: pushEnabled,
        sms_notifications_enabled: smsEnabled,
        email_for_expiring: emailForExpiring,
        email_for_expired: emailForExpired,
        email_daily_digest: emailDailyDigest,
        push_for_expiring: pushForExpiring,
        push_for_expired: pushForExpired,
        push_for_temperature: pushForTemperature,
        push_for_spoilage: pushForSpoilage,
        spoilage_reminder_enabled: spoilageReminderEnabled,
        spoilage_reminder_interval_minutes: spoilageReminderInterval,
        sms_for_critical: smsForCritical,
        sms_for_expiring: smsForExpiring,
        sms_for_expired: smsForExpired,
        sms_for_temperature: smsForTemperature,
        sms_for_dairy: smsForDairy,
        sms_repeat_interval_minutes: smsRepeatInterval,
        sms_max_duration_minutes: smsMaxDuration,
        alert_lead_days: alertLeadDays,
        quiet_hours_start: quietHoursStart,
        quiet_hours_end: quietHoursEnd,
        audit_day: auditDay,
        audit_time: auditTime
      });
      showToast('success', 'Preferences and SMS notification settings saved successfully!', 'Settings Saved');
      await loadLogs();
    } catch (err) {
      showToast('error', 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const handleEnablePush = async () => {
    setEnablingPush(true);
    try {
      const res = await subscribeToWebPush();
      if (res.success) {
        setHasPushSubscription(true);
        setPushEnabled(true);
        showToast('success', res.message, 'PWA Push Enabled');
        await loadSettings();
        await loadLogs();
      } else {
        showToast('warning', res.message, 'Push Permission Notice');
      }
    } catch (err: any) {
      showToast('error', err.message || 'Failed to enable Web Push');
    } finally {
      setEnablingPush(false);
    }
  };

  const handleUnsubscribePush = async () => {
    setUnsubscribingPush(true);
    try {
      const res = await unsubscribeFromWebPush();
      if (res.success) {
        setHasPushSubscription(false);
        setPushEnabled(false);
        showToast('info', res.message, 'Push Notifications Disabled');
        await loadSettings();
        await loadLogs();
      } else {
        showToast('error', res.message, 'Unsubscribe Failed');
      }
    } catch (err: any) {
      showToast('error', err.message || 'Failed to unsubscribe from Web Push');
    } finally {
      setUnsubscribingPush(false);
    }
  };

  const handleTestEmail = async () => {
    setTestingEmail(true);
    try {
      const res = await settingsApi.testEmail(email);
      showToast('success', `Test HTML email sent to ${email}`, 'Email Sent');
      await loadLogs();
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to send test email';
      showToast('error', msg, 'Email Delivery Error');
    } finally {
      setTestingEmail(false);
    }
  };

  const handleTestPush = async () => {
    setTestingPush(true);
    try {
      await settingsApi.testPush();
      showToast('success', 'Test push notification dispatched to your browser/phone!', 'Web Push Dispatched');
      await loadLogs();
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Push notification failed. Ensure notifications are enabled.';
      showToast('error', msg, 'Push Error');
    } finally {
      setTestingPush(false);
    }
  };

  const handleTestTelegram = async () => {
    setTestingTelegram(true);
    setTestTelegramResult(null);
    try {
      const res = await settingsApi.testTelegram(testTelegramChatId || undefined);
      setTestTelegramResult(res);
      showToast('success', `Telegram message delivered to chat ${res.recipient}! (Msg ID: ${res.provider_message_id})`, 'Telegram Delivered');
      await loadLogs();
    } catch (err: any) {
      let msg = err.response?.data?.detail;
      if (!msg) {
        if (err.response?.status === 502 || err.code === 'ERR_NETWORK') {
          msg = 'Backend API server is offline or unreachable on http://127.0.0.1:8000 (502 Bad Gateway). Please ensure the FastAPI backend is running.';
        } else {
          msg = err.message || 'Failed to send test Telegram message';
        }
      }
      showToast('error', msg, 'Telegram Delivery Error');
    } finally {
      setTestingTelegram(false);
    }
  };

  const handleTestSms = async () => {
    // If Twilio is not configured, route to Telegram test
    if (!smsSystemStatus?.twilio_configured) {
      return await handleTestTelegram();
    }
    const target = testSmsPhone || phoneNumber;
    if (!target) {
      showToast('warning', 'Please enter a mobile phone number first (e.g., +91 9876543210)');
      return;
    }
    setTestingSms(true);
    setTestSmsResult(null);
    try {
      const res = await settingsApi.testSms(target);
      setTestSmsResult(res);
      const isSim = res.is_simulated || (res.result && res.result.is_simulated);
      if (isSim) {
        showToast('info', `Simulated SMS logged for ${res.recipient || target}. SID: ${res.provider_message_id}`, 'Simulated SMS Dispatched');
      } else {
        showToast('success', `SMS transmitted to carrier for ${res.recipient || target}. SID: ${res.provider_message_id}`, 'SMS Delivered');
      }
      await loadLogs();
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to send test SMS';
      showToast('error', msg, 'SMS Error');
    } finally {
      setTestingSms(false);
    }
  };


  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <SettingsIcon className="w-6 h-6 text-emerald-600" />
            Settings & Notifications
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
            Configure mobile push alerts, repeating spoilage reminders, SMS carrier settings, and lead times
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            type="button"
            onClick={handleTestAllNotification}
            disabled={testingAll}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white font-bold text-xs shadow-sm transition-all disabled:opacity-50"
          >
            <Send className={`w-3.5 h-3.5 ${testingAll ? 'animate-spin' : ''}`} />
            {testingAll ? 'Sending...' : 'Send Test Notification'}
          </button>
        </div>
      </div>

      {/* =================================================================== */}
      {/* LIVE ACTIVE SPOILAGE INCIDENTS & REMINDERS                           */}
      {/* =================================================================== */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-soft space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-100 gap-2">
          <div className="flex items-center gap-2.5">
            <div className={`p-2 rounded-xl ${spoilageIncidents.length > 0 ? 'bg-rose-50 text-rose-600 animate-pulse' : 'bg-emerald-50 text-emerald-600'}`}>
              <AlertOctagon className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold text-slate-800">Active Spoilage Incidents &amp; Reminders</h2>
                {spoilageIncidents.length > 0 ? (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-black bg-rose-600 text-white uppercase tracking-wider">
                    {spoilageIncidents.length} Active Incident{spoilageIncidents.length > 1 ? 's' : ''}
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 uppercase tracking-wider">
                    All Clear
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-500">
                Tracked incidents receiving continuous reminders every {spoilageReminderInterval} minutes until resolved or removed
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={loadIncidents}
            disabled={loadingIncidents}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50 transition-colors self-start sm:self-auto"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingIncidents ? 'animate-spin' : ''}`} />
            Refresh Incidents
          </button>
        </div>

        {spoilageIncidents.length === 0 ? (
          <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200/80 flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
            <div className="text-xs text-emerald-900">
              <span className="font-bold">No active food spoilage incidents!</span>
              <p className="text-emerald-700 mt-0.5">
                All food items are currently fresh and within safe shelf life. When food is classified as spoiled or past its expiration date, immediate mobile notifications will trigger and repeat every {spoilageReminderInterval} minutes until resolved.
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {spoilageIncidents.map((incident) => {
              const countdown = formatCountdown(incident.next_reminder_at);
              const isResolving = resolvingIncidentId === incident.id;
              const isRemoving = removingIncidentId === incident.id;
              const foodName = incident.food_item_name || 'Food item';

              return (
                <div
                  key={incident.id}
                  className="p-4 rounded-xl border-2 border-rose-200 bg-rose-50/40 space-y-3 transition-all hover:border-rose-300"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-bold text-sm text-slate-900 flex items-center gap-1.5">
                        <AlertOctagon className="w-4 h-4 text-rose-600 shrink-0" />
                        {foodName}
                      </span>
                      {incident.zone_name && (
                        <span className="text-[11px] font-semibold text-slate-600 bg-white px-2 py-0.5 rounded-md border border-slate-200">
                          📍 {incident.zone_name}
                        </span>
                      )}
                      <span className="text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full bg-rose-600 text-white">
                        Reminder #{incident.reminder_count || 1}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 flex-wrap text-xs">
                      {incident.is_read ? (
                        <span className="text-[11px] font-semibold text-slate-600 bg-slate-100 px-2 py-0.5 rounded-md flex items-center gap-1">
                          <Check className="w-3 h-3 text-slate-500" /> Acknowledged
                        </span>
                      ) : (
                        <button
                          type="button"
                          onClick={() => handleAcknowledgeIncident(incident.id)}
                          className="px-2.5 py-1 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs flex items-center gap-1 transition-colors"
                        >
                          <Check className="w-3 h-3 text-slate-600" />
                          Acknowledge
                        </button>
                      )}

                      <button
                        type="button"
                        onClick={() => handleResolveIncident(incident.id)}
                        disabled={isResolving}
                        className="px-3 py-1 rounded-lg border border-emerald-300 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 font-bold text-xs flex items-center gap-1 transition-colors disabled:opacity-50"
                      >
                        <CheckCheck className="w-3.5 h-3.5 text-emerald-600" />
                        {isResolving ? 'Resolving...' : 'Mark as Resolved'}
                      </button>

                      <button
                        type="button"
                        onClick={() => handleRemoveFoodIncident(incident.id, foodName)}
                        disabled={isRemoving}
                        className="px-3 py-1 rounded-lg bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs flex items-center gap-1 shadow-xs transition-colors disabled:opacity-50"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        {isRemoving ? 'Removing...' : 'Remove Food'}
                      </button>
                    </div>
                  </div>

                  {/* Detection Evidence & Reasoning */}
                  <div className="text-xs bg-white/90 p-3 rounded-lg border border-rose-200/80 space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-bold text-slate-800">Alert Reason:</span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-slate-100 text-slate-700">
                        {incident.evidence_type === 'expiration_date'
                          ? '📅 Expiration Date Passed'
                          : incident.evidence_type === 'freshness_threshold'
                          ? '⏳ Shelf Life Threshold Exceeded'
                          : '🔬 ML Freshness Assessment'}
                      </span>
                      {incident.confidence_score && (
                        <span className="text-[10px] text-slate-500 font-mono">
                          Confidence: {Math.round(incident.confidence_score * 100)}%
                        </span>
                      )}
                    </div>
                    <p className="text-slate-600 text-[11px] leading-relaxed">
                      {incident.evidence_details || incident.message}
                    </p>
                  </div>

                  {/* Timing & Delivery Status Metadata */}
                  <div className="flex items-center justify-between gap-2 flex-wrap text-[11px] text-slate-500 pt-1">
                    <div className="flex items-center gap-3 flex-wrap">
                      <span>
                        Last Notified: <strong className="text-slate-700">{incident.last_notification_at ? new Date(incident.last_notification_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Just now'}</strong>
                      </span>
                      <span>
                        Next Scheduled Reminder: <strong className="text-rose-700 font-bold">{countdown || 'None'}</strong>
                        {incident.next_reminder_at && (
                          <span className="text-slate-400 font-mono text-[10px] ml-1">
                            ({new Date(incident.next_reminder_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })})
                          </span>
                        )}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                        <CheckCircle2 className="w-2.5 h-2.5" /> Reminders Scheduled
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {/* Profile & Contact */}
<div
  id="profile"
  className="bg-white p-6 rounded-2xl border border-slate-200 space-y-4 scroll-mt-6"
>
  <h2 className="text-lg font-bold text-slate-800">
    Profile & Contact
  </h2>

  <div>
    <label className="mb-2 block text-sm font-medium text-slate-700">
      Full Name
    </label>
    <input
      type="text"
      value={fullName}
      onChange={(e) => setFullName(e.target.value)}
      required
      className="w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-emerald-600"
      placeholder="Enter your name"
    />
  </div>

  <div>
    <label className="mb-2 block text-sm font-medium text-slate-700">
      Phone Number
    </label>
    <input
      type="tel"
      value={phoneNumber}
      onChange={(e) => setPhoneNumber(e.target.value)}
      className="w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-emerald-600"
      placeholder="Enter your phone number"
    />
  </div>

  <p className="text-xs text-slate-500">
    Use the Save Settings & Preferences button below to save changes.
  </p>
</div>
        {/* =================================================================== */}
        {/* 1. PRIMARY: EMAIL NOTIFICATIONS (SMTP / Resend / Brevo)             */}
        {/* =================================================================== */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-soft space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-100 gap-2">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-emerald-50 text-emerald-600">
                <Mail className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-sm font-bold text-slate-800">Email Notifications</h2>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 uppercase tracking-wider">
                    Primary Channel
                  </span>
                </div>
                <p className="text-xs text-slate-500">
                  Clean HTML emails with food thumbnails, expiry dates, and instant "Mark as used" action links
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={emailEnabled}
                  onChange={(e) => setEmailEnabled(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-600"></div>
              </label>
              <button
                type="button"
                onClick={handleTestEmail}
                disabled={testingEmail || !emailEnabled}
                className="px-3 py-1.5 rounded-xl border border-emerald-200 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 font-bold text-xs flex items-center gap-1.5 transition-colors disabled:opacity-50"
              >
                <Send className="w-3 h-3" />
                {testingEmail ? 'Sending...' : 'Send Test Email'}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1">
                Recipient Email Address
              </label>
              <input
                type="email"
                value={email}
                disabled
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-xs sm:text-sm bg-slate-50 text-slate-600 cursor-not-allowed"
              />
              <span className="text-[10px] text-slate-400 mt-1 block">
                Default: SMTP Gmail App Password or API provider (Resend / Brevo) configured in .env
              </span>
            </div>

            <div className="space-y-2 bg-slate-50/70 p-3.5 rounded-xl border border-slate-200/60">
              <span className="text-xs font-bold text-slate-700 block mb-1">
                Email Alert Subscriptions:
              </span>
              <label className="flex items-center gap-2.5 text-xs text-slate-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={emailForExpiring}
                  onChange={(e) => setEmailForExpiring(e.target.checked)}
                  className="rounded text-emerald-600 focus:ring-emerald-500"
                />
                <span>Expiring Soon Warnings (based on lead time)</span>
              </label>
              <label className="flex items-center gap-2.5 text-xs text-slate-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={emailForExpired}
                  onChange={(e) => setEmailForExpired(e.target.checked)}
                  className="rounded text-emerald-600 focus:ring-emerald-500"
                />
                <span>Expired / Spoilage Critical Alerts (Instant dispatch)</span>
              </label>
              <label className="flex items-center gap-2.5 text-xs text-slate-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={emailDailyDigest}
                  onChange={(e) => setEmailDailyDigest(e.target.checked)}
                  className="rounded text-emerald-600 focus:ring-emerald-500"
                />
                <span>Daily Digest Email (Every morning at 8:00 AM)</span>
              </label>
            </div>
          </div>
        </div>

        {/* =================================================================== */}
        {/* 2. PHONE: PWA WEB PUSH (VAPID Protocol)                             */}
        {/* =================================================================== */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-soft space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-100 gap-2">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-blue-50 text-blue-600">
                <Smartphone className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-sm font-bold text-slate-800">Phone Alerts (PWA Web Push)</h2>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-100 text-blue-800 uppercase tracking-wider">
                    VAPID Protocol
                  </span>
                </div>
                <p className="text-xs text-slate-500">
                  Instant mobile notifications to your home-screen PWA or phone browser without native app store install
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={pushEnabled}
                  onChange={(e) => setPushEnabled(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
              <button
                type="button"
                onClick={handleTestPush}
                disabled={testingPush || !pushEnabled || !hasPushSubscription}
                className="px-3 py-1.5 rounded-xl border border-blue-200 bg-blue-50 hover:bg-blue-100 text-blue-700 font-bold text-xs flex items-center gap-1.5 transition-colors disabled:opacity-50"
              >
                <Bell className="w-3 h-3" />
                {testingPush ? 'Sending...' : 'Send Test Push'}
              </button>
            </div>
          </div>

          {pushPermission === 'denied' && (
            <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 flex items-start gap-3">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <div className="text-xs">
                <span className="font-bold">Mobile Notification Permission Denied in Browser:</span>
                <p className="mt-0.5 text-rose-800 leading-relaxed">
                  Your browser has blocked push notifications for this site. To receive mobile spoilage reminders, click the site settings / padlock icon in your browser URL address bar, change Notifications to "Allow", and reload this page.
                </p>
              </div>
            </div>
          )}

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/70 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-slate-800">Device Push Subscription:</span>
                {hasPushSubscription ? (
                  <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                    <CheckCircle2 className="w-3 h-3" /> Active & Registered
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-[11px] font-bold text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">
                    <AlertCircle className="w-3 h-3" /> Not Registered Yet
                  </span>
                )}
              </div>
              <p className="text-[11px] text-slate-500">
                Click below to request browser permission and register this device's Service Worker with VAPID keys.
              </p>
            </div>

            <div className="flex items-center gap-2 flex-wrap self-start sm:self-auto shrink-0">
              <button
                type="button"
                disabled={enablingPush}
                onClick={handleEnablePush}
                className="px-4 py-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-bold text-xs shadow-sm transition-all flex items-center gap-1.5"
              >
                <Sparkles className="w-3.5 h-3.5" />
                {enablingPush ? 'Enabling...' : hasPushSubscription ? 'Re-register Device' : 'Enable Notifications'}
              </button>
              {hasPushSubscription && (
                <button
                  type="button"
                  disabled={unsubscribingPush}
                  onClick={handleUnsubscribePush}
                  className="px-3 py-2 rounded-xl border border-rose-200 bg-rose-50 hover:bg-rose-100 text-rose-700 font-bold text-xs transition-colors flex items-center gap-1.5"
                >
                  <XCircle className="w-3.5 h-3.5 text-rose-600" />
                  {unsubscribingPush ? 'Unsubscribing...' : 'Unsubscribe'}
                </button>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 pt-1">
            <label className="flex items-center gap-2 p-2.5 rounded-xl border border-slate-200 text-xs text-slate-700 cursor-pointer bg-white">
              <input
                type="checkbox"
                checked={pushForSpoilage}
                onChange={(e) => setPushForSpoilage(e.target.checked)}
                className="rounded text-rose-600 focus:ring-rose-500"
              />
              <span className="font-semibold text-rose-900">🚨 Spoilage Alerts</span>
            </label>
            <label className="flex items-center gap-2 p-2.5 rounded-xl border border-slate-200 text-xs text-slate-700 cursor-pointer bg-white">
              <input
                type="checkbox"
                checked={pushForExpiring}
                onChange={(e) => setPushForExpiring(e.target.checked)}
                className="rounded text-blue-600 focus:ring-blue-500"
              />
              <span>Expiring Soon Alerts</span>
            </label>
            <label className="flex items-center gap-2 p-2.5 rounded-xl border border-slate-200 text-xs text-slate-700 cursor-pointer bg-white">
              <input
                type="checkbox"
                checked={pushForExpired}
                onChange={(e) => setPushForExpired(e.target.checked)}
                className="rounded text-blue-600 focus:ring-blue-500"
              />
              <span>Expired Critical Alerts</span>
            </label>
            <label className="flex items-center gap-2 p-2.5 rounded-xl border border-slate-200 text-xs text-slate-700 cursor-pointer bg-white">
              <input
                type="checkbox"
                checked={pushForTemperature}
                onChange={(e) => setPushForTemperature(e.target.checked)}
                className="rounded text-blue-600 focus:ring-blue-500"
              />
              <span>Door Ajar / Temp Spikes</span>
            </label>
          </div>

          {/* Spoilage 2-Hour Recurring Reminders Configuration */}
          <div className="p-4 rounded-xl bg-gradient-to-r from-rose-50/60 to-amber-50/60 border border-rose-200/80 space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h3 className="text-xs font-bold text-rose-950 flex items-center gap-1.5">
                  <Clock className="w-4 h-4 text-rose-600" />
                  Recurring Spoilage Reminders
                </h3>
                <p className="text-[11px] text-slate-600 mt-0.5">
                  Sends an immediate alert when food is detected spoiled, followed by periodic reminders until removed or marked resolved.
                </p>
              </div>

              <label className="relative inline-flex items-center cursor-pointer shrink-0">
                <input
                  type="checkbox"
                  checked={spoilageReminderEnabled}
                  onChange={(e) => setSpoilageReminderEnabled(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-9 h-5 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-rose-600"></div>
              </label>
            </div>

            {spoilageReminderEnabled && (
              <div className="flex flex-col sm:flex-row sm:items-center gap-3 pt-2 border-t border-rose-100">
                <label className="text-xs font-medium text-slate-700 flex items-center gap-2">
                  <span>Reminder Interval:</span>
                  <select
                    value={spoilageReminderInterval}
                    onChange={(e) => setSpoilageReminderInterval(Number(e.target.value))}
                    className="px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-xs font-bold text-slate-800 focus:ring-2 focus:ring-rose-500 focus:outline-none"
                  >
                    <option value={15}>15 minutes (Fast Verification / Test Mode)</option>
                    <option value={30}>30 minutes</option>
                    <option value={60}>1 hour</option>
                    <option value={120}>2 hours (Recommended Default)</option>
                    <option value={240}>4 hours</option>
                    <option value={480}>8 hours</option>
                  </select>
                </label>
                <span className="text-[11px] text-slate-500">
                  Next reminder timestamp updates persistently in the database across server restarts.
                </span>
              </div>
            )}
          </div>
        </div>

        {/* =================================================================== */}
        {/* =================================================================== */}
        {/* 3. TELEGRAM BOT NOTIFICATIONS (Primary Instant Mobile Alert Channel) */}
        {/* =================================================================== */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-soft space-y-5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-100 gap-3">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-sky-50 text-sky-600">
                <Send className="w-5 h-5 text-sky-600" />
              </div>
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <h2 className="text-sm font-bold text-slate-800">Telegram Bot Notifications (Mobile Alerts)</h2>
                  {telegramSystemStatus?.configured ? (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 uppercase tracking-wider flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                      Telegram Active (Chat: {telegramSystemStatus.chat_id})
                    </span>
                  ) : (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 uppercase tracking-wider flex items-center gap-1">
                      <AlertCircle className="w-3 h-3 text-amber-600" />
                      Setup Needed (.env keys missing)
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-500">
                  Instant mobile notifications sent directly to your Telegram chat via BotFather bot API
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={smsEnabled}
                  onChange={(e) => setSmsEnabled(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-sky-600"></div>
              </label>
            </div>
          </div>

          {!telegramSystemStatus?.configured && (
            <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 flex items-start gap-3">
              <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              <div className="text-xs">
                <span className="font-bold">Telegram Bot Provider Not Configured:</span>
                <p className="mt-0.5 text-amber-800 leading-relaxed">
                  To receive real-time notifications on your phone via Telegram, open your backend <code className="bg-amber-100 px-1 py-0.5 rounded text-amber-900 font-mono font-bold">.env</code> file and configure <code className="bg-amber-100 px-1 py-0.5 rounded text-amber-900 font-mono font-bold">TELEGRAM_BOT_TOKEN</code> (from @BotFather) and <code className="bg-amber-100 px-1 py-0.5 rounded text-amber-900 font-mono font-bold">TELEGRAM_CHAT_ID</code>.
                </p>
              </div>
            </div>
          )}

          {/* Target Chat ID display & Quick Instructions */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1">
                Active Telegram Chat ID
              </label>
              <input
                type="text"
                placeholder="e.g. 123456789 (from backend/.env)"
                value={testTelegramChatId || telegramSystemStatus?.chat_id || ''}
                onChange={(e) => setTestTelegramChatId(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-xs sm:text-sm focus:ring-2 focus:ring-sky-500 focus:outline-none font-mono bg-slate-50"
              />
              <span className="text-[10px] text-slate-500 mt-1 block">
                🤖 Configured via <code className="bg-slate-100 px-1 py-0.5 rounded text-slate-700">TELEGRAM_CHAT_ID</code> in backend/.env.
              </span>
            </div>

            <div className="bg-sky-50/60 p-3.5 rounded-xl border border-sky-200/60 text-xs text-sky-900 space-y-1">
              <div className="font-bold flex items-center gap-1.5 text-sky-800">
                <Zap className="w-3.5 h-3.5 text-sky-600" />
                Telegram Delivery Flow
              </div>
              <p className="text-[11px] text-sky-800/90 leading-relaxed">
                When an alert triggers, Telegram delivers an immediate rich notification with emojis and actionable advice. If unacknowledged, spoilage alerts repeat every {smsRepeatInterval} minutes up to {smsMaxDuration} minutes.
              </p>
            </div>
          </div>

          {/* Repeat Cadence Controls */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
            <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200/70">
              <label className="text-xs font-bold text-slate-800 block mb-1">
                Repeat Notification Interval
              </label>
              <p className="text-[11px] text-slate-500 mb-2">
                Time between repeated Telegram reminders while spoilage alert remains active
              </p>
              <select
                value={smsRepeatInterval}
                onChange={(e) => setSmsRepeatInterval(parseInt(e.target.value, 10))}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs bg-white focus:ring-2 focus:ring-sky-500 focus:outline-none font-semibold text-slate-700"
              >
                <option value={5}>Every 5 Minutes (Rapid Testing)</option>
                <option value={10}>Every 10 Minutes</option>
                <option value={15}>Every 15 Minutes (Default / Recommended)</option>
                <option value={30}>Every 30 Minutes</option>
                <option value={60}>Every 60 Minutes (1 Hour)</option>
              </select>
            </div>

            <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200/70">
              <label className="text-xs font-bold text-slate-800 block mb-1">
                Maximum Repeat Duration Cutoff
              </label>
              <p className="text-[11px] text-slate-500 mb-2">
                Hard limit after which Telegram repeats cease automatically
              </p>
              <select
                value={smsMaxDuration}
                onChange={(e) => setSmsMaxDuration(parseInt(e.target.value, 10))}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs bg-white focus:ring-2 focus:ring-sky-500 focus:outline-none font-semibold text-slate-700"
              >
                <option value={30}>30 Minutes</option>
                <option value={60}>1 Hour (60 Minutes)</option>
                <option value={120}>2 Hours (120 Minutes - Standard Max)</option>
                <option value={180}>3 Hours (180 Minutes)</option>
              </select>
            </div>
          </div>

          {/* Alert Category Subscriptions */}
          <div className="space-y-2 pt-1">
            <span className="text-xs font-bold text-slate-800 block">
              Telegram Alert Subscriptions:
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              <label className="flex items-start gap-2.5 p-3 rounded-xl border border-slate-200 bg-white hover:bg-slate-50/50 cursor-pointer transition-colors">
                <input
                  type="checkbox"
                  checked={smsForDairy}
                  onChange={(e) => setSmsForDairy(e.target.checked)}
                  className="rounded text-sky-600 focus:ring-sky-500 mt-0.5"
                />
                <div>
                  <span className="text-xs font-bold text-slate-800 block">🥛 Dairy Product Alerts</span>
                  <span className="text-[10px] text-slate-500">Milk, Yogurt, Paneer &amp; Cheese expiry warnings</span>
                </div>
              </label>

              <label className="flex items-start gap-2.5 p-3 rounded-xl border border-slate-200 bg-white hover:bg-slate-50/50 cursor-pointer transition-colors">
                <input
                  type="checkbox"
                  checked={smsForExpired}
                  onChange={(e) => setSmsForExpired(e.target.checked)}
                  className="rounded text-sky-600 focus:ring-sky-500 mt-0.5"
                />
                <div>
                  <span className="text-xs font-bold text-slate-800 block">⚠️ Expired / Spoiled Food</span>
                  <span className="text-[10px] text-slate-500">Critical notifications for expired groceries</span>
                </div>
              </label>

              <label className="flex items-start gap-2.5 p-3 rounded-xl border border-slate-200 bg-white hover:bg-slate-50/50 cursor-pointer transition-colors">
                <input
                  type="checkbox"
                  checked={smsForTemperature}
                  onChange={(e) => setSmsForTemperature(e.target.checked)}
                  className="rounded text-sky-600 focus:ring-sky-500 mt-0.5"
                />
                <div>
                  <span className="text-xs font-bold text-slate-800 block">🌡️ Temperature Spikes</span>
                  <span className="text-[10px] text-slate-500">Door ajar or temperature excursions beyond safe limits</span>
                </div>
              </label>

              <label className="flex items-start gap-2.5 p-3 rounded-xl border border-slate-200 bg-white hover:bg-slate-50/50 cursor-pointer transition-colors">
                <input
                  type="checkbox"
                  checked={smsForExpiring}
                  onChange={(e) => setSmsForExpiring(e.target.checked)}
                  className="rounded text-sky-600 focus:ring-sky-500 mt-0.5"
                />
                <div>
                  <span className="text-xs font-bold text-slate-800 block">⏳ Expiring Soon Warnings</span>
                  <span className="text-[10px] text-slate-500">Items nearing their expiry date ({alertLeadDays} days lead)</span>
                </div>
              </label>

              <label className="flex items-start gap-2.5 p-3 rounded-xl border border-slate-200 bg-white hover:bg-slate-50/50 cursor-pointer transition-colors">
                <input
                  type="checkbox"
                  checked={smsForCritical}
                  onChange={(e) => setSmsForCritical(e.target.checked)}
                  className="rounded text-sky-600 focus:ring-sky-500 mt-0.5"
                />
                <div>
                  <span className="text-xs font-bold text-slate-800 block">🚨 Critical Alerts Only</span>
                  <span className="text-[10px] text-slate-500">Filter out warnings; deliver only severe hazards</span>
                </div>
              </label>
            </div>
          </div>

          {/* Test Telegram Dispatcher */}
          <div className="bg-slate-50/80 p-4 rounded-xl border border-slate-200/80 space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h3 className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                  <Send className="w-3.5 h-3.5 text-sky-600" />
                  Send Test Telegram Message
                </h3>
                <p className="text-[11px] text-slate-500">
                  Verify bot token and chat ID reachability with a live test message to your Telegram app
                </p>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="text"
                  placeholder="Chat ID (e.g. 123456789)"
                  value={testTelegramChatId}
                  onChange={(e) => setTestTelegramChatId(e.target.value)}
                  className="px-3 py-1.5 rounded-xl border border-slate-200 text-xs bg-white font-mono focus:ring-2 focus:ring-sky-500 focus:outline-none w-48"
                />
                <button
                  type="button"
                  onClick={handleTestTelegram}
                  disabled={testingTelegram}
                  className="px-4 py-1.5 rounded-xl bg-sky-600 hover:bg-sky-700 text-white font-bold text-xs flex items-center gap-1.5 transition-colors disabled:opacity-50 shadow-xs"
                >
                  <Send className={`w-3 h-3 ${testingTelegram ? 'animate-spin' : ''}`} />
                  {testingTelegram ? 'Transmitting...' : 'Send Test Telegram'}
                </button>
              </div>
            </div>

            {/* Diagnostic Result Banner */}
            {testTelegramResult && (
              <div className={`p-3 rounded-xl border text-xs space-y-1 ${
                testTelegramResult.status === 'delivered' 
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-900' 
                  : 'bg-rose-50 border-rose-200 text-rose-900'
              }`}>
                <div className="flex items-center justify-between font-bold">
                  <span className="flex items-center gap-1.5">
                    {testTelegramResult.status === 'delivered' ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    ) : (
                      <AlertCircle className="w-3.5 h-3.5 text-rose-600" />
                    )}
                    {testTelegramResult.status === 'delivered' ? 'Telegram Message Delivered' : 'Telegram Transmission Failed'}
                  </span>
                  <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-white/80 border">
                    Msg ID: {testTelegramResult.provider_message_id || 'N/A'}
                  </span>
                </div>
                <div className="text-[11px] font-mono bg-white/70 p-2 rounded-lg border border-slate-200/50 mt-1">
                  {testTelegramResult.formatted_message}
                </div>
                <div className="text-[10px] opacity-80 pt-0.5">
                  Recipient Chat: <span className="font-mono font-semibold">{testTelegramResult.recipient}</span> • Provider: <span className="font-mono font-semibold">{testTelegramResult.provider}</span> • Status: <span className="font-semibold uppercase">{testTelegramResult.delivery_status}</span>
                </div>
              </div>
            )}
          </div>
        </div>


        {/* =================================================================== */}
        {/* 4. RULES, QUIET HOURS & AUDIT SCHEDULE                              */}
        {/* =================================================================== */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-soft space-y-4">
          <h2 className="text-sm font-bold text-slate-800 border-b border-slate-100 pb-3 flex items-center gap-2">
            <Clock className="w-4 h-4 text-emerald-600" />
            Alert Lead Times & Quiet Hours
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1">
                Expiration Lead Time
              </label>
              <select
                value={alertLeadDays}
                onChange={(e) => setAlertLeadDays(parseInt(e.target.value, 10))}
                className="w-full px-3 py-2.5 rounded-xl border border-slate-200 text-xs sm:text-sm bg-white focus:ring-2 focus:ring-emerald-500 focus:outline-none"
              >
                <option value={1}>1 Day Before Expiry</option>
                <option value={2}>2 Days Before Expiry (Recommended)</option>
                <option value={3}>3 Days Before Expiry</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1">
                Quiet Hours Start
              </label>
              <input
                type="time"
                value={quietHoursStart}
                onChange={(e) => setQuietHoursStart(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs sm:text-sm bg-white"
              />
            </div>

            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1">
                Quiet Hours End
              </label>
              <input
                type="time"
                value={quietHoursEnd}
                onChange={(e) => setQuietHoursEnd(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs sm:text-sm bg-white"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1">
                Weekly Fridge Audit Day
              </label>
              <select
                value={auditDay}
                onChange={(e) => setAuditDay(e.target.value)}
                className="w-full px-3 py-2.5 rounded-xl border border-slate-200 text-xs sm:text-sm bg-white focus:ring-2 focus:ring-emerald-500 focus:outline-none"
              >
                {['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'].map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1">
                Audit Reminder Time
              </label>
              <input
                type="time"
                value={auditTime}
                onChange={(e) => setAuditTime(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs sm:text-sm bg-white"
              />
            </div>
          </div>
        </div>

        {/* Submit */}
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs sm:text-sm px-7 py-3 rounded-xl shadow-md shadow-emerald-500/20 transition-all active:scale-95"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving...' : 'Save Settings & Preferences'}
          </button>
        </div>
      </form>

      {/* =================================================================== */}
      {/* 5. NOTIFICATION LOGS (notifications_log table)                       */}
      {/* =================================================================== */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-soft space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-100 gap-3">
          <div>
            <h2 className="text-sm font-bold text-slate-800 flex items-center gap-2">
              <Shield className="w-4 h-4 text-emerald-600" />
              Notification Dispatch History &amp; Retry Logs
            </h2>
            <p className="text-xs text-slate-500">
              Audit log of all attempted notifications with repeat cycles, Twilio message SIDs, and delivery states
            </p>
          </div>

          <div className="flex items-center gap-2">
            {/* Filter buttons */}
            <div className="flex items-center bg-slate-100 p-1 rounded-xl text-[11px] font-semibold text-slate-600">
              {(['all', 'sms', 'email', 'web_push'] as const).map((ch) => (
                <button
                  key={ch}
                  type="button"
                  onClick={() => setChannelFilter(ch)}
                  className={`px-2.5 py-1 rounded-lg uppercase tracking-wider text-[10px] font-bold transition-all ${
                    channelFilter === ch ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-500 hover:text-slate-900'
                  }`}
                >
                  {ch === 'all' ? 'All' : ch.replace('_', ' ')}
                </button>
              ))}
            </div>

            <button
              type="button"
              onClick={loadLogs}
              disabled={logsLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50 transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${logsLoading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>

        {logs.filter(l => channelFilter === 'all' || l.channel === channelFilter).length === 0 ? (
          <div className="py-8 text-center text-xs text-slate-400">
            No notification records found for the selected filter.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-100 text-slate-400 uppercase text-[10px] tracking-wider font-semibold">
                  <th className="py-2.5 px-3">Time</th>
                  <th className="py-2.5 px-3">Channel</th>
                  <th className="py-2.5 px-3">Recipient &amp; SID</th>
                  <th className="py-2.5 px-3">Content / Alert Message</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Cycle</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {logs
                  .filter(l => channelFilter === 'all' || l.channel === channelFilter)
                  .map((log) => {
                    const isSent = log.status === 'sent' || log.status === 'queued';
                    const isSimulated = log.status === 'simulated' || (log.provider && log.provider.includes('simulated'));
                    const dateStr = new Date(log.created_at).toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                      second: '2-digit'
                    });

                    return (
                      <tr key={log.id} className="hover:bg-slate-50/60 transition-colors">
                        <td className="py-2.5 px-3 whitespace-nowrap text-slate-500 font-mono text-[11px]">
                          {dateStr}
                        </td>
                        <td className="py-2.5 px-3 whitespace-nowrap">
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md font-bold text-[10px] uppercase ${
                            log.channel === 'email'
                              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                              : log.channel === 'web_push'
                              ? 'bg-blue-50 text-blue-700 border border-blue-200'
                              : 'bg-amber-50 text-amber-700 border border-amber-200'
                          }`}>
                            {log.channel === 'email' && <Mail className="w-2.5 h-2.5" />}
                            {log.channel === 'web_push' && <Smartphone className="w-2.5 h-2.5" />}
                            {log.channel === 'sms' && <MessageSquare className="w-2.5 h-2.5" />}
                            {log.channel}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 whitespace-nowrap text-slate-600 font-mono text-[11px]">
                          <div>{log.recipient || 'N/A'}</div>
                          {log.provider_message_id && (
                            <div className="text-[10px] text-slate-400 font-mono truncate max-w-[150px]">
                              ID: {log.provider_message_id}
                            </div>
                          )}
                        </td>
                        <td className="py-2.5 px-3 max-w-[280px]">
                          <div className="font-semibold text-slate-800 truncate">{log.title}</div>
                          <div className="text-[11px] text-slate-500 truncate">{log.message}</div>
                          {log.error_message && (
                            <div className="text-[10px] text-rose-500 truncate font-mono mt-0.5">
                              Error: {log.error_message}
                            </div>
                          )}
                        </td>
                        <td className="py-2.5 px-3 whitespace-nowrap">
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-bold text-[10px] ${
                            isSimulated
                              ? 'bg-amber-100 text-amber-800'
                              : isSent
                              ? 'bg-emerald-100 text-emerald-800'
                              : 'bg-rose-100 text-rose-800'
                          }`}>
                            {isSimulated ? (
                              <AlertCircle className="w-3 h-3 text-amber-600" />
                            ) : isSent ? (
                              <CheckCircle2 className="w-3 h-3" />
                            ) : (
                              <XCircle className="w-3 h-3" />
                            )}
                            {isSimulated ? 'Simulated' : log.status}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 whitespace-nowrap text-slate-500 font-mono text-[11px]">
                          {log.repeat_count && log.repeat_count > 1 ? (
                            <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 font-bold">
                              #{log.repeat_count}
                            </span>
                          ) : (
                            <span>#1</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
