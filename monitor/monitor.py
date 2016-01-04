import multiprocessing
import json
import time
import sys
import re
from collections import defaultdict

"""
stats = {
    'switches': defaultdict(dict)
}
"""

def _read_pipe(stats):
    count = 0
    while True:
        with open('/dev/shm/poxpipe','r') as pipe:
            data = pipe.read()
            p = multiprocessing.Process(target=_read_data, args=(data,stats))
            p.start()
            count += 1
            # print(count)
            if count % 10 == 0:
                pass
                #print(stats)
            #time.sleep(1)

def _read_data(data, stats):
    texts = data.split('#')
    for text in texts:
        if len(text) > 0:
            text = json.loads(text)
            if text['type'] == 'switch_portstats':
                dpid = text['data']['switch']
                # mutate the dictionary
                d = stats[0] 
                # assing values to the dictionary
                d['switches'][dpid]['port_stats'] = text['data']['stats']
                # at this point, changes are not still synced
                # to sync, reassing the dictionary
                stats[0] = d

            if text['type'] == 'switch_flowstats':
                dpid = text['data']['switch']
                d = stats[0]
                d['switches'][dpid]['flow_stats'] = text['data']['stats']
                stats[0] = d

def _process_stats(stats, stats_before, stats_processed):
    for switch_dpid, switch in stats[0]['switches'].items():
        
        d = stats_processed[0]
        d['switches'][switch_dpid]['port_stats'] = list()

        # Process traffic data with port stats
        if not switch.get('port_stats') is None:
            for port_stat in switch['port_stats']:
                port_no = port_stat['port_no']
                
                rx_before, tx_before = 0,0
                for port in stats_before[0]['switches'][switch_dpid].get('port_stats',list()):
                    if port['port_no'] == port_no:
                        rx_before = port['rx_packets']
                        tx_before = port['tx_packets']

                rx_diff = port_stat['rx_packets'] - rx_before
                tx_diff = port_stat['tx_packets'] - tx_before

                new_data = {'port_no': port_no, 'new_rx_packets': rx_diff, 'new_tx_packets': tx_diff,
                    'rx_packets': port_stat['rx_packets'], 'tx_packets': port_stat['tx_packets']}
                d['switches'][switch_dpid]['port_stats'].append(new_data)

        # Process traffic data with flow stats
        if not switch.get('flow_stats') is None:
            pass
        # for flow in switch['flow_stats']:

        stats_processed[0] = d
    stats_before[0] = stats[0]

def _address_to_dec(dpid, separator='-'):
    non_zero = ''.join([n for n in str(dpid).split(separator) if not n == '00'])
    return int('0x{}'.format(str(non_zero)), 16)

def _print_stats(stats, stats_before, stats_processed):
    count = 0
    while True:
        time.sleep(10)
        count += 1

        if count == 1:
            continue
        if count == 2:
            stats_before[0] = stats[0]
            continue

        _process_stats(stats, stats_before, stats_processed)

        message = []

        for switch_dpid, values in stats_processed[0]['switches'].items():
            micro_msg = '{0} ({1})\n'.format(switch_dpid,_address_to_dec(switch_dpid))
            for port_stat in values['port_stats']:
                micro_msg += '  {0}=> rx:{1}[{3}], tx:{2}[{4}];'.format(port_stat['port_no'],
                    port_stat['new_rx_packets'],port_stat['new_tx_packets'],
                    port_stat['rx_packets'], port_stat['tx_packets'])

            # for flow_stat in values['flow_stats']:
            #     micro_msg += '\n  '

            message.append(micro_msg)

        message = sorted(message, key=lambda msg: re.search('((.*))',msg).group(1))
        message = '\n'.join(message)

        with open('/dev/shm/monitor-stats.log','w') as out:
            out.write(message)

if __name__ == '__main__':
    manager = multiprocessing.Manager()

    # create a list proxy and append a mutable object (dict)
    stats = manager.list()
    stats.append({'switches':defaultdict(dict)})

    stats_before = manager.list()
    stats_before.append({'switches':defaultdict(dict)})

    stats_processed = manager.list()
    stats_processed.append({'switches':defaultdict(dict)})

    printer = multiprocessing.Process(target=_print_stats, 
        args=(stats,stats_before, stats_processed))
    printer.start()

    try:
        _read_pipe(stats)
    except KeyboardInterrupt:
        printer.terminate()
        printer.join()
        sys.exit(1)