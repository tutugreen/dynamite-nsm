import argparse


from dynamite_nsm.utilities import get_primary_ip_address
from dynamite_nsm.cmd.kibana import install, process, uninstall
from dynamite_nsm.service_to_commandline import append_interface_to_parser, append_interfaces_to_parser
from dynamite_nsm.cmd.kibana.config import get_interfaces as get_config_interfaces

KIBANA_CONFIG_HELP = 'Modify Kibana configurations.'

def get_action_parser():
    parser = argparse.ArgumentParser(description=f'Kibana @ {get_primary_ip_address()}')
    subparsers = parser.add_subparsers()
    append_interface_to_parser(subparsers, 'install', install.interface)
    append_interface_to_parser(subparsers, 'uninstall', uninstall.interface)
    append_interface_to_parser(subparsers, 'process', process.interface)

    config_parser = subparsers.add_parser('config', help=KIBANA_CONFIG_HELP)
    config_parser.set_defaults(sub_interface='config')
    config_sub_parsers = config_parser.add_subparsers()
    append_interfaces_to_parser(config_sub_parsers, interfaces=get_config_interfaces())
    return parser


def get_interfaces():
    return dict(
        install=install.interface,
        uninstall=uninstall.interface,
        process=process.interface,
        config=(get_config_interfaces(), KIBANA_CONFIG_HELP)
    )