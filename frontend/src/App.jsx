// src/App.jsx
import { useState } from 'react'
import './App.css' // Файл пустой, но пусть будет, пригодится для стилей

function App() {
  const [walletAddress, setWalletAddress] = useState("");

  // Функция подключения кошелька (заглушка)
  const connectWallet = async () => {
    if (window.ethereum) {
      try {
        const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
        setWalletAddress(accounts[0]);
      } catch (error) {
        console.error("Connection error:", error);
      }
    } else {
      alert("Donwload Metamask!");
    }
  };

  return (
    <div style={{ padding: "20px", textAlign: "center" }}>
      <h1>FlarePoly</h1>
      
      {/* Кнопка входа */}
      <div style={{ marginBottom: "20px" }}>
        {walletAddress ? (
          <p>Player: <strong>{walletAddress}</strong></p>
        ) : (
          <button onClick={connectWallet} style={{ padding: "10px 20px", fontSize: "16px" }}>
            Connect Wallet
          </button>
        )}
      </div>

      {/* Тут будет игровое поле */}
      <div style={{ border: "2px dashed gray", height: "400px", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <p>Here will be the gameboard (Board)</p>
      </div>
    </div>
  )
}

export default App