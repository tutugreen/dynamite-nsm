import logging
import os
import subprocess

from dynamite_nsm import utilities
from dynamite_nsm.logger import get_logger


def update_suricata_rules(stdout=True, verbose=False):
    """
    Update Suricata rules specified in the oinkmaster.conf file

    :param stdout: Print the output to console
    :param verbose: Include detailed debug messages
    """
    log_level = logging.INFO
    if verbose:
        log_level = logging.DEBUG
    logger = get_logger('OINKMASTER', level=log_level, stdout=stdout)
    environment_variables = utilities.get_environment_file_dict()
    suricata_config_directory = environment_variables.get('SURICATA_CONFIG')
    suricata_rules_directory = os.path.join(suricata_config_directory, "rules")
    logger.info(f'Updating Suricata rules: {suricata_rules_directory}.')
    if not suricata_config_directory:
        logger.error("Could not resolve SURICATA_CONFIG environment_variable. Is Suricata installed?")
        raise UpdateSuricataRulesError(
            "Could not resolve SURICATA_CONFIG environment_variable. Is Suricata installed?")
    oinkmaster_install_directory = environment_variables.get('OINKMASTER_HOME')
    p = subprocess.Popen(f'./oinkmaster.pl -C oinkmaster.conf -o {suricata_rules_directory}',
                         cwd=oinkmaster_install_directory, shell=True, stderr=subprocess.PIPE)
    err = p.communicate()
    if p.returncode != 0:
        logger.error(f'Oinkmaster returned a non-zero exit-code: {p.returncode}.')
        raise UpdateSuricataRulesError(f'Oinkmaster returned a non-zero exit-code: {p.returncode}; err: {err}.')


class UpdateSuricataRulesError(Exception):
    """
    Thrown when Suricata rules fail to update
    """

    def __init__(self, message):
        """
        :param message: A more specific error message
        """
        msg = "An error occurred while updating Suricata rule-sets: {}".format(message)
        super(UpdateSuricataRulesError, self).__init__(msg)
