https://oxfordeth-production.up.railway.app/

Flare Protocols

We used Flare’s Secure Random Number (SRN) for rolling 2 dice, which prevents the risk of predicting/manipulating the score. As SRN updates every 90 seconds, it was crucial to use it in hybrid with a unique public requestId, which together create a truly secure result, from which there is no way to determine the random numbers in SRN.

For all transactions between players and the bank we used FXPR synthetic currency, which verifies that there are sufficient funds on the account before paying and confirms the payments itself, triggering conditions from smart contracts. 
Also, it makes it easier to implement real currents in the future.

All the contracts were deployed  on the coston2 network using hardhat. The availability of Flare's Github repository massively simplified the process thanks to the prewritten configurations. 

