import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Search,
  Filter,
  ArrowUpDown,
  Plus,
  Trash2,
  Check,
  Edit2,
  Package,
  Calendar,
  Layers,
  Sparkles,
  AlertCircle
} from 'lucide-react';
import { foodsApi, zonesApi } from '../services/api';
import { FoodItem, Zone } from '../types';
import { useNotification } from '../context/NotificationContext';
import { getFoodEmoji } from '../utils/foodIcons';

export const FoodManagement: React.FC = () => {
  const [foods, setFoods] = useState<FoodItem[]>([]);
  const [zones, setZones] = useState<Zone[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedZone, setSelectedZone] = useState<string>('');
  const [selectedStatus, setSelectedStatus] = useState<string>('');
  const [sortBy, setSortBy] = useState('expiry_date');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [editItem, setEditItem] = useState<FoodItem | null>(null);

  const { showToast } = useNotification();

  const loadData = async () => {
    try {
      setLoading(true);
      const [foodsData, zonesData] = await Promise.all([
        foodsApi.getAll({
          search: search || undefined,
          zone_id: selectedZone || undefined,
          status: selectedStatus || undefined,
          sort_by: sortBy,
          sort_order: sortOrder
        }),
        zonesApi.getAll()
      ]);
      setFoods(foodsData);
      setZones(zonesData);
    } catch (err) {
      console.error('Failed to load foods:', err);
      showToast('error', 'Could not fetch food inventory');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [search, selectedZone, selectedStatus, sortBy, sortOrder]);

  const handleMarkUsed = async (id: number, name: string) => {
    try {
      await foodsApi.markUsed(id);
      showToast('success', `${name} marked as consumed!`, 'Inventory Updated');
      loadData();
    } catch (err) {
      showToast('error', 'Failed to update item state');
    }
  };

  const handleDelete = async (id: number, name: string) => {
    if (!window.confirm(`Delete ${name} from inventory?`)) return;
    try {
      await foodsApi.delete(id);
      showToast('info', `${name} removed from inventory`);
      loadData();
    } catch (err) {
      showToast('error', 'Failed to delete food item');
    }
  };

  const handleUpdateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editItem) return;

    try {
      await foodsApi.update(editItem.id, {
        name: editItem.name,
        quantity: editItem.quantity,
        unit: editItem.unit,
        zone_id: editItem.zone_id,
        freshness_status: editItem.freshness_status,
        expiry_date: editItem.expiry_date
      });
      showToast('success', `${editItem.name} updated successfully!`);
      setEditItem(null);
      loadData();
    } catch (err) {
      showToast('error', 'Failed to update item');
    }
  };

  const getStatusBadge = (status: string, daysLeft?: number) => {
    if (status === 'Expired' || status === 'Rotten' || (daysLeft !== undefined && daysLeft < 0)) {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-100 text-rose-700">
          Expired
        </span>
      );
    }
    if (status === 'Expiring Soon' || status === 'Ripe' || status === 'Overripe' || (daysLeft !== undefined && daysLeft <= 3)) {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-700">
          Expiring Soon
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-700">
        Fresh
      </span>
    );
  };

  const getItemEmoji = (name: string, category: string) => {
    return getFoodEmoji(name, category);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <Package className="w-6 h-6 text-emerald-600" />
            Food Management
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
            Track freshness, shelf assignments, and manage daily usage
          </p>
        </div>

        <Link
          to="/add-food"
          className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2.5 rounded-xl font-bold text-xs sm:text-sm shadow-sm shadow-emerald-500/20 transition-all self-start sm:self-auto"
        >
          <Plus className="w-4 h-4 stroke-[2.5]" />
          Add Food
        </Link>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-soft flex flex-col md:flex-row items-center gap-3">
        {/* Search */}
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search groceries by name, brand or category..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-xl border border-slate-200 text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
          />
        </div>

        {/* Zone Filter */}
        <div className="flex items-center gap-2 w-full md:w-auto">
          <select
            value={selectedZone}
            onChange={(e) => setSelectedZone(e.target.value)}
            className="w-full md:w-44 px-3 py-2 rounded-xl border border-slate-200 text-xs sm:text-sm bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
          >
            <option value="">All Zones</option>
            {zones.map((z) => (
              <option key={z.id} value={z.id}>
                {z.name}
              </option>
            ))}
          </select>

          {/* Status Filter */}
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="w-full md:w-36 px-3 py-2 rounded-xl border border-slate-200 text-xs sm:text-sm bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
          >
            <option value="">All Status</option>
            <option value="Fresh">Fresh</option>
            <option value="Expiring">Expiring Soon</option>
            <option value="Expired">Expired</option>
          </select>

          {/* Sort toggle */}
          <button
            onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
            className="p-2.5 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-600 transition-colors flex items-center justify-center flex-shrink-0"
            title="Toggle sort direction"
          >
            <ArrowUpDown className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Inventory Table */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-soft overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs sm:text-sm text-slate-600">
            <thead className="bg-slate-50/80 border-b border-slate-100 text-slate-500 text-[11px] font-bold uppercase tracking-wider">
              <tr>
                <th className="px-5 py-3.5">Food Item</th>
                <th className="px-5 py-3.5">Zone</th>
                <th className="px-5 py-3.5">Quantity</th>
                <th className="px-5 py-3.5">Expiry Date</th>
                <th className="px-5 py-3.5">Status</th>
                <th className="px-5 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-slate-400">
                    <div className="w-6 h-6 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                    Loading pantry inventory...
                  </td>
                </tr>
              ) : foods.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-slate-400">
                    No matching food items found in the fridge.
                  </td>
                </tr>
              ) : (
                foods.map((food) => (
                  <tr key={food.id} className="hover:bg-slate-50/70 transition-colors">
                    {/* Item */}
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-xl bg-slate-100 flex items-center justify-center text-base flex-shrink-0">
                          {getItemEmoji(food.name, food.category)}
                        </div>
                        <div>
                          <p className="font-bold text-slate-900">{food.name}</p>
                          <p className="text-[11px] text-slate-400">
                            {food.brand ? `${food.brand} • ` : ''}
                            {food.category}
                          </p>
                        </div>
                      </div>
                    </td>

                    {/* Zone */}
                    <td className="px-5 py-3.5">
                      <span className="font-medium text-slate-800 bg-slate-100 px-2 py-0.5 rounded-md text-xs">
                        {food.zone_name}
                      </span>
                    </td>

                    {/* Quantity */}
                    <td className="px-5 py-3.5 font-semibold text-slate-800">
                      {food.quantity} {food.unit}
                    </td>

                    {/* Expiry */}
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-1.5 text-slate-700 font-medium">
                        <Calendar className="w-3.5 h-3.5 text-slate-400" />
                        <span>{new Date(food.expiry_date).toLocaleDateString()}</span>
                      </div>
                      <span className="text-[10px] text-slate-400 block mt-0.5">
                        {(food.days_until_expiry ?? 0) <= 0
                          ? 'Past expiration'
                          : `${food.days_until_expiry} day(s) remaining`}
                      </span>
                    </td>

                    {/* Status */}
                    <td className="px-5 py-3.5">
                      {getStatusBadge(food.freshness_status, food.days_until_expiry)}
                    </td>

                    {/* Actions */}
                    <td className="px-5 py-3.5 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        {/* Mark Used */}
                        <button
                          onClick={() => handleMarkUsed(food.id, food.name)}
                          className="p-1.5 rounded-lg border border-slate-200 text-emerald-600 hover:bg-emerald-50 transition-colors"
                          title="Mark as Used/Consumed"
                        >
                          <Check className="w-4 h-4 stroke-[2.5]" />
                        </button>

                        {/* Edit */}
                        <button
                          onClick={() => setEditItem(food)}
                          className="p-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 transition-colors"
                          title="Edit Item"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>

                        {/* Delete */}
                        <button
                          onClick={() => handleDelete(food.id, food.name)}
                          className="p-1.5 rounded-lg border border-slate-200 text-rose-500 hover:bg-rose-50 transition-colors"
                          title="Delete from Fridge"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Edit Food Modal */}
      {editItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs">
          <div className="bg-white rounded-2xl p-6 max-w-md w-full shadow-2xl border border-slate-200">
            <h3 className="text-base font-bold text-slate-900 mb-4">Edit Food Item</h3>
            <form onSubmit={handleUpdateSubmit} className="space-y-4">
              <div>
                <label className="text-xs font-bold text-slate-600 mb-1 block">Item Name</label>
                <input
                  type="text"
                  value={editItem.name}
                  onChange={(e) => setEditItem({ ...editItem, name: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs sm:text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold text-slate-600 mb-1 block">Quantity</label>
                  <input
                    type="number"
                    step="0.1"
                    value={editItem.quantity}
                    onChange={(e) => setEditItem({ ...editItem, quantity: parseFloat(e.target.value) || 1 })}
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs sm:text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                    required
                  />
                </div>
                <div>
                  <label className="text-xs font-bold text-slate-600 mb-1 block">Unit</label>
                  <input
                    type="text"
                    value={editItem.unit}
                    onChange={(e) => setEditItem({ ...editItem, unit: e.target.value })}
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs sm:text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-bold text-slate-600 mb-1 block">Storage Zone</label>
                <select
                  value={editItem.zone_id}
                  onChange={(e) => setEditItem({ ...editItem, zone_id: parseInt(e.target.value, 10) })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs sm:text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                >
                  {zones.map((z) => (
                    <option key={z.id} value={z.id}>
                      {z.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs font-bold text-slate-600 mb-1 block">Freshness State</label>
                <select
                  value={editItem.freshness_status}
                  onChange={(e) => setEditItem({ ...editItem, freshness_status: e.target.value as any })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs sm:text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                >
                  <option value="Fresh">Fresh</option>
                  <option value="Ripe">Ripe</option>
                  <option value="Overripe">Overripe</option>
                  <option value="Rotten">Rotten</option>
                  <option value="Expiring Soon">Expiring Soon</option>
                  <option value="Expired">Expired</option>
                </select>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setEditItem(null)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-500 hover:bg-slate-100 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white shadow-xs transition-colors"
                >
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
