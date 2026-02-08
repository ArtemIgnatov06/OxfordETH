// src/App.jsx
import { useState } from "react";
import Board from "./components/Board/Board";
import "./App.css";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";


async function getActionMessage(playerIndex, action, params = "") {
  const res = await fetch(
    `${API}/action_message?playerIndex=${playerIndex}&action=${encodeURIComponent(
      action
    )}&params=${encodeURIComponent(params)}`
  );
  if (!res.ok) throw new Error("Failed to fetch action message");
  return res.json();
}

async function personalSign(message, address) {
  return window.ethereum.request({
    method: "personal_sign",
    params: [message, address],
  });
}

async function linkPlayerWallet(playerIndex, address) {
  // Ask backend for CONNECT message
  const { message } = await getActionMessage(playerIndex, "CONNECT", `address=${address}`);

  // Sign
  const signature = await personalSign(message, address);

  // Register on backend
  const res = await fetch(`${API}/connect`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      playerIndex,
      expectedMessage: message,
      proof: { address, message, signature },
    }),
  });

  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`Backend connect failed: ${txt}`);
  }
}

function App() {
  // store wallet per player slot
  const [playerWallets, setPlayerWallets] = useState([null, null, null, null]);

  const connectAsPlayer = async (playerIndex) => {
    if (!window.ethereum) {
      alert("Please install MetaMask!");
      return;
    }

    try {
      // MetaMask: user must select/switch the account they want
      const accounts = await window.ethereum.request({
        method: "eth_requestAccounts",
      });
      const address = accounts[0];

      // block duplicates
      if (playerWallets.includes(address)) {
        alert("This wallet is already assigned to a player.");
        return;
      }

      await linkPlayerWallet(playerIndex, address);

      setPlayerWallets((prev) => {
        const next = [...prev];
        next[playerIndex] = address;
        return next;
      });
    } catch (e) {
      console.error(e);
      alert(e.message || "Failed to connect wallet");
    }
  };

  return (
    <div className="app-container">
      <div className="wallet-overlay">
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {[0, 1, 2, 3].map((i) => (
            <div key={i} style={{ display: "flex", gap: 8, alignItems: "center" }}>
              {!playerWallets[i] ? (
                <button className="connect-btn" onClick={() => connectAsPlayer(i)}>
                  CONNECT P{i + 1}
                </button>
              ) : (
                <div className="wallet-connected">
                  <span className="status-dot">🟢</span>
                  P{i + 1}: {playerWallets[i].slice(0, 6)}...{playerWallets[i].slice(-4)}
                </div>
              )}
            </div>
          ))}
        </div>

        <div style={{ marginTop: 8, fontSize: 12, opacity: 0.8 }}>
          Tip: In MetaMask, switch account before connecting the next player.
        </div>
      </div>

      <Board playerWallets={playerWallets} />
    </div>
  );
}

export default App;
