# flashcash

Identify flashloan bots in multiple chains, for "academic research" purposes.

# Usage

1.  Enter your Etherscan / Polygonscan / etc API key in the API_KEY variable.
2.  (optional) Update the BLOCK_NUM_3_YRS_AGO field to your desired start block number for the search
3.  (optional) On L2s, choose the desired flash event in FLASH_EVENTS array
4.  Run get_flashbot_addr.py
5.  View results in created JSON - receivers_data_<chain>_<date>.json

# Supported Networks:

1.  Mainnet
2.  Polygon
3.  Arbitrum

# Supported Flashloan Providers

1.  aave-v2
2.  aave-v3
3.  uniswap-v3

# What to do with result flashloan bot addresses

1.  Decompile them [here](https://ethervm.io/decompile)
2.  Check if they still have $$$ and if they have a vulnerable callback function / other backdoor
3.  If so, you can:
    - send the flashloan bot a message in calldata
    - collect your 10% Bug bounty
4.  Consider sending a tip to yours truly.

# Help the project

I'll be happy to take in any pull requests, there is so much more to add. The code is messy, will get around to cleaning it up soon-ish.
