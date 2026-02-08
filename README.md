https://oxfordeth-production.up.railway.app/



## Flare Protocols

This project integrates multiple Flare protocols to ensure fairness, security, and on-chain verifiability of core game mechanics.

Dice rolls are generated using **Flare’s Secure Random Number (SRN)** via a custom `SecureDiceRoller` smart contract deployed on the **Coston2 testnet**. Initially, SRN was difficult to understand, particularly the concept of randomness being updated in fixed rounds (approximately every 90 seconds), which means it is not always immediately available. This required additional backend logic to wait and retry when SRN was between rounds. To prevent predictability or manipulation, each roll combines the SRN output with a unique public `requestId`. Once deployed, the contract proved reliable, and consuming the randomness from Python using Web3 and emitted events was straightforward.

All payments between players and the bank are handled using **FXRP synthetic currency**. FXRP is used to verify that sufficient funds exist before any transaction and to confirm payments through on-chain transfer events rather than trusting backend state. Understanding synthetic assets and configuring the FXRP contract required time, and deployment was not trivial. However, after setup, interacting with FXRP from Python was simple, with clean balance checks and transfer verification. Using FXRP also makes it easier to replace the in-game currency with real assets in the future without changing the game logic.

All smart contracts were deployed using **Hardhat** on the Flare Coston2 network. Deployment was one of the more challenging parts of development, especially when working with Flare-specific contracts and configuration for the first time. That said, the availability of Flare’s GitHub repositories, example projects, and prewritten configurations was extremely helpful, and support from Flare staff played an important role in resolving issues during development. Once deployed, contract usage was significantly easier than expected, particularly from a Python-based backend.






