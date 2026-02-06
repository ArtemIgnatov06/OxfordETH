// src/App.jsx
import { useState } from 'react'
import Board from './components/Board/Board'
import './App.css'

function App() {
  const [walletAddress, setWalletAddress] = useState("");

  const connectWallet = async () => {
    if (window.ethereum) {
      try {
        const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
        setWalletAddress(accounts[0]);
      } catch (error) {
        console.error("Connection error:", error);
      }
    } else {
      alert("Please install Metamask to play FlarePoly!");
    }
  };

  return (
    <div className="app-container">
      
      {/* WALLET WIDGET (Top Right) */}
      <div className="wallet-overlay">
        {!walletAddress ? (
          <button className="connect-btn" onClick={connectWallet}>
            CONNECT WALLET
          </button>
        ) : (
          <div className="wallet-connected">
            <span className="status-dot">🟢</span> 
            {walletAddress.slice(0, 6)}...{walletAddress.slice(-4)}
          </div>
        )}
      </div>

      {/* GAME BOARD */}
      <Board />
      
    </div>
  )
}

export default App