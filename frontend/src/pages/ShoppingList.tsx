import React, { useEffect, useMemo, useState } from 'react';
import {
  Check,
  CheckCheck,
  ClipboardList,
  Plus,
  ShoppingCart,
  Trash2,
  X,
} from 'lucide-react';
import {
  readShoppingList,
  shoppingListChangeEvent,
  ShoppingListItem,
  writeShoppingList,
} from '../utils/shoppingList';

type ListFilter = 'all' | 'needed' | 'bought';

const categories = ['Produce', 'Dairy', 'Protein', 'Pantry', 'Frozen', 'Household', 'Groceries'];

export const ShoppingList: React.FC = () => {
  const [items, setItems] = useState<ShoppingListItem[]>(() => readShoppingList());
  const [name, setName] = useState('');
  const [quantity, setQuantity] = useState('1');
  const [category, setCategory] = useState('Groceries');
  const [filter, setFilter] = useState<ListFilter>('needed');

  useEffect(() => {
    const refresh = () => setItems(readShoppingList());
    window.addEventListener(shoppingListChangeEvent, refresh);
    window.addEventListener('storage', refresh);
    return () => {
      window.removeEventListener(shoppingListChangeEvent, refresh);
      window.removeEventListener('storage', refresh);
    };
  }, []);

  const neededCount = items.filter((item) => !item.checked).length;
  const boughtCount = items.length - neededCount;
  const visibleItems = useMemo(() => {
    if (filter === 'needed') return items.filter((item) => !item.checked);
    if (filter === 'bought') return items.filter((item) => item.checked);
    return items;
  }, [filter, items]);

  const updateItems = (next: ShoppingListItem[]) => {
    setItems(next);
    writeShoppingList(next);
  };

  const handleAdd = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedName = name.trim();
    if (!trimmedName) return;

    const existingIndex = items.findIndex(
      (item) => item.name.toLocaleLowerCase() === trimmedName.toLocaleLowerCase()
    );

    if (existingIndex >= 0) {
      const next = [...items];
      next[existingIndex] = {
        ...next[existingIndex],
        checked: false,
        quantity: quantity.trim() || next[existingIndex].quantity || '1',
        category,
      };
      updateItems(next);
    } else {
      const next = [
        ...items,
        {
          id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
          name: trimmedName,
          category,
          quantity: quantity.trim() || '1',
          checked: false,
          createdAt: new Date().toISOString(),
        },
      ];
      updateItems(next);
    }

    setName('');
    setQuantity('1');
  };

  const toggleItem = (id: string) => {
    updateItems(items.map((item) => item.id === id ? { ...item, checked: !item.checked } : item));
  };

  const removeItem = (id: string) => {
    updateItems(items.filter((item) => item.id !== id));
  };

  const clearBought = () => {
    updateItems(items.filter((item) => !item.checked));
    setFilter('needed');
  };

  return (
    <div className="kitchen-page space-y-7 sm:space-y-8">
      <header className="flex flex-col gap-4 border-b border-[#dedfd4] pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="mb-2 inline-flex items-center gap-2 text-sm font-medium text-[#68746a]">
            <ShoppingCart className="h-4 w-4" />
            Household essentials
          </p>
          <h1 className="kitchen-heading text-4xl sm:text-5xl">Shopping list</h1>
          <p className="mt-3 max-w-2xl text-base leading-7 text-[#5b665e]">
            Keep your next grocery trip organised. Tick things off as you shop.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-sm">
          <span className="rounded-full bg-[#e5efdf] px-3 py-1.5 font-semibold text-[#315b39]">{neededCount} to buy</span>
          <span className="rounded-full bg-white px-3 py-1.5 font-semibold text-[#68746a] ring-1 ring-[#e1e2d8]">{boughtCount} checked</span>
        </div>
      </header>

      <section className="kitchen-panel p-5 sm:p-6">
        <h2 className="mb-4 flex items-center gap-2 font-semibold text-[#26372d]">
          <Plus className="h-5 w-5 text-[#315c43]" /> Add an item
        </h2>
        <form onSubmit={handleAdd} className="grid grid-cols-1 gap-3 sm:grid-cols-[minmax(0,1fr)_110px_170px_auto]">
          <label className="sr-only" htmlFor="shopping-item-name">Item name</label>
          <input
            id="shopping-item-name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="e.g. eggs, whole-grain bread"
            className="min-h-12 min-w-0 rounded-xl border border-[#d8ddd3] bg-white px-4 py-3 text-sm text-[#26372d] placeholder:text-[#899187] focus:border-[#315c43] focus:outline-none"
            maxLength={100}
            required
          />
          <label className="sr-only" htmlFor="shopping-item-quantity">Quantity</label>
          <input
            id="shopping-item-quantity"
            value={quantity}
            onChange={(event) => setQuantity(event.target.value)}
            placeholder="Quantity"
            className="min-h-12 min-w-0 rounded-xl border border-[#d8ddd3] bg-white px-3 py-3 text-sm text-[#26372d] placeholder:text-[#899187] focus:border-[#315c43] focus:outline-none"
            maxLength={30}
          />
          <label className="sr-only" htmlFor="shopping-item-category">Category</label>
          <select
            id="shopping-item-category"
            value={category}
            onChange={(event) => setCategory(event.target.value)}
            className="min-h-12 min-w-0 rounded-xl border border-[#d8ddd3] bg-white px-3 py-3 text-sm text-[#26372d] focus:border-[#315c43] focus:outline-none"
          >
            {categories.map((option) => <option key={option} value={option}>{option}</option>)}
          </select>
          <button type="submit" className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-[#315c43] px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#254a35] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#315c43]">
            <Plus className="h-4 w-4" /> Add
          </button>
        </form>
        <p className="mt-3 text-xs leading-5 text-[#718074]">
          This list is saved in this browser on this device. It is not yet synced to your account or other devices.
        </p>
      </section>

      <section className="kitchen-panel overflow-hidden">
        <div className="flex flex-col gap-3 border-b border-[#e6e6dc] bg-[#eef1e8] px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white text-[#315c43] ring-1 ring-[#dbe2d5]">
              <ClipboardList className="h-5 w-5" />
            </div>
            <div>
              <h2 className="kitchen-heading text-2xl">Your list</h2>
              <p className="mt-1 text-sm text-[#5b685f]">{neededCount === 0 ? 'Everything is checked off.' : `${neededCount} ${neededCount === 1 ? 'item' : 'items'} left to buy`}</p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {([
              ['needed', 'To buy'],
              ['all', 'All items'],
              ['bought', 'Checked'],
            ] as Array<[ListFilter, string]>).map(([value, label]) => (
              <button
                key={value}
                type="button"
                onClick={() => setFilter(value)}
                aria-pressed={filter === value}
                className={`min-h-9 rounded-lg px-3 py-2 text-xs font-semibold transition-colors ${filter === value ? 'bg-[#315c43] text-white' : 'bg-white text-[#4f5f53] ring-1 ring-[#d8ddd3] hover:bg-[#f7f8f2]'}`}
              >
                {label}
              </button>
            ))}
            {boughtCount > 0 && (
              <button type="button" onClick={clearBought} className="inline-flex min-h-9 items-center gap-1 rounded-lg px-2.5 py-2 text-xs font-semibold text-[#6c756c] hover:bg-white">
                <X className="h-3.5 w-3.5" /> Clear checked
              </button>
            )}
          </div>
        </div>

        {visibleItems.length === 0 ? (
          <div className="flex flex-col items-center px-6 py-12 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#e5efdf] text-[#356247]">
              {filter === 'bought' ? <CheckCheck className="h-7 w-7" /> : <ShoppingCart className="h-7 w-7" />}
            </div>
            <h3 className="kitchen-heading mt-4 text-2xl">
              {filter === 'bought' ? 'Nothing checked off yet' : filter === 'all' ? 'Your list is empty' : 'Nothing to buy right now'}
            </h3>
            <p className="mt-2 max-w-sm text-sm leading-6 text-[#68746a]">
              {filter === 'bought' ? 'Items you mark as bought will appear here.' : 'Add groceries above, or use a recipe idea to add its untracked ingredients.'}
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-[#ecece3]">
            {visibleItems.map((item) => (
              <li key={item.id} className={`flex items-center gap-3 px-4 py-4 sm:px-6 ${item.checked ? 'bg-[#fafaf6]' : 'bg-[#fffefa]'}`}>
                <button
                  type="button"
                  onClick={() => toggleItem(item.id)}
                  aria-label={item.checked ? `Mark ${item.name} as not bought` : `Mark ${item.name} as bought`}
                  aria-pressed={item.checked}
                  className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#315c43] ${item.checked ? 'border-[#4a7954] bg-[#4a7954] text-white' : 'border-[#aab8a7] bg-white text-transparent hover:border-[#315c43]'}`}
                >
                  <Check className="h-4 w-4" />
                </button>
                <div className="min-w-0 flex-1">
                  <p className={`break-words font-semibold ${item.checked ? 'text-[#8a9189] line-through' : 'text-[#26372d]'}`}>{item.name}</p>
                  <p className="mt-1 text-sm text-[#748075]">{item.category}{item.quantity ? ` · ${item.quantity}` : ''}</p>
                </div>
                <button type="button" onClick={() => removeItem(item.id)} aria-label={`Remove ${item.name}`} title="Remove item" className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-[#8b6256] transition-colors hover:bg-[#fbece6] hover:text-[#a8321b] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#315c43]">
                  <Trash2 className="h-4 w-4" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
};

export default ShoppingList;
