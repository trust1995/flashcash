import time
import requests
import json
import sha3
import datetime
from time import sleep

BASE_URL = 'https://api.etherscan.io/api'
API_KEY = 'YourAPIKeyHere'
PARAMS = 'module=logs&action=getLogs&fromBlock={start}&toBlock={end}&address={address}&topic0={event_hash}&offset=1000&apikey={api_key}'

class FlashEvent(object):
    def __init__(self, service_name, event_sig, callee_offset, is_indexed, contracts):
        self.service_name = service_name
        self.event_sig = event_sig
        self.event_hash = '0x' + sha3.keccak_256(event_sig.encode()).hexdigest()
        # if is_indexes, callee_offset is the index of topic array (not inc. event hash)
        # else, it is offset into data bytes array
        self.callee_offset = callee_offset
        self.is_indexed = is_indexed
        self.contracts = contracts

FLASH_EVENTS = [
FlashEvent('aave-v2', 'FlashLoan(address,address,address,uint256,uint256,uint16)', 0, True, [
        0x7d2768de32b0b80b7a3454c06bdac94a69ddc7a9
        ]),
    FlashEvent('uniswap-v3', 'Flash(address,address,uint256,uint256,uint256,uint256)', 0, True, [
        # DAI/USDC 0.01% , # DAI/USDC 0.05% ,
        0x5777d92f208679db4b9778590fa3cab3ac9e2168, 0x6c6bc977e13df9b0de53b251522280bb72383700,
        # USDC/ETH 0.3% , # USDC/ETH 0.05% ,
        0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8, 0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640,
        # USDC/USDT 0.01% , # FRAX/USDC 0.05% ,
        0x3416cf6c708da44db2624d63ea0aaef7113527c6, 0xc63b0708e2f7e69cb8a1df0e1389a98c35a76d52,
        # DAI/USDC 0.01% , # DAI/USDC 0.05% ,
        0x5777d92f208679db4b9778590fa3cab3ac9e2168, 0x6c6bc977e13df9b0de53b251522280bb72383700,
        # USDC/USDM 0.05% , # WBTC/USDC 0.3% ,
        0x8ee3cc8e29e72e03c4ab430d7b7e08549f0c71cc, 0x99ac8ca7087fa4a2a1fb6357269965a2014abc35,
        # USDC/SWYF 0.01% , # USDC/ETH 1% ,
        0x025b887e7f62d8b5f1564ba204187452cf27f634, 0x7bea39867e4169dbe237d55c8242a8f2fcdcc387,
        # DAI/USDC 0.01% , # DAI/USDC 0.05% ,
        0x5777d92f208679db4b9778590fa3cab3ac9e2168, 0x6c6bc977e13df9b0de53b251522280bb72383700,
        # WBTC/ETH 0.3% , # ETH/USDT 0.3% ,
        0xcbcdf9626bc03e24f779434178a73a0b4bad62ed, 0x4e68ccd3e89f51c3074ca5072bbac773960dfa36,
        # WBTC/ETH 0.05% , # DAI/ETH 0.3% ,
        0x4585fe77225b41b697c938b018e2ac67ac5a20c0, 0xc2e9f25be6257c210d7adf0d4cd6e3e881ba25f8,
        # DAI/FRAX 0.05% , # BIT/ETH 0.3% ,
        0x97e7d56a0408570ba1a7852de36350f7713906ec, 0x5c128d25a21f681e678cb050e551a895c9309945,
        # ETH/USDT 0.05% , # BUSD/USDC 0.05% ,
        0x11b815efb8f581194ae79006d24e0d814b7697f6, 0x00cef0386ed94d738c8f8a74e8bfd0376926d24c,
        # ETH/sETH 0.3%
        0x7379e81228514a1d2a6cf7559203998e20598346
    ]),

]


CURRENT_BLOCK_NUM = 15301873
#BLOCK_NUM_3_YRS_AGO = CURRENT_BLOCK_NUM - (4 * 60 * 24 * 365 * 3)
#BLOCK_NUM_3_YRS_AGO = CURRENT_BLOCK_NUM - 20000000
BLOCK_NUM_3_YRS_AGO = 15217773

def write_token_json_file(token_data):
    with open('tok_data.json','w') as fileobj:
        json.dump(token_data, fileobj)


BLOCK_JUMP_SPEED = 1000

def get_receivers(flash_event, contract, start_block, end_block):
    api_url = BASE_URL + '?' + PARAMS.format(start=start_block, end=end_block, address=contract, event_hash=flash_event.event_hash, api_key=API_KEY)
    while True:
        try:
            print('Fetching service {}, contract {}, start: {}, end: {}'.format(flash_event.service_name, contract, str(start_block), str(end_block)))
            response = requests.get(api_url).json()
            if 'message' not in response or response['message'] not in ('OK', "No records found"):
                print('Bad response!')
            elif response['message'] == 'No records found':
                return 0, end_block, {}
            else:
                receivers = {}
                for event in response['result']:
                    if flash_event.is_indexed:
                        key = hex(int(event['topics'][1 + flash_event.callee_offset], 16))
                        if not key in receivers:
                            receivers[key] = 0
                        receivers[key] += 1
                    else:
                        # Currently not needed
                        pass
                print('Received {} results'.format(len(response['result'])))
                return len(response['result']), int(response['result'][-1]['blockNumber'], 16), receivers
        except Exception as e:
            print('API request error: {}'.format(e))
            print('Retrying in 3 sec...')
            time.sleep(3)

def make_20_bytes(hex_string):
    assert len(hex_string) <= 42
    if len(hex_string) < 42:
        hex_string = '0x' + hex_string[2:].zfill(40)
    return hex_string


def dump_receivers(receivers):
    receivers['endBlock'] = CURRENT_BLOCK_NUM
    receivers['startBlock'] = BLOCK_NUM_3_YRS_AGO
    with open('receivers_data_{}.json'.format(datetime.datetime.now().strftime('%y-%m-%d')),'w') as fileobj:
        json.dump(receivers, fileobj)


def get_addr():
    receivers = {}
    for flash_event in FLASH_EVENTS:
        receivers[flash_event.service_name] = {}
        for contract in flash_event.contracts:
            print('service {}, contract {}'.format(flash_event.service_name, hex(contract)))
            contract = make_20_bytes(hex(contract))
            receivers[flash_event.service_name][contract] = {}
            contract_receivers = receivers[flash_event.service_name][contract]
            start_block = CURRENT_BLOCK_NUM - BLOCK_JUMP_SPEED
            earliest_reached = start_block
            end_block = CURRENT_BLOCK_NUM
            last_round = False
            while start_block > BLOCK_NUM_3_YRS_AGO or last_round:
                num_results, last_block, new_receivers = get_receivers(flash_event, contract, start_block, end_block)
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

                new_receivers_updatable = {receiver: contract_receivers[receiver] + new_receivers[receiver]
                                           if receiver in contract_receivers else new_receivers[receiver] for receiver in new_receivers}
                contract_receivers.update(new_receivers_updatable)
                sleep(0.1)
    dump_receivers(receivers)

if '__main__' == __name__:
    get_addr()
