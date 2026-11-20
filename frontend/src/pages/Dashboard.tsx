import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowRight,
  CalendarDays,
  Camera,
  CheckCircle2,
  ChevronRight,
  Clock3,
  Leaf,
  Package,
  Plus,
  RefreshCw,
  Sparkles,
  Utensils,
  XCircle,
} from 'lucide-react';
import { dashboardApi } from '../services/api';
import { DashboardSummary, FoodItem } from '../types';
import { SensorCharts } from '../components/SensorCharts';
import { getFoodEmoji } from '../utils/foodIcons';
import { useAuth } from '../context/AuthContext';

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  weekday: 'long',
  month: 'long',
  day: 'numeric',
  year: 'numeric',
});

const getDaysLeft = (food: FoodItem): number | null => {
  if (typeof food.days_until_expiry === 'number') return food.days_until_expiry;
  if (!food.expiry_date) return null;

  const parts = food.expiry_date.slice(0, 10).split('-').map(Number);
  if (parts.length !== 3 || parts.some(Number.isNaN)) return null;

  const expiry = new Date(parts[0], parts[1] - 1, parts[2]);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((expiry.getTime() - today.getTime()) / 86400000);
};

const getExpiryLabel = (daysLeft: number | null): string => {
  if (daysLeft === null) return 'Check date';
  if (daysLeft < 0) return 'Past date';
  if (daysLeft === 0) return 'Use today';
  if (daysLeft === 1) return 'Use tomorrow';
  return `In ${daysLeft} days`;
};

const getGreeting = (): string => {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
};

export const Dashboard: React.FC = () => {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const navigate = useNavigate();
  const { user } = useAuth();
  const firstName = user?.full_name?.trim().split(/\s+/)[0] || '';

  const loadData = async () => {
    try {
      const res = await dashboardApi.getSummary();
      setData(res);
      setLoadError(false);
    } catch (err) {
      console.error('Failed to load dashboard:', err);
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 20000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !data) {
    return (
      <div className="flex min-h-[55vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-center">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-[#356247] border-t-transparent" />
          <p className="text-sm font-medium text-[#5b685f]">Loading your kitchen…</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <section className="kitchen-panel mx-auto flex max-w-xl flex-col items-center gap-4 px-6 py-12 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#edf2e8] text-[#356247]">
          <RefreshCw className="h-7 w-7" />
        </div>
        <h1 className="kitchen-heading text-3xl">We couldn’t load your kitchen</h1>
        <p className="max-w-md text-sm leading-6 text-[#667168]">
          Check that Smart Fridge AI is running and try again. Your inventory has not been changed.
        </p>
        <button
          type="button"
          onClick={() => {
            setLoading(true);
            void loadData();
          }}
          className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-[#315c43] px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#254a35] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#315c43]"
        >
          <RefreshCw className="h-4 w-4" />
          Try again
        </button>
      </section>
    );
  }

  const stats = data.stats;
  const expiringItems = data.expiring_soon || [];
  const recentItems = data.recently_added || [];
  const needsAttention = stats.expiring_soon_items + stats.expired_items;
  const latestSensorReading = data.temperature_history_24h?.at(-1);
  const humidityReadings = [
    latestSensorReading?.top_hum,
    latestSensorReading?.middle_hum,
    latestSensorReading?.bottom_hum,
    latestSensorReading?.veg_hum,
  ].filter((value): value is number => typeof value === 'number' && Number.isFinite(value));
  const averageHumidity = humidityReadings.length
    ? Math.round(humidityReadings.reduce((sum, value) => sum + value, 0) / humidityReadings.length)
    : undefined;

  return (
    <div className="kitchen-page space-y-7 sm:space-y-8">
      <header className="flex flex-col gap-5 border-b border-[#dedfd4] pb-6 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p className="mb-2 inline-flex items-center gap-2 text-sm font-medium text-[#68746a]">
            <CalendarDays className="h-4 w-4" />
            {dateFormatter.format(new Date())}
          </p>
          <h1 className="kitchen-heading text-4xl sm:text-5xl">
            {getGreeting()}{firstName ? `, ${firstName}` : ''}.
          </h1>
          <p className="mt-3 max-w-2xl text-base leading-7 text-[#5b665e]">
            Keep track of what you have, use food in time, and make everyday meals easier.
          </p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
          <Link
            to="/webcam"
            className="inline-flex min-h-12 items-center justify-center gap-2.5 rounded-xl bg-[#315c43] px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#254a35] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#315c43]"
          >
            <Camera className="h-5 w-5" />
            Scan food
          </Link>
          <Link
            to="/add-food"
            className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl border border-[#b9c5b8] bg-[#fffefa] px-5 py-3 text-sm font-semibold text-[#294a36] transition-colors hover:bg-[#edf2e8] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#315c43]"
          >
            <Plus className="h-5 w-5" />
            Add manually
          </Link>
          <Link
            to="/foods"
            className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl border border-[#d8ddd3] px-4 py-3 text-sm font-semibold text-[#34443a] transition-colors hover:bg-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#315c43]"
          >
            View inventory
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </header>

      {loadError && (
        <div className="flex items-start gap-3 rounded-xl border border-[#ead6aa] bg-[#fff7df] px-4 py-3 text-sm text-[#75531c]" role="status">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
          <div className="flex-1">
            <p className="font-semibold">Some information may be out of date.</p>
            <p className="mt-0.5">We couldn’t refresh the latest kitchen data.</p>
          </div>
          <button type="button" onClick={() => void loadData()} className="shrink-0 font-semibold underline underline-offset-2">
            Retry
          </button>
        </div>
      )}

      <section aria-label="Inventory overview" className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <button type="button" onClick={() => navigate('/foods')} className="kitchen-panel group p-4 text-left transition-colors hover:bg-white sm:p-5">
          <span className="flex items-center justify-between gap-2 text-sm font-medium text-[#647066]">Food items <Package className="h-5 w-5 text-[#4a6250]" /></span>
          <span className="mt-3 block text-3xl font-semibold tracking-tight text-[#20352a]">{stats.total_items}</span>
          <span className="mt-1 block text-xs text-[#69756b]">In your inventory</span>
        </button>
        <button type="button" onClick={() => navigate('/foods?status=Fresh')} className="kitchen-panel group p-4 text-left transition-colors hover:bg-white sm:p-5">
          <span className="flex items-center justify-between gap-2 text-sm font-medium text-[#647066]">Fresh <Leaf className="h-5 w-5 text-[#4b7a4c]" /></span>
          <span className="mt-3 block text-3xl font-semibold tracking-tight text-[#2d6840]">{stats.fresh_items}</span>
          <span className="mt-1 block text-xs text-[#69756b]">Marked as fresh</span>
        </button>
        <button type="button" onClick={() => navigate('/foods?status=Expiring')} className="kitchen-panel group p-4 text-left transition-colors hover:bg-white sm:p-5">
          <span className="flex items-center justify-between gap-2 text-sm font-medium text-[#647066]">Use soon <Clock3 className="h-5 w-5 text-[#99651b]" /></span>
          <span className="mt-3 block text-3xl font-semibold tracking-tight text-[#99651b]">{stats.expiring_soon_items}</span>
          <span className="mt-1 block text-xs text-[#69756b]">Getting close to date</span>
        </button>
        <button type="button" onClick={() => navigate('/foods?status=Expired')} className="kitchen-panel group p-4 text-left transition-colors hover:bg-white sm:p-5">
          <span className="flex items-center justify-between gap-2 text-sm font-medium text-[#647066]">Past date <XCircle className="h-5 w-5 text-[#b83d27]" /></span>
          <span className="mt-3 block text-3xl font-semibold tracking-tight text-[#b83d27]">{stats.expired_items}</span>
          <span className="mt-1 block text-xs text-[#69756b]">Check these items</span>
        </button>
      </section>

      <section className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1.45fr)_minmax(300px,0.85fr)]">
        <div className="kitchen-panel overflow-hidden">
          <div className="flex flex-col gap-3 border-b border-[#e6e6dc] bg-[#eef1e8] px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
            <div>
              <h2 className="kitchen-heading text-2xl">Use soon</h2>
              <p className="mt-1 text-sm text-[#5b685f]">A quick look at food that needs your attention.</p>
            </div>
            <Link to="/foods?status=Expiring" className="inline-flex min-h-10 items-center gap-1 self-start text-sm font-semibold text-[#315c43] hover:underline sm:self-auto">
              View inventory <ChevronRight className="h-4 w-4" />
            </Link>
          </div>

          {expiringItems.length > 0 ? (
            <div className="divide-y divide-[#ecece3] px-4 sm:px-6">
              {expiringItems.slice(0, 5).map((food) => {
                const daysLeft = getDaysLeft(food);
                const urgent = daysLeft !== null && daysLeft <= 0;
                const soon = daysLeft !== null && daysLeft <= 3;
                return (
                  <div key={food.id} className="flex items-center gap-3 py-4 sm:gap-4">
                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-[#e5e5d9] bg-[#faf9f2] text-2xl" aria-hidden="true">
                      {getFoodEmoji(food.name, food.category)}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-semibold text-[#26372d]">{food.name}</p>
                      <p className="mt-1 text-sm text-[#69736b]">
                        {[food.zone_name, food.quantity !== undefined ? `${food.quantity} ${food.unit || ''}`.trim() : ''].filter(Boolean).join(' · ') || 'Storage location not set'}
                      </p>
                    </div>
                    <span className={`shrink-0 rounded-full px-3 py-1.5 text-xs font-semibold ${urgent ? 'bg-[#fbe4dc] text-[#a9321c]' : soon ? 'bg-[#fff0cf] text-[#805414]' : 'bg-[#e5efdf] text-[#315b39]'}`}>
                      {getExpiryLabel(daysLeft)}
                    </span>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="flex flex-col items-center px-6 py-10 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[#e5efdf] text-[#356247]"><CheckCircle2 className="h-6 w-6" /></div>
              <h3 className="mt-3 font-semibold text-[#2b4332]">Nothing needs attention here</h3>
              <p className="mt-1 max-w-sm text-sm leading-6 text-[#68746a]">There are no items in the current “use soon” list. Check your inventory for the full picture.</p>
              <Link to="/foods" className="mt-4 text-sm font-semibold text-[#315c43] hover:underline">Open inventory</Link>
            </div>
          )}
        </div>

        <aside className="space-y-5">
          <div className={`kitchen-panel p-5 sm:p-6 ${needsAttention > 0 ? 'border-[#eed7c9]' : 'border-[#dbe5d6]'}`}>
            <div className="flex items-start gap-3">
              <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${needsAttention > 0 ? 'bg-[#fbe4dc] text-[#b83d27]' : 'bg-[#e5efdf] text-[#356247]'}`}>
                {needsAttention > 0 ? <AlertTriangle className="h-5 w-5" /> : <CheckCircle2 className="h-5 w-5" />}
              </div>
              <div className="min-w-0">
                <h2 className="kitchen-heading text-2xl">{needsAttention > 0 ? 'A little attention goes a long way' : 'Your kitchen is looking good'}</h2>
                <p className="mt-2 text-sm leading-6 text-[#5b685f]">
                  {stats.expired_items > 0
                    ? `${stats.expired_items} item${stats.expired_items === 1 ? '' : 's'} marked past date. Check them before deciding whether to use or discard them.`
                    : stats.expiring_soon_items > 0
                    ? `${stats.expiring_soon_items} item${stats.expiring_soon_items === 1 ? '' : 's'} getting close to their date. Plan to use them soon.`
                    : 'No items are currently marked as expiring soon or past date.'}
                </p>
                {needsAttention > 0 && (
                  <Link to="/foods?status=Expiring" className="mt-4 inline-flex min-h-10 items-center gap-2 rounded-lg border border-[#d8c2b4] bg-white px-3.5 py-2 text-sm font-semibold text-[#7b382a] hover:bg-[#fff7f2]">
                    Review items <ArrowRight className="h-4 w-4" />
                  </Link>
                )}
              </div>
            </div>
          </div>

          {data.insights?.length > 0 && (
            <div className="kitchen-panel p-5 sm:p-6">
              <div className="flex items-center gap-2"><Sparkles className="h-5 w-5 text-[#54744e]" /><h2 className="kitchen-heading text-2xl">Kitchen notes</h2></div>
              <div className="mt-4 space-y-3">
                {data.insights.slice(0, 3).map((insight, index) => (
                  <p key={index} className="flex items-start gap-2.5 text-sm leading-6 text-[#536057]">
                    <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[#71936a]" />
                    <span>{insight.replace(/^[^\p{L}\p{N}]+/u, '').trim()}</span>
                  </p>
                ))}
              </div>
            </div>
          )}
        </aside>
      </section>

      {recentItems.length > 0 && (
        <section className="kitchen-panel overflow-hidden">
          <div className="flex items-center justify-between gap-3 border-b border-[#e6e6dc] px-5 py-4 sm:px-6">
            <div><h2 className="kitchen-heading text-2xl">Recently added</h2><p className="mt-1 text-sm text-[#5b685f]">The latest food added to your inventory.</p></div>
            <Link to="/foods" className="inline-flex min-h-10 items-center gap-1 text-sm font-semibold text-[#315c43] hover:underline">View all <ChevronRight className="h-4 w-4" /></Link>
          </div>
          <div className="grid grid-cols-1 divide-y divide-[#ecece3] px-5 sm:grid-cols-2 sm:divide-y-0 sm:divide-x sm:px-6 lg:grid-cols-3">
            {recentItems.slice(0, 6).map((food) => (
              <div key={food.id} className="flex items-center gap-3 py-4 sm:px-4 first:sm:pl-0 last:sm:pr-0">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-[#e5e5d9] bg-[#faf9f2] text-2xl" aria-hidden="true">{getFoodEmoji(food.name, food.category)}</div>
                <div className="min-w-0 flex-1"><p className="truncate font-semibold text-[#26372d]">{food.name}</p><p className="mt-1 truncate text-sm text-[#69736b]">{food.zone_name || 'Storage not set'}</p></div>
                <span className="shrink-0 rounded-full bg-[#e5efdf] px-2.5 py-1 text-xs font-semibold text-[#315b39]">{food.freshness_status}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {data.temperature_history_24h?.length > 0 && (
        <details className="kitchen-panel group overflow-hidden">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-5 py-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[#315c43] sm:px-6">
            <span className="flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#edf2e8] text-[#356247]"><Utensils className="h-5 w-5" /></span>
              <span><span className="block font-semibold text-[#26372d]">Fridge conditions</span><span className="mt-0.5 block text-sm text-[#69736b]">Temperature and available humidity readings from connected sensors</span></span>
            </span>
            <ChevronRight className="h-5 w-5 text-[#617066] transition-transform group-open:rotate-90" />
          </summary>
          <div className="border-t border-[#e6e6dc] p-3 sm:p-5"><SensorCharts temperatureHistory={data.temperature_history_24h} averageHumidity={averageHumidity} /></div>
        </details>
      )}

      {stats.total_items === 0 && (
        <section className="kitchen-panel flex flex-col items-start gap-4 p-6 sm:flex-row sm:items-center sm:justify-between sm:p-8">
          <div><h2 className="kitchen-heading text-3xl">Let’s add your first food item</h2><p className="mt-2 max-w-xl text-sm leading-6 text-[#5b685f]">Scan a grocery with your camera or add it manually. You can review the details before saving.</p></div>
          <div className="flex flex-wrap gap-3">
            <Link to="/webcam" className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-[#315c43] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#254a35]"><Camera className="h-4 w-4" /> Scan food</Link>
            <Link to="/add-food" className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-[#b9c5b8] px-4 py-2.5 text-sm font-semibold text-[#294a36] hover:bg-[#edf2e8]"><Plus className="h-4 w-4" /> Add manually</Link>
          </div>
        </section>
      )}
    </div>
  );
};
