// Smart Fridge PWA Service Worker - Push & Caching
self.addEventListener('install', (event) => {
  console.log('[SW] Service Worker Installed');
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  console.log('[SW] Service Worker Activated');
  event.waitUntil(self.clients.claim());
});

// Handle incoming Web Push notifications from FastAPI VAPID backend
self.addEventListener('push', (event) => {
  console.log('[SW] Push received:', event);
  let data = {
    title: 'Smart Fridge Alert',
    body: 'You have a new fridge alert!',
    icon: '/favicon.svg',
    badge: '/favicon.svg',
    url: '/alerts',
    tag: 'smart-fridge-alert'
  };

  if (event.data) {
    try {
      const parsed = event.data.json();
      data = { ...data, ...parsed };
    } catch (err) {
      data.body = event.data.text();
    }
  }

  const options = {
    body: data.body,
    icon: data.icon || '/favicon.svg',
    badge: data.badge || '/favicon.svg',
    tag: data.tag || 'smart-fridge',
    vibrate: [200, 100, 200, 100, 200],
    data: {
      url: data.url || '/alerts'
    },
    actions: [
      { action: 'open', title: '🚨 View Spoilage Alert' },
      { action: 'dismiss', title: 'Dismiss' }
    ]
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

// Handle notification clicks
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  if (event.action === 'dismiss') {
    return;
  }

  let targetUrl = (event.notification.data && event.notification.data.url) ? event.notification.data.url : '/alerts';
  if (!targetUrl.startsWith('http')) {
    targetUrl = new URL(targetUrl, self.location.origin).href;
  }

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if (client.url && 'focus' in client) {
          client.navigate(targetUrl);
          return client.focus();
        }
      }
      if (self.clients.openWindow) {
        return self.clients.openWindow(targetUrl);
      }
    })
  );
});
