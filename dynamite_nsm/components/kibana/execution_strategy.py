import os
from dynamite_nsm import const
from dynamite_nsm.services.kibana import install, process
from dynamite_nsm.components.base import execution_strategy
from dynamite_nsm.utilities import check_socket, prompt_input


def print_message(msg):
    print(msg)


def remove_kibana_tar_archive():
    dir_path = os.path.join(const.INSTALL_CACHE, const.KIBANA_ARCHIVE_NAME)
    if os.path.exists(dir_path):
        os.remove(dir_path)


def check_elasticsearch_target(host, port, perform_check=True):
    if not perform_check:
        return
    if not check_socket(host, port):
        print("ElasticSearch does not appear to be started on: {}:{}.".format(host, port))
        if str(prompt_input('Continue? [y|N]: ')).lower() != 'y':
            exit(0)
    return


class KibanaInstallStrategy(execution_strategy.BaseExecStrategy):

    def __init__(self, listen_address, listen_port, elasticsearch_host, elasticsearch_port, elasticsearch_password,
                 check_elasticsearch_connection, stdout, verbose):
        execution_strategy.BaseExecStrategy.__init__(
            self,
            strategy_name="kibana_install",
            strategy_description="Install Kibana with Dynamite Analytic views and connect to ElasticSearch.",
            functions=(
                check_elasticsearch_target,
                remove_kibana_tar_archive,
                install.install_kibana,
                process.stop,
                print_message,
                print_message
            ),
            arguments=(
                # check_elasticsearch_target
                {
                    "perform_check": bool(check_elasticsearch_connection),
                    "host": str(elasticsearch_host),
                    "port": int(elasticsearch_port)
                },
                # remove_kibana_tar_archive
                {},
                # install.install_kibana
                {
                    "configuration_directory": "/etc/dynamite/kibana/",
                    "install_directory": "/opt/dynamite/kibana/",
                    "log_directory": "/var/log/dynamite/kibana/",
                    "host": str(listen_address),
                    "port": int(listen_port),
                    "elasticsearch_host": str(elasticsearch_host),
                    "elasticsearch_port": int(elasticsearch_port),
                    "elasticsearch_password": str(elasticsearch_password),
                    "create_dynamite_user": True,
                    "stdout": bool(stdout),
                    "verbose": bool(verbose)
                },

                # process.stop
                {
                    "stdout": False
                },

                # print_message
                {
                    "msg": '[+] *** Kibana installed successfully. ***\n'
                },
                # print_message
                {
                    "msg": '[+] Next, Start your cluster: '
                           '\'dynamite kibana start\'.'
                }
            ),
            return_formats=(
                None,
                None,
                None,
                None,
                None,
                None
            ))


class KibanaUninstallStrategy(execution_strategy.BaseExecStrategy):

    def __init__(self, stdout, prompt_user):
        execution_strategy.BaseExecStrategy.__init__(
            self, strategy_name="kibana_uninstall",
            strategy_description="Uninstall Kibana.",
            functions=(
                install.uninstall_kibana,
                print_message
            ),
            arguments=(
                # install.uninstall_kibana
                {
                    "stdout": bool(stdout),
                    "prompt_user": bool(prompt_user)
                },

                # print_message
                {
                    "msg": '[+] *** Kibana uninstalled successfully. ***\n'
                },
            ),
            return_formats=(
                None,
                None
            )
        )


class KibanaProcessStartStrategy(execution_strategy.BaseExecStrategy):

    def __init__(self, stdout, status):
        execution_strategy.BaseExecStrategy.__init__(
            self,
            strategy_name="kibana_start",
            strategy_description="Start Kibana process.",
            functions=(
                process.start,
            ),
            arguments=(
                # process.start
                {
                    "stdout": stdout
                },
            ),
            return_formats=(
                None,
            )

        )
        if status:
            self.add_function(process.status, {}, return_format="json")


class KibanaProcessStopStrategy(execution_strategy.BaseExecStrategy):

    def __init__(self, stdout, status):
        execution_strategy.BaseExecStrategy.__init__(
            self, strategy_name="kibana_stop",
            strategy_description="Stop Kibana process.",
            functions=(
                process.stop,
            ),
            arguments=(
                # process.start
                {
                    "stdout": stdout
                },
            ),
            return_formats=(
                None,
            )

        )
        if status:
            self.add_function(process.status, {}, return_format="json")


class KibanaProcessRestartStrategy(execution_strategy.BaseExecStrategy):

    def __init__(self, stdout, status):
        execution_strategy.BaseExecStrategy.__init__(
            self, strategy_name="kibana_restart",
            strategy_description="Restart Kibana process.",
            functions=(
                process.stop,
                process.start,
            ),
            arguments=(
                # process.start
                {
                    "stdout": stdout
                },

                # process.stop
                {
                    "stdout": stdout
                }
            ),
            return_formats=(
                None,
                None
            )
        )
        if status:
            self.add_function(process.status, {}, return_format="json")


class KibanaProcessStatusStrategy(execution_strategy.BaseExecStrategy):

    def __init__(self):
        execution_strategy.BaseExecStrategy.__init__(
            self, strategy_name="kibana_status",
            strategy_description="Get the status of the Kibana process.",
            functions=(
                process.status,
            ),
            arguments=(
                # process.status
                {},
            ),
            return_formats=(
                'json',
            )
        )


# Test Functions


def run_install_strategy():
    kb_install_strategy = KibanaInstallStrategy(
        listen_address="0.0.0.0",
        listen_port=5601,
        elasticsearch_host="localhost",
        elasticsearch_port=9200,
        elasticsearch_password="changeme",
        check_elasticsearch_connection=False,
        stdout=True,
        verbose=True
    )
    kb_install_strategy.execute_strategy()


def run_uninstall_strategy():
    kb_uninstall_strategy = KibanaUninstallStrategy(
        stdout=True,
        prompt_user=False
    )
    kb_uninstall_strategy.execute_strategy()


def run_process_start_strategy():
    kb_start_strategy = KibanaProcessStartStrategy(
        stdout=True,
        status=True
    )
    kb_start_strategy.execute_strategy()


def run_process_stop_strategy():
    kb_stop_strategy = KibanaProcessStopStrategy(
        stdout=True,
        status=True
    )
    kb_stop_strategy.execute_strategy()


def run_process_restart_strategy():
    kb_restart_strategy = KibanaProcessRestartStrategy(
        stdout=True,
        status=True
    )
    kb_restart_strategy.execute_strategy()


def run_process_status_strategy():
    kb_status_strategy = KibanaProcessStatusStrategy()
    kb_status_strategy.execute_strategy()


if __name__ == '__main__':
    run_install_strategy()
    run_process_start_strategy()
    run_process_stop_strategy()
    run_process_restart_strategy()
    run_process_status_strategy()
    run_uninstall_strategy()
    pass
