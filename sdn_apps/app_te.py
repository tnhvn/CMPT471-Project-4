from email.policy import default
import json
from os import stat

import networkx as nx

from app import NetworkApp
from rule import  Action, ActionType, Rule, MatchPattern
from te_objs import PassByPathObjective, MinLatencyObjective, MaxBandwidthObjective
from utils_json import DefaultEncoder
import utils_net as un

class TEApp(NetworkApp):
    def __init__(self, topo_file, json_file, of_controller=None, priority=2):
        super(TEApp, self).__init__(
            topo_file, json_file, of_controller, priority)
        self.pass_by_paths_obj = []  # a list of PassByPathObjective objects
        self.min_latency_obj = []  # a list of MinLatencyObjective objects
        self.max_bandwidth_obj = []  # a list of MaxBandwidthObjective objects

    def add_pass_by_path_obj(self, pass_by_obj):
        self.pass_by_paths_obj.append(pass_by_obj)

    def add_min_latency_obj(self, min_lat_obj):
        self.min_latency_obj.append(min_lat_obj)

    def add_max_bandwidth_obj(self, max_bw_obj):
        self.max_bandwidth_obj.append(max_bw_obj)

    # This function reads the TE objectives in the `self.json_file`
    # Then, parses the JSON objects to the three list:
    #       self.pass_by_paths_obj
    #       self.min_latency_obj
    #       self.max_bandwidth_obj
    def from_json(self):
        with open('%s' % self.json_file) as f:
            # TODO: complete
            objects = json.load(f)
            print(object)

            pass_by_path_objs = objects["pass_by_paths"]
            min_lat_objs = objects["min_latency"]
            max_bw_objs = objects["max_bandwidth"]

            for obj in pass_by_path_objs:
                match_pattern = obj["match_pattern"]
                pass_by_obj = PassByPathObjective(
                    match_pattern=MatchPattern(match_pattern["src_mac"], match_pattern["dst_mac"], match_pattern["mac_proto"],
                                               match_pattern["ip_proto"], match_pattern["src_ip"], match_pattern["dst_ip"],
                                               match_pattern["src_port"], match_pattern["dst_port"], match_pattern["in_port"]),
                    switches=obj["switches"],
                    symmetric=obj["symmetric"])
                self.add_pass_by_path_obj(pass_by_obj)

            for obj in min_lat_objs:
                match_pattern = obj["match_pattern"]
                min_lat_obj = MinLatencyObjective(
                    match_pattern=MatchPattern(match_pattern["src_mac"], match_pattern["dst_mac"], match_pattern["mac_proto"],
                                               match_pattern["ip_proto"], match_pattern["src_ip"], match_pattern["dst_ip"],
                                               match_pattern["src_port"], match_pattern["dst_port"], match_pattern["in_port"]),
                    src_switch=obj["src_switch"],
                    dst_switch=obj["dst_switch"],
                    symmetric=obj["symmetric"])
                self.add_min_latency_obj(min_lat_obj)

            for obj in max_bw_objs:
                match_pattern = obj["match_pattern"]
                max_bw_obj = MaxBandwidthObjective(
                    match_pattern=MatchPattern(match_pattern["src_mac"], match_pattern["dst_mac"], match_pattern["mac_proto"],
                                               match_pattern["ip_proto"], match_pattern["src_ip"], match_pattern["dst_ip"],
                                               match_pattern["src_port"], match_pattern["dst_port"], match_pattern["in_port"]),
                    src_switch=obj["src_switch"],
                    dst_switch=obj["dst_switch"],
                    symmetric=obj["symmetric"])
                self.add_max_bandwidth_obj(max_bw_obj)
            pass

    # Translates the TE objectives to the `json_file`
    def to_json(self, json_file):
        json_dict = {
            'pass_by_paths': self.pass_by_paths_obj,
            'min_latency': self.min_latency_obj,
            'max_bandwidth': self.max_bandwidth_obj,
        }

        with open('%s' % json_file, 'w', encoding='utf-8') as f:
            json.dump(json_dict, f, ensure_ascii=False,
                      indent=4, cls=DefaultEncoder)

    # This function translates the objectives in `self.pass_by_paths_obj` to a list of Rules in `self.rules`
    # It should:
    #   call `self.calculate_rules_for_path` as needed
    #   handle traffic in reverse direction when `symmetric` is True
    #   call `self.send_openflow_rules()` at the end
    def provision_pass_by_paths(self):
        self.rules = []
        # TODO: complete
        for obj in self.pass_by_paths_obj:
            path = [str(x) for x in obj.switches]
            self.rules.extend(self.calculate_rules_for_path(
                path=path, match_pattern=obj.match_pattern))
            if (obj.symmetric):
                path = path.reverse()
                self.rules.extend(self.calculate_rules_for_path(
                    path=path, match_pattern=obj.match_pattern))
        self.send_openflow_rules()

    # This function translates the objectives in `self.min_latency_obj` to a list of Rules in `self.rules`
    # It should:
    #   call `self.calculate_rules_for_path` as needed
    #   consider using the function `networkx.shortest_path` in the networkx package
    #   handle traffic in reverse direction when `symmetric` is True
    #   call `self.send_openflow_rules()` at the end
    def provision_min_latency_paths(self):
        self.rules = []
        # TODO: complete

        for n1 in self.topo.nodes():
            pattern = MatchPattern(dst_mac=un.mn_get_host_mac(n1))
            action = Action(action_type=ActionType.FORWARD, out_port=1)
            rule = Rule(switch_id=int(n1), match_pattern=pattern, action=action)
            self.add_rule(rule)

        for obj in self.min_latency_obj:
            path = nx.shortest_path(self.topo, str(obj.src_switch), 
                str(obj.dst_switch), weight='delay')

            # print(path)

            obj.match_pattern.src_mac = un.mn_get_host_mac(obj.src_switch)
            obj.match_pattern.dst_mac = un.mn_get_host_mac(obj.dst_switch)

            # self.rules.extend(self.calculate_rules_for_path(path=path, 
            #     match_pattern=obj.match_pattern))
            
            rules = self.calculate_rules_for_path(path=path, match_pattern=obj.match_pattern)
            for r in rules:
                self.add_rule(r)

            if (obj.symmetric):

                obj.match_pattern.src_mac = un.mn_get_host_mac(obj.dst_switch)
                obj.match_pattern.dst_mac = un.mn_get_host_mac(obj.src_switch)

                path = nx.shortest_path(self.topo, str(obj.dst_switch), 
                    str(obj.src_switch), 'delay')
                rules = self.calculate_rules_for_path(path=path, match_pattern=obj.match_pattern)
                for r in rules:
                    self.add_rule(r)

        self.send_openflow_rules()


    # BONUS:
    # This function translates the objectives in `self.max_bandwidth_obj` to a list of Rules in `self.rules`
    # It should:
    #   call `self.calculate_rules_for_path` as needed
    #   consider what algorithms to use (from networkx) to calculate the paths
    #   handle traffic in reverse direction when `symmetric` is True
    #   call `self.send_openflow_rules()` at the end
    def provision_max_bandwidth_paths(self):
        self.rules = []
        print(self.topo.edges())
        for edge in self.topo.edges():
            print (self.topo[1][2])
            print((self.topo.get_edge_data("1", "2", default = 0))["bw"])
        for obj in self.min_latency_obj:
            path = self.max_bandwidth_path(str(obj.src_switch), 
                str(obj.dst_switch))
            self.rules.extend(self.calculate_rules_for_path(
                path=path, match_pattern=obj.match_pattern))
            if (obj.symmetric):
                path = self.max_bandwidth_path(str(obj.dst_switch), 
                    str(obj.src_switch))
                self.rules.extend(self.calculate_rules_for_path(
                    path=path, match_pattern=obj.match_pattern))
                pass
        self.send_openflow_rules()
        pass

    # def max_bandwidth_path(self, src_switch, dst_switch):
    #     path = []
    #     status = {}  # status map
    #     parent = {}  # store the parent of current switch
    #     fringe = {} # fringes are stored in a list
    #     bw = {}  # bandwidth associated with each switch

    #     for v in self.topo.nodes():
    #         status[v] = 'unseen'

    #     bw[src_switch] = float('inf')
    #     parent[src_switch] = None
    #     status[src_switch] = 'intree'

    #     for edge in self.topo.edges():
    #         if (edge[0] == src_switch):
    #             v = edge[1]
    #             parent[v] = src_switch
    #             status[v] = 'fringe'
    #             bw[v] = (self.topo.get_edge_data(edge[0], edge[1]))["bw"]
    #             fringe[v] = bw[v]      
        
    #     while (len(fringe)!=0) and (not status[dst_switch] == 'intree'):

    #     return path


    # BONUS: Used to react to changes in the network (the controller notifies the App)
    def on_notified(self, change, n1, n2):
        if change == 'linkdown':
            self.topo.remove_edge(n1, n2)
            self.provision_min_latency_paths()
        print('network changed')
