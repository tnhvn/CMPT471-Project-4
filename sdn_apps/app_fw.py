import json

from app import NetworkApp
from rule import Action, ActionType, Rule, MatchPattern
from utils_json import DefaultEncoder


def parse_action(d):
    if 'action_type' in d:
        return {
            'action_type': getattr(ActionType, d['action_type']),
            'out_port': d.get('out_port', None)
        }
    return d


class FirewallApp(NetworkApp):
    def __init__(self, json_file, of_controller=None, priority=3):
        super(FirewallApp, self).__init__(
            None, json_file, of_controller, priority)

    # Translates the firewall policy file in `self.json_file` to a list of Rule objects `self.rules`
    def from_json(self):
        with open('%s' % self.json_file) as f:
            rules = json.load(f, object_hook=parse_action)
            # TODO: complete
            self.rules = []
            for rule in rules:
                match_pattern = rule["match_pattern"]
                action = rule["action"]
                self.rules.append(Rule(
                    switch_id=rule["switch_id"],
                    match_pattern=MatchPattern(match_pattern["src_mac"], match_pattern["dst_mac"], match_pattern["mac_proto"],
                                               match_pattern["ip_proto"], match_pattern["src_ip"], match_pattern["dst_ip"],
                                               match_pattern["src_port"], match_pattern["dst_port"], match_pattern["in_port"]),
                    action=Action(action["action_type"], action["out_port"])))

    # Writes the firewall policy to a JSON file
    def to_json(self, json_file):
        with open('%s' % json_file, 'w', encoding='utf-8') as f:
            json.dump(self.rules, f, ensure_ascii=False,
                      indent=4, cls=DefaultEncoder)

    # This function calls `send_openflow_rules` only.
    # This is because the policy is the actual OpenFlow rules to be sent.
    def calculate_firewall_rules(self):
        self.send_openflow_rules()

    # BONUS: Used to react to changes in the network (the controller notifies the App)
    def on_notified(self, **kwargs):
        print('network change')
