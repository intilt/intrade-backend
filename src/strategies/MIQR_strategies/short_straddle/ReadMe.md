Nifty 0DTE Short Gamma
Strategy 1: Sample 920 Straddle

1. Short ATM straddle
2. For wings, long OTM 10 strikes away for both call and put
3. Entry and exit of wings correspond with the short legs
4. SL 20% on the individual short legs.
5. If one leg SL hits, trail SL of remaining short leg to entry price, if in profit. If in loss, exit at current market price
6. 10% buffer between trigger and limit price for all entries and exits for the short legs
7. If SL skips, convert to market order after 2 seconds
8. If any orders/legs are rejected, retry every 2 seconds for 30 seconds before stopping strategy
9. Entry time 9.20
10. Exit time 15.20