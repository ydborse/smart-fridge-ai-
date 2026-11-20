export interface ShoppingListItem {
  id: string;
  name: string;
  category: string;
  quantity: string;
  checked: boolean;
  createdAt: string;
}

const STORAGE_KEY = 'smart-fridge-shopping-list-v1';
const CHANGE_EVENT = 'smart-fridge-shopping-list-changed';

export function readShoppingList(): ShoppingListItem[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((entry): entry is ShoppingListItem =>
      Boolean(entry) &&
      typeof entry.id === 'string' &&
      typeof entry.name === 'string' &&
      typeof entry.category === 'string' &&
      typeof entry.quantity === 'string' &&
      typeof entry.checked === 'boolean' &&
      typeof entry.createdAt === 'string'
    );
  } catch {
    return [];
  }
}

export function writeShoppingList(items: ShoppingListItem[]): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    window.dispatchEvent(new CustomEvent(CHANGE_EVENT));
  } catch (error) {
    console.error('Could not save the shopping list in this browser:', error);
  }
}

export function addShoppingItems(
  names: string[],
  category = 'Groceries'
): ShoppingListItem[] {
  const items = readShoppingList();
  const now = new Date().toISOString();
  const next = [...items];

  names.forEach((rawName) => {
    const name = rawName.trim();
    if (!name) return;

    const existingIndex = next.findIndex(
      (item) => item.name.toLocaleLowerCase() === name.toLocaleLowerCase()
    );

    if (existingIndex >= 0) {
      // If the item was previously checked off, re-open it instead of creating a duplicate.
      if (next[existingIndex].checked) {
        next[existingIndex] = { ...next[existingIndex], checked: false };
      }
      return;
    }

    next.push({
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
      name,
      category,
      quantity: '1',
      checked: false,
      createdAt: now,
    });
  });

  writeShoppingList(next);
  return next;
}

export const shoppingListChangeEvent = CHANGE_EVENT;
