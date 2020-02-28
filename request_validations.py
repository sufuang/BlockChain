
from collections import OrderedDict
from .constants import INITIATED, TRACKED


def validate_request(data):

    if not data.get('block_type'):
        return False
    else:
        block_type = data['block_type']
        if block_type == INITIATED:
            return validate_initiated_request(data)
        elif block_type == TRACKED:
            return validate_tracked_request(data)
        else:
            return False


def validate_initiated_request(data):
    required = ['actor', 'supplier', 'item', 'quantity', 'actor_key', 'signature']
    if not all(k in data for k in required):
        return False

    return OrderedDict({
        'actor': data['actor'],
        'supplier': data['supplier'],
        'item': data['item'],
        'quantity': data['quantity']
    })


def validate_tracked_request(data):
    required = ['node_id', 'actor', 'courier', 'status', 'actor_key', 'signature']
    if not all(k in data for k in required):
        return False

    return OrderedDict({
        'actor': data['actor'],
        'courier': data['courier'],
        'status': data['status']
    })
