import React, { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowDownUp,
  CalendarDays,
  Check,
  CheckCircle2,
  ChevronRight,
  Clock3,
  Edit2,
  Filter,
  Leaf,
  Package,
  Plus,
  RefreshCw,
  Search,
  Trash2,
  X,
} from 'lucide-react';
import { foodsApi, zonesApi } from '../services/api';
import { FoodItem, Zone } from '../types';
import { useNotification } from '../context/NotificationContext';
import { getFoodEmoji } from '../utils/foodIcons';

type InventoryGroupKey = 'review' | 'today' | 'soon' | 'fresh';

type InventoryGroup = {
  key: InventoryGroupKey;
  title: string;
  description: string;
  className: string;
  icon: React.ComponentType<{ className?: string }>;
  items: FoodItem[];
};

const parseLocalDate = (value?: string): Date | null => {
  if (!value) return null;
  const parts = value.slice(0, 10).split('-').map(Number);
  if (parts.length !== 3 || parts.some((part) => !Number.isFinite(part) || part < 1)) return null;
  const date = new Date(parts[0], parts[1] - 1, parts[2]);
  return Number.isNaN(date.getTime()) ? null : date;
};

const getDaysLeft = (food: FoodItem): number | null => {
  if (typeof food.days_until_expiry === 'number') return food.days_until_expiry;
  const expiry = parseLocalDate(food.expiry_date);
  if (!expiry) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  expiry.setHours(0, 0, 0, 0);
  return Math.round((expiry.getTime() - today.getTime()) / 86400000);
};

const formatExpiryDate = (value?: string): string => {
  const date = parseLocalDate(value);
  return date
    ? date.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })
    : 'Date not set';
};

const formatDaysLeft = (days: number | null): string => {
  if (days === null) return 'Check date';
  if (days < 0) return 'Past date · review';
  if (days === 0) return 'Use today';
  if (days === 1) return 'In 1 day';
  return `In ${days} days`;
};

const getGroupKey = (food: FoodItem): InventoryGroupKey => {
  const days = getDaysLeft(food);
  const status = String(food.freshness_status || '').toLowerCase();
  if (status === 'expired' || status === 'rotten' || (days !== null && days < 0)) return 'review';
  if (days === 0) return 'today';
  if (
    status === 'expiring soon' ||
    status === 'ripe' ||
    status === 'overripe' ||
    (days !== null && days >= 1 && days <= 7)
  ) return 'soon';
  return 'fresh';
};

const getStatusStyles = (status: string): string => {
  const normalized = status.toLowerCase();
  if (normalized === 'expired' || normalized === 'rotten') return 'bg-[#fbe4dc] text-[#a9321c]';
  if (normalized === 'expiring soon' || normalized === 'overripe') return 'bg-[#fff0cf] text-[#805414]';
  if (normalized === 'ripe') return 'bg-[#f7edcf] text-[#785a20]';
  return 'bg-[#e5efdf] text-[#315b39]';
};

const getUrgencyStyles = (food: FoodItem): string => {
  const key = getGroupKey(food);
  if (key === 'review' || key === 'today') return 'bg-[#fbe4dc] text-[#a9321c]';
  if (key === 'soon') return 'bg-[#fff0cf] text-[#805414]';
  return 'bg-[#e5efdf] text-[#315b39]';
};

export const FoodManagement: React.FC = () => {
  const [foods, setFoods] = useState<FoodItem[]>([]);
  const [zones, setZones] = useState<Zone[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [search, setSearch] = useState('');
  const [selectedZone, setSelectedZone] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [editItem, setEditItem] = useState<FoodItem | null>(null);
  const [saving, setSaving] = useState(false);
  const [searchParams] = useSearchParams();
  const queryStatus = searchParams.get('status') ?? '';
  const { showToast } = useNotification();

  useEffect(() => {
    setSelectedStatus(queryStatus);
  }, [queryStatus]);

  useEffect(() => {
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      setLoading(true);
      try {
        const [foodsData, zonesData] = await Promise.all([
          foodsApi.getAll({
            search: search.trim() || undefined,
            zone_id: selectedZone || undefined,
            status: selectedStatus || undefined,
            sort_by: 'expiry_date',
            sort_order: sortOrder,
          }),
          zonesApi.getAll(),
        ]);
        if (cancelled) return;
        setFoods(foodsData);
        setZones(zonesData);
        setLoadError(false);
      } catch (error) {
        console.error('Failed to load foods:', error);
        if (!cancelled) {
          setLoadError(true);
          showToast('error', 'Could not load the food inventory. Check the connection and try again.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, search ? 250 : 0);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [search, selectedZone, selectedStatus, sortOrder]);

  const groups = useMemo<InventoryGroup[]>(() => {
    const definitions: Omit<InventoryGroup, 'items'>[] = [
      {
        key: 'review',
        title: 'Review date',
        description: 'Items past their date or marked as spoiled. Check them before deciding what to do.',
        className: 'bg-[#fbebe5] text-[#a9321c]',
        icon: AlertTriangle,
      },
      {
        key: 'today',
        title: 'Use today',
        description: 'Items with a date today.',
        className: 'bg-[#fff0e8] text-[#a93a22]',
        icon: Clock3,
      },
      {
        key: 'soon',
        title: 'Use this week',
        description: 'Items marked as ripening or with a listed date within a week.',
        className: 'bg-[#fff3d9] text-[#805414]',
        icon: CalendarDays,
      },
      {
        key: 'fresh',
        title: 'Fresh / later',
        description: 'Items not currently flagged as urgent. Keep their dates up to date.',
        className: 'bg-[#e8f0e3] text-[#315b39]',
        icon: Leaf,
      },
    ];

    return definitions.map((definition) => ({
      ...definition,
      items: foods.filter((food) => getGroupKey(food) === definition.key),
    }));
  }, [foods]);

  const needsReviewCount = groups.find((group) => group.key === 'review')?.items.length ?? 0;
  const useTodayCount = groups.find((group) => group.key === 'today')?.items.length ?? 0;
  const useSoonCount = groups.find((group) => group.key === 'soon')?.items.length ?? 0;
  const hasFilters = Boolean(search || selectedZone || selectedStatus);

  const clearFilters = () => {
    setSearch('');
    setSelectedZone('');
    setSelectedStatus('');
  };

  const handleMarkUsed = async (id: number, name: string) => {
    try {
      await foodsApi.markUsed(id);
      showToast('success', `${name} marked as consumed.`, 'Inventory updated');
      const [foodsData, zonesData] = await Promise.all([
        foodsApi.getAll({
          search: search.trim() || undefined,
          zone_id: selectedZone || undefined,
          status: selectedStatus || undefined,
          sort_by: 'expiry_date',
          sort_order: sortOrder,
        }),
        zonesApi.getAll(),
      ]);
      setFoods(foodsData);
      setZones(zonesData);
    } catch (error) {
      console.error('Failed to mark food as used:', error);
      showToast('error', 'Could not update this item. Please try again.');
    }
  };

  const handleDelete = async (id: number, name: string) => {
    if (!window.confirm(`Remove ${name} from your inventory?`)) return;
    try {
      await foodsApi.delete(id);
      showToast('info', `${name} removed from inventory.`);
      const foodsData = await foodsApi.getAll({
        search: search.trim() || undefined,
        zone_id: selectedZone || undefined,
        status: selectedStatus || undefined,
        sort_by: 'expiry_date',
        sort_order: sortOrder,
      });
      setFoods(foodsData);
    } catch (error) {
      console.error('Failed to delete food:', error);
      showToast('error', 'Could not remove this item. Please try again.');
    }
  };

  const handleUpdateSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!editItem) return;

    setSaving(true);
    try {
      await foodsApi.update(editItem.id, {
        name: editItem.name.trim(),
        quantity: editItem.quantity,
        unit: editItem.unit.trim(),
        zone_id: editItem.zone_id,
        freshness_status: editItem.freshness_status,
        expiry_date: editItem.expiry_date,
      });
      showToast('success', `${editItem.name} updated successfully.`);
      setEditItem(null);
      const foodsData = await foodsApi.getAll({
        search: search.trim() || undefined,
        zone_id: selectedZone || undefined,
        status: selectedStatus || undefined,
        sort_by: 'expiry_date',
        sort_order: sortOrder,
      });
      setFoods(foodsData);
    } catch (error) {
      console.error('Failed to update food:', error);
      showToast('error', 'Could not save these changes. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="kitchen-page space-y-6 sm:space-y-7">
      <header className="flex flex-col gap-4 border-b border-[#dedfd4] pb-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="mb-2 flex items-center gap-2 text-sm font-medium text-[#68746a]">
            <Package className="h-4 w-4" /> Your kitchen at a glance
          </p>
          <h1 className="kitchen-heading text-4xl sm:text-5xl">Your food inventory</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[#5b665e] sm:text-base">
            Find what you have, check dates, and keep the food you use most within easy reach.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Link
            to="/webcam"
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-[#315c43] px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#254a35]"
          >
            <Package className="h-4 w-4" /> Scan food
          </Link>
          <Link
            to="/add-food"
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-[#b9c5b8] bg-[#fffefa] px-4 py-2.5 text-sm font-semibold text-[#294a36] transition-colors hover:bg-[#edf2e8]"
          >
            <Plus className="h-4 w-4" /> Add manually
          </Link>
        </div>
      </header>

      {needsReviewCount + useTodayCount > 0 && (
        <div className="flex items-start gap-3 rounded-xl border border-[#f0d6c9] bg-[#fff3ed] px-4 py-3.5 sm:px-5" role="status">
          <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[#fbe0d5] text-[#ae3820]">
            <AlertTriangle className="h-5 w-5" />
          </span>
          <div className="min-w-0 flex-1">
            <p className="font-semibold text-[#8f2c1b]">
              {needsReviewCount + useTodayCount} {needsReviewCount + useTodayCount === 1 ? 'item needs' : 'items need'} attention
            </p>
            <p className="mt-1 text-sm leading-5 text-[#7a4c40]">
              {needsReviewCount > 0 && `${needsReviewCount} marked past date or spoiled`}
              {needsReviewCount > 0 && useTodayCount > 0 && ' · '}
              {useTodayCount > 0 && `${useTodayCount} listed for today`}. Check the item details and packaging.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setSelectedStatus('Expired')}
            className="hidden shrink-0 items-center gap-1 self-center text-sm font-semibold text-[#8f2c1b] hover:underline sm:inline-flex"
          >
            Review <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      )}

      <section className="grid grid-cols-2 gap-3 sm:grid-cols-4" aria-label="Inventory summary">
        <div className="kitchen-panel p-4 sm:p-5">
          <p className="flex items-center justify-between gap-2 text-sm font-medium text-[#647066]">All items <Package className="h-4 w-4" /></p>
          <p className="mt-2 text-3xl font-semibold tracking-tight text-[#20352a]">{foods.length}</p>
          <p className="mt-1 text-xs text-[#69756b]">Matching your filters</p>
        </div>
        <div className="kitchen-panel p-4 sm:p-5">
          <p className="flex items-center justify-between gap-2 text-sm font-medium text-[#647066]">Review <AlertTriangle className="h-4 w-4 text-[#b83d27]" /></p>
          <p className="mt-2 text-3xl font-semibold tracking-tight text-[#b83d27]">{needsReviewCount}</p>
          <p className="mt-1 text-xs text-[#69756b]">Past date / marked spoiled</p>
        </div>
        <div className="kitchen-panel p-4 sm:p-5">
          <p className="flex items-center justify-between gap-2 text-sm font-medium text-[#647066]">Use today <Clock3 className="h-4 w-4 text-[#99651b]" /></p>
          <p className="mt-2 text-3xl font-semibold tracking-tight text-[#99651b]">{useTodayCount}</p>
          <p className="mt-1 text-xs text-[#69756b]">Listed date is today</p>
        </div>
        <div className="kitchen-panel p-4 sm:p-5">
          <p className="flex items-center justify-between gap-2 text-sm font-medium text-[#647066]">Use this week <CalendarDays className="h-4 w-4 text-[#805414]" /></p>
          <p className="mt-2 text-3xl font-semibold tracking-tight text-[#805414]">{useSoonCount}</p>
          <p className="mt-1 text-xs text-[#69756b]">Ripe / upcoming</p>
        </div>
      </section>

      <section className="kitchen-panel p-4 sm:p-5" aria-label="Search and filter inventory">
        <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-[#394b3e]">
          <Filter className="h-4 w-4" /> Find an item
        </div>
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-[minmax(0,1fr)_210px_190px_auto]">
          <label className="relative block">
            <span className="sr-only">Search food inventory</span>
            <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-[#788178]" />
            <input
              type="search"
              placeholder="Search food, brand or category…"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              className="min-h-11 w-full rounded-xl border border-[#d8ddd3] bg-[#fffefa] py-2.5 pl-10 pr-3 text-sm text-[#26352c] placeholder:text-[#8a928a]"
            />
          </label>
          <label>
            <span className="sr-only">Filter by storage location</span>
            <select
              value={selectedZone}
              onChange={(event) => setSelectedZone(event.target.value)}
              className="min-h-11 w-full rounded-xl border border-[#d8ddd3] bg-[#fffefa] px-3 text-sm text-[#394b3e]"
            >
              <option value="">All storage locations</option>
              {zones.map((zone) => <option key={zone.id} value={zone.id}>{zone.name}</option>)}
            </select>
          </label>
          <label>
            <span className="sr-only">Filter by status</span>
            <select
              value={selectedStatus}
              onChange={(event) => setSelectedStatus(event.target.value)}
              className="min-h-11 w-full rounded-xl border border-[#d8ddd3] bg-[#fffefa] px-3 text-sm text-[#394b3e]"
            >
              <option value="">All freshness states</option>
              <option value="Fresh">Fresh</option>
              <option value="Expiring">Expiring soon</option>
              <option value="Expired">Expired / spoiled</option>
            </select>
          </label>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setSortOrder((current) => current === 'asc' ? 'desc' : 'asc')}
              className="inline-flex min-h-11 flex-1 items-center justify-center gap-2 rounded-xl border border-[#d8ddd3] bg-[#fffefa] px-3 text-sm font-medium text-[#394b3e] hover:bg-[#edf2e8] lg:flex-none"
              title={`Sort by expiry date ${sortOrder === 'asc' ? 'earliest first' : 'latest first'}`}
              aria-label={`Change expiry date sort order. Current: ${sortOrder === 'asc' ? 'earliest first' : 'latest first'}`}
            >
              <ArrowDownUp className="h-4 w-4" /> Sort
            </button>
            {hasFilters && (
              <button
                type="button"
                onClick={clearFilters}
                className="inline-flex min-h-11 items-center justify-center gap-1 rounded-xl px-3 text-sm font-medium text-[#536057] hover:bg-[#f0f0e8]"
              >
                <X className="h-4 w-4" /> Clear
              </button>
            )}
          </div>
        </div>
        <div className="mt-3 flex items-center justify-between gap-3 text-xs text-[#738076]">
          <span>{loading ? 'Updating inventory…' : `${foods.length} ${foods.length === 1 ? 'item' : 'items'} shown`}</span>
          {loadError && <button type="button" onClick={() => window.location.reload()} className="font-semibold text-[#a9321c] underline underline-offset-2">Retry</button>}
        </div>
      </section>

      {loadError && foods.length === 0 && !loading ? (
        <section className="kitchen-panel flex flex-col items-center px-6 py-12 text-center">
          <AlertTriangle className="h-8 w-8 text-[#b83d27]" />
          <h2 className="kitchen-heading mt-3 text-2xl">We couldn't load your inventory</h2>
          <p className="mt-2 max-w-md text-sm leading-6 text-[#68746a]">Check that the backend is running, then try refreshing the page.</p>
          <button type="button" onClick={() => window.location.reload()} className="mt-4 inline-flex min-h-11 items-center gap-2 rounded-xl bg-[#315c43] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#254a35]"><RefreshCw className="h-4 w-4" /> Refresh page</button>
        </section>
      ) : loading && foods.length === 0 ? (
        <section className="kitchen-panel flex flex-col items-center px-6 py-12 text-center" role="status">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-[#315c43] border-t-transparent" />
          <p className="mt-3 text-sm text-[#68746a]">Loading your food inventory…</p>
        </section>
      ) : foods.length === 0 ? (
        <section className="kitchen-panel flex flex-col items-center px-6 py-12 text-center">
          <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#edf2e8] text-[#315c43]"><Package className="h-7 w-7" /></span>
          <h2 className="kitchen-heading mt-4 text-2xl">{hasFilters ? 'No matching food found' : 'Your inventory is ready for its first item'}</h2>
          <p className="mt-2 max-w-md text-sm leading-6 text-[#68746a]">
            {hasFilters ? 'Try a different search or clear the filters to see more items.' : 'Add a grocery manually or scan it with your camera. You can check the details before saving.'}
          </p>
          <div className="mt-4 flex flex-wrap justify-center gap-3">
            {hasFilters && <button type="button" onClick={clearFilters} className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-[#b9c5b8] px-4 py-2.5 text-sm font-semibold text-[#294a36] hover:bg-[#edf2e8]">Clear filters</button>}
            {!hasFilters && <Link to="/add-food" className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-[#315c43] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#254a35]"><Plus className="h-4 w-4" /> Add manually</Link>}
          </div>
        </section>
      ) : (
        <div className="space-y-5">
          {groups.filter((group) => group.items.length > 0).map((group) => {
            const GroupIcon = group.icon;
            return (
              <section key={group.key} className="kitchen-panel overflow-hidden">
                <div className="flex flex-col gap-3 border-b border-[#e6e6dc] bg-[#f6f6ef] px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-5">
                  <div className="flex items-start gap-3">
                    <span className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${group.className}`}><GroupIcon className="h-5 w-5" /></span>
                    <div>
                      <h2 className="kitchen-heading text-2xl">{group.title}</h2>
                      <p className="mt-1 text-sm leading-5 text-[#677269]">{group.description}</p>
                    </div>
                  </div>
                  <span className="self-start rounded-full border border-[#e0e2d8] bg-[#fffefa] px-3 py-1 text-xs font-semibold text-[#566258] sm:self-center">{group.items.length} {group.items.length === 1 ? 'item' : 'items'}</span>
                </div>

                <div className="divide-y divide-[#ecece3]">
                  {group.items.map((food) => {
                    const daysLeft = getDaysLeft(food);
                    return (
                      <article key={food.id} className="grid grid-cols-1 gap-3 px-4 py-4 transition-colors hover:bg-[#fcfbf6] sm:px-5 lg:grid-cols-[minmax(0,1.5fr)_minmax(100px,0.65fr)_minmax(150px,0.95fr)_minmax(120px,0.7fr)_auto] lg:items-center lg:gap-4">
                        <div className="flex min-w-0 items-center gap-3">
                          <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl border border-[#e5e5d9] bg-[#faf9f2] text-2xl" aria-hidden="true">{getFoodEmoji(food.name, food.category)}</span>
                          <div className="min-w-0">
                            <h3 className="truncate font-semibold text-[#25372b]">{food.name}</h3>
                            <p className="mt-1 truncate text-sm text-[#69736b]">{food.brand ? `${food.brand} · ` : ''}{food.category}</p>
                            <span className={`mt-2 inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${getStatusStyles(food.freshness_status)}`}>{food.freshness_status}</span>
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:contents">
                          <div className="min-w-0">
                            <p className="text-xs font-medium uppercase tracking-wide text-[#879087]">Quantity</p>
                            <p className="mt-1 font-semibold text-[#34443a]">{food.quantity} {food.unit}</p>
                          </div>
                          <div className="min-w-0">
                            <p className="text-xs font-medium uppercase tracking-wide text-[#879087]">Stored in</p>
                            <p className="mt-1 truncate text-sm font-medium text-[#49564d]">{food.zone_name || 'Location not set'}</p>
                          </div>
                          <div className="col-span-2 min-w-0 sm:col-span-1">
                            <p className="text-xs font-medium uppercase tracking-wide text-[#879087]">Listed date</p>
                            <p className="mt-1 text-sm font-medium text-[#34443a]">{formatExpiryDate(food.expiry_date)}</p>
                            <span className={`mt-1 inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${getUrgencyStyles(food)}`}>{formatDaysLeft(daysLeft)}</span>
                          </div>
                        </div>

                        <div className="flex flex-wrap items-center gap-2 border-t border-[#eeeee6] pt-3 lg:justify-end lg:border-0 lg:pt-0">
                          <button type="button" onClick={() => handleMarkUsed(food.id, food.name)} className="inline-flex min-h-10 flex-1 items-center justify-center gap-2 rounded-lg border border-[#cbd9c7] bg-white px-3 py-2 text-sm font-semibold text-[#315c43] hover:bg-[#edf2e8] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#315c43] sm:flex-none" aria-label={`Mark ${food.name} as used`} title="Mark as used">
                            <Check className="h-4 w-4" /> <span className="sm:hidden xl:inline">Used</span>
                          </button>
                          <button type="button" onClick={() => setEditItem(food)} className="inline-flex min-h-10 flex-1 items-center justify-center gap-2 rounded-lg border border-[#d8ddd3] bg-white px-3 py-2 text-sm font-semibold text-[#49564d] hover:bg-[#f2f2eb] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#315c43] sm:flex-none" aria-label={`Edit ${food.name}`} title="Edit item">
                            <Edit2 className="h-4 w-4" /> <span className="sm:hidden xl:inline">Edit</span>
                          </button>
                          <button type="button" onClick={() => handleDelete(food.id, food.name)} className="inline-flex min-h-10 flex-1 items-center justify-center gap-2 rounded-lg border border-[#ead0c8] bg-white px-3 py-2 text-sm font-semibold text-[#a9321c] hover:bg-[#fff3ed] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#a9321c] sm:flex-none" aria-label={`Remove ${food.name}`} title="Remove from inventory">
                            <Trash2 className="h-4 w-4" /> <span className="sm:hidden xl:inline">Remove</span>
                          </button>
                        </div>
                      </article>
                    );
                  })}
                </div>
              </section>
            );
          })}
        </div>
      )}

      <p className="px-1 text-xs leading-5 text-[#778178]">
        Dates are reminders, not a food-safety test. Check packaging and the item's condition before deciding whether to eat or discard it.
      </p>

      {editItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-[#1e2c22]/45 p-4" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !saving) setEditItem(null); }}>
          <section role="dialog" aria-modal="true" aria-labelledby="edit-food-title" className="my-auto w-full max-w-lg rounded-2xl border border-[#e0e2d8] bg-[#fffefa] p-5 shadow-2xl sm:p-6">
            <div className="mb-5 flex items-start justify-between gap-3">
              <div>
                <h2 id="edit-food-title" className="kitchen-heading text-2xl">Edit food item</h2>
                <p className="mt-1 text-sm text-[#69736b]">Keep the details up to date.</p>
              </div>
              <button type="button" disabled={saving} onClick={() => setEditItem(null)} className="rounded-lg p-2 text-[#69736b] hover:bg-[#f0f0e8] disabled:opacity-50" aria-label="Close edit form"><X className="h-5 w-5" /></button>
            </div>
            <form onSubmit={handleUpdateSubmit} className="space-y-4">
              <label className="block">
                <span className="mb-1.5 block text-sm font-semibold text-[#49564d]">Food name</span>
                <input type="text" value={editItem.name} onChange={(event) => setEditItem({ ...editItem, name: event.target.value })} className="min-h-11 w-full rounded-xl border border-[#d8ddd3] bg-white px-3 text-sm" required />
              </label>
              <div className="grid grid-cols-2 gap-3">
                <label className="block">
                  <span className="mb-1.5 block text-sm font-semibold text-[#49564d]">Quantity</span>
                  <input type="number" min="0.1" step="0.1" value={editItem.quantity} onChange={(event) => setEditItem({ ...editItem, quantity: Number(event.target.value) })} className="min-h-11 w-full rounded-xl border border-[#d8ddd3] bg-white px-3 text-sm" required />
                </label>
                <label className="block">
                  <span className="mb-1.5 block text-sm font-semibold text-[#49564d]">Unit</span>
                  <input type="text" value={editItem.unit} onChange={(event) => setEditItem({ ...editItem, unit: event.target.value })} className="min-h-11 w-full rounded-xl border border-[#d8ddd3] bg-white px-3 text-sm" required />
                </label>
              </div>
              <label className="block">
                <span className="mb-1.5 block text-sm font-semibold text-[#49564d]">Storage location</span>
                <select value={editItem.zone_id} onChange={(event) => setEditItem({ ...editItem, zone_id: Number(event.target.value) })} className="min-h-11 w-full rounded-xl border border-[#d8ddd3] bg-white px-3 text-sm">
                  {zones.map((zone) => <option key={zone.id} value={zone.id}>{zone.name}</option>)}
                </select>
              </label>
              <label className="block">
                <span className="mb-1.5 block text-sm font-semibold text-[#49564d]">Best-before / expiry date</span>
                <input type="date" value={editItem.expiry_date?.slice(0, 10) || ''} onChange={(event) => setEditItem({ ...editItem, expiry_date: event.target.value })} className="min-h-11 w-full rounded-xl border border-[#d8ddd3] bg-white px-3 text-sm" required />
              </label>
              <label className="block">
                <span className="mb-1.5 block text-sm font-semibold text-[#49564d]">Freshness status</span>
                <select value={editItem.freshness_status} onChange={(event) => setEditItem({ ...editItem, freshness_status: event.target.value as FoodItem['freshness_status'] })} className="min-h-11 w-full rounded-xl border border-[#d8ddd3] bg-white px-3 text-sm">
                  <option value="Fresh">Fresh</option>
                  <option value="Ripe">Ripe</option>
                  <option value="Overripe">Overripe</option>
                  <option value="Rotten">Rotten</option>
                  <option value="Expiring Soon">Expiring soon</option>
                  <option value="Expired">Expired</option>
                </select>
              </label>
              <div className="flex flex-col-reverse gap-2 border-t border-[#e6e6dc] pt-4 sm:flex-row sm:justify-end">
                <button type="button" disabled={saving} onClick={() => setEditItem(null)} className="min-h-11 rounded-xl border border-[#d8ddd3] px-4 py-2.5 text-sm font-semibold text-[#49564d] hover:bg-[#f2f2eb] disabled:opacity-50">Cancel</button>
                <button type="submit" disabled={saving} className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-[#315c43] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#254a35] disabled:cursor-wait disabled:opacity-60">
                  {saving ? <><RefreshCw className="h-4 w-4 animate-spin" /> Saving…</> : <><CheckCircle2 className="h-4 w-4" /> Save changes</>}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
    </div>
  );
};
