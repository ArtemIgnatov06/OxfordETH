// src/components/Board/BoardData.js

export const TILES = [
  // --- BOTTOM ROW (Right to Left) ---
  { id: 0, type: 'corner', subtype: 'go', name: 'START', price: null },
  { id: 1, type: 'property', family: 'meme', name: 'DOGE', price: 0.12, rent: 10 },
  { id: 2, type: 'property', family: 'meme', name: 'PEPE', price: 0.00001, rent: 5 },
  { id: 3, type: 'chance', name: 'Chance', price: null },
  { id: 4, type: 'property', family: 'meme', name: 'SHIB', price: 0.00002, rent: 8 },
  { id: 5, type: 'tax', name: 'Gas Fee', price: 50 }, // Филлер
  
  // --- LEFT COLUMN (Bottom to Top) ---
  { id: 6, type: 'corner', subtype: 'jail', name: 'JAIL', price: null },
  { id: 7, type: 'property', family: 'sol', name: 'SOL', price: 145, rent: 14 },
  { id: 8, type: 'property', family: 'sol', name: 'JUP', price: 1.2, rent: 12 },
  { id: 9, type: 'chance', name: 'Chance', price: null },
  { id: 10, type: 'property', family: 'bnb', name: 'BNB', price: 580, rent: 50 },
  { id: 11, type: 'property', family: 'bnb', name: 'CAKE', price: 2.5, rent: 20 },

  // --- TOP ROW (Left to Right) ---
  { id: 12, type: 'corner', subtype: 'parking', name: 'HODL', price: null }, // Free Parking
  { id: 13, type: 'property', family: 'eth', name: 'ETH', price: 2400, rent: 200 },
  { id: 14, type: 'property', family: 'eth', name: 'ARB', price: 1.1, rent: 15 },
  { id: 15, type: 'chance', name: 'Chance', price: null },
  { id: 16, type: 'property', family: 'eth', name: 'UNI', price: 7.5, rent: 18 },
  { id: 17, type: 'tax', name: 'Rug Pull', price: 100 }, // Филлер

  // --- RIGHT COLUMN (Top to Bottom) ---
  { id: 18, type: 'corner', subtype: 'gotojail', name: 'GO TO JAIL', price: null },
  { id: 19, type: 'property', family: 'btc', name: 'BTC', price: 65000, rent: 500 },
  { id: 20, type: 'property', family: 'btc', name: 'WBTC', price: 64900, rent: 480 },
  { id: 21, type: 'chance', name: 'Chance', price: null },
  { id: 22, type: 'property', family: 'btc', name: 'STX', price: 1.8, rent: 25 },
  { id: 23, type: 'action', name: 'Airdrop', price: null }, // Бонус
];

export const FAMILY_COLORS = {
  meme: '#FF69B4', // Розовый
  sol: '#9945FF',  // Фиолетовый
  bnb: '#F0B90B',  // Желтый
  eth: '#627EEA',  // Синий
  btc: '#F7931A',  // Оранжевый
};