import json
from hashlib import sha256
import time
from time import time
import datetime
from urllib.parse import urlparse
from uuid import uuid4
from blockchain import *

import binascii

from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5


MINING_DIFFICULTY = 2


class Block:
    def __init__(self, index, block_type, order_id, tx, timestamp, previous_hash, nonce=0):
        self.index = index
        self.block_type = block_type
        self.order_id = order_id
        self.transaction = tx
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.nonce = nonce

    def compute_hash(self):
        """return a hash value of the block contents"""
        block_string = json.dumps(self.__dict__, sort_keys=True)
        return sha256(block_string.encode()).hexdigest()

    def __str__(self):
        my_hash = self.compute_hash()
        return f'index: {self.index}\nblock type: {self.block_type}\nOrder Id: {self.order_id}\nTransaction: ' \
            f'{self.transaction}\nTimestamp: {datetime.datetime.fromtimestamp(self.timestamp)}\nPrevious Hash: {self.previous_hash}\nHash: {my_hash}' \
            f'\nNonce: {self.nonce}'


class Blockchain:
    def __init__(self):
        self.chain = []
        # Generate random number to be used as node_id
        self.order_id = str(uuid4()).replace('-', '')
        # Create genesis block
        self.create_genesis_block()
        self.transaction = dict()
        self.peers = {'http://127.0.0.1:8001', 'http://127.0.0.1:8002'}
        # self.peers = {'http://127.0.0.1:8001'}

    def create_genesis_block(self):
        """"""
        gen_block = Block(0, '', self.order_id, '', time(), '00')
        gen_block.hash = gen_block.compute_hash()
        self.chain.append(gen_block)

    @property
    def last_block(self):
        return self.chain[-1]

    def __str__(self):
        """returns blockchain in string form"""
        bc_string = ''
        count = 0
        for block in self.chain:
            bc_string += f'\n\nBlock {count}:\n{block}'
            count += 1
        return bc_string

    def register_node(self, node_url):
        """add new node to list of nodes"""
        # checking node_url has valid format
        parsed_url = urlparse(node_url)
        if parsed_url.netloc:
            self.peers.add(parsed_url.netloc)
        elif parsed_url.path:
            # accepts a url without a scheme like '192.168.0.5:5000'
            self.peers.add(parsed_url.path)
        else:
            raise ValueError('Invalid URL')

    @staticmethod
    def verify_transaction_signature(transaction, actor_key, signature):
        """
        Check that the provided signature corresponds to transaction
        signed by the public key (actor's public key)
        """
        actor_key = actor_key
        public_key = RSA.importKey(binascii.unhexlify(actor_key))
        verifier = PKCS1_v1_5.new(public_key)
        h = SHA.new(str(transaction).encode('utf8'))
        return verifier.verify(h, binascii.unhexlify(signature))

    def submit_transaction(self, transaction, actor, signature):
        """
        add a transaction to the transaction array if it is verified
        """
        transaction_verified = self.verify_transaction_signature(transaction, actor, signature)
        if transaction_verified:
            self.transaction = transaction
            return len(self.chain) + 1
        else:
            return False

    def add_announced_block(self, block):
        self.chain.append(block)
        return block

    def add_block(self, block):
        """
        Add a block to the blockchain
        :return:
        """

        self.chain.append(block)
        self.transaction = dict()
        return block

    def proof_of_work(self, block):
        """
        Proof of work algorithm
        """

        block.nonce = 0
        while Blockchain.valid_proof(block) is False:
            block.nonce += 1

        return block.nonce

    @staticmethod
    def valid_proof(block, difficulty=MINING_DIFFICULTY):
        """
        Check if a hash value satisfies the mining conditions. This function is used within the proof_of_work function.
        """

        guess_hash = block.compute_hash()
        return guess_hash[:difficulty] == '0' * difficulty


    def mine(self, block_type, node_id):
        # We run the proof of work algorithm to get the next proof...
        previous_hash = self.last_block.compute_hash()
        proposed_block = Block(len(self.chain), block_type, node_id, self.transaction, time(),
                               previous_hash)
        proposed_block.nonce = self.proof_of_work(proposed_block)

        # Forge the new Block by adding it to the chain

        block = self.add_block(proposed_block)
        return block

    @classmethod
    def check_chain_validity(cls, chain):
        """"""
        result = True
        previous_hash = '0'

        for block in chain:
            block_hash = block.hash

            if not Blockchain.is_valid_proof(block, block.hash) or previous_hash != block.previous_hash:
                result = False
                break

            block.hash, previous_hash = block_hash, block_hash

        return result

