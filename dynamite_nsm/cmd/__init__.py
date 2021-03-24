import argparse
from typing import Optional

from dynamite_nsm.cmd import elasticsearch, logstash, kibana, suricata, zeek, filebeat, updates


def process_arguments(args: argparse.Namespace, component: Optional[str], interface: Optional[str] = None,
                      sub_interface: Optional[str] = None):
    """
    Selects the proper execution context given an argparse.Namespace, executes the namespace against that context

    :param args: The argparse.Namespace object containing all the user selected commandline arguments
    :param component: A string representing the name of the component (elasticsearch, logstash, kibana, zeek, suricata,
                      or filebeat)
    :param interface: A string representing the name of the interface (E.G config, install, process, logs, uninstall)
    :param sub_interface: A string representing a sub-interface (for example a config or log name)

    :return: The results of the executed context.
    """
    component_modules = dict(
        elasticsearch=elasticsearch,
        logstash=logstash,
        kibana=kibana,
        zeek=zeek,
        suricata=suricata,
        filebeat=filebeat,
        updates=updates
    )

    try:
        component_interface = getattr(component_modules[component], interface)
        if sub_interface:
            component_interface = getattr(component_interface, sub_interface)
    except KeyError:
        raise ModuleNotFoundError(f'{component} is not a valid component module.')
    except AttributeError:
        raise ModuleNotFoundError(f'{component}.{interface} is not a valid interface module.')
    return component_interface.interface.execute(args)
