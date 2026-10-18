import { settingsApi } from './api';

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

export async function registerServiceWorker(): Promise<ServiceWorkerRegistration | null> {
  if (!('serviceWorker' in navigator)) {
    console.warn('Service Workers are not supported in this browser.');
    return null;
  }

  try {
    const reg = await navigator.serviceWorker.register('/sw.js');
    console.log('[PWA] Service Worker registered successfully:', reg.scope);
    return reg;
  } catch (err) {
    console.error('[PWA] Service Worker registration failed:', err);
    return null;
  }
}

export async function subscribeToWebPush(): Promise<{ success: boolean; message: string }> {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    return {
      success: false,
      message: 'Web Push is not supported on this browser or platform.'
    };
  }

  try {
    // 1. Request notification permission
    const permission = await Notification.requestPermission();
    if (permission !== 'granted') {
      return {
        success: false,
        message: 'Notification permission was denied. Please allow notifications in browser site settings.'
      };
    }

    // 2. Ensure Service Worker is registered and active
    const registration = await navigator.serviceWorker.ready;

    // 3. Fetch VAPID Public Key from backend
    const vapidData = await settingsApi.getVapidPublicKey();
    if (!vapidData.public_key) {
      return {
        success: false,
        message: 'Web Push is disabled or VAPID key is missing on the server.'
      };
    }

    const applicationServerKey = urlBase64ToUint8Array(vapidData.public_key);

    // 4. Subscribe with PushManager
    const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: applicationServerKey as any
    });

    // 5. Send subscription JSON to backend
    const subJson = subscription.toJSON();
    await settingsApi.subscribePush(subJson);

    return {
      success: true,
      message: 'Push notifications successfully enabled! Your device is now registered.'
    };
  } catch (err: any) {
    console.error('Error subscribing to web push:', err);
    return {
      success: false,
      message: err.message || 'Failed to complete push subscription.'
    };
  }
}

export async function unsubscribeFromWebPush(): Promise<{ success: boolean; message: string }> {
  try {
    if ('serviceWorker' in navigator) {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.getSubscription();
      if (subscription) {
        await subscription.unsubscribe();
      }
    }
    await settingsApi.unsubscribePush();
    return {
      success: true,
      message: 'Successfully unsubscribed from Web Push notifications.'
    };
  } catch (err: any) {
    console.error('Error unsubscribing from web push:', err);
    return {
      success: false,
      message: err.message || 'Failed to unsubscribe.'
    };
  }
}

