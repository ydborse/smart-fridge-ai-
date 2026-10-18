/**
 * Intelligent Food Item to Emoji Mapper
 * Maps specific fruit, vegetable, dairy, and food names to accurate visual icons
 * with category fallbacks.
 */
export function getFoodEmoji(name?: string, category?: string): string {
  if (!name && !category) return '🥫';
  const cleanName = (name || '').toLowerCase().trim();

  // Specific Fruits
  if (cleanName.includes('apple')) return '🍎';
  if (cleanName.includes('banana')) return '🍌';
  if (cleanName.includes('strawberr')) return '🍓';
  if (cleanName.includes('tomato')) return '🍅';
  if (cleanName.includes('lychee') || cleanName.includes('litchi') || cleanName.includes('cherry')) return '🍒';
  if (cleanName.includes('avocado')) return '🥑';
  if (cleanName.includes('lemon') || cleanName.includes('lime')) return '🍋';
  if (cleanName.includes('orange') || cleanName.includes('citrus') || cleanName.includes('tangerine')) return '🍊';
  if (cleanName.includes('grape')) return '🍇';
  if (cleanName.includes('watermelon') || cleanName.includes('melon')) return '🍉';
  if (cleanName.includes('mango')) return '🥭';
  if (cleanName.includes('peach')) return '🍑';
  if (cleanName.includes('pear')) return '🍐';
  if (cleanName.includes('pineappl')) return '🍍';
  if (cleanName.includes('kiwi')) return '🥝';
  if (cleanName.includes('blueberr') || cleanName.includes('berr')) return '🫐';
  if (cleanName.includes('pomegranat')) return '🫐';

  // Specific Vegetables
  if (cleanName.includes('capsicum') || cleanName.includes('bell pepper') || cleanName.includes('pepper')) return '🫑';
  if (cleanName.includes('chilli') || cleanName.includes('chili') || cleanName.includes('jalapeno')) return '🌶️';
  if (cleanName.includes('coriander') || cleanName.includes('cilantro') || cleanName.includes('herb') || cleanName.includes('mint') || cleanName.includes('parsley')) return '🌿';
  if (cleanName.includes('carrot')) return '🥕';
  if (cleanName.includes('broccoli')) return '🥦';
  if (cleanName.includes('potato')) return '🥔';
  if (cleanName.includes('onion') || cleanName.includes('garlic')) return '🧅';
  if (cleanName.includes('cucumber') || cleanName.includes('zucchini')) return '🥒';
  if (cleanName.includes('lettuce') || cleanName.includes('spinach') || cleanName.includes('cabbage') || cleanName.includes('salad')) return '🥬';
  if (cleanName.includes('corn')) return '🌽';
  if (cleanName.includes('mushroom')) return '🍄';
  if (cleanName.includes('eggplant') || cleanName.includes('brinjal')) return '🍆';
  if (cleanName.includes('pea')) return '🫛';

  // Dairy & Proteins
  if (cleanName.includes('milk')) return '🥛';
  if (cleanName.includes('curd') || cleanName.includes('yogurt') || cleanName.includes('yoghurt')) return '🥣';
  if (cleanName.includes('paneer') || cleanName.includes('cheese') || cleanName.includes('tofu')) return '🧀';
  if (cleanName.includes('egg')) return '🥚';
  if (cleanName.includes('chicken') || cleanName.includes('meat') || cleanName.includes('beef') || cleanName.includes('pork') || cleanName.includes('lamb')) return '🍗';
  if (cleanName.includes('fish') || cleanName.includes('salmon') || cleanName.includes('shrimp') || cleanName.includes('seafood')) return '🐟';

  // Bakery, Beverages & Prepared Foods
  if (cleanName.includes('bread') || cleanName.includes('toast') || cleanName.includes('croissant') || cleanName.includes('bakery')) return '🍞';
  if (cleanName.includes('juice')) return '🧃';
  if (cleanName.includes('water') || cleanName.includes('soda')) return '🥤';
  if (cleanName.includes('pasta') || cleanName.includes('noodle') || cleanName.includes('spaghetti')) return '🍝';
  if (cleanName.includes('soup') || cleanName.includes('stew') || cleanName.includes('curry')) return '🍲';
  if (cleanName.includes('pizza')) return '🍕';
  if (cleanName.includes('biscuit') || cleanName.includes('cookie') || cleanName.includes('oreo')) return '🍪';

  // Category fallback
  switch (category) {
    case 'Fruits':
      return '🍎';
    case 'Vegetables':
      return '🥗';
    case 'Dairy':
      return '🥛';
    case 'Beverages':
      return '🧃';
    case 'Meat/Seafood':
      return '🍗';
    case 'Leftovers':
      return '🍲';
    default:
      return '🥫';
  }
}
