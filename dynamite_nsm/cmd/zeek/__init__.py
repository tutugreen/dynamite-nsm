import argparse

from dynamite_nsm.cmd.service_interfaces import append_service_interface_to_parser, append_service_interfaces_to_parser
from dynamite_nsm.cmd.zeek import install, process, uninstall
from dynamite_nsm.cmd.zeek.logs import get_interfaces as get_logs_interfaces
from dynamite_nsm.utilities import get_primary_ip_address


def get_action_parser():
    parser = argparse.ArgumentParser(description=f'Zeek @ {get_primary_ip_address()}')
    subparsers = parser.add_subparsers()

    append_service_interface_to_parser(subparsers, 'install', install.interface, interface_group_name='interface')
    append_service_interface_to_parser(subparsers, 'uninstall', uninstall.interface, interface_group_name='interface')
    append_service_interface_to_parser(subparsers, 'process', process.interface, interface_group_name='interface')
    log_parser = subparsers.add_parser('logs', help='Attach to various Zeek logs.')
    log_parser.set_defaults(interface='logs')
    log_sub_parsers = log_parser.add_subparsers()
    append_service_interfaces_to_parser(log_sub_parsers, interfaces=get_logs_interfaces(),
                                        interface_group_name='sub_interface')
    return parser


def get_interfaces():
    return dict(
        install=install.interface,
        uninstall=uninstall.interface,
        process=process.interface,
        logs=get_logs_interfaces()
    )
