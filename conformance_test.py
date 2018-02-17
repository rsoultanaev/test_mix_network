from sphinxmix.SphinxClient import *
from sphinxmix.SphinxParams import SphinxParams
from sphinxmix.SphinxNode import sphinx_process

from petlib.bn import Bn

from base64 import b64encode

import sys
import subprocess

pki_tuple = namedtuple('pki_tuple', ['id', 'private_key', 'public_key'])

def run_client_under_test(client_command, dest, message, use_nodes, node_keys):
    dest_encoded = b64encode(dest).decode()
    message_encoded = b64encode(message).decode()

    node_key_pairs = []
    for i in range(len(use_nodes)):
        pair = str(use_nodes[i]) + ':' + b64encode(node_keys[i].export()).decode()
        node_key_pairs.append(pair)

    run_command = []
    for command in client_command.split(' '):
        run_command.append(command)

    run_command.append(dest_encoded)
    run_command.append(message_encoded)

    for node_key_pair in node_key_pairs:
        run_command.append(node_key_pair)

    return subprocess.run(run_command, stdout=subprocess.PIPE).stdout


def initialise_pki(sphinx_params, num_mix_nodes):
    pki = {}

    for i in range(num_mix_nodes):
        node_id = i
        private_key = sphinx_params.group.gensecret()
        public_key = sphinx_params.group.expon(sphinx_params.group.g, private_key)
        pki[node_id] = pki_tuple(node_id, private_key, public_key)

    return pki


def test_create_forward_message_creation(client_command, num_mix_nodes=10, num_path_nodes=5):
    params = SphinxParams()

    pki = initialise_pki(params, num_mix_nodes)

    use_nodes = rand_subset(pki.keys(), num_path_nodes)
    nodes_routing = list(map(Nenc, use_nodes))
    node_keys = [pki[n].public_key for n in use_nodes]

    dest = b'bob'
    message = b'this is a test'

    bin_message = run_client_under_test(client_command, dest, message, use_nodes, node_keys)

    param_dict = { (params.max_len, params.m): params }
    _, (header, delta) = unpack_message(param_dict, bin_message)

    x = pki[use_nodes[0]].private_key

    while True:
        ret = sphinx_process(params, x, header, delta)
        (tag, B, (header, delta)) = ret
        routing = PFdecode(params, B)

        if routing[0] == Relay_flag:
            addr = routing[1]
            x = pki[addr].private_key 
        elif routing[0] == Dest_flag:
            dec_dest, dec_msg = receive_forward(params, delta)

            if dec_dest == dest and dec_msg == message:
                print('Success')
            else:
                print('Failure')

            break
        else:
            print('Failure')
            break


if __name__ == '__main__':
    test_create_forward_message_creation(sys.argv[1])

