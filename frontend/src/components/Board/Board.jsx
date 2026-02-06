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

  // Функция для определения Grid Area (CSS Grid)
  // Индекс 0..23 мапится на координаты сетки 7x7
  const getPositionStyle = (index) => {
    // 0 = Bottom Right (7, 7)
    // 1-5 = Bottom Row (Moving Left)
    // 6 = Bottom Left (7, 1)
    // ... и т.д.
    
    let row, col;

    if (index === 0) { row = 7; col = 7; } // START
    else if (index > 0 && index < 6) { row = 7; col = 7 - index; } // BOTTOM
    else if (index === 6) { row = 7; col = 1; } // JAIL
    else if (index > 6 && index < 12) { row = 7 - (index - 6); col = 1; } // LEFT
    else if (index === 12) { row = 1; col = 1; } // PARKING
    else if (index > 12 && index < 18) { row = 1; col = 1 + (index - 12); } // TOP
    else if (index === 18) { row = 1; col = 7; } // GO TO JAIL
    else { row = 1 + (index - 18); col = 7; } // RIGHT

    return { gridRow: row, gridColumn: col };
  };

  const handleRoll = () => {
    // Эмуляция Flare RNG
    const d1 = Math.floor(Math.random() * 6) + 1;
    const d2 = Math.floor(Math.random() * 6) + 1;
    setDice([d1, d2]);
    addMessage("Player", `Rolled ${d1 + d2} (${d1} + ${d2})`);
  };

  const addMessage = (user, text) => {
    setMessages(prev => [...prev.slice(-4), { user, text }]); // Храним только последние 5
  };

  const handleChatSend = (e) => {
    if (e.key === 'Enter' && chatMsg) {
      addMessage("Me", chatMsg);
      setChatMsg("");
    }
  };

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
            {/* Если это актив (property), рисуем цветную шапку */}
            {tile.type === 'property' && (
              <div 
                className="color-bar" 
                style={{ backgroundColor: FAMILY_COLORS[tile.family] }}
              />
            )}

            <div className="tile-content">
              {tile.type === 'corner' ? (
                // УГЛОВЫЕ КЛЕТКИ
                <div style={{fontSize: '10px'}}>{tile.name}</div>
              ) : tile.type === 'chance' ? (
                // ШАНС
                <div style={{color: '#a5b4fc'}}>❓<br/>CHANCE</div>
              ) : (
                // ОБЫЧНЫЕ КЛЕТКИ
                <>
                  <div className="tile-name">{tile.name}</div>
                  {tile.price && (
                    <div className="tile-price">${tile.price}</div>
                  )}
                </>
              )}
            </div>
            
            {/* Индекс для дебага (можно убрать) */}
            <div style={{position:'absolute', bottom:1, right:2, fontSize:8, opacity:0.3}}>
              {tile.id}
            </div>
          </div>
        ))}

      </div>
    </div>
  );
};

export default Board;