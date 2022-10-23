# Using CoinMarketCap API
from time import sleep
import requests
import json
import sha3

BASE_URL = 'https://api.etherscan.io/api'
API_KEY = 'YourAPITokenHere'
PARAMS = 'module=account&action=txlist&address={address}&startblock={start}&endblock={end}&&offset=1000&apikey={api_key}'


PAIRS = [
        # DAI/USDC , # USDC-ETH ,
        0xae461ca67b15dc8dc81ce7615e0320da1a9ab8d5, 0xb4e16d0168e52d35cacd2c6185b44281ec28c9dc,
        # FEI-TRIBE, # WISE-ETH ,
        0x9928e4046d7c6513326ccea028cd3e7a91c7590a, 0x21b8065d10f73ee2e260e5b47d3344d3ced7596e,
        # FXS-FRAX, # FNK-USDT ,
        0xe1573b9d29e2183b1af0e743dc2754979a40d237, 0x61b62c5d56ccd158a38367ef2f539668a06356ab,
        # ETH-USDT, # MC-ETH,
        0x0d4a11d5eeaac28ec3f61d100daf4d40471f1852, 0xccb63225a7b19dcf66717e4d40c9a72b39331d61,
        # PAXG-ETH , # UNI-ETH ,
        0x9c4fe5ffd9a9fc5678cfbd93aa2d4fd684b67c4c, 0xd3d2e2692501a5c9ca623199d38826e513033a17,
        # USDC-USDT, # DAI-ETH ,
        0x3041cbd36888becc7bbcbc0045e3b1f144466f5f, 0xa478c2975ab1ea89e8196811f51a7b7ade33eb11,
        # WBTC-ETH, # USDC-CAW ,
        0xbb2b8038a1640196fbe3e38816f3e67cba72d940, 0x7a809081f991ecfe0ab2727c7e90d2ad7c2e411e,
        ]

CURRENT_BLOCK_NUM = 15301873
#BLOCK_NUM_3_YRS_AGO = CURRENT_BLOCK_NUM - (4 * 60 * 24 * 365 * 3)
#BLOCK_NUM_3_YRS_AGO = CURRENT_BLOCK_NUM - 20000000
BLOCK_NUM_3_YRS_AGO = 15217773

#CURRENT_BLOCK_NUM = 15115696
#BLOCK_NUM_3_YRS_AGO = CURRENT_BLOCK_NUM - (4 * 60 * 24 * 365 * 3)
#BLOCK_NUM_3_YRS_AGO = CURRENT_BLOCK_NUM - 2000000
SWAP_METHODID = "0x022c0d9f"

BLOCK_JUMP_SPEED = 1000

def get_receivers(contract, start_block, end_block):
    api_url = BASE_URL + '?' + PARAMS.format(start=start_block, end=end_block, address=contract,api_key=API_KEY)
    while True:
        try:
            print('Fetching contract {}, start: {}, end: {}'.format(contract, str(start_block), str(end_block)))
            response = requests.get(api_url).json()
            if 'message' not in response or response['message'] not in ('OK', "No transactions found"):
                print('Bad response!')
            elif response['message'] == 'No records found':
                return 0, end_block, {}
            else:
                receivers = {}
                for tx in response['result']:
                    if tx['methodId'] != SWAP_METHODID or tx['isError'] != '0':
                        continue
                    input_data = tx['input'][2 + 8:]
                    to = '0x' + input_data[64*2 + 24:64*3]
                    data = input_data[64*4:64*5]
                    if int(data, 16) == 0:
                        continue
                    if not to in receivers:
                        receivers[to] = 0
                    receivers[to] += 1
                print('Received {} results'.format(len(response['result'])))
                if len(response['result']) == 0:
                    return 0, 0, receivers
                return len(response['result']), int(response['result'][-1]['blockNumber'], 16), receivers
        except Exception as e:
            print('API request error: {}'.format(e))
            print('Retrying in 3 sec...')
            sleep(3)

def make_20_bytes(hex_string):
    assert len(hex_string) <= 42
    if len(hex_string) < 42:
        hex_string = '0x' + hex_string[2:].zfill(40)
    return hex_string


def dump_receivers(receivers):
    import datetime
    receivers['endBlock'] = CURRENT_BLOCK_NUM
    receivers['startBlock'] = BLOCK_NUM_3_YRS_AGO
    with open('receivers_data_{}.json'.format(datetime.datetime.now().strftime('%y-%m-%d')),'w') as fileobj:
        json.dump(receivers, fileobj)

def get_addr():
    receivers = {}
    for pair in PAIRS:
        pair = make_20_bytes(hex(pair))
        receivers[pair] = {}
        print('pair {}'.format(pair))
        pair_receivers = receivers[pair]
        start_block = CURRENT_BLOCK_NUM - BLOCK_JUMP_SPEED
        earliest_reached = start_block
        end_block = CURRENT_BLOCK_NUM
        last_round = False
        while start_block > BLOCK_NUM_3_YRS_AGO or last_round:
            num_results, last_block, new_receivers = get_receivers(pair, start_block, end_block)
            print(num_results)
            if num_results >= 1000:
                start_block = last_block
                print('Over 1k results, start: {}, end {}'.format(str(start_block), str(end_block)))
            else:
                end_block = earliest_reached
                if earliest_reached == start_block:
                    # Less than full page result, on new jump, can jump lower
                    if num_results == 0:
                        earliest_reached = start_block = start_block - BLOCK_JUMP_SPEED * 1000
                    else:
                        earliest_reached = start_block = start_block - BLOCK_JUMP_SPEED * int((1000.0 / num_results))
                    print('Under 1k results, new jump, start: {}, end {}'.format(str(start_block), str(end_block)))
                else:
                    # Completed previous over 1k results, jump regular
                    earliest_reached = start_block = earliest_reached - BLOCK_JUMP_SPEED
                    print('Under 1k results, new jump, start: {}, end {}'.format(str(start_block), str(end_block)))
                if start_block < BLOCK_NUM_3_YRS_AGO and not last_round:
                    print('setting last round')
                    start_block = BLOCK_NUM_3_YRS_AGO
                    last_round = True
                elif last_round:
                    print('unsetting last round')
                    last_round = False
            new_receivers_updatable = {receiver: pair_receivers[receiver] + new_receivers[receiver]
                                       if receiver in pair_receivers else new_receivers[receiver] for receiver in new_receivers}
            pair_receivers.update(new_receivers_updatable)
            sleep(0.1)
    dump_receivers(receivers)

if '__main__' == __name__:
    get_addr()
