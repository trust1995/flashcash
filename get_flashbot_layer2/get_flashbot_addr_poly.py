import requests
import json
import sha3
from time import sleep

BASE_URL = 'https://api.polygonscan.com/api'
API_KEY = 'YourAPITokenHere'
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
#FlashEvent('aave-v3', 'FlashLoan(address,address,address,uint256,uint8,uint256,uint16)', 0, True, [
#        0x794a61358D6845594F94dc1DB02A252b5b4814aD
#        ]),
FlashEvent('aave-v2', 'FlashLoan(address,address,address,uint256,uint256,uint16)', 0, True, [
        0x8dff5e27ea6b7ac08ebfdf9eb090f32ee9a30fcf
        ]),
]

CURRENT_BLOCK_NUM = 31660363
BLOCK_NUM_1_YRS_AGO = 31155673
BLOCK_JUMP_SPEED = 1000

#CURRENT_BLOCK_NUM = 30605577
#BLOCK_NUM_1_YRS_AGO = 22060550
#BLOCK_JUMP_SPEED = 1000

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
            sleep(3)

def make_20_bytes(hex_string):
    assert len(hex_string) <= 42
    if len(hex_string) < 42:
        hex_string = '0x' + hex_string[2:].zfill(40)
    return hex_string

def dump_receivers(receivers):
    import datetime
    receivers['endBlock'] = CURRENT_BLOCK_NUM
    receivers['startBlock'] = BLOCK_NUM_1_YRS_AGO
    with open('receivers_data_poly_{}.json'.format(datetime.datetime.now().strftime('%y-%m-%d')),'w') as fileobj:
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
            while start_block > BLOCK_NUM_1_YRS_AGO or last_round:
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
                    if start_block < BLOCK_NUM_1_YRS_AGO and not last_round:
                        print('setting last round')
                        start_block = BLOCK_NUM_1_YRS_AGO
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
