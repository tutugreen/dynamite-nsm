import os
import sys
import json
import time
import base64
import shutil
from yaml import load, dump

try:
    from urllib2 import urlopen
    from urllib2 import URLError
    from urllib2 import HTTPError
    from urllib2 import Request
except Exception:
    from urllib.request import urlopen
    from urllib.error import URLError
    from urllib.error import HTTPError
    from urllib.request import Request
    from urllib.parse import urlencode

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

from dynamite_nsm import const
from dynamite_nsm import utilities
from dynamite_nsm import exceptions as general_exceptions
from dynamite_nsm.services.elasticsearch import exceptions as elastic_exceptions


class ConfigManager:
    """
    Wrapper for configuring elasticsearch.yml and jvm.options
    """

    tokens = {
        'node_name': ('node.name',),
        'cluster_name': ('cluster.name',),
        'seed_hosts': ('discovery.seed_hosts',),
        'initial_master_nodes': ('cluster.initial_master_nodes',),
        'network_host': ('network.host',),
        'http_port': ('http.port',),
        'path_data': ('path.data',),
        'path_logs': ('path.logs',),
        'search_max_buckets': ('search.max_buckets',),
    }

    def __init__(self, configuration_directory):
        """
        :param configuration_directory: Path to the configuration directory (E.G /etc/dynamite/elasticsearch/)
        """
        self.configuration_directory = configuration_directory
        self.java_home = None
        self.ls_home = None
        self.ls_path_conf = None
        self.java_initial_memory = None
        self.java_maximum_memory = None

        self.node_name = None
        self.cluster_name = None
        self.seed_hosts = None
        self.initial_master_nodes = None
        self.network_host = None
        self.http_port = None
        self.path_data = None
        self.path_logs = None
        self.search_max_buckets = None

        self._parse_environment_file()
        self._parse_jvm_options()
        self._parse_elasticyaml()

    def _parse_elasticyaml(self):

        def set_instance_var_from_token(variable_name, data):
            """
            :param variable_name: The name of the instance variable to update
            :param data: The parsed yaml object
            :return: True if successfully located
            """
            if variable_name not in self.tokens.keys():
                return False
            key_path = self.tokens[variable_name]
            value = data
            try:
                for k in key_path:
                    value = value[k]
                setattr(self, var_name, value)
            except KeyError:
                pass
            return True

        elasticyaml_path = os.path.join(self.configuration_directory, 'elasticsearch.yml')
        try:
            with open(elasticyaml_path, 'r') as configyaml:
                self.config_data = load(configyaml, Loader=Loader)
        except IOError:
            raise elastic_exceptions.ReadElasticConfigError("Could not locate config at {}".format(elasticyaml_path))
        except Exception as e:
            raise elastic_exceptions.ReadElasticConfigError(
                "General exception when opening/parsing config at {}; {}".format(elasticyaml_path, e))

        for var_name in vars(self).keys():
            set_instance_var_from_token(variable_name=var_name, data=self.config_data)

    def _parse_jvm_options(self):
        """
        Parses the initial and max heap allocation from jvm.options configuration
        :return: A dictionary containing the initial_memory and maximum_memory allocated to JVM heap
        """
        config_path = os.path.join(self.configuration_directory, 'jvm.options')
        try:
            with open(config_path) as config_f:
                for line in config_f.readlines():
                    if not line.startswith('#') and '-Xms' in line:
                        self.java_initial_memory = int(line.replace('-Xms', '').strip()[0:-1])
                    elif not line.startswith('#') and '-Xmx' in line:
                        self.java_maximum_memory = int(line.replace('-Xmx', '').strip()[0:-1])
        except IOError:
            raise general_exceptions.ReadJavaConfigError("Could not locate config at {}".format(config_path))
        except Exception as e:
            raise general_exceptions.ReadJavaConfigError(
                "General Exception when opening/parsing config at {}; {}".format(config_path, e))

    def _parse_environment_file(self):
        """
        Parses the /etc/dynamite/environment file and returns results for JAVA_HOME, ES_PATH_CONF, ES_HOME;
        stores the results in class variables of the same name
        """
        env_path = os.path.join(const.CONFIG_PATH, 'environment')
        try:
            with open(env_path) as env_f:
                for line in env_f.readlines():
                    if line.startswith('JAVA_HOME'):
                        self.java_home = line.split('=')[1].strip()
                    elif line.startswith('ES_PATH_CONF'):
                        self.es_path_conf = line.split('=')[1].strip()
                    elif line.startswith('ES_HOME'):
                        self.es_home = line.split('=')[1].strip()
        except IOError:
            raise general_exceptions.ReadConfigError("Could not locate environment config at {}".format(env_path))
        except Exception as e:
            raise general_exceptions.ReadConfigError(
                "General Exception when opening/parsing environment config at {}; {}".format(env_path, e))

    def write_jvm_config(self):
        """
        Overwrites the JVM initial/max memory if settings were updated
        """
        new_output = ''
        jvm_options_path = os.path.join(self.configuration_directory, 'jvm.options')
        try:
            with open(jvm_options_path) as config_f:
                for line in config_f.readlines():
                    if not line.startswith('#') and '-Xms' in line:
                        new_output += '-Xms' + str(self.java_initial_memory) + 'g'
                    elif not line.startswith('#') and '-Xmx' in line:
                        new_output += '-Xmx' + str(self.java_maximum_memory) + 'g'
                    else:
                        new_output += line
                    new_output += '\n'
        except IOError:
            raise general_exceptions.ReadJavaConfigError("Could not locate {}".format(jvm_options_path))
        except Exception as e:
            raise general_exceptions.ReadJavaConfigError(
                "General Exception when opening/parsing environment config at {}; {}".format(
                    self.configuration_directory, e))

        backup_configurations = os.path.join(self.configuration_directory, 'config_backups/')
        java_config_backup = os.path.join(backup_configurations, 'jvm.options.backup.{}'.format(
            int(time.time())
        ))
        try:
            os.makedirs(backup_configurations, exist_ok=True)
        except Exception as e:
            raise general_exceptions.WriteJavaConfigError(
                "General error while attempting to create backup directory at {}; {}".format(backup_configurations, e))
        try:
            shutil.copy(os.path.join(self.configuration_directory, 'jvm.options'), java_config_backup)
        except Exception as e:
            raise general_exceptions.WriteJavaConfigError(
                "General error while attempting to copy old jvm.options file to {}; {}".format(backup_configurations,
                                                                                               e))
        try:
            with open(os.path.join(self.configuration_directory, 'jvm.options'), 'w') as config_f:
                config_f.write(new_output)
        except IOError:
            raise general_exceptions.WriteJavaConfigError("Could not locate {}".format(self.configuration_directory))
        except Exception as e:
            raise general_exceptions.WriteJavaConfigError(
                "General error while attempting to write new jvm.options file to {}; {}".format(backup_configurations,
                                                                                                e))

    def write_elasticsearch_config(self):

        def update_dict_from_path(path, value):
            """
            :param path: A tuple representing each level of a nested path in the yaml document
                        ('vars', 'address-groups', 'HOME_NET') = /vars/address-groups/HOME_NET
            :param value: The new value
            :return: None
            """
            partial_config_data = self.config_data
            for i in range(0, len(path) - 1):
                try:
                    partial_config_data = partial_config_data[path[i]]
                except KeyError:
                    pass
            partial_config_data.update({path[-1]: value})

        timestamp = int(time.time())
        backup_configurations = os.path.join(self.configuration_directory, 'config_backups/')
        elastic_config_backup = os.path.join(backup_configurations, 'elastic.yml.backup.{}'.format(timestamp))
        try:
            os.makedirs(backup_configurations, exist_ok=True)
        except Exception as e:
            raise elastic_exceptions.WriteElasticConfigError(
                "General error while attempting to create backup directory at {}; {}".format(backup_configurations, e))
        try:
            shutil.copy(os.path.join(self.configuration_directory, 'elasticsearch.yml'), elastic_config_backup)
        except Exception as e:
            raise elastic_exceptions.WriteElasticConfigError(
                "General error while attempting to copy old elasticsearch.yml file to {}; {}".format(
                    backup_configurations, e))
        for k, v in vars(self).items():
            if k not in self.tokens:
                continue
            token_path = self.tokens[k]
            update_dict_from_path(token_path, v)
        try:
            with open(os.path.join(self.configuration_directory, 'elasticsearch.yml'), 'w') as configyaml:
                dump(self.config_data, configyaml, default_flow_style=False)
        except IOError:
            raise elastic_exceptions.WriteElasticConfigError("Could not locate {}".format(self.configuration_directory))
        except Exception as e:
            raise elastic_exceptions.WriteElasticConfigError(
                "General error while attempting to write new elasticsearch.yml file to {}; {}".format(
                    self.configuration_directory, e))

    def write_configs(self):
        """
        Writes both the JVM and elasticsearch.yml configurations, backs up originals
        """
        self.write_elasticsearch_config()
        self.write_jvm_config()


class PasswordConfigManager:
    """
    Provides a basic interface for resetting ElasticSearch passwords
    """

    def __init__(self, auth_user, current_password):
        self.auth_user = auth_user
        self.current_password = current_password
        self.env_vars = utilities.get_environment_file_dict()

    def _set_user_password(self, user, password, stdout=False):
        if stdout:
            sys.stdout.write('[+] Updating password for {}\n'.format(user))
        try:
            try:
                es_config = ConfigManager(configuration_directory=self.env_vars.get('ES_PATH_CONF'))
            except general_exceptions.ReadConfigError as e:
                raise general_exceptions.ResetPasswordError("Could not read configuration; {}".format(e))
            try:
                try:
                    base64string = base64.b64encode('%s:%s' % (self.auth_user, self.current_password))
                except TypeError:
                    encoded_bytes = '{}:{}'.format(self.auth_user, self.current_password).encode('utf-8')
                    base64string = base64.b64encode(encoded_bytes).decode('utf-8')
                url_request = Request(
                    url='http://{}:{}/_xpack/security/user/{}/_password'.format(
                        es_config.network_host,
                        es_config.http_port,
                        user
                    ),
                    data=json.dumps({'password': password}),
                    headers={'Content-Type': 'application/json', 'kbn-xsrf': True}
                )
                url_request.add_header("Authorization", "Basic %s" % base64string)
                try:
                    urlopen(url_request)
                except TypeError:
                    urlopen(url_request, data=json.dumps({'password': password}).encode('utf-8'))
            except HTTPError as e:
                if e.code != 200:
                    sys.stderr.write('[-] Failed to update {} password - [{}]\n'.format(user, e))
                    raise general_exceptions.ResetPasswordError(
                        "Elasticsearch API returned a {} code while attempting to reset user: {} password; {}".format(
                            e.code, user, e))
        except Exception as e:
            raise general_exceptions.ResetPasswordError(
                "General exception while resetting Elasticsearch password; {}".format(e))

    def set_apm_system_password(self, new_password, stdout=False):
        """
        Reset the builtin apm_system user

        :param new_password: The new password
        :param stdout: Print status to stdout
        """
        self._set_user_password('apm_system', new_password, stdout=stdout)

    def set_beats_password(self, new_password, stdout=False):
        """
        Reset the builtin beats user

        :param new_password: The new password
        :param stdout: Print status to stdout
        """
        self._set_user_password('beats_system', new_password, stdout=stdout)

    def set_elastic_password(self, new_password, stdout=False):
        """
        Reset the builtin elastic user

        :param new_password: The new password
        :param stdout: Print status to stdout
        """
        self._set_user_password('elastic', new_password, stdout=stdout)

    def set_kibana_password(self, new_password, stdout=False):
        """
        Reset the builtin kibana user

        :param new_password: The new password
        :param stdout: Print status to stdout
        """
        self._set_user_password('kibana', new_password, stdout=stdout)

    def set_logstash_system_password(self, new_password, stdout=False):
        """
        Reset the builtin logstash user

        :param new_password: The new password
        :param stdout: Print status to stdout
        """
        self._set_user_password('logstash_system', new_password, stdout=stdout)

    def set_remote_monitoring_password(self, new_password, stdout=False):
        """
        Reset the builtin remote_monitoring_user user

        :param new_password: The new password
        :param stdout: Print status to stdout
        """
        self._set_user_password('remote_monitoring_user', new_password, stdout=stdout)

    def set_all_passwords(self, new_password, stdout=False):
        """
        Reset all builtin user passwords

        :param new_password: The new password
        :param stdout: Print status to stdout
        """
        self.set_apm_system_password(new_password, stdout=stdout)
        self.set_remote_monitoring_password(new_password, stdout=stdout)
        self.set_logstash_system_password(new_password, stdout=stdout)
        self.set_kibana_password(new_password, stdout=stdout)
        self.set_beats_password(new_password, stdout=stdout)
        self.set_elastic_password(new_password, stdout=stdout)


def change_elasticsearch_password(old_password, password='changeme', stdout=False):
    """
    Change the Elasticsearch password for all builtin users

    :param old_password: The old Elasticsearch password
    :param password: The new Elasticsearch password
    :param stdout: Print status to stdout
    :return: True, if successful
    """
    from dynamite_nsm.services.elasticsearch import process as elastic_process
    from dynamite_nsm.services.elasticsearch import profile as elastic_profile

    if not elastic_process.ProcessManager().start():
        sys.stderr.write('[-] Could not start ElasticSearch Process. Password reset failed.')
        raise general_exceptions.ResetPasswordError(
            "Elasticsearch process was not able to start, check your elasticsearch logs.")
    while not elastic_profile.ProcessProfiler().is_listening:
        if stdout:
            sys.stdout.write('[+] Waiting for ElasticSearch API to become accessible.\n')
        time.sleep(1)
    if stdout:
        sys.stdout.write('[+] ElasticSearch API is up.\n')
        sys.stdout.write('[+] Sleeping for 10 seconds, while ElasticSearch API finishes booting.\n')
        sys.stdout.flush()
    time.sleep(10)
    es_pw_config = PasswordConfigManager(
        'elastic', current_password=old_password)
    es_pw_config.set_all_passwords(password, stdout=stdout)
