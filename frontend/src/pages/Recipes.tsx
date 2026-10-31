import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  Clock3,
  CookingPot,
  Plus,
  RefreshCw,
  ShoppingCart,
  Utensils,
} from 'lucide-react';
import { foodsApi } from '../services/api';
import { FoodItem } from '../types';
import { addShoppingItems } from '../utils/shoppingList';

interface RecipeIngredient {
  name: string;
  matchers: string[];
  category: string;
}

interface RecipeDefinition {
  id: string;
  title: string;
  description: string;
  time: string;
  ingredients: RecipeIngredient[];
  steps: string[];
}

const recipes: RecipeDefinition[] = [
  {
    id: 'chilli-tofu',
    title: 'Quick chilli tofu stir-fry',
    description: 'A simple pan meal using tofu and vegetables you have tracked.',
    time: '20 min',
    ingredients: [
      { name: 'Tofu', matchers: ['tofu', 'bean curd'], category: 'Protein' },
      { name: 'Chilli', matchers: ['chilli', 'chili'], category: 'Produce' },
      { name: 'Bell pepper', matchers: ['capsicum', 'bell pepper', 'bell peppers'], category: 'Produce' },
      { name: 'Carrot', matchers: ['carrot'], category: 'Produce' },
      { name: 'Rice', matchers: ['rice'], category: 'Pantry' },
    ],
    steps: ['Cut the tofu and vegetables into bite-sized pieces.', 'Stir-fry in a little oil until hot and cooked to your preference.', 'Serve with cooked rice; season with pantry sauces if available.'],
  },
  {
    id: 'tomato-egg',
    title: 'Tomato and chilli egg scramble',
    description: 'A quick breakfast idea for tomatoes that need using soon.',
    time: '12 min',
    ingredients: [
      { name: 'Tomatoes', matchers: ['tomato'], category: 'Produce' },
      { name: 'Eggs', matchers: ['egg'], category: 'Protein' },
      { name: 'Chilli', matchers: ['chilli', 'chili'], category: 'Produce' },
      { name: 'Onion', matchers: ['onion'], category: 'Produce' },
    ],
    steps: ['Chop the vegetables and soften them in a pan.', 'Add beaten eggs and stir gently until fully cooked.', 'Serve warm with toast or flatbread if available.'],
  },
  {
    id: 'tomato-pasta',
    title: 'Simple tomato pasta',
    description: 'An easy tomato-based pasta; add greens if you have them.',
    time: '25 min',
    ingredients: [
      { name: 'Tomatoes', matchers: ['tomato'], category: 'Produce' },
      { name: 'Pasta', matchers: ['pasta', 'macaroni', 'spaghetti'], category: 'Pantry' },
      { name: 'Spinach', matchers: ['spinach'], category: 'Produce' },
      { name: 'Cheese', matchers: ['cheese', 'parmesan'], category: 'Dairy' },
    ],
    steps: ['Cook the pasta according to its package instructions.', 'Cook chopped tomatoes in a pan until they soften into a sauce.', 'Toss the pasta with the sauce and add spinach or cheese if available.'],
  },
  {
    id: 'carrot-soup',
    title: 'Carrot and tomato soup',
    description: 'A warming soup to use tracked vegetables together.',
    time: '30 min',
    ingredients: [
      { name: 'Carrots', matchers: ['carrot'], category: 'Produce' },
      { name: 'Tomatoes', matchers: ['tomato'], category: 'Produce' },
      { name: 'Onion', matchers: ['onion'], category: 'Produce' },
      { name: 'Milk or stock', matchers: ['milk', 'stock', 'broth'], category: 'Pantry' },
    ],
    steps: ['Chop the vegetables and cook until softened.', 'Add water or stock, then simmer until the carrots are tender.', 'Blend carefully until smooth and season to taste.'],
  },
  {
    id: 'banana-yogurt',
    title: 'Banana and yoghurt bowl',
    description: 'A no-cook breakfast or snack with optional nuts or oats.',
    time: '5 min',
    ingredients: [
      { name: 'Banana', matchers: ['banana'], category: 'Produce' },
      { name: 'Yoghurt', matchers: ['yoghurt', 'yogurt', 'curd'], category: 'Dairy' },
      { name: 'Oats', matchers: ['oat'], category: 'Pantry' },
      { name: 'Nuts or seeds', matchers: ['almond', 'walnut', 'seed', 'peanut'], category: 'Pantry' },
    ],
    steps: ['Slice the banana into a bowl.', 'Add yoghurt and stir gently.', 'Top with oats or nuts if available.'],
  },
  {
    id: 'cucumber-salad',
    title: 'Cucumber yoghurt salad',
    description: 'A cool side dish with a few everyday ingredients.',
    time: '8 min',
    ingredients: [
      { name: 'Cucumber', matchers: ['cucumber'], category: 'Produce' },
      { name: 'Yoghurt', matchers: ['yoghurt', 'yogurt', 'curd'], category: 'Dairy' },
      { name: 'Mint', matchers: ['mint'], category: 'Produce' },
      { name: 'Lemon', matchers: ['lemon'], category: 'Produce' },
    ],
    steps: ['Dice the cucumber and chop the mint.', 'Mix with yoghurt and a squeeze of lemon.', 'Season to taste and serve chilled.'],
  },
];

function isUseableTrackedFood(food: FoodItem): boolean {
  const status = (food.freshness_status || '').toLowerCase();
  if (status === 'rotten' || status === 'expired') return false;
  if (typeof food.days_until_expiry === 'number' && food.days_until_expiry < 0) return false;
  return true;
}

function matchIngredient(ingredient: RecipeIngredient, foodItems: FoodItem[]): FoodItem | undefined {
  return foodItems.find((food) => {
    const searchable = `${food.name} ${food.category} ${food.brand || ''}`.toLocaleLowerCase();
    return ingredient.matchers.some((matcher) => searchable.includes(matcher.toLocaleLowerCase()));
  });
}

export const Recipes: React.FC = () => {
  const [foods, setFoods] = useState<FoodItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [expanded, setExpanded] = useState<string[]>([]);
  const [addedMessage, setAddedMessage] = useState('');

  const loadFoods = async () => {
    try {
      const inventory = await foodsApi.getAll({ sort_by: 'expiry_date', sort_order: 'asc' });
      setFoods(inventory.filter(isUseableTrackedFood));
      setLoadError(false);
    } catch (error) {
      console.error('Could not load inventory for recipe ideas:', error);
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void loadFoods(); }, []);

  const matchedRecipes = useMemo(() => recipes.map((recipe) => {
    const ingredients = recipe.ingredients.map((ingredient) => ({
      ...ingredient,
      matchedFood: matchIngredient(ingredient, foods),
    }));
    const availableCount = ingredients.filter((ingredient) => ingredient.matchedFood).length;
    const soonCount = ingredients.filter((ingredient) =>
      ingredient.matchedFood && typeof ingredient.matchedFood.days_until_expiry === 'number' && ingredient.matchedFood.days_until_expiry <= 3
    ).length;
    return { ...recipe, ingredients, availableCount, soonCount };
  }).filter((recipe) => recipe.availableCount > 0)
    .sort((a, b) => b.soonCount - a.soonCount || b.availableCount - a.availableCount), [foods]);

  const toggleExpanded = (id: string) => {
    setExpanded((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
  };

  const addMissingToList = (recipe: typeof matchedRecipes[number]) => {
    const missingNames = recipe.ingredients.filter((ingredient) => !ingredient.matchedFood).map((ingredient) => ingredient.name);
    if (missingNames.length === 0) {
      setAddedMessage(`All listed ingredients for ${recipe.title} are in your tracked inventory.`);
      return;
    }
    addShoppingItems(missingNames, 'Groceries');
    setAddedMessage(`Added ${missingNames.length} untracked ingredient${missingNames.length === 1 ? '' : 's'} for ${recipe.title} to your shopping list.`);
  };

  return (
    <div className="kitchen-page space-y-7 sm:space-y-8">
      <header className="flex flex-col gap-4 border-b border-[#dedfd4] pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="mb-2 inline-flex items-center gap-2 text-sm font-medium text-[#68746a]">
            <CookingPot className="h-4 w-4" />
            Meal ideas from your kitchen
          </p>
          <h1 className="kitchen-heading text-4xl sm:text-5xl">What can we make?</h1>
          <p className="mt-3 max-w-2xl text-base leading-7 text-[#5b665e]">
            Suggestions are based on your tracked inventory. Ingredients not found in the list may already be in your pantry.
          </p>
        </div>
        <Link to="/shopping-list" className="inline-flex min-h-11 items-center justify-center gap-2 self-start rounded-xl border border-[#b9c5b8] bg-[#fffefa] px-4 py-3 text-sm font-semibold text-[#294a36] transition-colors hover:bg-[#edf2e8] sm:self-auto">
          <ShoppingCart className="h-4 w-4" /> Open shopping list <ArrowRight className="h-4 w-4" />
        </Link>
      </header>

      {loadError && (
        <div role="alert" className="flex items-start gap-3 rounded-xl border border-[#ead6aa] bg-[#fff7df] px-4 py-3 text-sm text-[#75531c]">
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
          <div className="flex-1">
            <p className="font-semibold">Couldn't load your food inventory.</p>
            <p className="mt-1">Recipe suggestions need the live inventory, so we haven't shown made-up matches.</p>
          </div>
          <button type="button" onClick={() => { setLoading(true); void loadFoods(); }} className="shrink-0 font-semibold underline underline-offset-2">Try again</button>
        </div>
      )}

      {addedMessage && (
        <div role="status" className="flex items-start gap-2 rounded-xl border border-[#dbe5d6] bg-[#edf2e8] px-4 py-3 text-sm text-[#315b39]">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
          <p className="flex-1">{addedMessage}</p>
          <button type="button" onClick={() => setAddedMessage('')} aria-label="Dismiss message" className="rounded p-1 hover:bg-white"><span aria-hidden="true">×</span></button>
        </div>
      )}

      {loading ? (
        <div className="kitchen-panel flex min-h-48 flex-col items-center justify-center gap-3 p-8 text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-[#315c43] border-t-transparent" />
          <p className="text-sm text-[#68746a]">Checking your tracked ingredients…</p>
        </div>
      ) : matchedRecipes.length === 0 ? (
        <div className="kitchen-panel flex flex-col items-center px-6 py-12 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#e5efdf] text-[#356247]"><Utensils className="h-7 w-7" /></div>
          <h2 className="kitchen-heading mt-4 text-2xl">Let's add a few ingredients first</h2>
          <p className="mt-2 max-w-md text-sm leading-6 text-[#68746a]">We couldn't match the current tracked inventory to these simple meal ideas. Add food items, then come back for suggestions. Items marked Rotten or Expired are intentionally excluded.</p>
          <Link to="/foods" className="mt-5 inline-flex min-h-11 items-center gap-2 rounded-xl bg-[#315c43] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#254a35]">View inventory <ArrowRight className="h-4 w-4" /></Link>
        </div>
      ) : (
        <>
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="kitchen-heading text-2xl">Ideas using what you have</h2>
              <p className="mt-1 text-sm text-[#68746a]">{matchedRecipes.length} ideas matched to your current inventory</p>
            </div>
            <span className="hidden items-center gap-1.5 rounded-full bg-[#e5efdf] px-3 py-1.5 text-xs font-semibold text-[#315b39] sm:inline-flex"><CheckCircle2 className="h-3.5 w-3.5" /> Based on tracked food</span>
          </div>
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            {matchedRecipes.map((recipe) => {
              const isExpanded = expanded.includes(recipe.id);
              const missingCount = recipe.ingredients.filter((ingredient) => !ingredient.matchedFood).length;
              return (
                <article key={recipe.id} className="kitchen-panel flex flex-col overflow-hidden">
                  <div className="flex items-start gap-4 border-b border-[#e8e8de] bg-[#f7f6ef] p-5 sm:p-6">
                    <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-white text-[#315c43] ring-1 ring-[#e1e2d8]"><CookingPot className="h-7 w-7" /></div>
                    <div className="min-w-0 flex-1">
                      <h3 className="kitchen-heading text-2xl">{recipe.title}</h3>
                      <p className="mt-2 text-sm leading-6 text-[#5b685f]">{recipe.description}</p>
                      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs font-medium text-[#69756b]">
                        <span className="inline-flex items-center gap-1 rounded-full bg-white px-2.5 py-1 ring-1 ring-[#e1e2d8]"><Clock3 className="h-3.5 w-3.5" /> {recipe.time}</span>
                        <span className="rounded-full bg-[#e5efdf] px-2.5 py-1 text-[#315b39]">{recipe.availableCount} of {recipe.ingredients.length} tracked</span>
                        {recipe.soonCount > 0 && <span className="rounded-full bg-[#fff0cf] px-2.5 py-1 text-[#805414]">Uses {recipe.soonCount} item(s) due soon</span>}
                      </div>
                    </div>
                  </div>

                  <div className="flex-1 p-5 sm:p-6">
                    <h4 className="text-sm font-semibold text-[#34443a]">Ingredients</h4>
                    <ul className="mt-3 flex flex-wrap gap-2">
                      {recipe.ingredients.map((ingredient) => (
                        <li key={ingredient.name} className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium ${ingredient.matchedFood ? 'bg-[#e5efdf] text-[#315b39]' : 'bg-[#fff0cf] text-[#805414]'}`}>
                          {ingredient.matchedFood ? <CheckCircle2 className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
                          {ingredient.matchedFood ? ingredient.matchedFood.name : ingredient.name}
                          {!ingredient.matchedFood && <span className="opacity-75">· not tracked</span>}
                        </li>
                      ))}
                    </ul>
                    <button type="button" onClick={() => toggleExpanded(recipe.id)} aria-expanded={isExpanded} className="mt-5 inline-flex min-h-10 items-center gap-2 text-sm font-semibold text-[#315c43] hover:underline">
                      {isExpanded ? 'Hide cooking steps' : 'Show cooking steps'} <ChevronDown className={`h-4 w-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                    </button>
                    {isExpanded && (
                      <ol className="mt-3 space-y-2 rounded-xl border border-[#e1e2d8] bg-white p-4 text-sm leading-6 text-[#526056]">
                        {recipe.steps.map((step, index) => <li key={step} className="flex items-start gap-2"><span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#edf2e8] text-xs font-semibold text-[#315c43]">{index + 1}</span><span>{step}</span></li>)}
                      </ol>
                    )}
                  </div>
                  <div className="flex flex-col gap-3 border-t border-[#e8e8de] bg-white px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
                    <p className="text-xs leading-5 text-[#7b857b]">Check the condition of food and cook it safely before eating.</p>
                    <button type="button" onClick={() => addMissingToList(recipe)} className="inline-flex min-h-10 shrink-0 items-center justify-center gap-2 rounded-xl border border-[#b9c5b8] px-3.5 py-2 text-sm font-semibold text-[#294a36] transition-colors hover:bg-[#edf2e8]">
                      <ShoppingCart className="h-4 w-4" /> {missingCount ? 'Add untracked to list' : 'Review ingredients'}
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
};

export default Recipes;
