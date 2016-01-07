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

            if text['type'] == 'linkstats':
                (dpid1, port1),(dpid2, port2) = text['data']['link']
                up = 1 if text['data']['up'] is True else 0
                d = stats[0]
                d['links'][dpid1][port1] = up
                d['links'][dpid2][port2] = up
                # Hack: conn to controller is always up
                d['links'][dpid1][65534] = 1
                d['links'][dpid2][65534] = 1
                stats[0] = d

def default_True():
    return 1

def default_zero():
    return 0

def defaultdict_with_zero():
    return defaultdict(default_zero)

def _process_stats(stats, stats_before, stats_processed):
    for switch_dpid, switch in stats[0]['switches'].items():
        
        d = stats_processed[0]
        d['switches'][switch_dpid]['port_stats'] = list()

        d_stats = stats[0]

        # Process traffic data with port stats
        if not switch.get('port_stats') is None:
            for port_stat in switch['port_stats']:
                port_no = port_stat['port_no']
                
                rx_before, tx_before = 0,0
                for port in stats_before[0]['switches'][switch_dpid].get('port_stats',list()):
                    if port['port_no'] == port_no:
                        rx_before = port['rx_packets']
                        tx_before = port['tx_packets']

                # difference between now and before in no of packets
                rx_diff = port_stat['rx_packets'] - rx_before
                tx_diff = port_stat['tx_packets'] - tx_before

                new_data = {'port_no': port_no, 'new_rx_packets': rx_diff, 'new_tx_packets': tx_diff,
                    'rx_packets': port_stat['rx_packets'], 'tx_packets': port_stat['tx_packets']}
                d['switches'][switch_dpid]['port_stats'].append(new_data)

        d['switches'][switch_dpid]['flow_stats'] = defaultdict(defaultdict_with_zero)
        # Process traffic data with flow stats
        if not switch.get('flow_stats') is None:
            hosts_stats = defaultdict(defaultdict_with_zero)
            # Aggregate all flow stats
            for flow_stat in switch['flow_stats']:
                addr_dst = flow_stat['match'].get('dl_dst')
                addr_src = flow_stat['match'].get('dl_src')

                if not addr_dst is None:
                    addr_dst = _address_to_dec(addr_dst, separator=':')
                    hosts_stats[addr_dst]['packets_in'] += flow_stat['packet_count']
                    hosts_stats[addr_dst]['bytes_in'] += flow_stat['byte_count']
                    # d['switches'][switch_dpid]['flow_stats'][addr_dst]['packets_in'] += flow_stat['packet_count']
                    # d['switches'][switch_dpid]['flow_stats'][addr_dst]['bytes_in'] += flow_stat['byte_count']
                if not addr_src is None:
                    addr_src = _address_to_dec(addr_src, separator=':')
                    hosts_stats[addr_src]['packets_out'] += flow_stat['packet_count']
                    hosts_stats[addr_src]['bytes_out'] += flow_stat['byte_count']
                    # d['switches'][switch_dpid]['flow_stats'][addr_src]['packets_out'] += flow_stat['packet_count']
                    # d['switches'][switch_dpid]['flow_stats'][addr_src]['bytes_out'] += flow_stat['byte_count']

            for addr, addr_stats in hosts_stats.items():
                if not switch.get('flow_stats_aggr') is None and not switch['flow_stats_aggr'].get(addr) is None:
                    in_diff = addr_stats['packets_in'] - switch['flow_stats_aggr'].get(addr)['packets_in']
                    d['switches'][switch_dpid]['flow_stats'][addr]['new_packets_in'] = in_diff
                    d['switches'][switch_dpid]['flow_stats'][addr]['packets_in'] = addr_stats['packets_in']

                    out_diff = addr_stats['packets_out'] - switch['flow_stats_aggr'].get(addr)['packets_out']
                    d['switches'][switch_dpid]['flow_stats'][addr]['new_packets_out'] = out_diff
                    d['switches'][switch_dpid]['flow_stats'][addr]['packets_out'] = addr_stats['packets_out']


            d_stats['switches'][switch_dpid]['flow_stats_aggr'] = hosts_stats
            stats[0] = d_stats
                
        stats_processed[0] = d
    stats_before[0] = stats[0]

# def default_to_regular(d):
#     if isinstance(d, defaultdict):
#         print('converting')
#         d = {k: default_to_regular(v) for k, v in d.items()}
#     return d

def port_status(switch, port, stats):
    up = stats[0]['links'].get(switch,{}).get(port,None)
    if up is None:
        return '?'
    if up:
        return 'up'
    return 'down'

def _address_to_dec(dpid, separator='-'):
    non_zero = ''.join([n for n in str(dpid).split(separator) if not n == '00'])
    return int('0x{}'.format(str(non_zero)), 16)

def _print_stats(stats, stats_before, stats_processed):
    count = 0
    while True:
        time.sleep(10)
        count += 1
        print(count)
        if count == 1:
            continue
        if count == 2:
            stats_before[0] = stats[0]
            continue

        _process_stats(stats, stats_before, stats_processed)
        
        message = []
        for switch_dpid, values in stats_processed[0]['switches'].items():
            micro_msg = '{0} ({1})\n'.format(switch_dpid,_address_to_dec(switch_dpid))
            micro_msg += ' -> ports: '
            for port_stat in values['port_stats']:
                micro_msg += '  {0}({5})=> rx:{1}[{3}], tx:{2}[{4}];'.format(port_stat['port_no'],
                    port_stat['new_rx_packets'],port_stat['new_tx_packets'],
                    port_stat['rx_packets'], port_stat['tx_packets'],
                    port_status(_address_to_dec(switch_dpid), int(port_stat['port_no']), stats))

            micro_msg += '\n -> flows: '
            for host_no, host_stats in values['flow_stats'].items():
                micro_msg += ' {0}=> in:{1}[{3}], out:{2}[{4}];'.format(host_no, 
                    host_stats['new_packets_in'], host_stats['new_packets_out'],
                    host_stats['packets_in'], host_stats['packets_out'])

            message.append(micro_msg)

        message = sorted(message, key=lambda msg: re.search('((.*))',msg).group(1))
        message = '\n'.join(message)

        with open('/dev/shm/monitor-stats.log','w') as out:
            out.write(message)

if __name__ == '__main__':
    manager = multiprocessing.Manager()

    # create a list proxy and append a mutable object (dict)
    stats = manager.list()
    stats.append({'switches':defaultdict(dict), 'links': defaultdict(dict)})

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