from pox.core import core
import pox.openflow.libopenflow_01 as of
import pox.lib.packet as pkt                  # Packet parsing/construction
import pox.lib.util as poxutil                # Various util functions

import json

log = core.getLogger('RuleForwarding')

rules = None
accepted_ips = None

def _handle_PacketIn(event):
	dpid = poxutil.dpid_to_str(event.connection.dpid)
	packet = event.parsed

	ip = packet.find('ipv4')
	tcp = packet.find('tcp')
	if tcp is None: # No TCP data
		if not ip is None:
			dstip = str(ip.dstip)
			if not dstip in accepted_ips:
				return
			outport = rules[dpid][dstip]
			msg = of.ofp_flow_mod()
			msg.match = of.ofp_match()
			msg.match.dl_type = 0x800 # ethernet IPv4
			msg.match.nw_dst = ip.dstip
			msg.idle_timeout = 10
			msg.actions.append(of.ofp_action_output(port=outport))
			msg.data = event.ofp
			event.connection.send(msg)
	else: # TCP is always on IP
		dstip = str(ip.dstip)
		if not dstip in accepted_ips:
			return
		outport = rules[dpid][dstip]
		msg = of.ofp_flow_mod()
		msg.match = of.ofp_match()
		msg.match.dl_type = 0x800 # ethernet IPv4
		msg.match.nw_dst = ip.dstip
		msg.match.nw_proto = 6
		msg.match.tp_dst = 80
		msg.idle_timeout = 500
		msg.actions.append(of.ofp_action_output(port=outport))
		msg.data = event.ofp
		event.connection.send(msg)



@poxutil.eval_args
def launch(rules_path = './rules.json', accept_ips='10.0.0.1,10.0.0.2,10.0.0.3,10.0.0.4,10.0.0.5'):
	global rules, accepted_ips

	with open(rules_path,'r') as frule:
		rules = frule.read()
	rules = json.loads(rules)

	accepted_ips = accept_ips.split(',')

	log.info('Rules loaded from {}'.format(rules_path))

	core.openflow.addListenerByName("PacketIn", _handle_PacketIn)

	log.info('l3_rules is Up')