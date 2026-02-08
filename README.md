https://oxfordeth-production.up.railway.app/


## Flare Protocols:

We used Flare’s Secure Random Number (SRN) to generate dice rolls in a trustless way. Understanding how SRN works was not straightforward at first, especially the fact that randomness updates in fixed rounds roughly every 90 seconds. This meant that SRN is not always immediately available, so additional backend logic was required to handle waiting and retries. To avoid predictability, the SRN output was combined with a unique public requestId, which ensures that the final dice result cannot be determined in advance or manipulated. While the concept and initial setup were difficult, once the contract was deployed the randomness was very reliable and easy to consume from Python using Web3 and emitted events.

All transactions between players and the bank were handled using FXRP synthetic currency. Working with FXRP required time to understand, particularly how balances and transfers should be verified on-chain instead of trusting the backend. Deployment and configuration were not trivial, but after setup FXRP integrated cleanly into the game logic. From the backend perspective, checking balances and confirming transfers via contract events was straightforward, and using FXRP makes it easier to replace the in-game currency with real assets in the future without changing core logic.

All smart contracts were deployed on the Flare Coston2 network using Hardhat. The deployment process itself was challenging, especially when working with Flare-specific contracts and configuration for the first time. However, the availability of Flare’s GitHub repositories, example projects, and prewritten configurations was extremely helpful, and support from Flare staff made debugging and deployment issues much easier to resolve. Once deployed, interaction with the contracts from Python was significantly easier than expected, and the backend–blockchain integration was stable and reliable throughout development.




