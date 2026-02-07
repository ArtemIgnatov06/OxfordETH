// src/components/Board/Board.jsx
import React, { useEffect, useMemo, useRef, useState } from 'react';
import './Board.css';
import { TILES, FAMILY_COLORS } from './BoardData';

const PLAYERS_MAX = 4;
const PLAYER_COLORS = ['#22c55e', '#3b82f6', '#a855f7', '#f97316'];

const isPropertyBuyable = (tile) => tile?.type === 'property' && tile?.price != null;

const Board = () => {
  const [dice, setDice] = useState([1, 1]);
  const [chatMsg, setChatMsg] = useState('');
  const [messages, setMessages] = useState([{ user: 'System', text: 'Welcome to FlarePoly Testnet!' }]);

  const chatListRef = useRef(null);
  const shouldStickToBottomRef = useRef(true);

  const playersCount = PLAYERS_MAX;

  const [playerPos, setPlayerPos] = useState(() => Array.from({ length: playersCount }, () => 0));
  const [activePlayer, setActivePlayer] = useState(0);

  // tileId -> ownerPlayerIndex
  const [ownership, setOwnership] = useState({});

  // покупка на приземлении: { tileId, playerIndex }
  const [buyPrompt, setBuyPrompt] = useState(null);

  // FlareCoins по игрокам (state, двигаются только при сделках улиц)
  const [balances, setBalances] = useState(() => [4200, 1337, 777, 9001].slice(0, playersCount));

  // ===== STREET OFFERS =====
  // offer = { id, type:'sell'|'buy', from, to, tileId, priceFC, createdAt }
  const [tradeOffers, setTradeOffers] = useState([]);

  // модалка создания оффера (SELL/BUY)
  const [tradeOpen, setTradeOpen] = useState(false);
  const [tradeForm, setTradeForm] = useState({
    mode: 'sell',     // 'sell' | 'buy'
    tileId: null,     // number
    target: 1,        // player index
    priceFC: 500,     // number
  });

  const base = import.meta.env.BASE_URL;
  const getTokenIconSrc = (tile) => `${base}images/${tile.name}.png`;

  const addMessage = (user, text) => setMessages((prev) => [...prev, { user, text }]);

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
    const map = {};
    for (let p = 0; p < playersCount; p++) {
      const tileId = playerPos[p];
      (map[tileId] ||= []).push(p);
    }
    return map;
  }, [playerPos, playersCount]);

  const walletMocks = useMemo(() => {
    const baseAddrs = ['0xA1b2...C3d4', '0xBEEF...1337', '0x9f12...0AA1', '0xDEAD...B00B'];
    return baseAddrs.slice(0, playersCount);
  }, [playersCount]);

  const incomingOffersForActive = useMemo(
    () => tradeOffers.filter((o) => o.to === activePlayer),
    [tradeOffers, activePlayer]
  );

  const myOwnedTiles = useMemo(() => {
    const mine = [];
    for (const [tileIdStr, ownerIdx] of Object.entries(ownership)) {
      const tileId = Number(tileIdStr);
      if (ownerIdx === activePlayer) mine.push(tileId);
    }
    mine.sort((a, b) => a - b);
    return mine;
  }, [ownership, activePlayer]);

  const otherOwnedTiles = useMemo(() => {
    const arr = [];
    for (const [tileIdStr, ownerIdx] of Object.entries(ownership)) {
      const tileId = Number(tileIdStr);
      if (ownerIdx != null && ownerIdx !== activePlayer) arr.push(tileId);
    }
    arr.sort((a, b) => a - b);
    return arr;
  }, [ownership, activePlayer]);

  // ===== BUY ON LANDING =====
  const handleRoll = async () => {
    // блок если: модалка покупки/трейда или есть входящие офферы у текущего игрока
    if (buyPrompt || tradeOpen || incomingOffersForActive.length > 0) return;

    const d1 = Math.floor(Math.random() * 6) + 1;
    const d2 = Math.floor(Math.random() * 6) + 1;
    setDice([d1, d2]);

    const steps = d1 + d2;
    addMessage('Player', `P${activePlayer + 1} rolled ${steps} (${d1} + ${d2})`);

    const startPos = playerPos[activePlayer];
    const finalPos = (startPos + steps) % TILES.length;

    await animateMove(activePlayer, steps);

    const tile = TILES[finalPos];

    if (isPropertyBuyable(tile) && ownership[finalPos] == null) {
      setBuyPrompt({ tileId: finalPos, playerIndex: activePlayer });
      return;
    }

    setActivePlayer((p) => (p + 1) % playersCount);
  };

  const handleBuy = () => {
    if (!buyPrompt) return;
    const { tileId, playerIndex } = buyPrompt;

    setOwnership((prev) => ({ ...prev, [tileId]: playerIndex }));
    addMessage('System', `P${playerIndex + 1} bought ${TILES[tileId].name} for $${TILES[tileId].price}`);

    setBuyPrompt(null);
    setActivePlayer((p) => (p + 1) % playersCount);
  };

  const handleSkipBuy = () => {
    if (!buyPrompt) return;
    const { tileId, playerIndex } = buyPrompt;

    addMessage('System', `P${playerIndex + 1} skipped ${TILES[tileId].name}`);

    setBuyPrompt(null);
    setActivePlayer((p) => (p + 1) % playersCount);
  };

  // ===== OPEN TRADE MODAL =====
  const openTradeSell = () => {
    const tileId = myOwnedTiles[0] ?? null;
    const target = (activePlayer + 1) % playersCount;

    setTradeForm({ mode: 'sell', tileId, target, priceFC: 500 });
    setTradeOpen(true);
  };

  const openTradeBuy = () => {
    const tileId = otherOwnedTiles[0] ?? null;
    const owner = tileId != null ? ownership[tileId] : null;

    setTradeForm({
      mode: 'buy',
      tileId,
      target: owner ?? ((activePlayer + 1) % playersCount), // target = owner
      priceFC: 500,
    });
    setTradeOpen(true);
  };

  const setTradeMode = (mode) => {
    if (mode === 'sell') {
      const tileId = myOwnedTiles[0] ?? null;
      setTradeForm((f) => ({
        ...f,
        mode: 'sell',
        tileId,
        target: f.target === activePlayer ? (activePlayer + 1) % playersCount : f.target,
      }));
    } else {
      const tileId = otherOwnedTiles[0] ?? null;
      const owner = tileId != null ? ownership[tileId] : null;
      setTradeForm((f) => ({
        ...f,
        mode: 'buy',
        tileId,
        target: owner ?? ((activePlayer + 1) % playersCount),
      }));
    }
  };

  const onTradeTileChange = (nextTileIdRaw) => {
    const nextTileId = nextTileIdRaw === '' ? null : Number(nextTileIdRaw);

    setTradeForm((f) => {
      if (f.mode === 'buy') {
        const owner = nextTileId != null ? ownership[nextTileId] : f.target;
        return { ...f, tileId: nextTileId, target: owner ?? f.target };
      }
      return { ...f, tileId: nextTileId };
    });
  };

  const createTradeOffer = () => {
    const priceFC = Math.max(0, Math.floor(Number(tradeForm.priceFC) || 0));
    const tileId = tradeForm.tileId != null ? Number(tradeForm.tileId) : null;
    const target = Number(tradeForm.target);

    if (tileId == null) return addMessage('System', 'Trade: select a tile');
    const tile = TILES[tileId];

    if (!isPropertyBuyable(tile)) return addMessage('System', 'Trade: tile is not tradable');
    if (!priceFC) return addMessage('System', 'Trade: price must be > 0');
    if (target === activePlayer) return addMessage('System', 'Trade: cannot target yourself');

    const ownerIdx = ownership[tileId];

    if (tradeForm.mode === 'sell') {
      if (ownerIdx !== activePlayer) return addMessage('System', 'Trade: you can SELL only your own tile');
    } else {
      if (ownerIdx == null) return addMessage('System', 'Trade: tile is not owned (just buy it on landing)');
      if (ownerIdx !== target) return addMessage('System', 'Trade: target must be the current owner');
    }

    const offer = {
      id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
      type: tradeForm.mode, // 'sell' | 'buy'
      from: activePlayer,
      to: target,
      tileId,
      priceFC,
      createdAt: Date.now(),
    };

    setTradeOffers((prev) => [offer, ...prev]);

    if (offer.type === 'sell') {
      addMessage('System', `P${offer.from + 1} offers to SELL ${tile.name} to P${offer.to + 1} for ${offer.priceFC} FC`);
    } else {
      addMessage('System', `P${offer.from + 1} offers to BUY ${tile.name} from P${offer.to + 1} for ${offer.priceFC} FC`);
    }

    setTradeOpen(false);
  };

  const removeOffer = (id) => setTradeOffers((prev) => prev.filter((o) => o.id !== id));

  const acceptOffer = (id) => {
    const offer = tradeOffers.find((o) => o.id === id);
    if (!offer) return;

    if (activePlayer !== offer.to) return addMessage('System', 'Accept offers only on your turn.');

    const tile = TILES[offer.tileId];
    const currentOwner = ownership[offer.tileId];

    const seller = offer.type === 'sell' ? offer.from : offer.to;
    const buyer = offer.type === 'sell' ? offer.to : offer.from;

    if (currentOwner !== seller) {
      addMessage('System', `Offer invalid: tile owner changed for ${tile.name}`);
      removeOffer(id);
      return;
    }

    if ((balances[buyer] ?? 0) < offer.priceFC) {
      addMessage('System', `Deal failed: P${buyer + 1} has not enough FC`);
      return;
    }

    setBalances((prev) => {
      const next = [...prev];
      next[buyer] -= offer.priceFC;
      next[seller] += offer.priceFC;
      return next;
    });

    setOwnership((prev) => ({ ...prev, [offer.tileId]: buyer }));

    addMessage('System', `Deal: ${tile.name} P${seller + 1} → P${buyer + 1} for ${offer.priceFC} FC`);

    removeOffer(id);
    setActivePlayer((p) => (p + 1) % playersCount);
  };

  const declineOffer = (id) => {
    const offer = tradeOffers.find((o) => o.id === id);
    if (!offer) return;

    if (activePlayer !== offer.to) return addMessage('System', 'Decline offers only on your turn.');

    addMessage('System', `Offer declined by P${offer.to + 1}`);
    removeOffer(id);
    setActivePlayer((p) => (p + 1) % playersCount);
  };

  // ===== CHAT AUTO SCROLL =====
  useEffect(() => {
    const el = chatListRef.current;
    if (!el) return;
    if (shouldStickToBottomRef.current) el.scrollTop = el.scrollHeight;
  }, [messages]);

  return (
    <div className="board-layout">
      <div className="monopoly-wrapper">
        <div className="monopoly-board">

          {/* --- CENTER --- */}
          <div className="board-center">
            <div className="center-logo">
              <h1 className="flare-title">FLAREPOLY</h1>
              <p className="flare-subtitle">REAL-TIME CRYPTO MONOPOLY</p>
            </div>

            <div className="game-controls">
              <div className="dice-section">
                <div className="dice-display">🎲 {dice[0]} : {dice[1]}</div>

                <button
                  className="roll-btn"
                  onClick={handleRoll}
                  disabled={!!buyPrompt || tradeOpen || incomingOffersForActive.length > 0}
                >
                  {buyPrompt || tradeOpen
                    ? 'WAIT...'
                    : incomingOffersForActive.length > 0
                      ? 'OFFERS...'
                      : 'ROLL DICE'}
                </button>
              </div>

              <div className="chat-box">
                <div
                  className="chat-messages"
                  ref={chatListRef}
                  onScroll={() => {
                    const el = chatListRef.current;
                    if (!el) return;
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

          {/* --- TILES --- */}
          {TILES.map((tile) => {
            const playersHere = byTile[tile.id] || [];
            const gradient = buildConicGradient(playersHere);
            const activeHere = playersHere.includes(activePlayer);
            const activeColor = activeHere ? PLAYER_COLORS[activePlayer] : 'transparent';

            const ownerIdx = ownership[tile.id];
            const ownerColor = ownerIdx != null ? PLAYER_COLORS[ownerIdx] : null;

            return (
              <div
                key={tile.id}
                className={`tile ${tile.type} ${ownerIdx != null ? 'owned' : ''}`}
                style={getPositionStyle(tile.id)}
                data-owner={ownerIdx != null ? `p${ownerIdx + 1}` : ''}
              >
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
                  <div className="color-bar" style={{ backgroundColor: FAMILY_COLORS[tile.family] }} />
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

                      <div className="tile-name owned-name" data-owner={ownerIdx != null ? `p${ownerIdx + 1}` : ''}>
                        {tile.name}
                      </div>

                      {ownerIdx != null && <div className="owner-badge">P{ownerIdx + 1}</div>}

                      {tile.price != null && <div className="tile-price">${tile.price}</div>}
                    </>
                  ) : (
                    <>
                      <div className="tile-name">{tile.name}</div>
                      {tile.price != null && <div className="tile-price">${tile.price}</div>}
                    </>
                  )}
                </div>

                <div className="tile-id">{tile.id}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* --- RIGHT PANEL --- */}
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
              <div className="wallet-chip wallet-chip-coins">
                <img className="flare-coin-icon" src={`${base}images/FLARE.png`} alt="FLARE" loading="lazy" />
                {balances[idx]} FC
              </div>
            </div>
          </div>
        ))}

        <div className="wallet-actions">
          <button className="buy-btn secondary" onClick={openTradeSell}>SELL STREET</button>
          <button className="buy-btn secondary" onClick={openTradeBuy}>BUY STREET</button>
        </div>

        <div className="wallet-offers">
          <div className="wallets-title">INCOMING OFFERS (P{activePlayer + 1})</div>

          {incomingOffersForActive.length === 0 ? (
            <div className="offers-empty">No offers</div>
          ) : (
            incomingOffersForActive.slice(0, 6).map((o) => {
              const tile = TILES[o.tileId];
              return (
                <div key={o.id} className="offer-card">
                  <div className="offer-top">
                    <div className={`offer-type offer-type-${o.type}`}>{o.type.toUpperCase()}</div>
                    <div className="offer-text">
                      <span className={`offer-from p${o.from + 1}`}>P{o.from + 1}</span>{' '}
                      {o.type === 'sell' ? 'sells' : 'buys'}{' '}
                      <span className="offer-tile">{tile?.name}</span>
                    </div>
                  </div>

                  <div className="offer-bottom">
                    <div className="offer-price">
                      <img className="flare-coin-icon" src={`${base}images/FLARE.png`} alt="FLARE" loading="lazy" />
                      {o.priceFC} FC
                    </div>

                    <div className="offer-actions">
                      <button className="buy-btn secondary" onClick={() => declineOffer(o.id)}>DECLINE</button>
                      <button className="buy-btn primary" onClick={() => acceptOffer(o.id)}>ACCEPT</button>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        <div className="wallets-hint">
          Офферы принимаются/отклоняются только в свой ход. Сделка: улица ↔ FC.
        </div>
      </aside>

      {/* --- MODAL: BUY ON LANDING --- */}
      {buyPrompt && (() => {
        const tile = TILES[buyPrompt.tileId];
        const pIdx = buyPrompt.playerIndex;

        return (
          <div className="buy-modal-backdrop" onClick={handleSkipBuy}>
            <div className="buy-modal" onClick={(e) => e.stopPropagation()}>
              <div className="buy-modal-header">
                <div className="buy-modal-title">Buy asset?</div>
                <button className="buy-modal-x" onClick={handleSkipBuy}>✕</button>
              </div>

              <div className="buy-modal-body">
                <div className="buy-asset-row">
                  <div className="buy-asset-icon">
                    <img src={getTokenIconSrc(tile)} alt={tile.name} />
                  </div>
                  <div className="buy-asset-meta">
                    <div className="buy-asset-name"> {tile.name} </div>
                    <div className="buy-asset-sub">Player P{pIdx + 1} can buy this tile</div>
                  </div>
                </div>

                <div className="buy-price">
                  Price: <span className="buy-price-num">${tile.price}</span>
                </div>
              </div>

              <div className="buy-modal-actions">
                <button className="buy-btn secondary" onClick={handleSkipBuy}>SKIP</button>
                <button className="buy-btn primary" onClick={handleBuy}>BUY</button>
              </div>
            </div>
          </div>
        );
      })()}

      {/* --- MODAL: CREATE STREET OFFER --- */}
      {tradeOpen && (() => {
        const sellMode = tradeForm.mode === 'sell';
        const selectableTiles = sellMode ? myOwnedTiles : otherOwnedTiles;

        const tile = tradeForm.tileId != null ? TILES[tradeForm.tileId] : null;
        const inferredOwner = tradeForm.tileId != null ? ownership[tradeForm.tileId] : null;
        const buyTarget = inferredOwner != null ? inferredOwner : tradeForm.target;

        return (
          <div className="buy-modal-backdrop" onClick={() => setTradeOpen(false)}>
            <div className="buy-modal" onClick={(e) => e.stopPropagation()}>
              <div className="buy-modal-header">
                <div className="buy-modal-title">{sellMode ? 'Sell your street' : 'Offer to buy a street'}</div>
                <button className="buy-modal-x" onClick={() => setTradeOpen(false)}>✕</button>
              </div>

              <div className="buy-modal-body">
                <div className="trade-tabs">
                  <button className={`trade-tab ${sellMode ? 'active' : ''}`} onClick={() => setTradeMode('sell')}>SELL</button>
                  <button className={`trade-tab ${!sellMode ? 'active' : ''}`} onClick={() => setTradeMode('buy')}>BUY</button>
                </div>

                <div className="trade-row">
                  <div className="trade-label">Tile</div>
                  <select
                    className="trade-select"
                    value={tradeForm.tileId ?? ''}
                    onChange={(e) => onTradeTileChange(e.target.value)}
                  >
                    <option value="" disabled>
                      {selectableTiles.length ? 'Select a tile' : (sellMode ? 'You own no streets' : 'No streets to buy')}
                    </option>
                    {selectableTiles.map((tid) => (
                      <option key={tid} value={tid}>
                        #{tid} — {TILES[tid]?.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="trade-row">
                  <div className="trade-label">{sellMode ? 'Sell to' : 'Owner'}</div>

                  <select
                    className="trade-select"
                    value={sellMode ? tradeForm.target : buyTarget}
                    disabled={!sellMode}
                    onChange={(e) => setTradeForm((f) => ({ ...f, target: Number(e.target.value) }))}
                  >
                    {Array.from({ length: playersCount }, (_, i) => i)
                      .filter((i) => i !== activePlayer)
                      .map((i) => (
                        <option key={i} value={i}>PLAYER {i + 1}</option>
                      ))}
                  </select>
                </div>

                <div className="trade-row">
                  <div className="trade-label">Price (FC)</div>
                  <input
                    className="trade-input"
                    type="number"
                    min="1"
                    step="1"
                    value={tradeForm.priceFC}
                    onChange={(e) => setTradeForm((f) => ({ ...f, priceFC: e.target.value }))}
                  />
                </div>

                <div className="trade-summary">
                  <div className="trade-summary-balance">
                    Your balance: <span className="trade-balance-num">{balances[activePlayer]} FC</span>
                  </div>

                  {tile && (
                    <div className="trade-summary-tile">
                      <div className="trade-summary-icon">
                        <img src={getTokenIconSrc(tile)} alt={tile.name} />
                      </div>
                      <div className="trade-summary-meta">
                        <div className="trade-summary-name">{tile.name}</div>
                        <div className="trade-summary-sub">
                          {sellMode
                            ? `Offer: sell to P${tradeForm.target + 1}`
                            : `Offer: buy from P${(ownership[tradeForm.tileId] ?? tradeForm.target) + 1}`}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div className="buy-modal-actions">
                <button className="buy-btn secondary" onClick={() => setTradeOpen(false)}>CANCEL</button>
                <button
                  className="buy-btn primary"
                  onClick={createTradeOffer}
                  disabled={!tradeForm.tileId && tradeForm.tileId !== 0}
                >
                  SEND OFFER
                </button>
              </div>
            </div>
          </div>
        );
      })()}
    </div>
  );
};

export default Board;
