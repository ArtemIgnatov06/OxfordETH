// src/components/Board/BoardData.js

export const TILES = [
  // --- BOTTOM ROW (Right to Left) ---
  { id: 0, type: 'corner', subtype: 'go', name: 'START', price: null },

  // JOKE family (2)
  { id: 1, type: 'property', family: 'meme', name: 'DOGE', price: 0.12, rent: 10 },
  { id: 2, type: 'property', family: 'meme', name: 'PEPE', price: 0.00001, rent: 5 },

  { id: 3, type: 'chance', name: 'Chance', price: null },

  // SOL family (3)
  { id: 4, type: 'property', family: 'sol', name: 'BONK', price: 0.00002, rent: 8 },

  { id: 5, type: 'tax', name: 'Gas Fee', price: 100 },

  // --- LEFT COLUMN (Bottom to Top) ---
  { id: 6, type: 'corner', subtype: 'jail', name: 'JAIL', price: null },

  // SOL family (остальные 2)
  { id: 7, type: 'property', family: 'sol', name: 'SOL', price: 145, rent: 14 },
  { id: 8, type: 'property', family: 'sol', name: 'JUP', price: 1.2, rent: 12 },

  { id: 9, type: 'chance', name: 'Chance', price: null },

  // BNB family (2 тут)
  { id: 10, type: 'property', family: 'bnb', name: 'BNB', price: 580, rent: 50 },
  { id: 11, type: 'property', family: 'bnb', name: 'CAKE', price: 2.5, rent: 20 },

  // --- TOP ROW (Left to Right) ---
  { id: 12, type: 'corner', subtype: 'parking', name: 'HODL', price: null },

  // ✅ TWT фиксируем на 13
  { id: 13, type: 'property', family: 'bnb', name: 'TWT', price: 1.1, rent: 16 },

  // ⬇️ всё что было с 13 — сдвинуто на +1 (кроме GO TO JAIL)
  { id: 14, type: 'property', family: 'eth', name: 'ETH', price: 2400, rent: 200 },
  { id: 15, type: 'property', family: 'eth', name: 'ARB', price: 1.1, rent: 15 },
  { id: 16, type: 'chance', name: 'Chance', price: null },
  { id: 17, type: 'property', family: 'eth', name: 'UNI', price: 7.5, rent: 18 },

  // --- RIGHT COLUMN (Top to Bottom) ---
  // ❗ НЕ двигаем
  { id: 18, type: 'corner', subtype: 'gotojail', name: 'GO TO JAIL', price: null },

  // (Rug Pull был 17 -> стал 19, потому что 18 занято GO TO JAIL)
  { id: 19, type: 'tax', name: 'Gas Fee', price: 100 },

  // BTC family (3) — сдвинулись на +1
  { id: 20, type: 'property', family: 'btc', name: 'BTC', price: 65000, rent: 500 },
  { id: 21, type: 'property', family: 'btc', name: 'WBTC', price: 64900, rent: 480 },
  { id: 22, type: 'chance', name: 'Chance', price: null },
  { id: 23, type: 'property', family: 'btc', name: 'STX', price: 1.8, rent: 25 },
];

export const FAMILY_COLORS = {
  meme: '#FF69B4',
  sol: '#9945FF',
  bnb: '#F0B90B',
  eth: '#627EEA',
  btc: '#F7931A',
};
