  // src/components/Board/Board.jsx
  import React, { useEffect, useMemo, useRef, useState } from 'react';
  import './Board.css';
  import { TILES, FAMILY_COLORS } from './BoardData';
  import ChanceModal from "../Chance/ChanceModal";

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  const FXRP_CONTRACT = import.meta.env.VITE_FXRP_CONTRACT; // ERC-20 FXRP token address

  // --- Metamask signing helpers ---
  const hasEthereum = () => typeof window !== 'undefined' && !!window.ethereum;

  const personalSign = async (message, address) => {
    return window.ethereum.request({
      method: 'personal_sign',
      params: [message, address],
    });
  };

  // --- ERC-20 transfer helpers (no ethers dependency) ---
  const pad32 = (hex) => hex.replace(/^0x/, '').padStart(64, '0');
  const encodeErc20TransferData = (to, amountRaw) => {
    // transfer(address,uint256) selector
    const selector = '0xa9059cbb';
    const toPadded = pad32(to);
    const amtHex = BigInt(amountRaw).toString(16);
    const amtPadded = amtHex.padStart(64, '0');
    return selector + toPadded + amtPadded;
  };

  const sendFxrpTransfer = async ({ from, to, amountRaw }) => {
    if (!hasEthereum()) throw new Error('MetaMask not found');
    if (!FXRP_CONTRACT) throw new Error('VITE_FXRP_CONTRACT is not set');

    // ensure wallet is connected
    await window.ethereum.request({ method: 'eth_requestAccounts' });

    const data = encodeErc20TransferData(to, amountRaw);

    const txParams = {
      from,
      to: FXRP_CONTRACT,
      value: '0x0',
      data,
    };

    const txHash = await window.ethereum.request({
      method: 'eth_sendTransaction',
      params: [txParams],
    });

    return txHash;
  };

  const getActionMessage = async (playerIndex, action, params = "") => {
    const res = await fetch(
      `${API_URL}/action_message?playerIndex=${playerIndex}&action=${encodeURIComponent(action)}&params=${encodeURIComponent(params)}`
    );
    if (!res.ok) {
      const txt = await res.text();
      throw new Error(`Failed to fetch action message: ${txt}`);
    }
    return res.json(); // { message }
  };

  // Build SigProof for ACTIVE player turn (backend requires active player to sign)
  const buildProofForActiveTurn = async (action, params = "") => {
    if (!hasEthereum()) throw new Error("MetaMask not found");

    // backend state tells who is active + which wallet is bound to that player
    const sRes = await fetch(`${API_URL}/state`);
    const state = await sRes.json();
    const p = state.activePlayer;
    const addr = state.playerWallets?.[p];

    if (!addr) {
      throw new Error(`Active player P${p + 1} has no connected wallet. Connect it first.`);
    }

    // ask backend for the exact message (includes nonce)
    const { message } = await getActionMessage(p, action, params);

    // sign it with the wallet that is connected for that player
    const signature = await personalSign(message, addr);

    return { address: addr, message, signature };
  };

  // API helper that supports signed actions
  const apiCall = async (endpoint, method = 'GET', body = null) => {
    try {
      const options = {
        method,
        headers: { 'Content-Type': 'application/json' },
      };
      if (body) options.body = JSON.stringify(body);

      const res = await fetch(`${API_URL}${endpoint}`, options);

      if (!res.ok) {
        // backend sometimes returns json, sometimes plain text
        let errText = '';
        try {
          const errJson = await res.json();
          errText = errJson?.detail || JSON.stringify(errJson);
        } catch {
          errText = await res.text();
        }
        throw new Error(errText || 'API Error');
      }

      // Some endpoints may return empty; but ours return json state
      try {
        return await res.json();
      } catch {
        return null;
      }
    } catch (e) {
      console.error("API Action Failed:", e);
      return null;
    }
  };

  const PLAYER_COLORS = ['#22c55e', '#3b82f6', '#a855f7', '#f97316'];

  const Board = () => {
    // === LOCAL UI STATE ===
    const [chatMsg, setChatMsg] = useState('');
    const [isRolling, setIsRolling] = useState(false);
    const chatListRef = useRef(null);
    const shouldStickToBottomRef = useRef(true);

    // === SERVER STATE ===
    const [gameState, setGameState] = useState(null);

    // Локальные позиции для анимации
    const [visualPlayerPos, setVisualPlayerPos] = useState([0, 0, 0, 0]);

    // Модалка трейдов
    const [tradeOpen, setTradeOpen] = useState(false);
    const [tradeForm, setTradeForm] = useState({
      mode: 'sell',
      tileId: null,
      target: 1,
      priceFC: 500,
    });

    const base = import.meta.env.BASE_URL;
    const getTokenIconSrc = (tile) => `${base}images/${tile.name}.png`;
    const flareIconSrc = `${base}images/FLARE.png`;

    const renderFlarePrice = (value) => {
      if (value == null) return null;
      return (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <img
            src={flareIconSrc}
            alt="FC"
            style={{ width: 14, height: 14, objectFit: 'contain', filter: 'drop-shadow(0 2px 6px rgba(0,0,0,0.35))' }}
            draggable="false"
          />
          <span>{value}</span>
        </span>
      );
    };

    // ===== CHANCE CARD UI =====
    const [chanceCard, setChanceCard] = useState(null); // { text, delta, key }
    const lastMsgCountRef = useRef(0);
    const closeChance = () => setChanceCard(null);

    // ===== GAME OVER / BANKRUPT UI =====
    const [winnerModalOpen, setWinnerModalOpen] = useState(false);
    const [bankruptModal, setBankruptModal] = useState(null); // { playerIndex }
    const lastEliminatedRef = useRef([false, false, false, false]);

    // === DATA FETCHING ===
    const fetchState = async () => {
      if (isRolling) return;
      try {
        const res = await fetch(`${API_URL}/state`);
        const data = await res.json();
        setGameState(data);
        if (!isRolling) setVisualPlayerPos(data.playerPos);
      } catch (e) {
        console.error("Error fetching state:", e);
      }
    };

    // Polling
    useEffect(() => {
      fetchState();
      const interval = setInterval(fetchState, 1000);
      return () => clearInterval(interval);
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isRolling]);

    // === DERIVED DATA ===
    const playersCount = gameState ? gameState.playerPos.length : 3;
    const activePlayer = gameState ? gameState.activePlayer : 0;
    const balances = gameState ? gameState.balances : [0, 0, 0, 0];
    const ownership = gameState ? gameState.ownership : {};
    const messages = gameState ? gameState.messages : [];
    const buyPrompt = gameState ? gameState.buyPrompt : null;
    const tradeOffers = gameState ? gameState.tradeOffers : [];
    const dice = gameState ? gameState.dice : [1, 1];

    // NEW from backend:
    const eliminated = gameState ? gameState.eliminated : [false, false, false, false];
    const gameOver = gameState ? gameState.gameOver : false;
    const winner = gameState ? gameState.winner : null;
    const skipTurns = gameState ? gameState.skipTurns : [0, 0, 0, 0];

    const playerWallets = gameState ? gameState.playerWallets : [null, null, null, null];
    const pendingSettlement = gameState ? gameState.pendingSettlement : null;

    const activeEliminated = !!eliminated?.[activePlayer];

    // ===== CHANCE: ловим новые NEWS сообщения и показываем карточку =====
    useEffect(() => {
      if (!gameState) return;

      const prevCount = lastMsgCountRef.current;
      const nextCount = messages.length;

      // При первом подключении синхронизируемся, чтобы не открыть модалки на "Welcome..."
      if (prevCount === 0 && nextCount > 0) {
        lastMsgCountRef.current = nextCount;
        return;
      }

      if (nextCount > prevCount) {
        const newSlice = messages.slice(prevCount);
        const newsMsg = [...newSlice].reverse().find((m) => m.type === "news");

        if (newsMsg) {
          setChanceCard({
            text: newsMsg.text,
            delta: typeof newsMsg.delta === "number" ? newsMsg.delta : null,
            key: Date.now(),
          });
        }
      }

      lastMsgCountRef.current = nextCount;
    }, [messages, gameState]);

    // ===== BANKRUPT / GAME OVER реакция (из backend eliminated/gameOver/winner) =====
    useEffect(() => {
      if (!gameState) return;

      // 1) банкрот конкретного игрока
      const prev = lastEliminatedRef.current || [];
      const now = eliminated || [];
      for (let i = 0; i < now.length; i++) {
        if (!prev[i] && now[i]) {
          setBankruptModal({ playerIndex: i });
          break;
        }
      }
      lastEliminatedRef.current = [...now];

      // 2) окончание игры
      if (gameOver) {
        setWinnerModalOpen(true);
        setTradeOpen(false);
        setChanceCard(null);
      }
    }, [gameState, eliminated, gameOver]);

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

    // === HELPERS ===
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

    const byTile = useMemo(() => {
      const map = {};
      for (let p = 0; p < playersCount; p++) {
        const tileId = visualPlayerPos[p];
        (map[tileId] ||= []).push(p);
      }
      return map;
    }, [visualPlayerPos, playersCount]);

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

    // === ANIMATION LOGIC ===
    const animateMove = async (playerIndex, startPos, steps) => {
      return new Promise((resolve) => {
        let currentStep = 0;

        const tick = () => {
          currentStep++;
          setVisualPlayerPos((prev) => {
            const next = [...prev];
            next[playerIndex] = (startPos + currentStep) % TILES.length;
            return next;
          });

          if (currentStep < steps) {
            setTimeout(tick, 120);
          } else {
            resolve();
          }
        };

        tick();
      });
    };

    // === SIGNED ACTION WRAPPER ===
    const signedAction = async (action, params, endpoint, bodyExtra = null) => {
      try {
        const proof = await buildProofForActiveTurn(action, params);
        const payload = bodyExtra ? { ...bodyExtra, proof } : { proof };
        const newState = await apiCall(endpoint, 'POST', payload);
        if (newState) setGameState(newState);
        return newState;
      } catch (e) {
        console.error(e);
        alert(e.message || 'Action failed');
        return null;
      }
    };

    // === ACTIONS ===
    const handleRoll = async () => {
      if (gameOver) return;
      if (activeEliminated) return;
      if (isRolling || buyPrompt || tradeOpen || incomingOffersForActive.length > 0 || !!chanceCard) return;
      if (pendingSettlement) {
        alert('Pending on-chain settlement. Finish /settle first.');
        return;
      }

      setIsRolling(true);

      const newState = await signedAction('ROLL', '', '/roll');
      if (newState) {
        const moverIdx = activePlayer;
        const oldPos = visualPlayerPos[moverIdx];
        const newPos = newState.playerPos[moverIdx];

        let steps = newPos - oldPos;
        if (steps < 0) steps += TILES.length;

        const stepsToAnimate = steps === 0 ? 0 : steps;
        if (stepsToAnimate > 0) await animateMove(moverIdx, oldPos, stepsToAnimate);
      }

      setIsRolling(false);
    };

    const handleBuy = async () => {
      if (!buyPrompt || gameOver || activeEliminated) return;
      if (pendingSettlement) {
        alert('Pending on-chain settlement. Finish /settle first.');
        return;
      }

      // backend expects BUY signed params: tileId=<id>
      await signedAction('BUY', `tileId=${buyPrompt.tileId}`, '/buy', { tileId: buyPrompt.tileId });
    };
    const handlePayAndSettle = async () => {
      if (!pendingSettlement) return;
      if (gameOver || activeEliminated) return;

      // pendingSettlement schema from backend: { from, to, amountRaw, ... }
      const { from, to, amountRaw } = pendingSettlement;

      // Basic sanity
      if (!from || !to || amountRaw == null) {
        alert('Invalid pending settlement payload');
        return;
      }

      try {
        // 1) Send FXRP ERC-20 transfer (MetaMask popup)
        const txHash = await sendFxrpTransfer({ from, to, amountRaw });

        // 2) Submit tx hash to backend settlement (signed by active player)
        await signedAction('SETTLE', `tx=${txHash}`, '/settle', { txHash });
      } catch (e) {
        console.error(e);
        alert(e.message || 'Payment/settlement failed');
      }
    };



    const handleSkipBuy = async () => {
      if (gameOver || activeEliminated) return;
      if (!buyPrompt) return;

      await signedAction('SKIP_BUY', `tileId=${buyPrompt.tileId}`, '/skip_buy');
    };

    const handleReset = async () => {
      // reset is usually admin/debug — in many backends it is unsigned.
      // If your backend requires signature for RESET, change to signedAction('RESET','', '/reset')
      const newState = await apiCall('/reset', 'POST');
      if (newState) {
        setGameState(newState);
        setVisualPlayerPos([0, 0, 0, 0]);
        setChanceCard(null);
        setWinnerModalOpen(false);
        setBankruptModal(null);
        lastMsgCountRef.current = 0;
        lastEliminatedRef.current = [false, false, false, false];
      }
    };

    // --- Trade Logic ---
    const openTradeSell = () => {
      if (gameOver || activeEliminated) return;
      if (pendingSettlement) return;
      const tileId = myOwnedTiles[0] ?? null;
      const target = (activePlayer + 1) % playersCount;
      setTradeForm({ mode: 'sell', tileId, target, priceFC: 500 });
      setTradeOpen(true);
    };

    const openTradeBuy = () => {
      if (gameOver || activeEliminated) return;
      if (pendingSettlement) return;
      const tileId = otherOwnedTiles[0] ?? null;
      const owner = tileId != null ? ownership[tileId] : null;
      setTradeForm({
        mode: 'buy',
        tileId,
        target: owner ?? ((activePlayer + 1) % playersCount),
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

    const createTradeOffer = async () => {
      if (gameOver || activeEliminated) return;
      if (pendingSettlement) {
        alert('Pending on-chain settlement. Finish /settle first.');
        return;
      }

      const priceFC = Math.max(0, Math.floor(Number(tradeForm.priceFC) || 0));
      const tileId = tradeForm.tileId != null ? Number(tradeForm.tileId) : null;
      const target = Number(tradeForm.target);

      if (tileId == null) return;

      const offerType = tradeForm.mode; // "sell" | "buy"

      const params = `type=${offerType}&to=${target}&tileId=${tileId}&priceFC=${priceFC}`;

      await signedAction('CREATE_OFFER', params, '/offers', {
        type: offerType,
        to: target,
        tileId,
        priceFC,
      });

      setTradeOpen(false);
    };
    
    const acceptOffer = async (id) => {
      if (gameOver || activeEliminated) return;
      if (pendingSettlement) {
        alert('Pending on-chain settlement. Finish /settle first.');
        return;
      }

      await signedAction('ACCEPT_OFFER', `offerId=${id}`, `/offers/${id}/accept`);
    };

    const declineOffer = async (id) => {
      if (gameOver || activeEliminated) return;
      if (pendingSettlement) {
        alert('Pending on-chain settlement. Finish /settle first.');
        return;
      }

      await signedAction('DECLINE_OFFER', `offerId=${id}`, `/offers/${id}/decline`);
    };

    const handleSendChat = async () => {
      if (!chatMsg.trim()) return;
      if (gameOver) return;

      const textToSend = chatMsg;
      setChatMsg('');

      // Chat should be signed by ACTIVE player too
      const newState = await signedAction('CHAT', `text=${encodeURIComponent(textToSend)}`, '/chat', { text: textToSend });
      if (!newState) {
        // if failed, restore input so user doesn't lose text
        setChatMsg(textToSend);
      }
    };

    // --- Chat Auto Scroll ---
    useEffect(() => {
      const el = chatListRef.current;
      if (!el) return;
      if (shouldStickToBottomRef.current) el.scrollTop = el.scrollHeight;
    }, [messages]);

    // === RENDER LOADING ===
    if (!gameState) {
      return <div className="board-loading">Connecting to server... (Run backend on port 8000)</div>;
    }

    // === RENDER MAIN ===
    return (
      <div className="board-layout">
        <div className="monopoly-wrapper">
          <div className="monopoly-board">

            {/* --- CENTER --- */}
            <div className="board-center">
              <div className="center-logo">
                <img
                  src={`${base}FLAREPOLY.svg`}
                  alt="FlarePoly"
                  className="flare-logo"
                  draggable="false"
                />
                <button onClick={handleReset} style={{ opacity: 0.3, fontSize: '10px' }}>
                  RESET GAME
                </button>
              </div>

              <div className="game-controls">
                <div className="dice-section">
                  <div className="dice-display">🎲 {dice[0]} : {dice[1]}</div>

                  <button
                    className="roll-btn"
                    onClick={handleRoll}
                    disabled={
                      gameOver ||
                      activeEliminated ||
                      isRolling ||
                      !!buyPrompt ||
                      tradeOpen ||
                      incomingOffersForActive.length > 0 ||
                      !!chanceCard ||
                      !!pendingSettlement
                    }
                    title={pendingSettlement ? 'Pending on-chain settlement' : ''}
                  >
                    {gameOver
                      ? 'GAME OVER'
                      : activeEliminated
                        ? `P${activePlayer + 1} OUT`
                        : isRolling
                          ? 'MOVING...'
                          : buyPrompt || tradeOpen
                            ? 'WAIT...'
                            : incomingOffersForActive.length > 0
                              ? 'OFFERS...'
                              : !!chanceCard
                                ? 'CHANCE...'
                                : pendingSettlement
                                  ? 'SETTLE...'
                                  : skipTurns?.[activePlayer] > 0
                                    ? `PRISON (${skipTurns[activePlayer]})`
                                    : `P${activePlayer + 1} ROLL`}
                  </button>

                  {/* tiny helper: show which wallet is bound to active player */}
                  <div style={{ marginTop: 6, fontSize: 11, opacity: 0.75 }}>
                    Active wallet:{' '}
                    {playerWallets?.[activePlayer]
                      ? `${playerWallets[activePlayer].slice(0, 6)}...${playerWallets[activePlayer].slice(-4)}`
                      : 'not connected'}
                  </div>

                  {pendingSettlement && (
                    <div style={{ marginTop: 6, fontSize: 11, opacity: 0.85 }}>
                      Settlement required: {pendingSettlement.kind} — tile #{pendingSettlement.tileId}
                    </div>
                  )}
                  
              {pendingSettlement && (
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    gap: 12,
                    padding: 12,
                    margin: "10px 0",
                    border: "1px solid rgba(255,255,255,0.15)",
                    borderRadius: 10,
                    background: "rgba(255,255,255,0.06)",
                  }}
                >
                  <div>
                    <b>On-chain payment pending.</b> Send FXRP then settle to continue.
                  </div>
                  <button onClick={handlePayAndSettle}>PAY &amp; SETTLE</button>
                </div>
              )}
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
                      <div key={i} className="chat-msg-row">
                        <span
                          className="chat-user"
                          style={{
                            color: m.user.startsWith('P') && !isNaN(parseInt(m.user.slice(1)))
                              ? PLAYER_COLORS[parseInt(m.user.slice(1)) - 1]
                              : m.user === "News"
                                ? "#a5b4fc"
                                : "#888"
                          }}
                        >
                          {m.user}:
                        </span>
                        <span className="chat-text">{m.text}</span>
                      </div>
                    ))}
                  </div>

                  <div className="chat-input-wrapper">
                    <input
                      className="chat-input"
                      placeholder={`Say as Active Player (P${activePlayer + 1})...`}
                      value={chatMsg}
                      onChange={(e) => setChatMsg(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleSendChat();
                      }}
                      disabled={!!pendingSettlement}
                    />
                    <button className="chat-send-btn" onClick={handleSendChat} disabled={!!pendingSettlement}>➤</button>
                  </div>
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
                        <div className="corner-full"><img className="corner-full-img" src={`${base}images/SYSTEMBUG.png`} alt="BUG" /></div>
                      ) : tile.subtype === 'jail' ? (
                        <div className="corner-full"><img className="corner-full-img" src={`${base}images/ACCOUNTBLOCKED.png`} alt="BLOCKED" /></div>
                      ) : tile.subtype === 'go' ? (
                        <div className="corner-full"><img className="corner-full-img" src={`${base}images/START.png`} alt="START" /></div>
                      ) : (
                        <div className="corner-full"><img className="corner-full-img" src={`${base}images/SYSTEMDOWN.png`} alt="DOWN" /></div>
                      )
                    ) : tile.type === 'chance' ? (
                      <div className="corner-full"><img className="corner-full-img" src={`${base}images/CHANCE.png`} alt="CHANCE" /></div>
                    ) : tile.type === 'property' ? (
                      <>
                        <div className="token-icon-wrap">
                          <img className="token-icon" src={getTokenIconSrc(tile)} alt={tile.name} />
                        </div>
                        <div className="tile-name owned-name" data-owner={ownerIdx != null ? `p${ownerIdx + 1}` : ''}>
                          {tile.name}
                        </div>
                        {ownerIdx != null && <div className="owner-badge">P{ownerIdx + 1}</div>}
                        {tile.price != null && (
                          <div className="tile-price">
                            {renderFlarePrice(tile.price)} <span style={{ opacity: 0.8 }}>FC</span>
                          </div>
                        )}
                      </>
                    ) : (
                      <>
                        <div className="tile-name">{tile.name}</div>
                        {tile.price != null && (
                          <div className="tile-price">
                            {renderFlarePrice(tile.price)} <span style={{ opacity: 0.8 }}>FC</span>
                          </div>
                        )}
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

          {gameState.balances.map((bal, idx) => {
            const isActive = idx === activePlayer;
            const isOut = !!eliminated?.[idx];
            const prisonSkips = skipTurns?.[idx] || 0;
            const inPrison = prisonSkips > 0;

            return (
              <div
                key={idx}
                className={`wallet-card ${isActive ? 'active' : ''}`}
                style={{
                  opacity: isOut ? 0.45 : 1,
                  filter: isOut ? 'grayscale(0.8)' : 'none',
                }}
                title={isOut ? 'BANKRUPT' : ''}
              >
                <div className="wallet-left">
                  <div className="player-dot" style={{ background: PLAYER_COLORS[idx] }} />
                  <div className="wallet-meta">
                    <div className="wallet-name">
                      PLAYER {idx + 1} {isOut ? '— BANKRUPT' : ''}
                    </div>
                    <div className="wallet-addr">
                      {playerWallets?.[idx]
                        ? `${playerWallets[idx].slice(0, 6)}...${playerWallets[idx].slice(-4)}`
                        : `0xWallet...${idx}`}
                    </div>
                  </div>
                </div>

                <div className="wallet-right">
                  <div className="wallet-chip">POS {visualPlayerPos[idx]}</div>

                  {inPrison && (
                    <div className="wallet-chip" style={{ fontWeight: 900 }}>
                      PRISON {prisonSkips}
                    </div>
                  )}

                  <div className="wallet-chip wallet-chip-coins">
                    <img className="flare-coin-icon" src={flareIconSrc} alt="FC" />
                    {bal} FC
                  </div>
                </div>
              </div>
            );
          })}

          <div className="wallet-actions">
            <button
              className="buy-btn secondary"
              onClick={openTradeSell}
              disabled={tradeOpen || gameOver || activeEliminated || !!pendingSettlement}
            >
              SELL CURRENCY
            </button>
            <button
              className="buy-btn secondary"
              onClick={openTradeBuy}
              disabled={tradeOpen || gameOver || activeEliminated || !!pendingSettlement}
            >
              BUY CURRENCY
            </button>
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
                      <div className="offer-price">{o.priceFC} FC</div>
                      <div className="offer-actions">
                        <button className="buy-btn secondary" onClick={() => declineOffer(o.id)} disabled={gameOver || activeEliminated || !!pendingSettlement}>DECLINE</button>
                        <button className="buy-btn primary" onClick={() => acceptOffer(o.id)} disabled={gameOver || activeEliminated || !!pendingSettlement}>ACCEPT</button>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
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
                    Price:{' '}
                    <span className="buy-price-num">
                      {renderFlarePrice(tile.price)} <span style={{ opacity: 0.8 }}>FC</span>
                    </span>
                  </div>
                  {pendingSettlement && (
                    <div style={{ marginTop: 10, fontSize: 12, opacity: 0.85 }}>
                      Payment required. After FXRP transfer, call <b>/settle</b> with tx hash.
                    </div>
                  )}
                </div>

                <div className="buy-modal-actions">
                  <button className="buy-btn secondary" onClick={handleSkipBuy} disabled={!!pendingSettlement}>SKIP</button>
                  {!pendingSettlement ? (
                    <button className="buy-btn primary" onClick={handleBuy}>BUY</button>
                  ) : (
                    <button className="buy-btn primary" onClick={handlePayAndSettle}>PAY &amp; SETTLE</button>
                  )}
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
                    disabled={(!tradeForm.tileId && tradeForm.tileId !== 0) || !!pendingSettlement}
                  >
                    SEND OFFER
                  </button>
                </div>
              </div>
            </div>
          );
        })()}

        {/* --- MODAL: CHANCE CARD --- */}
        <ChanceModal
          open={!!chanceCard}
          text={chanceCard?.text || ""}
          delta={chanceCard?.delta}
          onClose={closeChance}
        />

        {/* --- MODAL: BANKRUPT (конкретный игрок) --- */}
        {bankruptModal && (
          <div className="buy-modal-backdrop" onClick={() => setBankruptModal(null)}>
            <div className="buy-modal" onClick={(e) => e.stopPropagation()}>
              <div className="buy-modal-header">
                <div className="buy-modal-title">Game Over (Player)</div>
                <button className="buy-modal-x" onClick={() => setBankruptModal(null)}>✕</button>
              </div>
              <div className="buy-modal-body">
                <div style={{ color: '#e2e8f0', fontWeight: 900, fontSize: 14 }}>
                  P{bankruptModal.playerIndex + 1} is BANKRUPT 💀
                </div>
                <div style={{ marginTop: 8, color: '#94a3b8', fontSize: 12 }}>
                  Этот игрок вылетел из игры. Ходы продолжатся для остальных.
                </div>
              </div>
              <div className="buy-modal-actions">
                <button className="buy-btn primary" onClick={() => setBankruptModal(null)}>
                  OK
                </button>
              </div>
            </div>
          </div>
        )}

        {/* --- MODAL: GAME OVER (остался один) --- */}
        {winnerModalOpen && gameOver && (
          <div className="buy-modal-backdrop" onClick={() => setWinnerModalOpen(false)}>
            <div className="buy-modal" onClick={(e) => e.stopPropagation()}>
              <div className="buy-modal-header">
                <div className="buy-modal-title">GAME OVER</div>
                <button className="buy-modal-x" onClick={() => setWinnerModalOpen(false)}>✕</button>
              </div>
              <div className="buy-modal-body">
                <div style={{ color: '#e2e8f0', fontWeight: 900, fontSize: 16 }}>
                  Winner: P{(winner ?? 0) + 1} 🎉
                </div>
                <div style={{ marginTop: 8, color: '#94a3b8', fontSize: 12 }}>
                  Игра окончена — в живых остался только один игрок.
                </div>
              </div>
              <div className="buy-modal-actions">
                <button className="buy-btn secondary" onClick={() => setWinnerModalOpen(false)}>
                  CLOSE
                </button>
                <button className="buy-btn primary" onClick={handleReset}>
                  NEW GAME
                </button>
              </div>
            </div>
          </div>
        )}

      </div>
    );
  };

  export default Board;
