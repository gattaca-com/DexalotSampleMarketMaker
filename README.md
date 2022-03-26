# Dexalot Sample Market Maker

- Each team will be assigned a token and will be market making it against AVAX in Dexalot's Dev environment. i,e TEAM1/AVAX will be the first team's pair. We will send the funds to you.

- Team's will not market make against each other for this challenge.

- Start with depositing your tokens from the frontend (See bonus items)

### Our Info
- TEAM2 Address: 0x92BbD24434e0dF6c609Ba37f5Fb69EB0eF81cFF6
- Trading Pair: TEAM2/AVAX
- Start Balance: 20,000 TEAM2 & 5000 AVAX

### TODO List

- ~~Get Reference Data from the RESTAPI (contract addresses, pairs, trade increments, min, max trade amount) **(20 points)**~~
- Enter a BUY & a SELL order with a predefined spread around a given mid price or last price against the contracts. (Keep orders in an internal map). **(20 points)**
- Shut down your market maker manually.
~~- Restart your market maker &  Get your open orders from RESTAPI at startup. **(20 points)**~~
- Wait ~10 seconds and Cancel Buy & Sell your previously opened orders. if you can foresee & mitigate a potential issue in the previous step. (mitigating code to be submitted in an email). **(5 points)**
- Wait ~20 seconds and enter a new set of buy & sell orders  with different prices based on the changing mid/last price  against the contracts. **(20 points)**
- Wait ~30 seconds and CancelAll all your open orders using CancelAll against the contracts. **(15 points)**

Bonus:

- Listen to OrderUpdate Events. We will enter an order that will fill one of your orders and your code have to react by entering a new order in about ~10 seconds after the fill. **(10 points)**
- Listen to Executed Events and react to it as above. **(10 points)**
~~- Read the orderbook from the contracts and console.log it. **(10 points)**~~
- Deposit tokens into Dexalot Portfolio programmatically. **(5 points)** 
- Get gas cost of each order and log it before in order to make buy/sell decisions with t-cost in mind (and console.log it). **(10 points)**