""" Distributed custom topology

Based on the example of the book "Designing and Implementing IP/MPLS-Based
Ethernet Layer 2 VPN Services: An Advanced Guide for VPLS and VLL" for the
class TTCR

author: Oscar Araque
"""

"""
TOPOLOGY CONFIG
"""
distributed_topo = {'sw_main_ring': 13, 
	'secondary_rings': [[3, (13,2),(14,16)], [5, (4,5),(17,21)], [4,(10, 8),(22,25)]], 
	'ring_link_bw': 1000,
	'ring_link_lat': '5ms',
	'access_link_bw': 1000,
	'access_link_lat': "2ms",
	'hosts': [
			[[1], 12, 26],
			[[2], 11, None],
			[[3], 22, None],
			[[4], 23, None],
			[[5,6], 23, 27],
			[[7,9], 24, None],
			[[10,11], 7, 28],
			[[12,13], 21, None],
			[[14], 18, 29],
			[[15,16], 29, 30],
			[[17,18], 29, 31],
			[[19,21], 17, 32]
		]
}

datacenter_desc = {
	'link_bw': 1000,
	'link_lat': '3ms',
	'sw_acc': [14,15,16],
	'name_sws': [33,34,35],
	'n_servers': 6,
	'sw_sv_links': [[1,2],[3,4],[5,6]]
}

ring_topo = {'sw_main_ring': 10,
        'ring_link_bw': 1000, 
        'ring_link_lat': '3ms'}
"""
END OF TOPOLOGY CONFIG
"""

from mininet.topo import Topo


# Add main ring. Supposed a topo dict good formatted
def main_ring(self, topo_desc=None):
        if topo_desc is None:
                raise ValueError

        n_sw = topo_desc.get('sw_main_ring',13)
        bw = topo_desc.get('ring_link_bw',1000)
        lat = topo_desc.get('ring_link_lat','3ms')
        sw_list = []
        for i in range(n_sw):
                sw_list.append(self.addSwitch('s{}'.format(i+1)))
                if i == 0:
                        continue
                self.addLink(sw_list[i], sw_list[i-1], bw=bw,delay=lat)
        self.addLink(sw_list[0], sw_list[-1], bw=bw,delay=lat)
        return sw_list

# Add secundary rings
def secondary_rings(self, topo_desc=None, main_ring=None):
        if topo_desc is None:
                raise ValueError

        rings = topo_desc.get('secondary_rings')
	sr_list = []
        for i in range(len(rings)):
                n_sw_ring = rings[i][0] # number switches in ring
                bw = topo_desc.get('ring_link_bw',1000)
                lat = topo_desc.get('ring_link_lat','3ms')
                begin = rings[i][1][0] # connection to main ring 1
                end = rings[i][1][1] # connection to main ring 2
                begin_names = rings[i][2][0] # start of namespace
                end_names = rings[i][2][1] + 1# end of namespace

                sw_list = []
                for j in range(begin_names,end_names):
                        sw_list.append(self.addSwitch('s{}'.format(j)))
                        if j == begin_names:
                                self.addLink(sw_list[j-begin_names],main_ring[begin-1], \
                                bw=bw,delay=lat)
                                continue
                        if j == (end_names - 1):
                                self.addLink(sw_list[j-begin_names],main_ring[end-1], \
                                bw=bw,delay=lat)
			self.addLink(sw_list[j-begin_names],sw_list[j-begin_names-1], \
				bw=bw,delay=lat)
		
		sr_list.extend(sw_list)
	main_ring.extend(sr_list)

# Add hosts: with or whithout access node
def add_hosts(self, hosts_names=[], sw_acc=None, sw_mr=None, mr=None, bw=None, delay=None, topo_desc=None):
	"""
	Add n_hosts to the main ring or secondary rings. Can have an access switch or be
	directly connected.
	"""
	n_hosts = len(hosts_names)
	if n_hosts == 1:
		hosts_names = [hosts_names[0],hosts_names[0]]

	if not sw_acc is None:
		mr.append(self.addSwitch('s{}'.format(sw_acc)))
		self.addLink(mr[-1], mr[sw_mr-1], bw=topo_desc.get('ring_link_bw'), delay=topo_desc.get('ring_link_lat'))
	else:
		sw_acc = sw_mr

	hosts_list =[]
	for i in range(hosts_names[0], hosts_names[1]+1):
		hosts_list.append(self.addHost('h{}'.format(i)))
		self.addLink(hosts_list[-1], mr[sw_acc-1], bw=bw, delay=delay)
	

# Read the condiguration for hosts and call add_hosts to add them all
def add_all_hosts(self, topo_desc=None, mr=None):
	hosts = topo_desc.get('hosts') # list with config for all the hosts
	def_bw = topo_desc.get('access_link_bw') # default values for bw and delay
	def_lat = topo_desc.get('access_link_lat')
	hosts_list = []
	
	for i_hosts in hosts:
		namespace = i_hosts[0] # namespace for hosts
		sw_mr = i_hosts[1] # switch from main or secodary ring to connect
		sw_acc = i_hosts[2] # name of access switch
              	if len(i_hosts) == 3: # bw and delay by default
			add_hosts(self, hosts_names=namespace, sw_acc=sw_acc, sw_mr=sw_mr, \
				mr=mr, bw=def_bw, delay=def_lat, topo_desc=topo_desc)		
		elif len(i_hosts) == 4: # bw specified but delay by default
			add_hosts(self, hosts_names=namespace, sw_acc=sw_acc, sw_mr=sw_mr, \
				mr=mr, bw=i_hosts[3], delay=def_lat, topo_desc=topo_desc)
		elif len(i_hosts) == 5: # bw and delay specified
			add_hosts(self, hosts_names=namespace, sw_acc=sw_acc, sw_mr=sw_mr, \
				mr=mr, bw=i_hosts[3], delay=i_hosts[4], topo_desc=topo_desc)


def add_datacenter(self, mr=None, datacenter_desc=None):
	bw = datacenter_desc.get('link_bw')
	lat = datacenter_desc.get('link_lat')
	n_servers = datacenter_desc.get('n_servers',4)
	name_sws = datacenter_desc.get('name_sws')
	sw_acc = datacenter_desc.get('sw_acc')
	links = datacenter_desc.get('sw_sv_links')
	
	# Add switches
	sw_list = []
	for sw in name_sws:
		sw_list.append(self.addSwitch('s{}'.format(sw)))
		for sw_acc_i in sw_acc:
			self.addLink(sw_list[-1], mr[sw_acc_i-1], bw=bw, delay=lat)

	# Add servers
	server_list = []
	for i in range(n_servers):
		server_list.append(self.addHost('sv{}'.format(i)))
	
	# Link servers to switches
	for sw_i, sw in enumerate(links):
		for sv in sw:
			self.addLink(server_list[sv-1], sw_list[sw_i],bw=bw,delay=lat) 


class DataCenterDistributed(Topo):
	"Distributed network and a data center connected to it."

	def __init__(self, topo_desc=None, datacenter_desc=None):
		"Create topology"
		
		# Initialize topology
		Topo.__init__(self)
		
		# Create distributed topology
		create_mr = main_ring
		create_sr = secondary_rings
		create_hosts = add_all_hosts
		create_datacenter = add_datacenter
	
		mr = create_mr(self,topo_desc)
		create_sr(self,topo_desc,main_ring=mr)
		create_hosts(self, topo_desc, mr=mr)

		# Create Data center onto existing topology
		create_datacenter(self, mr=mr, datacenter_desc=datacenter_desc)


class Distributed(Topo):
	"Distributed Network"

	def __init__(self, topo_desc=None):
		"Create topology"
		
		# Initialize topology
		Topo.__init__(self)
		
		create_mr = main_ring
		create_sr = secondary_rings
		create_hosts = add_all_hosts
	
		mr = create_mr(self,topo_desc)
		create_sr(self,topo_desc,main_ring=mr)
		create_hosts(self, topo_desc, mr=mr)



class Ring(Topo):
	"A simple ring"


	def __init__(self, topo_desc=None):
		Topo.__init__(self)
		
		create_ring = main_ring
		ring = create_ring(self, topo_desc)


topos = {'distributed': (lambda: Distributed(distributed_topo)), 
	'videostreaming': (lambda: DataCenterDistributed(distributed_topo, datacenter_desc)),
        'ring': (lambda: Ring(ring_topo))}
