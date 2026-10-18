import axios from 'axios';
import {
  User, Zone, FoodItem, AlertItem, DashboardSummary,
  PredictionResponse, DairyPredictionResponse, BarcodeProduct, AuditSession, NotificationLog, SchedulerStatus
} from '../types';

const API_BASE = '/api';

export const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach JWT token from localStorage if valid
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('smart_fridge_token');
  if (token && token !== 'undefined' && token !== 'null' && token.trim() !== '') {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let onConnectionErrorCallback: ((isDown: boolean) => void) | null = null;
export const setConnectionErrorListener = (cb: (isDown: boolean) => void) => {
  onConnectionErrorCallback = cb;
};

api.interceptors.response.use(
  (response) => {
    onConnectionErrorCallback?.(false);
    return response;
  },
  (error) => {
    // Discriminate between Vite dev-proxy connection drops (empty 502 body) vs intentional backend HTTP 502
    const hasBackendDetail = Boolean(error.response?.data?.detail);
    const isProxyOrNetworkError = !error.response || error.code === 'ERR_NETWORK' || (
      [502, 503, 504].includes(error.response.status) && !hasBackendDetail
    );

    if (isProxyOrNetworkError) {
      onConnectionErrorCallback?.(true);
      if (error.response?.status === 502 && !hasBackendDetail) {
        error.message = 'Backend API server is offline or unreachable on http://127.0.0.1:8000 (502 Bad Gateway)';
      }
    }

    if (error.response && error.response.status === 401) {
      localStorage.removeItem('smart_fridge_token');
    }
    return Promise.reject(error);
  }
);

export const checkBackendHealth = async (): Promise<boolean> => {
  try {
    // Attempt /api/health first (standard proxied API), fallback to root /health
    let res;
    try {
      res = await api.get('/health', { timeout: 2500 });
    } catch {
      res = await axios.get('/health', { timeout: 2500 });
    }
    const isOk = res.data?.status === 'healthy' || res.data?.status === 'degraded';
    onConnectionErrorCallback?.(!isOk);
    return isOk;
  } catch {
    onConnectionErrorCallback?.(true);
    return false;
  }
};

// Auth API
export const authApi = {
  login: async (email: string, password: string) => {
    const res = await api.post('/auth/login', { email, password });
    return res.data;
  },
  register: async (data: any) => {
    const res = await api.post('/auth/register', data);
    return res.data;
  },
  getMe: async (): Promise<User> => {
    const res = await api.get('/auth/me');
    return res.data;
  },
};

// Dashboard API
export const dashboardApi = {
  getSummary: async (): Promise<DashboardSummary> => {
    const res = await api.get('/dashboard/summary');
    return res.data;
  },
};

// Foods API
export const foodsApi = {
  getAll: async (params?: any): Promise<FoodItem[]> => {
    const res = await api.get('/foods', { params });
    return res.data;
  },
  getById: async (id: number): Promise<FoodItem> => {
    const res = await api.get(`/foods/${id}`);
    return res.data;
  },
  create: async (data: any): Promise<FoodItem> => {
    const res = await api.post('/foods', data);
    return res.data;
  },
  update: async (id: number, data: any): Promise<FoodItem> => {
    const res = await api.put(`/foods/${id}`, data);
    return res.data;
  },
  delete: async (id: number) => {
    const res = await api.delete(`/foods/${id}`);
    return res.data;
  },
  markUsed: async (id: number): Promise<FoodItem> => {
    const res = await api.post(`/foods/${id}/use`);
    return res.data;
  },
  markDiscarded: async (id: number): Promise<FoodItem> => {
    const res = await api.post(`/foods/${id}/discard`);
    return res.data;
  },
};

// AI Recognition & Prediction
export const aiApi = {
  predictFreshness: async (
    file: File,
    useWebcamModel = false
  ): Promise<PredictionResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await api.post('/predict', formData, {
      params: useWebcamModel ? { use_webcam_model: true } : undefined,
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },
  lookupBarcode: async (barcode: string): Promise<BarcodeProduct> => {
    const res = await api.get(`/barcode/${barcode}`);
    return res.data;
  },
  ocrExpiry: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await api.post('/ocr/expiry', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },
  predictDairy: async (file: File): Promise<DairyPredictionResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await api.post('/predict/dairy', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },
};

// Zones & Sensors
export const zonesApi = {
  getAll: async (): Promise<Zone[]> => {
    const res = await api.get('/zones');
    return res.data;
  },
  getSensorsLatest: async () => {
    const res = await api.get('/sensors/latest');
    return res.data;
  },
  getSensorsHistory: async (hours = 24) => {
    const res = await api.get(`/sensors/history?hours=${hours}`);
    return res.data;
  },
  postSensorReading: async (data: { zone_code: string; temperature: number; humidity: number }) => {
    const res = await api.post('/sensors', data);
    return res.data;
  }
};

// Alerts
export const alertsApi = {
  getAll: async (params?: any): Promise<AlertItem[]> => {
    const res = await api.get('/alerts', { params });
    return res.data;
  },
  markRead: async (id: number) => {
    const res = await api.put(`/alerts/${id}/read`);
    return res.data;
  },
  resolve: async (id: number) => {
    const res = await api.put(`/alerts/${id}/resolve`);
    return res.data;
  },
  markAllRead: async () => {
    const res = await api.put('/alerts/read-all');
    return res.data;
  },
  delete: async (id: number) => {
    const res = await api.delete(`/alerts/${id}`);
    return res.data;
  },
  evaluate: async () => {
    const res = await api.post('/alerts/evaluate');
    return res.data;
  },
  testNotification: async (channel = 'all') => {
    const res = await api.post(`/alerts/test-notification?channel=${channel}`);
    return res.data;
  },
  getSchedulerStatus: async (): Promise<SchedulerStatus> => {
    const res = await api.get('/alerts/scheduler-status');
    return res.data;
  },
  getActiveSpoilage: async (): Promise<AlertItem[]> => {
    const res = await api.get('/alerts/active-spoilage');
    return res.data;
  },
  removeFood: async (alertId: number) => {
    const res = await api.post(`/alerts/${alertId}/remove-food`);
    return res.data;
  },
  createSpoilageAlert: async (data: {
    food_item_id: number;
    food_name: string;
    zone_name?: string;
    freshness_status?: string;
    confidence?: number;
    category?: string;
  }) => {
    const res = await api.post('/alerts/spoilage', data);
    return res.data;
  },
};

// Weekly Audit
export const auditApi = {
  submitAudit: async (files: File[]): Promise<AuditSession> => {
    const formData = new FormData();
    files.forEach((f) => formData.append('files', f));
    const res = await api.post('/audit', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },
  getSessions: async (): Promise<AuditSession[]> => {
    const res = await api.get('/audit/sessions');
    return res.data;
  },
  resolveMissing: async (resultId: number, resolution: string) => {
    const res = await api.post('/audit/resolve', { result_id: resultId, resolution });
    return res.data;
  },
};

// History & Analytics
export const historyApi = {
  get: async (action?: string) => {
    const res = await api.get('/history', { params: { action } });
    return res.data;
  },
};

// Settings & Notifications
export const settingsApi = {
  get: async () => {
    const res = await api.get('/settings');
    return res.data;
  },
  update: async (data: any) => {
    const res = await api.put('/settings', data);
    return res.data;
  },
  testEmail: async (recipient?: string) => {
    const res = await api.post(`/settings/test-email${recipient ? `?recipient=${encodeURIComponent(recipient)}` : ''}`);
    return res.data;
  },
  testPush: async () => {
    const res = await api.post('/settings/test-push');
    return res.data;
  },
  testTelegram: async (chatId?: string) => {
    const res = await api.post(`/settings/test-telegram${chatId ? `?chat_id=${encodeURIComponent(chatId)}` : ''}`);
    return res.data;
  },
  testSms: async (phoneNumber?: string) => {
    const res = await api.post(`/settings/test-sms${phoneNumber ? `?phone_number=${encodeURIComponent(phoneNumber)}` : ''}`);
    return res.data;
  },
  getVapidPublicKey: async (): Promise<{ public_key: string; enabled: boolean }> => {
    const res = await api.get('/settings/vapid-public-key');
    return res.data;
  },
  subscribePush: async (subscription: any) => {
    const res = await api.post('/settings/subscribe-push', subscription);
    return res.data;
  },
  unsubscribePush: async () => {
    const res = await api.post('/settings/unsubscribe-push');
    return res.data;
  },
  getNotificationLogs: async (limit = 30): Promise<NotificationLog[]> => {
    const res = await api.get('/settings/notifications-log', { params: { limit } });
    return res.data;
  },
};

// Dataset & Retraining Loop
export const datasetApi = {
  getStats: async () => {
    const res = await api.get('/dataset/stats');
    return res.data;
  },
  getPending: async () => {
    const res = await api.get('/dataset/pending');
    return res.data;
  },
  verifyImage: async (id: number, action: 'approve' | 'reject', targetSplit = 'train') => {
    const res = await api.post(`/dataset/verify/${id}?action=${action}&target_split=${targetSplit}`);
    return res.data;
  },
  submitFeedback: async (data: any) => {
    const res = await api.post('/dataset/feedback', data);
    return res.data;
  }
};
