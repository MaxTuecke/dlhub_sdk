from dlhub_sdk.utils.schemas import validate_against_dlhub_schema
from dlhub_sdk.config import (
    DLHUB_AT_OPTNAME, DLHUB_AT_EXPIRES_OPTNAME, DLHUB_RT_OPTNAME,
    lookup_option, write_option, format_output, remove_option,
    internal_auth_client, check_logged_in, safeprint, DLHUB_SERVICE_ADDRESS)
from tempfile import mkstemp

import pandas as pd
import globus_sdk
import platform
import requests
import boto3
import uuid
import os


class DLHubClient:
    """Main class for interacting with the DLHub service

    Holds helper operations for performing common tasks with the DLHub service. For example,
    `get_servables` produces a list of all servables registered with DLHub."""


    def __init__(self, timeout=None):
        """Initialize the client

        Args:
            timeout (int): Timeout for any call to service. (default is no timeout)
            """
        self.timeout = timeout

    def _get_servables(self):
        """Get all of the servables available in the service

        Returns:
            (pd.DataFrame) Summary of all the models available in the service
        """
        r = requests.get("{service}/servables".format(
            service=DLHUB_SERVICE_ADDRESS), timeout=self.timeout)
        return pd.DataFrame(r.json())

    def list_servables(self):
        """Get a list of the servables available in the service

        Returns:
            (pd.DataFrame) Summary of all the models available in the service
        """
        df_tmp = self._get_servables()
        return df_tmp['name']

    def get_id_by_name(self, name):
        """Get the ID of a DLHub servable by name

        Args:
            name (string): Name of the servable
        Returns:
            (string) UUID of the servable
        """

        df_tmp = self._get_servables()
        serv = df_tmp[df_tmp.name == name]
        return serv.iloc[0]['uuid']

    def describe_servable(self, servable_id):
        """Get a list of the servables available in the service
        Args:
            servable_id (string): ID of the servable
        Returns:
            (pd.DataFrame) Summary of all the models available in the service
        """
        df_tmp = self._get_servables()
        serv = df_tmp[df_tmp.uuid == servable_id]
        return serv.iloc[0]

    def run(self, servable_id, data):
        """Invoke a DLHub servable

        Args:
            servable_id (string): UUID of the servable
            data (dict): Dictionary of the data to send to the servable
        Returns:
            (pd.DataFrame): Reply from the service
        """
        servable_path = '{service}/servables/{servable_id}/run'.format(
            service=DLHUB_SERVICE_ADDRESS, servable_id=servable_id)

        r = requests.post(servable_path, json=data, timeout=self.timeout)
        if r.status_code is not 200:
            raise Exception(r)
        return pd.DataFrame(r.json())

    def publish_servable(self, model):
        """Submit a servable to DLHub

        If this servable has not been published before, it will be assigned a unique identifier.

        If it has been published before (DLHub detects if it has an identifier), then DLHub
        will update the model to the new version.

        Args:
            model (BaseMetadataModel): Model to be submitted
        Returns:
            (string) Task ID of this submission, used for checking for success
        """

        # If unassigned, give the model a UUID
        if model.dlhub_id is None:
            model.assign_uuid()

        # Get the metadata
        metadata = model.to_dict(simplify_paths=True)

        # Validate against the servable schema
        validate_against_dlhub_schema(metadata, 'servable')

        # Stage data for DLHub to access
        staged_path = self._stage_data(model)
        # Mark the method used to submit the model
        metadata['dlhub']['transfer_method'] = {'S3': staged_path}

        # Publish to DLHub
        response = requests.post('{service}/publish'.format(service=DLHUB_SERVICE_ADDRESS),
                                 json=metadata, timeout=self.timeout)

        task_id = response.json()['task_id']
        return task_id

    def _stage_data(self, servable):
        """
        Stage data to the DLHub service.

        :param data_path: The data to upload
        :return str: path to the data on S3
        """
        s3 = boto3.resource('s3')

        # Generate a uuid to deposit the data
        dest_uuid = str(uuid.uuid4())
        dest_dir = 'servables/'
        bucket_name = 'dlhub-anl'

        fp, zip_filename = mkstemp('.zip')
        os.close(fp)
        os.unlink(zip_filename)

        try:
            servable.get_zip_file(zip_filename)

            destpath = os.path.join(dest_dir, dest_uuid, zip_filename.split("/")[-1])
            print("Uploading: {}".format(zip_filename))
            res = s3.Object(bucket_name, destpath).put(ACL="public-read",
                                                       Body=open(zip_filename, 'rb'))
            staged_path = os.path.join("s3://", bucket_name, dest_dir, dest_uuid)
            return staged_path
        except Exception as e:
            print("Publication error: {}".format(e))
        finally:
            os.unlink(zip_filename)

    def _store_config(self, token_response):
        """
        Store the tokens on disk.

        :param token_response:
        :return:
        """
        tkn = token_response.by_resource_server

        search_at = tkn['search.api.globus.org']['access_token']
        search_rt = tkn['search.api.globus.org']['refresh_token']
        search_at_expires = tkn['search.api.globus.org']['expires_at_seconds']

        write_option(DLHUB_RT_OPTNAME, search_rt)
        write_option(DLHUB_AT_OPTNAME, search_at)
        write_option(DLHUB_AT_EXPIRES_OPTNAME, search_at_expires)

    def _revoke_current_tokens(self, native_client):
        for token_opt in (DLHUB_RT_OPTNAME, DLHUB_AT_OPTNAME):
            token = lookup_option(token_opt)
            if token:
                native_client.aotuh2_revoke_token(token)

    def _do_login_flow(self):
        """
        Do the globus native client login flow.

        :return:
        """

        native_client = internal_auth_client()

        label = platform.node() or None

        # TODO: Change this to dlhub's scope.
        SEARCH_ALL_SCOPE = 'urn:globus:auth:scope:search.api.globus.org:all'

        native_client.oauth2_start_flow(
            requested_scopes=SEARCH_ALL_SCOPE,
            refresh_tokens=True, prefill_named_grant=label)
        linkprompt = 'Please log into Globus here'
        safeprint('{0}:\n{1}\n{2}\n{1}\n'
                  .format(linkprompt, '-' * len(linkprompt),
                          native_client.oauth2_get_authorize_url()))
        auth_code = input(
            'Enter the resulting Authorization Code here:\n').strip()
        tkn = native_client.oauth2_exchange_code_for_tokens(auth_code)
        self._revoke_current_tokens(native_client)
        self._store_config(tkn)

    def logout(self):
        """
        Perform a globus logout
        :return:
        """
        safeprint(u'Logging out of DLHub CLI\n')

        native_client = internal_auth_client()

        # remove tokens from config and revoke them
        # also, track whether or not we should print the rescind help
        for token_opt in (DLHUB_RT_OPTNAME, DLHUB_AT_OPTNAME):
            # first lookup the token -- if not found we'll continue
            token = lookup_option(token_opt)
            if not token:
                safeprint(('Warning: Found no token named "{}"! '
                           'Recommend rescinding consent').format(token_opt))
                continue
            # token was found, so try to revoke it
            try:
                native_client.oauth2_revoke_token(token)
            # if we network error, revocation failed -- print message and abort so
            # that we can revoke later when the network is working
            except globus_sdk.NetworkError:
                safeprint(('Failed to reach Globus to revoke tokens. '
                           'Because we cannot revoke these tokens, cancelling '
                           'logout'))
                return
            # finally, we revoked, so it's safe to remove the token
            remove_option(token_opt)

        # remove expiration time, just for cleanliness
        remove_option(DLHUB_AT_EXPIRES_OPTNAME)

        # if print_rescind_help is true, we printed warnings above
        # so, jam out an extra newline as a separator
        safeprint("Logged out")

    def login(self, force=None):
        """
        Perform a globus auth native client login.

        :return:
        """

        if not force and check_logged_in():
            safeprint('You are already logged in!')
            return

        self._do_login_flow()
