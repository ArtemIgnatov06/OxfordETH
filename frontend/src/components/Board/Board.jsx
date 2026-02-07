// src/components/Board/Board.jsx
import React, { useEffect, useMemo, useRef, useState } from 'react';
import './Board.css';
import { TILES, FAMILY_COLORS } from './BoardData';

const PLAYERS_MAX = 4;
const PLAYER_COLORS = ['#22c55e', '#3b82f6', '#a855f7', '#f97316'];

const Board = () => {
  const [dice, setDice] = useState([1, 1]);
  const [chatMsg, setChatMsg] = useState('');
  const [messages, setMessages] = useState([{ user: 'System', text: 'Welcome to FlarePoly Testnet!' }]);
  const chatListRef = useRef(null);
const shouldStickToBottomRef = useRef(true);
  const playersCount = PLAYERS_MAX;

  const [playerPos, setPlayerPos] = useState(() => Array.from({ length: playersCount }, () => 0));
  const [activePlayer, setActivePlayer] = useState(0);

  const base = import.meta.env.BASE_URL;
  const getTokenIconSrc = (tile) => `${base}images/${tile.name}.png`;

    const addMessage = (user, text) => {
    setMessages((prev) => [...prev, { user, text }]);
    };

  const getPositionStyle = (index) => {
    let row, col;
    if (index === 0) { row = 7; col = 7; }
    else if (index > 0 && index < 6) { row = 7; col = 7 - index; }
    else if (index === 6) { row = 7; col = 1; }
    else if (index > 6 && index < 12) { row = 7 - (index - 6); col = 1; }
    else if (index === 12) { row = 1; col = 1; }
    else if (index > 12 && index < 18) { row = 1; col = 1 + (index - 12); }
    else if (index === 18) { row = 1; col = 7; }
    else { row = 1 + (index - 18); col = 7; }
    return { gridRow: row, gridColumn: col };
  };

  const animateMove = async (playerIndex, steps) => {
    return new Promise((resolve) => {
      let remaining = steps;
      const tick = () => {
        setPlayerPos((prev) => {
          const next = [...prev];
          next[playerIndex] = (next[playerIndex] + 1) % TILES.length;
          return next;
        });
        remaining -= 1;
        if (remaining <= 0) return resolve();
        setTimeout(tick, 120);
      };
      setTimeout(tick, 120);
    });
  };

  const handleRoll = async () => {
    const d1 = Math.floor(Math.random() * 6) + 1;
    const d2 = Math.floor(Math.random() * 6) + 1;
    setDice([d1, d2]);

    const steps = d1 + d2;
    addMessage('Player', `P${activePlayer + 1} rolled ${steps} (${d1} + ${d2})`);

    await animateMove(activePlayer, steps);
    setActivePlayer((p) => (p + 1) % playersCount);
  };

  const walletMocks = useMemo(() => {
    const baseAddrs = ['0xA1b2...C3d4', '0xBEEF...1337', '0x9f12...0AA1', '0xDEAD...B00B'];
    return baseAddrs.slice(0, playersCount);
  }, [playersCount]);
  const flareCoinsMock = useMemo(() => {
  // заглушки, потом заменишь на реальные данные
  return [4200, 1337, 777, 9001].slice(0, playersCount);
}, [playersCount]);

  const buildConicGradient = (playersOnTile) => {
    const n = playersOnTile.length;
    if (n === 0) return null;

    const step = 360 / n;
    const parts = playersOnTile.map((pIdx, i) => {
      const from = i * step;
      const to = (i + 1) * step;
      const col = PLAYER_COLORS[pIdx];
      return `${col} ${from}deg ${to}deg`;
    });

    return `conic-gradient(from -90deg, ${parts.join(', ')})`;
  };

  const byTile = useMemo(() => {
    const map = {}; // tileId -> [playerIndex...]
    for (let p = 0; p < playersCount; p++) {
      const tileId = playerPos[p];
      (map[tileId] ||= []).push(p);
    }
    return map;
  }, [playerPos, playersCount]);

    useEffect(() => {
    const el = chatListRef.current;
    if (!el) return;

    // автоскролл вниз только если пользователь "внизу"
    if (shouldStickToBottomRef.current) {
      el.scrollTop = el.scrollHeight;
    }
  }, [messages]);

  
  return (
    <div className="board-layout">
      <div className="monopoly-wrapper">
        <div className="monopoly-board">

          {/* --- ЦЕНТРАЛЬНАЯ ПАНЕЛЬ --- */}
          <div className="board-center">
            <div className="center-logo">
              <h1 className="flare-title">FLAREPOLY</h1>
              <p className="flare-subtitle">REAL-TIME CRYPTO MONOPOLY</p>
            </div>

            <div className="game-controls">
              <div className="dice-section">
                <div className="dice-display">🎲 {dice[0]} : {dice[1]}</div>
                <button className="roll-btn" onClick={handleRoll}>ROLL DICE</button>
              </div>

              <div className="chat-box">
                <div
                className="chat-messages"
                ref={chatListRef}
                onScroll={() => {
                    const el = chatListRef.current;
                    
                    if (!el) return;
                    // считаем "я внизу", если до конца осталось <= 24px
                    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight <= 24;
                    shouldStickToBottomRef.current = atBottom;
                }}
                >
                {messages.map((m, i) => (
                    <div key={i}><strong>{m.user}:</strong> {m.text}</div>
                ))}
                </div>

                <input
                  className="chat-input"
                  placeholder="Type..."
                  value={chatMsg}
                  onChange={(e) => setChatMsg(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && chatMsg) {
                      addMessage('Me', chatMsg);
                      setChatMsg('');
                    }
                  }}
                />
              </div>
            </div>
          </div>

          {/* --- КЛЕТКИ --- */}
          {TILES.map((tile) => {
            const playersHere = byTile[tile.id] || [];
            const gradient = buildConicGradient(playersHere);
            const activeHere = playersHere.includes(activePlayer);
            const activeColor = activeHere ? PLAYER_COLORS[activePlayer] : 'transparent';

            return (
              <div
                key={tile.id}
                className={`tile ${tile.type}`}
                style={getPositionStyle(tile.id)}
              >
                {/* ✅ РАМКА ВНУТРИ КЛЕТКИ => идеальное совпадение */}
                {playersHere.length > 0 && (
                  <div
                    className={`tile-ring ${activeHere ? 'active' : ''}`}
                    style={{
                      '--ring-gradient': gradient,
                      '--active-color': activeColor,
                    }}
                  />
                )}

                {tile.type === 'property' && (
                  <div
                    className="color-bar"
                    style={{ backgroundColor: FAMILY_COLORS[tile.family] }}
                  />
                )}

                <div className="tile-content">
                  {tile.type === 'corner' ? (
                    tile.subtype === 'gotojail' ? (
                      <div className="corner-full">
                        <img className="corner-full-img" src={`${base}images/SYSTEMBUG.png`} alt="SYSTEM BUG" loading="lazy" />
                      </div>
                    ) : tile.subtype === 'jail' ? (
                      <div className="corner-full">
                        <img className="corner-full-img" src={`${base}images/ACCOUNTBLOCKED.png`} alt="ACCOUNT BLOCKED" loading="lazy" />
                      </div>
                    ) : tile.subtype === 'go' ? (
                      <div className="corner-full">
                        <img className="corner-full-img" src={`${base}images/START.png`} alt="START" loading="lazy" />
                      </div>
                    ) : tile.subtype === 'parking' ? (
                      <div className="corner-full">
                        <img className="corner-full-img" src={`${base}images/SYSTEMDOWN.png`} alt="SYSTEM DOWN" loading="lazy" />
                      </div>
                    ) : (
                      <div className="corner-title">{tile.name}</div>
                    )
                  ) : tile.type === 'chance' ? (
                    <div className="corner-full">
                      <img className="corner-full-img" src={`${base}images/CHANCE.png`} alt="CHANCE" loading="lazy" />
                    </div>
                  ) : tile.type === 'property' ? (
                    <>
                      <div className="token-icon-wrap">
                        <img className="token-icon" src={getTokenIconSrc(tile)} alt={tile.name} loading="lazy" />
                      </div>
                      <div className="tile-name">{tile.name}</div>
                      {tile.price != null && <div className="tile-price">${tile.price}</div>}
                    </>
                  ) : (
                    <>
                      <div className="tile-name">{tile.name}</div>
                      {tile.price != null && <div className="tile-price">${tile.price}</div>}
                    </>
                  )}
                </div>

                <div style={{ position: 'absolute', bottom: 1, right: 2, fontSize: 8, opacity: 0.3 }}>
                  {tile.id}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ПРАВАЯ ПАНЕЛЬ */}
      <aside className="wallets-panel">
        <div className="wallets-title">PLAYERS</div>

        {walletMocks.map((addr, idx) => (
          <div key={idx} className={`wallet-card ${idx === activePlayer ? 'active' : ''}`}>
            <div className="wallet-left">
              <div className="player-dot" style={{ background: PLAYER_COLORS[idx] }} />
              <div className="wallet-meta">
                <div className="wallet-name">PLAYER {idx + 1}</div>
                <div className="wallet-addr">{addr}</div>
              </div>
            </div>

            <div className="wallet-right">
            <div className="wallet-chip">POS {playerPos[idx]}</div>
            <div className="wallet-chip wallet-chip-coins">🔥 {flareCoinsMock[idx]} FC</div>
            </div>
          </div>
        ))}

        <div className="wallets-hint">
          Сейчас 4 игрока-заглушки. Потом подключим реальные адреса и количество 2–4.
        </div>
      </aside>
    </div>
  );
};

export default Board;
