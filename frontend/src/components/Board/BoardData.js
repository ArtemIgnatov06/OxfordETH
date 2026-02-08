// src/components/Board/BoardData.js

export const TILES = [
  // --- BOTTOM ROW (Right to Left) ---
  { id: 0, type: 'corner', subtype: 'go', name: 'START', price: null },

  // MEME family (2) ✅ подняли цены до нормального масштаба
  { id: 1, type: 'property', family: 'meme', name: 'DOGE', price: 60, rent: 8 },
  { id: 2, type: 'property', family: 'meme', name: 'PEPE', price: 40, rent: 6 },

  { id: 3, type: 'chance', name: 'Chance', price: null },

  // SOL family (3) ✅ подняли BONK и чуть выровняли JUP
  { id: 4, type: 'property', family: 'sol', name: 'BONK', price: 80, rent: 10 },

  { id: 5, type: 'tax', name: 'Gas Fee', price: 100 },

  // --- LEFT COLUMN (Bottom to Top) ---
  { id: 6, type: 'corner', subtype: 'jail', name: 'ACCOUNT BLOCKED', price: null },

  // SOL family
  { id: 7, type: 'property', family: 'sol', name: 'SOL', price: 145, rent: 14 },
  { id: 8, type: 'property', family: 'sol', name: 'JUP', price: 110, rent: 12 },

  { id: 9, type: 'chance', name: 'Chance', price: null },

  // BNB family
  { id: 10, type: 'property', family: 'bnb', name: 'BNB', price: 580, rent: 50 },
  { id: 11, type: 'property', family: 'bnb', name: 'CAKE', price: 250, rent: 22 },

  // --- TOP ROW (Left to Right) ---
  { id: 12, type: 'corner', subtype: 'parking', name: 'SYSTEM DOWN', price: null },

  // BNB family
  { id: 13, type: 'property', family: 'bnb', name: 'TWT', price: 120, rent: 14 },

  // ETH family
  { id: 14, type: 'property', family: 'eth', name: 'ETH', price: 2400, rent: 200 },
  { id: 15, type: 'property', family: 'eth', name: 'ARB', price: 200, rent: 18 },
  { id: 16, type: 'chance', name: 'Chance', price: null },
  { id: 17, type: 'property', family: 'eth', name: 'UNI', price: 300, rent: 24 },

  // --- RIGHT COLUMN (Top to Bottom) ---
  { id: 18, type: 'corner', subtype: 'gotojail', name: 'SYSTEM BUG', price: null },

  { id: 19, type: 'tax', name: 'Gas Fee', price: 100 },

  // BTC family
  { id: 20, type: 'property', family: 'btc', name: 'BTC', price: 65000, rent: 500 },
  { id: 21, type: 'property', family: 'btc', name: 'WBTC', price: 64900, rent: 480 },
  { id: 22, type: 'chance', name: 'Chance', price: null },
  { id: 23, type: 'property', family: 'btc', name: 'STX', price: 180, rent: 25 },
];

export const FAMILY_COLORS = {
  meme: '#FF69B4',
  sol: '#9945FF',
  bnb: '#F0B90B',
  eth: '#627EEA',
  btc: '#F7931A',
};
