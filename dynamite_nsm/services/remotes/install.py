import os
import json
import tarfile
from typing import Optional

from dynamite_nsm import utilities
from dynamite_nsm.services.base import install, systemctl


class InstallManager(install.BaseInstallManager):

    def __init__(self, install_directory: str, stdout: Optional[bool] = False, verbose: Optional[bool] = False):
        """ Install a new remote manager authentication package
        Args:
            install_directory: Path to the install directory (E.G /opt/dynamite/remotes/)
            stdout: Print output to console
            verbose: Include detailed debug messages
        """
        super().__init__('node', verbose, stdout)
        self.install_directory = install_directory

    @staticmethod
    def patch_sshd_config() -> None:
        """Locate and patch the sshd_config file with logic to allow only pubkey auth for dynamite-remote user.
        Returns:
            None
        """
        sshd_config_location = None
        sshd_config_addition = '\nMatch User dynamite-remote' \
                               '\n\tPasswordAuthentication no' \
                               '\n\tPubkeyAuthentication yes\n'

        probable_sshd_locations = ['/etc/ssh/sshd_config']
        for loc in probable_sshd_locations:
            if os.path.exists(loc):
                sshd_config_location = loc
                break
        if sshd_config_location:
            with open(sshd_config_location, 'r') as sshd_config_in:
                if 'Match User dynamite-remote' not in sshd_config_in.read():
                    with open(sshd_config_location, 'a') as sshd_config_out:
                        sshd_config_out.write(sshd_config_addition)

    @staticmethod
    def patch_sudoers_file() -> None:
        """Add logic to allow the dynamite-remote user root access to invoke dynamite commandline utility w/o a password
        Returns:
            None
        """
        sudoers_file_location = None
        sudoers_file_addition = '\ndynamite-remote ALL=(ALL) NOPASSWD: /usr/local/bin/dynamite\n'
        probable_sudoers_locations = ['/etc/sudoers']
        for loc in probable_sudoers_locations:
            if os.path.exists(loc):
                sudoers_file_location = loc
                break
        if sudoers_file_location:
            with open(sudoers_file_location, 'r') as sudoers_file_in:
                if sudoers_file_addition not in sudoers_file_in.read():
                    with open(sudoers_file_location, 'a') as sudoers_file_out:
                        sudoers_file_out.write(sudoers_file_addition)

    def setup(self, archive: str) -> None:
        """ Install node to remotely manage this instance of DynamiteNSM

        Args:
            archive: The path to the tar.gz archive generated by the dynamite-remote utility.

        Returns:
            None
        """
        tar = tarfile.open(archive)
        metadata = json.load(tar.extractfile('metadata.json'))
        utilities.create_dynamite_remote_user()
        remote_user_root = '/home/dynamite-remote/'
        pub_key_root = f'{remote_user_root}/.ssh/'
        pub_key_file_path = f'{pub_key_root}/authorized_keys'
        pub_key_content = tar.extractfile('key.pub').read()
        self.logger.debug(f'Creating directory: {self.install_directory}')
        utilities.makedirs(self.install_directory)
        self.logger.debug(f'Creating directory: {pub_key_root}')
        utilities.makedirs(pub_key_root)
        self.logger.debug(f'Setting permissions of {pub_key_root} to 700.')
        utilities.set_permissions_of_file(pub_key_root, 700)
        self.logger.debug(f'Setting up public key for {metadata["hostname"]}')

        # Install the public key
        self.logger.info(f'Installing public key for {metadata["hostname"]}')
        with open(pub_key_file_path, 'a') as pub_key_out:
            pub_key_out.write('\n' + pub_key_content.decode('utf-8'))
            self.logger.debug(f'Setting permissions of {pub_key_file_path} to 644.')
            utilities.set_permissions_of_file(pub_key_file_path, 644)

        # Install the metadata file
        with open(f'{self.install_directory}/{metadata["hostname"]}', 'w') as metadata_out:
            metadata_out.write(json.dumps(metadata))

        self.logger.debug(f'Setting ownership of {self.install_directory} to dynamite-remote.')
        utilities.set_ownership_of_file(self.install_directory, user='dynamite-remote', group='dynamite-remote')
        self.logger.debug(f'Setting ownership of {pub_key_file_path} to dynamite-remote.')
        utilities.set_ownership_of_file(remote_user_root, user='dynamite-remote', group='dynamite-remote')
        self.logger.debug('Patching sudoers file.')
        self.patch_sudoers_file()
        self.logger.debug('Patching sshd_config')
        self.patch_sshd_config()
        self.logger.info(f'{metadata["hostname"]} has been installed as a remote on this node. '
                         f'You can now access it via dynamite-remote via:'
                         f' \'dynamite-remote execute {metadata["node_name"]} <dynamite command>')


class UninstallManager(install.BaseUninstallManager):

    """
    Uninstall Dynamite remote manager
    """

    def __init__(self, stdout: Optional[bool] = False, verbose: Optional[bool] = False):
        """
        :param stdout: Print output to console
        :param verbose: Include detailed debug messages
        """

        super().__init__('node', ['/home/dynamite-remote/.ssh'], stdout=stdout, verbose=verbose)
        utilities.delete_dynamite_remote_user()
