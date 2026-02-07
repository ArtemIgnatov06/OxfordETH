// src/components/Board/Board.jsx
import React, { useState } from 'react';
import './Board.css';
import { TILES, FAMILY_COLORS } from './BoardData';

const Board = () => {
  const [dice, setDice] = useState([1, 1]);
  const [chatMsg, setChatMsg] = useState("");
  const [messages, setMessages] = useState([
    { user: "System", text: "Welcome to FlarePoly Testnet!" }
  ]);

  const getPositionStyle = (index) => {
    let row, col;

    if (index === 0) { row = 7; col = 7; }               // START
    else if (index > 0 && index < 6) { row = 7; col = 7 - index; } // bottom row
    else if (index === 6) { row = 7; col = 1; }          // JAIL
    else if (index > 6 && index < 12) { row = 7 - (index - 6); col = 1; } // left col
    else if (index === 12) { row = 1; col = 1; }         // HODL
    else if (index > 12 && index < 18) { row = 1; col = 1 + (index - 12); } // top row
    else if (index === 18) { row = 1; col = 7; }         // GO TO JAIL
    else { row = 1 + (index - 18); col = 7; }            // right col

    return { gridRow: row, gridColumn: col };
  };

  const handleRoll = () => {
    const d1 = Math.floor(Math.random() * 6) + 1;
    const d2 = Math.floor(Math.random() * 6) + 1;
    setDice([d1, d2]);
    addMessage("Player", `Rolled ${d1 + d2} (${d1} + ${d2})`);
  };

  const addMessage = (user, text) => {
    setMessages(prev => [...prev.slice(-4), { user, text }]);
  };

  const handleChatSend = (e) => {
    if (e.key === 'Enter' && chatMsg) {
      addMessage("Me", chatMsg);
      setChatMsg("");
    }
  };

  // базовый путь (важно для деплоя не из корня)
  const base = import.meta.env.BASE_URL;

  // Иконки коинов из public/images/<NAME>.png
  const getTokenIconSrc = (tile) => `${base}images/${tile.name}.png`;

  return (
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
              <div className="chat-messages">
                {messages.map((m, i) => (
                  <div key={i}><strong>{m.user}:</strong> {m.text}</div>
                ))}
              </div>
              <input
                className="chat-input"
                placeholder="Type..."
                value={chatMsg}
                onChange={(e) => setChatMsg(e.target.value)}
                onKeyDown={handleChatSend}
              />
            </div>
          </div>
        </div>

        {/* --- ГЕНЕРАЦИЯ КЛЕТОК --- */}
        {TILES.map((tile) => (
          <div
            key={tile.id}
            className={`tile ${tile.type}`}
            style={getPositionStyle(tile.id)}
          >
            {/* цветная шапка для property */}
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
                    <img
                        className="corner-full-img"
                        src={`${base}images/GOTOJAIL.png`}
                        alt="GO TO JAIL"
                        loading="lazy"
                    />
                    <div className="corner-overlay">
                        <div className="corner-title-big"></div>
                    </div>
                    </div>
                ) : tile.subtype === 'jail' ? (
                    <div className="corner-full">
                    <img
                        className="corner-full-img"
                        src={`${base}images/JAIL.png`}
                        alt="JAIL"
                        loading="lazy"
                    />
                    <div className="corner-overlay">
                        <div className="corner-title-big"></div>
                    </div>
                    </div>
                ) : tile.subtype === 'go' ? (
                    <div className="corner-full">
                    <img
                        className="corner-full-img"
                        src={`${base}images/START.png`}
                        alt="START"
                        loading="lazy"
                    />
                    <div className="corner-overlay">
                        <div className="corner-title-big"></div>
                    </div>
                    </div>
                ) : tile.subtype === 'parking' ? (
                    <div className="corner-full">
                    <img
                        className="corner-full-img"
                        src={`${base}images/HODL.png`}
                        alt="HODL"
                        loading="lazy"
                    />
                    <div className="corner-overlay">
                        <div className="corner-title-big"></div>
                    </div>
                    </div>
                ) : (
                    <div className="corner-title">{tile.name}</div>
                )
                ) : tile.type === 'chance' ? (
                <div className="corner-full">
                    <img
                    className="corner-full-img"
                    src={`${base}images/CHANCE.png`}
                    alt="CHANCE"
                    loading="lazy"
                    />
                    <div className="corner-overlay">
                    <div className="corner-title-big"></div>
                    </div>
                </div>
                ) : tile.type === 'property' ? (

                // PROPERTY: иконка + название + цена
                <>
                  <div className="token-icon-wrap">
                    <img
                      className="token-icon"
                      src={getTokenIconSrc(tile)}
                      alt={tile.name}
                      loading="lazy"
                    />
                  </div>

                  <div className="tile-name">{tile.name}</div>
                  {tile.price != null && (
                    <div className="tile-price">${tile.price}</div>
                  )}
                </>
              ) : (
                // остальные (tax/action и т.п.)
                <>
                  <div className="tile-name">{tile.name}</div>
                  {tile.price != null && (
                    <div className="tile-price">${tile.price}</div>
                  )}
                </>
              )}
            </div>

            {/* debug id */}
            <div style={{ position: 'absolute', bottom: 1, right: 2, fontSize: 8, opacity: 0.3 }}>
              {tile.id}
            </div>
          </div>
        ))}

      </div>
    </div>
  );
};

export default Board;
