from .blockchain_services import Blockchain, Block
from .constants import INITIATED
from .request_validations import validate_request
from uuid import uuid4

from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import requests
import jsonpickle

bc_app = Flask(__name__)

CORS(bc_app)

# Instantiate the Blockchain
blockchain = Blockchain()
# peers = set('http://127.0.0.1:8000')


@bc_app.route('/chain', methods=['GET'])
def get_chain():
    if len(blockchain.chain) > 0:
        consensus()
        chain_data = []
        for block in blockchain.chain:
            chain_data.append(block.__dict__)
        response = {'length': len(chain_data),
                    'chain': chain_data,
                    'peers': list(blockchain.peers)}
        return jsonify(response), 200
    else:
        response = {'length': 0,
                    'chain': [],
                    'peers': list(blockchain.peers)}
        return jsonify(response), 200


@bc_app.route('/new_transaction', methods=['POST'])
def add_new_transaction():
    tx_data = request.get_json()
    # print(tx_data['block_type'])
    transaction = validate_request(tx_data)

    if not transaction:
        return 'Invalid Request', 400

    transaction_result = blockchain.submit_transaction(transaction, tx_data['actor_key'], tx_data['signature'])

    if not transaction_result:
        response = {'message': 'Invalid Transaction!'}
        return jsonify(response), 406
    else:
        # mine a block
        block_type = tx_data['block_type']
        node_id = str(uuid4())[:8].upper() if block_type == INITIATED else tx_data['node_id']
        block = blockchain.mine(block_type, node_id)
        announce_new_block(block)
        return jsonify(block.__dict__), 200


@bc_app.route('/register_node', methods=['POST'])
def register_new_peers():
    node_address = request.get_json()['node_address']
    if not node_address:
        return 'Invalid Data', 400

    # add the node to the peer list
    blockchain.peers.add(node_address)
    # return the consensus blockchain to the newly registered node so that it can sync
    return get_chain()


@bc_app.route('/register_with', methods=['POST'])
def register_with_existing_node():
    """
    Internally calls the `register_node` endpoint to
    register current node with the node specified in the
    request, and sync the blockchain as well as peer data.
    :return:
    """
    node_address = request.get_json()["node_address"]
    if not node_address:
        return "Invalid data", 400

    data = {"node_address": request.host_url}
    headers = {'Content-Type': "application/json"}

    # make a request to register with remote node and obtain information
    response = requests.post(node_address + "/register_node", data=json.dumps(data), headers=headers)

    if response.status_code == 200:
        global blockchain
        # global peers
        # update chain and the peers
        chain_dump = response.json()['chain']
        blockchain = create_chain_from_dump(chain_dump)
        blockchain.peers.update(response.json()['peers'])
        return "Registration successful", 200
    else:
        # if something goes wring, pass it on to the api response
        return response.content, response.status_code


def create_chain_from_dump(chain_dump):
    bc = Blockchain()
    for idx, block_data in enumerate(chain_dump):
        block = Block(block_data['index'],
                      block_data['block_type'],
                      block_data['order_id'],
                      block_data['transaction'],
                      block_data['timestamp'],
                      block_data['previous_hash'])
        if idx > 0:
            added = bc.add_block(block.nonce, block.previous_hash, block.block_type, block.order_id)
            if not added:
                raise Exception("The chain dump is tampered!!")
        else:  # the block is a genisis block, no verification needed
            bc.chain.append(block)
    return bc


@bc_app.route('/add_block', methods=['POST'])
def verify_and_add_block():
    """endpoint to add a block that has been mined by another node to the chain.
    The block is first verified and then added to the node's blockchain."""
    block_data = request.get_json()
    block = Block(block_data['index'],
                  block_data['block_type'],
                  block_data['order_id'],
                  block_data['transaction'],
                  block_data['timestamp'],
                  block_data['previous_hash'],
                  block_data['nonce'])
    added = blockchain.add_announced_block(block)

    if not added:
        return 'The block was discarded by the node', 400
    print(blockchain)
    return 'Block added to the chain', 201


def consensus():
    """simple consensus algorithm makes sure that the node's blockchain matches with the longest
    blockchain in the network"""
    global blockchain
    longest_chain = None
    current_len = len(blockchain.chain)

    for node in blockchain.peers:
        response = requests.get('{}/chain'.format(node))
        length = response.json()['length']
        chain = response.json()['chain']
        if length > current_len and blockchain.check_chain_validity(chain):
            current_len = length
            longest_chain = chain

    if longest_chain:
        blockchain = longest_chain
        # print('Ran consensus algorithm')
        return True
    # print('Ran consensus algorithm ')
    return False


def announce_new_block(block):
    """sends newly mined block to all the nodes in the network. Functions should be called after each mined block"""
    print(blockchain)
    for peer in blockchain.peers:
        url = "{}/add_block".format(peer)
        # print(f'about to send request.post to {url}')
        # requests.post(url, data=json.dumps(block, sort_keys=True))
        # headers = {'Content-Type: "application/json; charset=utf-8", 'Accept': 'text/json'}
        headers = {'Content-Type': "application/json", "Accept": "text/plain"}
        # print(block)
        r = requests.post(url, json=block.__dict__, headers=headers)
        # print(r.status_code, r.reason)


