# sdn-diagnosis
Fault Diagnosis on SDN Networks

## Mininet
Launch mininet:
```
sudo ./pox.py forwarding.l2_pairs openflow.discovery openflow.spanning_tree --no-flood --hold-down log.level --INFO
```

Lauch with monitor module enabled and grepping for interesting data only:
```
sudo ./pox.py forwarding.l2_pairs openflow.discovery openflow.spanning_tree --no-flood --hold-down monitor log.level --DEBUG 2>&1 | grep -i "Monitor\|connected\|ports"
```
