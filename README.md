# Dexalot Sample Market Maker
## Market Making Contest

- Each team will be assigned a token and will be market making it against AVAX in Dexalot's Dev environment. i,e TEAM1/AVAX will be the first team's pair. We will send the funds to you.
- Team's will not market make against each other for this challenge.
- Start with depositing your tokens from the frontend (See bonus items)

### Our Info
- TEAM2 Address: 0x92BbD24434e0dF6c609Ba37f5Fb69EB0eF81cFF6
- Trading Pair: TEAM2/AVAX
- Start Balance: 20,000 TEAM2 & 5000 AVAX

### Challenges
1. Get Reference Data from the RESTAPI (contract addresses, pairs, trade increments, min, max trade amount) **(20 points)**
2. Enter a BUY & a SELL order with a predefined spread around a given mid price or last price against the contracts. (Keep orders in an internal map). **(20 points)**
3. Shut down your market maker manually.
4. Restart your market maker &  Get your open orders from RESTAPI at startup. **(20 points)**
5. Wait ~10 seconds and Cancel Buy & Sell your previously opened orders. if you can foresee & mitigate a potential issue in the previous step. (mitigating code to be submitted in an email). **(5 points)**
6. Wait ~20 seconds and enter a new set of buy & sell orders  with different prices based on the changing mid/last price  against the contracts. **(20 points)**
7. Wait ~30 seconds and CancelAll all your open orders using CancelAll against the contracts. **(15 points)**

### Bonus Challenges:
8. Listen to OrderUpdate Events. We will enter an order that will fill one of your orders and your code have to react by entering a new order in about ~10 seconds after the fill. **(10 points)**
9. Listen to Executed Events and react to it as above. **(10 points)**
10. Read the orderbook from the contracts and console.log it. **(10 points)**
11. Deposit tokens into Dexalot Portfolio programmatically. **(5 points)** 
12. Get gas cost of each order and log it before in order to make buy/sell decisions with t-cost in mind (and console.log it). **(10 points)**

## Solutions
To run either solution, set your `PRIVATE_KEY` in the environment variables.

`demo_script.py` is a simple demo script that performs the actions outlined in challenges `1-7`, `10` and `11`. 

`market_maker.py` is a simple market maker implementation that aims to complete all challenges `1-12`. The market maker can be configured via `config.py`.

### Exchange Handler Config
```
base_url - Base url of the Dexalot REST API (https://api.dexalot-dev.com/api/)
timeout - Timeout interval for API requests in seconds
trade_pair - Pair to be traded (TEAM2/AVAX)
```

### Market Maker Configuration
```
default_mid_price - Default mid price if no orders are present in the orderbook
default_amount - Default trade amount in base asset
order_price_tolerance - Tolerance used when comparing desired order prices with current order prices (0.5% = 0.005).
                      - Orders will only be moved when this tolerance is exceeded to reduce order placement turnover, hence, reducing fees paid.
                      - Should be set to a low value to reduce spread drift.
order_amount_tolerance - Tolerance used when comparing desired order size with current order size (20% = 0.2).
                       - Orders will only be moved when this tolerance is exceeded to reduce order placement turnover, hence, reducing fees paid
                       - A lower value means the MM will replenish partially filled LIMIT orders sooner.
target_spread - Target spread (this can vary slightly due to order_price_tolerance)
n_price_levels - Number of orderbook price levels to fetch.
n_agg_orders - Number of orders to aggregate across n_price_levels.
additional_state_update - Additional state update incase events are missed or out of sync
```