# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------


import os
import unittest
import time

from azure.cli.testsdk import ScenarioTest, ResourceGroupPreparer, StorageAccountPreparer, record_only

TEST_DIR = os.path.abspath(os.path.join(os.path.abspath(__file__), '..'))


class SynapseScenarioTests(ScenarioTest):
    location = "eastus2euap"

    @record_only()
    @ResourceGroupPreparer(name_prefix='synapse-cli', random_name_length=16)
    @StorageAccountPreparer(name_prefix='adlsgen2', length=16, location=location, hns=True, key='storage-account')
    def test_workspaces(self, resource_group, storage_account):
        # create a workspace
        self._create_workspace()

        # check workspace name
        self.cmd('az synapse workspace check-name --name {workspace}', checks=[
            self.check('available', False)
        ])

        # get workspace with workspace name
        workspace = self.cmd('az synapse workspace show --name {workspace} --resource-group {rg}', checks=[
            self.check('name', self.kwargs['workspace']),
            self.check('type', 'Microsoft.Synapse/workspaces'),
            self.check('provisioningState', 'Succeeded')
        ]).get_output_in_json()

        self.kwargs["workspace-id"] = workspace['id']

        # list all workspaces under a specific resource group
        self.cmd('az synapse workspace list --resource-group {rg}', checks=[
            self.check('[0].type', 'Microsoft.Synapse/workspaces')
        ])

        # update workspace
        self.cmd('az synapse workspace update --ids {workspace-id} --tags key1=value1', checks=[
            self.check('tags.key1', 'value1'),
            self.check('name', self.kwargs['workspace']),
            self.check('id', self.kwargs['workspace-id']),
            self.check('type', 'Microsoft.Synapse/workspaces'),
            self.check('provisioningState', 'Succeeded')
        ])

        # delete workspace with workspace name
        self.cmd('az synapse workspace delete --name {workspace} --resource-group {rg} --yes')
        import time
        time.sleep(120)
        self.cmd('az synapse workspace show --name {workspace} --resource-group {rg}', expect_failure=True)

    @record_only()
    @ResourceGroupPreparer(name_prefix='synapse-cli', random_name_length=16)
    @StorageAccountPreparer(name_prefix='adlsgen2', length=16, location=location, hns=True, key='storage-account')
    def test_managed_virtual_network_workspace(self):
        # test workspace with managed virtual network
        self._create_workspace("--enable-managed-virtual-network")
        self.cmd('az synapse workspace show --name {workspace} --resource-group {rg}', checks=[
            self.check('name', self.kwargs['workspace']),
            self.check('type', 'Microsoft.Synapse/workspaces'),
            self.check('provisioningState', 'Succeeded'),
            self.check('managedVirtualNetwork', 'default')
        ])

    @record_only()
    @ResourceGroupPreparer(name_prefix='synapse-cli', random_name_length=16)
    @StorageAccountPreparer(name_prefix='adlsgen2', length=16, location=location, hns=True, key='storage-account')
    def test_spark_pool(self):
        self.kwargs.update({
            'location': 'eastus',
            'workspace': 'testsynapseworkspace',
            'rg': 'rg',
            'spark-pool': self.create_random_name(prefix='testpool', length=15),
            'spark-version': '2.4'
        })

        # create a workspace
        self._create_workspace()

        # check workspace name
        self.cmd('az synapse workspace check-name --name {workspace}', checks=[
            self.check('available', False)
        ])

        # create spark pool
        spark_pool = self.cmd('az synapse spark pool create --name {spark-pool} --spark-version {spark-version}'
                              ' --workspace {workspace} --resource-group {rg} --node-count 3 --node-size Medium',
                              checks=[
                                  self.check('name', self.kwargs['spark-pool']),
                                  self.check('type', 'Microsoft.Synapse/workspaces/bigDataPools'),
                                  self.check('provisioningState', 'Succeeded')
                              ]).get_output_in_json()

        self.kwargs['pool-id'] = spark_pool['id']

        # get spark pool with spark pool name
        self.cmd('az synapse spark pool show --name {spark-pool} --workspace {workspace} --resource-group {rg}',
                 checks=[
                     self.check('name', self.kwargs['spark-pool']),
                     self.check('type', 'Microsoft.Synapse/workspaces/bigDataPools'),
                     self.check('provisioningState', 'Succeeded')
                 ])

        # list all spark pools under the workspace
        self.cmd('az synapse spark pool list --workspace {workspace} --resource-group {rg}', checks=[
            self.check('[0].type', 'Microsoft.Synapse/workspaces/bigDataPools')
        ])

        # update spark pool
        self.cmd('az synapse spark pool update --ids {pool-id} --tags key1=value1', checks=[
            self.check('tags.key1', 'value1'),
            self.check('name', self.kwargs['spark-pool']),
            self.check('type', 'Microsoft.Synapse/workspaces/bigDataPools'),
            self.check('provisioningState', 'Succeeded')
        ])

        # delete spark pool with spark pool name
        self.cmd(
            'az synapse spark pool delete --name {spark-pool} --workspace {workspace} --resource-group {rg} --yes')
        self.cmd('az synapse spark pool show --name {spark-pool} --workspace {workspace} --resource-group {rg}',
                 expect_failure=True)

    @record_only()
    @unittest.skip('(keyvaultfailure) KeyVault set-policy failed with Bad Request')
    def test_workspace_with_cmk(self):
        self.kwargs.update({
            'location': 'eastus',
            'workspace': 'testsynapseworkspacecmk',
            'rg': 'testrg',
            'storage-account': 'teststorageforsynapsecmk',
            'file-system': self.create_random_name(prefix='fs', length=16),
            'login-user': 'cliuser1',
            'login-password': self.create_random_name(prefix='Pswd1', length=16),
            'key-identifier': 'https://testcmksoftdelete.vault.azure.net/keys/newcmk',
            'new-key-identifier': 'https://testcmksoftdelete.vault.azure.net/keys/newkey',
            'managed-identity': '00000000-0000-1111-2222-333333333333'
        })

        # create workspace supporting cmk, data exfiltration
        workspace_cmk = self.cmd(
            'az synapse workspace create --name {workspace} --resource-group {rg} --storage-account {storage-account} '
            '--file-system {file-system} --sql-admin-login-user {login-user} '
            '--sql-admin-login-password {login-password} --key-identifier {key-identifier} '
            ' --location {location} --enable-managed-vnet True --prevent-exfiltration True --allowed-tenant-ids \'""\' ', checks=[
                self.check('name', self.kwargs['workspace']),
                self.check('type', 'Microsoft.Synapse/workspaces'),
                self.check('provisioningState', 'Succeeded')
            ]).get_output_in_json()

        self.kwargs['managed-identity'] = workspace_cmk['identity']['principalId']

        # set access policy
        self.cmd(
            'az keyvault set-policy --name testcmksoftdelete --object-id {managed-identity} --key-permissions get unwrapKey wrapKey ')

        # active workspace
        self.cmd(
            'az synapse workspace activate --name default --key-identifier {key-identifier} --resource-group {rg} --workspace-name {workspace}', checks=[
                self.check('name', 'default'),
                self.check('type', 'Microsoft.Synapse/workspaces/keys')
            ])
        import time
        time.sleep(120)

        # create workspace key
        self.cmd(
            'az synapse workspace key create --name newkey --key-identifier {new-key-identifier}  --resource-group {rg} --workspace-name {workspace}', checks=[
                self.check('name', 'newkey'),
                self.check('type', 'Microsoft.Synapse/workspaces/keys')
            ])

        # set access policy
        self.cmd(
            'az keyvault set-policy --name testcmksoftdelete --object-id {managed-identity} --key-permissions get unwrapKey wrapKey ')

        # list workspace key
        self.cmd(
            'az synapse workspace key list --resource-group {rg} --workspace-name {workspace}', checks=[
                self.check('[0].name', 'default'),
                self.check('[0].type', 'Microsoft.Synapse/workspaces/keys'),
                self.check('[0].keyVaultUrl', self.kwargs['key-identifier']),
            ])

        # show workspace key
        self.cmd(
            'az synapse workspace key show --name default --resource-group {rg} --workspace-name {workspace}', checks=[
                self.check('name', 'default'),
                self.check('type', 'Microsoft.Synapse/workspaces/keys'),
                self.check('keyVaultUrl', self.kwargs['key-identifier']),
            ])

        # show sql access to managed identity
        self.cmd(
            'az synapse workspace managed-identity show-sql-access --resource-group {rg} --workspace-name {workspace}', checks=[
                self.check('grantSqlControlToManagedIdentity.actualState', 'Disabled'),
                self.check('type', 'Microsoft.Synapse/workspaces/managedIdentitySqlControlSettings')
            ])

        # grant sql access to managed identity
        self.cmd(
            'az synapse workspace managed-identity grant-sql-access --resource-group {rg} --workspace-name {workspace}', checks=[
                self.check('grantSqlControlToManagedIdentity.actualState', 'Enabled'),
                self.check('type', 'Microsoft.Synapse/workspaces/managedIdentitySqlControlSettings')
            ])

        # invoke sql access to managed identity
        self.cmd(
            'az synapse workspace managed-identity revoke-sql-access --resource-group {rg} --workspace-name {workspace}', checks=[
                self.check('grantSqlControlToManagedIdentity.actualState', 'Disabled'),
                self.check('type', 'Microsoft.Synapse/workspaces/managedIdentitySqlControlSettings')
            ])

        # switch active key
        self.cmd(
            'az synapse workspace update --resource-group {rg} --name {workspace} --key-name newkey ', checks=[
                self.check('encryption.cmk.key.name', 'newkey')
            ])

        # update allowed tenant ids
        self.cmd(
            'az synapse workspace update --resource-group {rg} --name {workspace} --allowed-tenant-ids 72f988bf-86f1-41af-91ab-2d7cd011db47 ', checks=[
                self.check('managedVirtualNetworkSettings.allowedAadTenantIdsForLinking[0]', "72f988bf-86f1-41af-91ab-2d7cd011db47")
            ])

    @record_only()
    @ResourceGroupPreparer(name_prefix='synapse-cli', random_name_length=16)
    @StorageAccountPreparer(name_prefix='adlsgen2', length=16, location=location, hns=True, key='storage-account')
    def test_sql_pool(self):
        self.kwargs.update({
            'location': 'eastus2euap',
            'workspace': 'testsynapseworkspace',
            'rg': 'rg',
            'sql-pool': self.create_random_name(prefix='testsqlpool', length=15),
            'performance-level': 'DW400c'
        })

        # create a workspace
        self._create_workspace()

        # check workspace name
        self.cmd('az synapse workspace check-name --name {workspace}', checks=[
            self.check('available', False)
        ])

        # create sql pool
        sql_pool = self.cmd(
            'az synapse sql pool create --name {sql-pool} --performance-level {performance-level} '
            '--workspace {workspace} --resource-group {rg}', checks=[
                self.check('name', self.kwargs['sql-pool']),
                self.check('type', 'Microsoft.Synapse/workspaces/sqlPools'),
                self.check('provisioningState', 'Succeeded'),
                self.check('status', 'Online')
            ]).get_output_in_json()

        self.kwargs['pool-id'] = sql_pool['id']

        # get sql pool with sql pool name
        self.cmd('az synapse sql pool show --name {sql-pool} --workspace {workspace} --resource-group {rg}',
                 checks=[
                     self.check('name', self.kwargs['sql-pool']),
                     self.check('type', 'Microsoft.Synapse/workspaces/sqlPools'),
                     self.check('provisioningState', 'Succeeded'),
                     self.check('status', 'Online')
                 ])

        # list all sql pools under the workspace
        self.cmd('az synapse sql pool list --workspace {workspace} --resource-group {rg}', checks=[
            self.check('[0].type', 'Microsoft.Synapse/workspaces/sqlPools')
        ])

        # update sql pool
        self.cmd('az synapse sql pool update --ids {pool-id} --tags key1=value1')

        # get sql pool with sql pool id
        self.cmd('az synapse sql pool show --ids {pool-id}',
                 checks=[
                     self.check('name', self.kwargs['sql-pool']),
                     self.check('type', 'Microsoft.Synapse/workspaces/sqlPools'),
                     self.check('tags.key1', 'value1'),
                     self.check('provisioningState', 'Succeeded'),
                     self.check('status', 'Online')
                 ])

        # pause sql pool
        self.cmd('az synapse sql pool pause --name {sql-pool} --workspace {workspace} --resource-group {rg}', checks=[])
        self.cmd('az synapse sql pool show --name {sql-pool} --workspace {workspace} --resource-group {rg}',
                 checks=[
                     self.check('name', self.kwargs['sql-pool']),
                     self.check('type', 'Microsoft.Synapse/workspaces/sqlPools'),
                     self.check('status', 'Paused')
                 ])

        # resume sql pool
        self.cmd('az synapse sql pool resume --name {sql-pool} --workspace {workspace} --resource-group {rg}',
                 checks=[])
        self.cmd('az synapse sql pool show --name {sql-pool} --workspace {workspace} --resource-group {rg}',
                 checks=[
                     self.check('name', self.kwargs['sql-pool']),
                     self.check('type', 'Microsoft.Synapse/workspaces/sqlPools'),
                     self.check('status', 'Online')
                 ])

        # delete sql pool with sql pool name
        self.cmd(
            'az synapse sql pool delete --name {sql-pool} --workspace {workspace} --resource-group {rg} --yes')

        self.cmd('az synapse sql pool show --name {sql-pool} --workspace {workspace} --resource-group {rg}',
                 expect_failure=True)

    @record_only()
    def test_sql_pool_restore_and_list_deleted(self):
        self.kwargs.update({
            'location': 'eastus2euap',
            'workspace': 'zes0219test',
            'rg': 'chayang-test-rg',
            'sql-pool': 'rivertiger0220 ',
            'performance-level': 'DW1000c',
            'dest-sql-pool': self.create_random_name(prefix='destsqlpool', length=15),
            'restore-point-time': '2021-05-24T08:09:15'
        })

        # restore sql pool
        self.cmd('az synapse sql pool restore --name {sql-pool} --workspace-name {workspace} --resource-group {rg} '
                 '--dest-name {dest-sql-pool} --time {restore-point-time}',
                 checks=[
                     self.check('name', self.kwargs['dest-sql-pool'])
                 ])

        # get the new created sql pool
        self.cmd('az synapse sql pool show --name {dest-sql-pool} --workspace-name {workspace} --resource-group {rg}',
                 checks=[
                     self.check('name', self.kwargs['dest-sql-pool']),
                     self.check('type', 'Microsoft.Synapse/workspaces/sqlPools'),
                     self.check('provisioningState', 'Succeeded'),
                     self.check('status', 'Online')
                 ])

        # delete dest sql pool with dest sql pool name
        self.cmd(
            'az synapse sql pool delete --name {dest-sql-pool} --workspace-name {workspace} --resource-group {rg} --yes')

        # deleted list take several mins to show
        time.sleep(200)

        # test list-deleted
        self.cmd('az synapse sql pool list-deleted --workspace-name {workspace} --resource-group {rg}',
                 checks=[
                     self.greater_than("length([])", 0)
                 ])

    @record_only()
    def test_sql_pool_classification_and_recommendation(self):
        self.kwargs.update({
            'location': 'eastus2euap',
            'workspace': 'zes0514test',
            'rg': 'chayang-test-rg',
            'sql-pool': 'sqlzes0514test',
            'schema': 'dbo',
            'table': 'Persons',
            'column': 'City',
            'label': 'Confidential',
            'information-type': '"Contact Info"'
        })

        # classification create
        self.cmd('az synapse sql pool classification create --name {sql-pool} --workspace-name {workspace} '
                 '--resource-group {rg} --schema {schema} --table {table} --column {column} '
                 '--label {label} --information-type {information-type}',
                 checks=[
                     self.check('labelName', self.kwargs['label'])
                 ])

        # classification show
        self.cmd('az synapse sql pool classification show --name {sql-pool} --workspace-name {workspace} '
                 '--resource-group {rg} --schema {schema} --table {table} --column {column}',
                 checks=[
                     self.check('labelName', self.kwargs['label'])
                 ])

        # classification list
        self.cmd('az synapse sql pool classification list --name {sql-pool} --workspace-name {workspace} '
                 '--resource-group {rg}',
                 checks=[
                     self.check('[0].labelName', self.kwargs['label'])
                 ])

        # classification update
        self.cmd('az synapse sql pool classification update --name {sql-pool} --workspace-name {workspace} '
                 '--resource-group {rg} --schema {schema} --table {table} --column {column} '
                 '--label {label} --information-type {information-type}')

        # classification delete
        self.cmd('az synapse sql pool classification delete --name {sql-pool} --workspace-name {workspace} '
                 '--resource-group {rg} --schema {schema} --table {table} --column {column}')

        # recommendation enable
        self.cmd('az synapse sql pool classification recommendation enable --name {sql-pool} '
                 '--workspace-name {workspace} --resource-group {rg} '
                 '--schema {schema} --table {table} --column {column}')

        # recommendation list
        self.cmd('az synapse sql pool classification recommendation list --name {sql-pool} '
                 '--workspace-name {workspace} --resource-group {rg}',
                 checks=[
                     self.greater_than("length([])", 0)
                 ])

        self.cmd('az synapse sql pool classification recommendation disable --name {sql-pool} '
                 '--workspace-name {workspace} --resource-group {rg} '
                 '--schema {schema} --table {table} --column {column}')

        # After disable the length of list should be equal with 0
        self.cmd('az synapse sql pool classification recommendation list --name {sql-pool} '
                 '--workspace-name {workspace} --resource-group {rg}',
                 checks=[
                     self.check("length([])", 0)
                 ])

    @record_only()
    def test_sql_pool_tde(self):
        self.kwargs.update({
            'location': 'eastus2euap',
            'workspace': 'zes0508test',
            'rg': 'chayang-test-rg',
            'sql-pool': 'zes0508test1pool' #self.create_random_name(prefix='testsqlpool', length=15),
        })

        self.cmd(
            'az synapse sql pool tde set --status Enabled --name {sql-pool} --workspace-name {workspace} \
            --resource-group {rg} --transparent-data-encryption-name current')

        self.cmd('az synapse sql pool tde show --name {sql-pool} --workspace-name {workspace} --resource-group {rg} \
                 --transparent-data-encryption-name current',
                 checks=[
                     self.check('name', "current"),
                     self.check('status', "Enabled")
                 ])

    @record_only()
    def test_sql_pool_threat_policy(self):
        self.kwargs.update({
            'location': 'eastus2euap',
            'workspace': 'zes0508test',
            'rg': 'chayang-test-rg',
            'sql-pool': 'zes0508test1pool',  # self.create_random_name(prefix='testsqlpool', length=15),
            'storage-account': 'chayangstoragewestus2',
            'threat-policy': 'threatpolicy'
        })

        self.cmd('az synapse sql pool threat-policy update --state Enabled --storage-account {storage-account} '
                 '--name {sql-pool} --workspace-name {workspace} --resource-group {rg} --security-alert-policy-name {threat-policy}')

        self.cmd('az synapse sql pool threat-policy show '
                 '--name {sql-pool} --workspace-name {workspace} --resource-group {rg} --security-alert-policy-name {threat-policy}',
                 checks=[
                     self.check('state', 'Enabled')
                 ])


    @ResourceGroupPreparer(name_prefix='synapse-cli', random_name_length=16)
    def test_sql_ws_audit_policy_logentry_eventhub(self):
        self.kwargs.update({
            'location': 'eastus',
            'log_analytics_workspace_name': self.create_random_name("laws", 20),
            'retention-days': '30',
            'audit-actions-input': 'DATABASE_LOGOUT_GROUP',
            'audit-actions-expected': ['DATABASE_LOGOUT_GROUP'],
            'eventhub_name': self.create_random_name("ehsrv", 20),
            'eventhub_namespace': self.create_random_name("ehnamespace", 20),
            'eventhub_auth_rule': self.create_random_name("ehauthruledb", 20),
        })

        # create a workspace
        self._create_workspace_eastus()

        self.kwargs['storage-endpoint'] = self._get_storage_endpoint(self.kwargs['storage-account'], self.kwargs['rg'])
        self.kwargs['storage-key'] = self._get_storage_key(self.kwargs['storage-account'], self.kwargs['rg'])

        # test show command
        self.cmd('az synapse sql audit-policy show '
                 '--workspace-name {workspace} --resource-group {rg} --blob-auditing-policy-name bapname',
                 checks=[
                     self.check('state', 'Disabled')
                 ])

        self.cmd('az synapse sql audit-policy update --resource-group {rg} --workspace-name {workspace}'
                 ' --state Enabled --bsts Enabled --storage-key {storage-key} --storage-endpoint={storage-endpoint}'
                 ' --retention-days={retention-days} --actions {audit-actions-input} --blob-auditing-policy-name bapname',
                 checks=[
                     self.check('state', 'Enabled'),
                     self.check('storageEndpoint', self.kwargs['storage-endpoint']),
                     self.check('retentionDays', self.kwargs['retention-days']),
                     self.check('auditActionsAndGroups', self.kwargs['audit-actions-expected'])
                 ])

        # get audit policy
        self.cmd('az synapse sql audit-policy show '
                 '--workspace-name {workspace} --resource-group {rg} --blob-auditing-policy-name bapname',
                 checks=[
                     self.check('state', 'Enabled'),
                     self.check('blobStorageTargetState', 'Enabled'),
                     self.check('logAnalyticsTargetState', 'Disabled'),
                     self.check('eventHubTargetState', 'Disabled'),
                     self.check('isAzureMonitorTargetEnabled', False)])

        self.cmd('az synapse sql audit-policy update --resource-group {rg} --workspace-name {workspace}'
                 ' --state Enabled --bsts Enabled --storage-account {storage-account}'
                 ' --retention-days={retention-days} --actions {audit-actions-input} --blob-auditing-policy-name bapn',
                 checks=[
                     self.check('state', 'Enabled'),
                     self.check('storageEndpoint', self.kwargs['storage-endpoint']),
                     self.check('retentionDays',  self.kwargs['retention-days']),
                     self.check('auditActionsAndGroups', self.kwargs['audit-actions-expected'])])

        # update audit policy - disable
        self.cmd('az synapse sql audit-policy update --resource-group {rg} --workspace-name {workspace}'
                 ' --state Disabled --blob-auditing-policy-name bapn',
                 checks=[
                     self.check('state', 'Disabled'),
                     self.check('retentionDays', self.kwargs['retention-days']),
                     self.check('auditActionsAndGroups', self.kwargs['audit-actions-expected'])])

        # create log analytics workspace
        self.kwargs['log_analytics_workspace_id']= self.cmd('az monitor log-analytics workspace create --resource-group {rg} '
                 '--workspace-name {log_analytics_workspace_name}',
                 checks=[
                     self.check('name', self.kwargs['log_analytics_workspace_name']),
                     self.check('provisioningState', 'Succeeded')]).get_output_in_json()['id']

        # update audit policy - enable log analytics target
        self.cmd('az synapse sql audit-policy update --resource-group {rg} --workspace-name {workspace}'
                 ' --state Enabled'
                 ' --lats Enabled --lawri {log_analytics_workspace_id} '
                 ' --blob-auditing-policy-name bapn',
                 checks=[
                     self.check('state', 'Enabled'),
                     self.check('retentionDays', self.kwargs['retention-days']),
                     self.check('auditActionsAndGroups', self.kwargs['audit-actions-expected'])])

        # get audit policy - verify logAnalyticsTargetState is enabled and isAzureMonitorTargetEnabled is true
        self.cmd('az synapse sql audit-policy show --resource-group {rg} --workspace-name {workspace}'
                 ' --blob-auditing-policy-name bapn',
                 checks=[
                     self.check('state', 'Enabled'),
                     self.check('blobStorageTargetState', 'Enabled'),
                     self.check('logAnalyticsTargetState', 'Enabled'),
                     self.check('eventHubTargetState', 'Disabled'),
                     self.check('isAzureMonitorTargetEnabled', True)])

        # update audit policy - disable log analytics target
        self.cmd('az synapse sql audit-policy update --resource-group {rg} --workspace-name {workspace}'
                 ' --state Enabled --lats Disabled'
                 ' --blob-auditing-policy-name bapn',
                 checks=[
                     self.check('state', 'Enabled'),
                     self.check('retentionDays', self.kwargs['retention-days']),
                     self.check('auditActionsAndGroups', self.kwargs['audit-actions-expected'])])

        # get audit policy - verify logAnalyticsTargetState is disabled and isAzureMonitorTargetEnabled is false
        self.cmd('az synapse sql audit-policy show --resource-group {rg} --workspace-name {workspace}'
                 ' --blob-auditing-policy-name bapname',
                 checks=[
                     self.check('state', 'Enabled'),
                     self.check('blobStorageTargetState', 'Enabled'),
                     self.check('logAnalyticsTargetState', 'Disabled'),
                     self.check('eventHubTargetState', 'Disabled'),
                     self.check('isAzureMonitorTargetEnabled', False)])

        # create event hub namespace
        self.cmd('az eventhubs namespace create --resource-group {rg} -n {eventhub_namespace} --location eastus',
                 checks=[
                     self.check('provisioningState', 'Succeeded')])

        # create event hub
        self.cmd('az eventhubs eventhub create --resource-group {rg} -n {eventhub_name} --namespace-name {eventhub_namespace}',
                 checks=[
                     self.check('status', 'Active')])

        # create event hub autorization rule
        self.kwargs['eventhub_auth_rule_id'] = self.cmd(
            'az eventhubs namespace authorization-rule create --resource-group {rg} -n {eventhub_auth_rule} '
            '--namespace-name {eventhub_namespace} --rights Listen Manage Send').get_output_in_json()['id']

        # update audit policy - enable event hub target
        self.cmd('az synapse sql audit-policy update --resource-group {rg} --workspace-name {workspace}'
                 ' --state Enabled --event-hub-target-state Enabled'
                 ' --ehari {eventhub_auth_rule_id} --event-hub {eventhub_name}'
                 ' --blob-auditing-policy-name bapn',
                 checks=[
                     self.check('state', 'Enabled'),
                     self.check('retentionDays', self.kwargs['retention-days']),
                     self.check('auditActionsAndGroups', self.kwargs['audit-actions-expected'])])

        # get audit policy - verify eventHubTargetState is enabled and isAzureMonitorTargetEnabled is true
        self.cmd('az synapse sql audit-policy show --resource-group {rg} --workspace-name {workspace}'
                 ' --blob-auditing-policy-name bapn',
                 checks=[
                     self.check('state', 'Enabled'),
                     self.check('blobStorageTargetState', 'Enabled'),
                     self.check('logAnalyticsTargetState', 'Disabled'),
                     self.check('eventHubTargetState', 'Enabled'),
                     self.check('isAzureMonitorTargetEnabled', True)])

        # update audit policy - disable event hub target
        self.cmd('az synapse sql audit-policy update --resource-group {rg} --workspace-name {workspace}'
                 ' --state Enabled --event-hub-target-state Disabled --blob-auditing-policy-name bapn',
                 checks=[
                     self.check('state', 'Enabled'),
                     self.check('retentionDays', self.kwargs['retention-days']),
                     self.check('auditActionsAndGroups', self.kwargs['audit-actions-expected'])])

        # get audit policy - verify eventHubTargetState is disabled and isAzureMonitorTargetEnabled is false
        self.cmd('az synapse sql audit-policy show --resource-group {rg} --workspace-name {workspace}'
                 ' --blob-auditing-policy-name bapn',
                 checks=[
                     self.check('state', 'Enabled'),
                     self.check('isAzureMonitorTargetEnabled', False),
                     self.check('blobStorageTargetState', 'Enabled'),
                     self.check('logAnalyticsTargetState', 'Disabled'),
                     self.check('eventHubTargetState', 'Disabled'),
                     self.check('isAzureMonitorTargetEnabled', False)])


    @ResourceGroupPreparer(name_prefix='synapse-cli', random_name_length=16)
    def test_sql_pool_audit_policy_logentry_eventhub(self):
        self.kwargs.update({
            'location': 'eastus',
            'log_analytics_workspace_name': self.create_random_name("laws", 20),
            'sql-pool': self.create_random_name(prefix='testsqlpool', length=15),
            'performance-level': 'DW400c',
            'retention-days': '30',
            'audit-actions-expected': ['SUCCESSFUL_DATABASE_AUTHENTICATION_GROUP'],
            'audit-actions-input': 'SUCCESSFUL_DATABASE_AUTHENTICATION_GROUP',
            'eventhub_name': self.create_random_name("ehsrv", 20),
            'eventhub_namespace':  self.create_random_name("ehnamespace", 20),
            'eventhub_auth_rule': self.create_random_name("ehauthruledb", 20),
        })

        # create a workspace
        self._create_workspace_eastus()

        # create sql pool
        sql_pool = self.cmd(
            'az synapse sql pool create --name {sql-pool} --performance-level {performance-level} '
            '--workspace {workspace} --resource-group {rg}', checks=[
                self.check('name', self.kwargs['sql-pool']),
                self.check('type', 'Microsoft.Synapse/workspaces/sqlPools'),
                self.check('provisioningState', 'Succeeded'),
                self.check('status', 'Online')
            ]).get_output_in_json()

        self.kwargs['storage-endpoint'] = self._get_storage_endpoint(self.kwargs['storage-account'], self.kwargs['rg'])
        self.kwargs['storage-key'] = self._get_storage_key(self.kwargs['storage-account'], self.kwargs['rg'])

        # test show command
        self.cmd('az synapse sql pool audit-policy show '
                 '--workspace-name {workspace} --resource-group {rg} --name {sql-pool} ',
                 checks=[
                     self.check('state', 'Disabled')
                 ])

        # update audit policy - enable
        self.cmd('az synapse sql pool audit-policy update --resource-group {rg} --workspace-name {workspace} --name {sql-pool} '
             ' --state Enabled --bsts Enabled --storage-key {storage-key} --storage-endpoint={storage-endpoint}'
             ' --retention-days={retention-days} --actions {audit-actions-input} --blob-auditing-policy-name bapname',
             checks=[
                 self.check('state', 'Enabled'),
                 self.check('storageEndpoint', self.kwargs['storage-endpoint']),
                 self.check('retentionDays', self.kwargs['retention-days']),
                 self.check('auditActionsAndGroups', self.kwargs['audit-actions-expected'])])

        # get audit policy
        self.cmd('az synapse sql pool audit-policy show '
             '--workspace-name {workspace} --resource-group {rg} --name {sql-pool} --blob-auditing-policy-name bapname',
             checks=[
                 self.check('state', 'Enabled'),
                 self.check('blobStorageTargetState', 'Enabled'),
                 self.check('logAnalyticsTargetState', 'Disabled'),
                 self.check('eventHubTargetState', 'Disabled'),
                 self.check('isAzureMonitorTargetEnabled', False)])

        self.cmd('az synapse sql pool audit-policy update --resource-group {rg} --workspace-name {workspace}'
             ' --name {sql-pool} --state Enabled --bsts Enabled --storage-account {storage-account}'
             ' --retention-days={retention-days} --actions {audit-actions-input} --blob-auditing-policy-name bapn',
             checks=[
                 self.check('state', 'Enabled'),
                 self.check('storageEndpoint', self.kwargs['storage-endpoint']),
                 self.check('retentionDays', self.kwargs['retention-days']),
                 self.check('auditActionsAndGroups', self.kwargs['audit-actions-expected'])])

        # update audit policy - disable
        self.cmd('az synapse sql pool audit-policy update --resource-group {rg} --workspace-name {workspace}'
             ' --name {sql-pool} --state Disabled --blob-auditing-policy-name bapn',
             checks=[
                 self.check('state', 'Disabled'),
                 self.check('retentionDays', self.kwargs['retention-days']),
                 self.check('auditActionsAndGroups', self.kwargs['audit-actions-expected'])])

        ## create log analytics workspace
        self.kwargs['log_analytics_workspace_id']= self.cmd('az monitor log-analytics workspace create --resource-group {rg} '
                                              '--workspace-name {log_analytics_workspace_name}',
                                              checks=[
                                                  self.check('name', self.kwargs['log_analytics_workspace_name']),
                                                  self.check('provisioningState',
                                                                'Succeeded')]).get_output_in_json()['id']

        # update audit policy - enable log analytics target
        self.cmd('az synapse sql pool audit-policy update --resource-group {rg} --workspace-name {workspace}'
                 ' --name {sql-pool} --state Enabled'
                 ' --lats Enabled --lawri {log_analytics_workspace_id} '
                 ' --blob-auditing-policy-name bapn',
                 checks=[
                     self.check('state', 'Enabled'),
                     self.check('retentionDays', self.kwargs['retention-days']),
                     self.check('auditActionsAndGroups', self.kwargs['audit-actions-expected'])])

        # get audit policy - verify logAnalyticsTargetState is enabled and isAzureMonitorTargetEnabled is true
        self.cmd('az synapse sql pool audit-policy show --resource-group {rg} --workspace-name {workspace}'
                 ' --name {sql-pool} ',
                 checks=[
                     self.check('state', 'Enabled'),
                     self.check('blobStorageTargetState', 'Enabled'),
                     self.check('logAnalyticsTargetState', 'Enabled'),
                     self.check('eventHubTargetState', 'Disabled'),
                     self.check('isAzureMonitorTargetEnabled', True)])

        # update audit policy - disable log analytics target
        self.cmd('az synapse sql pool audit-policy update --resource-group {rg} --workspace-name {workspace}'
                 ' --name {sql-pool} --state Enabled --lats Disabled'
                 ' --blob-auditing-policy-name bapn',
                 checks=[
                     self.check('state', 'Enabled'),
                     self.check('retentionDays', self.kwargs['retention-days']),
                     self.check('auditActionsAndGroups', self.kwargs['audit-actions-expected'])])

        # get audit policy - verify logAnalyticsTargetState is disabled and isAzureMonitorTargetEnabled is false
        self.cmd('az synapse sql pool audit-policy show --resource-group {rg} --workspace-name {workspace}'
                 ' --name {sql-pool}',
                 checks=[
                     self.check('state', 'Enabled'),
                     self.check('blobStorageTargetState', 'Enabled'),
                     self.check('logAnalyticsTargetState', 'Disabled'),
                     self.check('eventHubTargetState', 'Disabled'),
                     self.check('isAzureMonitorTargetEnabled', False)])

        # create event hub namespace
        self.cmd('az eventhubs namespace create --resource-group {rg} -n {eventhub_namespace} --location eastus',
                 checks=[
                     self.check('provisioningState', 'Succeeded')])

        # create event hub
        self.cmd('az eventhubs eventhub create --resource-group {rg} -n {eventhub_name} --namespace-name {eventhub_namespace}',
                 checks=[
                     self.check('status', 'Active')])


        # create event hub autorization rule
        self.kwargs['eventhub_auth_rule_id'] = self.cmd(
            'az eventhubs namespace authorization-rule create --resource-group {rg} -n {eventhub_auth_rule} '
            '--namespace-name {eventhub_namespace} --rights Listen Manage Send').get_output_in_json()['id']

        # update audit policy - enable event hub target
        self.cmd('az synapse sql pool audit-policy update --resource-group {rg} --workspace-name {workspace}'
                 ' --name {sql-pool} --state Enabled --event-hub-target-state Enabled'
                 ' --ehari {eventhub_auth_rule_id} --event-hub {eventhub_name}'
                 ' --blob-auditing-policy-name bapn',
                 checks=[
                     self.check('state', 'Enabled'),
                     self.check('retentionDays', self.kwargs['retention-days']),
                     self.check('auditActionsAndGroups', self.kwargs['audit-actions-expected'])])

        # get audit policy - verify eventHubTargetState is enabled and isAzureMonitorTargetEnabled is true
        self.cmd('az synapse sql pool audit-policy show --resource-group {rg} --workspace-name {workspace}'
                 '  --name {sql-pool}',
                 checks=[
                     self.check('state', 'Enabled'),
                     self.check('blobStorageTargetState', 'Enabled'),
                     self.check('logAnalyticsTargetState', 'Disabled'),
                     self.check('eventHubTargetState', 'Enabled'),
                     self.check('isAzureMonitorTargetEnabled', True)])

        # update audit policy - disable event hub target
        self.cmd('az synapse sql pool audit-policy update --resource-group {rg} --workspace-name {workspace}'
                 '  --name {sql-pool} --state Enabled --event-hub-target-state Disabled --blob-auditing-policy-name bapn',
                 checks=[
                     self.check('state', 'Enabled'),
                     self.check('retentionDays', self.kwargs['retention-days']),
                     self.check('auditActionsAndGroups', self.kwargs['audit-actions-expected'])])

        # get audit policy - verify eventHubTargetState is disabled and isAzureMonitorTargetEnabled is false
        self.cmd('az synapse sql pool audit-policy show --resource-group {rg} --workspace-name {workspace}'
                 ' --name {sql-pool}',
                 checks=[
                     self.check('state', 'Enabled'),
                     self.check('blobStorageTargetState', 'Enabled'),
                     self.check('logAnalyticsTargetState', 'Disabled'),
                     self.check('eventHubTargetState', 'Disabled'),
                     self.check('isAzureMonitorTargetEnabled', False)])


    @record_only()
    def test_sql_aad_admin(self):
        self.kwargs.update({
            'location': 'eastus2euap',
            'workspace': 'zes0508test',
            'rg': 'chayang-test-rg',
            'user-name': 'fakeuser',
            'object-id': '00000000-0000-4002-becf-488f3e6ab703',
            'user-email': 'fakeuser@fakedomain.com'
        })
        # Test create cmdlet
        self.cmd('az synapse sql ad-admin create --workspace-name {workspace} --resource-group {rg} '
                 '--display-name {user-name} --object-id {object-id}',
                 checks=[
                     self.check('login', self.kwargs['user-name'])
                 ])

        # Test show cmdlet
        self.cmd('az synapse sql ad-admin show --workspace-name {workspace} --resource-group {rg}',
                 checks=[
                     self.check('login', self.kwargs['user-name']),
                     self.check('name', 'activeDirectory')
                 ])

        # Test update cmdlet
        self.cmd('az synapse sql ad-admin update --workspace-name {workspace} --resource-group {rg} '
                 '--display-name {user-email}',
                 checks=[
                     self.check('login', self.kwargs['user-email'])
                 ])
        # Test delete cmdlet
        self.cmd('az synapse sql ad-admin delete --workspace-name {workspace} --resource-group {rg} -y')
        self.cmd('az synapse sql ad-admin show --workspace-name {workspace} --resource-group {rg}', expect_failure=True)


    @record_only()
    @ResourceGroupPreparer(name_prefix='synapse-cli', random_name_length=16)
    @StorageAccountPreparer(name_prefix='adlsgen2', length=16, location=location, hns=True, key='storage-account')
    def test_ip_firewall_rules(self, resource_group, storage_account):
        self.kwargs.update({
            'workspace': 'testsynapseworkspace',
            'rg': 'rg',
            'ruleName': self.create_random_name(prefix='rule', length=8),
            'startIpAddress': "0.0.0.0",
            'endIpAddress': "255.255.255.255",
            'secondIpAddress': "192.0.0.1"
        })

        # create a workspace
        self._create_workspace()

        # check workspace name
        self.cmd('az synapse workspace check-name --name {workspace}', checks=[
            self.check('available', False)
        ])

        # create a firewall rule
        self.cmd(
            'az synapse workspace firewall-rule create --name {ruleName} --workspace-name {workspace} '
            '--resource-group {rg} --start-ip-address {startIpAddress} --end-ip-address {endIpAddress}',
            checks=[
                self.check('name', self.kwargs['ruleName']),
                self.check('type', 'Microsoft.Synapse/workspaces/firewallRules'),
                self.check('provisioningState', 'Succeeded')
            ])

        # get a firewall rule
        self.cmd(
            'az synapse workspace firewall-rule show --name {ruleName} --workspace-name {workspace} '
            '--resource-group {rg}',
            checks=[
                self.check('name', self.kwargs['ruleName']),
                self.check('type', 'Microsoft.Synapse/workspaces/firewallRules'),
                self.check('provisioningState', 'Succeeded')
            ])
        # update a firewall rule
        self.cmd(
            'az synapse workspace firewall-rule update --name {ruleName} --workspace-name {workspace} '
            '--resource-group {rg} --start-ip-address {secondIpAddress}',
            checks=[
                self.check('name', self.kwargs['ruleName']),
                self.check('startIpAddress', self.kwargs['secondIpAddress']),
                self.check('type', 'Microsoft.Synapse/workspaces/firewallRules'),
                self.check('provisioningState', 'Succeeded')
            ])

        # list all firewall rules under a specific workspace
        self.cmd('az synapse workspace firewall-rule list --workspace-name {workspace} --resource-group {rg}',
                 checks=[
                     self.check('[0].type', 'Microsoft.Synapse/workspaces/firewallRules')
                 ])

        # delete a firewall rule
        self.cmd(
            'az synapse workspace firewall-rule delete --name {ruleName} --workspace-name {workspace} '
            '--resource-group {rg} --yes')
        import time
        time.sleep(20)
        self.cmd('az synapse workspace firewall-rule show --name {ruleName} --workspace-name {workspace} '
                 '--resource-group {rg}', expect_failure=True)

    @record_only()
    @ResourceGroupPreparer(name_prefix='synapse-cli', random_name_length=16)
    def test_spark_job(self, resource_group):
        self.kwargs.update({
            'spark-pool': 'testsparkpool',
            'workspace': 'testsynapseworkspace',
            'job': 'WordCount_Java',
            'main-definition-file': 'abfss://testfilesystem@adlsgen2account.dfs.core.windows.net/samples/java/wordcount/wordcount.jar',
            'main-class-name': 'WordCount',
            'arguments': [
                'abfss://testfilesystem@adlsgen2account.dfs.core.windows.net/samples/java/wordcount/shakespeare.txt',
                'abfss://testfilesystem@adlsgen2account.dfs.core.windows.net/samples/java/wordcount/result/'],
            'executors': 2,
            'executor-size': 'Medium',
            'configuration': '{\\"spark.dynamicAllocation.maxExecutors\\":\\"18\\"}'
        })

        # create a spark batch job
        batch_job = self.cmd('az synapse spark job submit --name {job} --workspace-name {workspace} '
                             '--spark-pool-name {spark-pool} --main-definition-file {main-definition-file} '
                             '--main-class-name {main-class-name} --arguments {arguments} '
                             '--executors {executors} --executor-size {executor-size} --configuration {configuration} ',
                             checks=[self.check('name', self.kwargs['job']),
                                     self.check('jobType', 'SparkBatch'),
                                     self.check('state', 'not_started'),
                                     self.check('livyInfo.jobCreationRequest.configuration',
                                                        '{{\'spark.dynamicAllocation.maxExecutors\': \'18\'}}')
                                     ]).get_output_in_json()

        self.kwargs['batch-id'] = batch_job['id']

        # get a spark batch job with batch id
        self.cmd('az synapse spark job show --livy-id {batch-id} --workspace-name {workspace} '
                 '--spark-pool-name {spark-pool}', checks=[self.check('id', self.kwargs['batch-id'])])

        # list all spark batch jobs under a specific spark pool
        self.cmd('az synapse spark job list --workspace-name {workspace} '
                 '--spark-pool-name {spark-pool}',
                 checks=[
                     self.check('sessions[0].jobType', 'SparkBatch')
                 ])

        # cancel a spark batch job with batch id
        self.cmd('az synapse spark job cancel --livy-id {batch-id} --workspace-name {workspace} '
                 '--spark-pool-name {spark-pool} --yes')
        import time
        time.sleep(60)
        self.cmd('az synapse spark job show --livy-id {batch-id} --workspace-name {workspace} '
                 '--spark-pool-name {spark-pool}',
                 checks=[
                     self.check('result', 'Cancelled')
                 ])

    @record_only()
    @ResourceGroupPreparer(name_prefix='synapse-cli', random_name_length=16)
    def test_spark_session_and_statements(self, resource_group):
        self.kwargs.update({
            'spark-pool': 'testsparkpool',
            'workspace': 'testsynapseworkspace',
            'job': self.create_random_name(prefix='clisession', length=14),
            'executor-size': 'Small',
            'executors': 2,
            'code': "\"import time\ntime.sleep(10)\nprint('hello from cli')\"",
            'language': 'pyspark'
        })

        # create a spark session
        create_result = self.cmd('az synapse spark session create --name {job} --workspace-name {workspace} '
                                 '--spark-pool-name {spark-pool} --executor-size {executor-size} '
                                 '--executors {executors}',
                                 checks=[
                                     self.check('jobType', 'SparkSession'),
                                     self.check('name', self.kwargs['job']),
                                     self.check('state', 'not_started')
                                 ]).get_output_in_json()

        self.kwargs['session-id'] = create_result['id']

        # wait for creating spark session
        import time
        time.sleep(360)

        # get a spark session
        self.cmd('az synapse spark session show --livy-id {session-id} --workspace-name {workspace} '
                 '--spark-pool-name {spark-pool}',
                 checks=[
                     self.check('id', self.kwargs['session-id']),
                     self.check('state', 'idle')
                 ])

        # list all spark session jobs under a specific spark pook
        self.cmd('az synapse spark session list --workspace-name {workspace} '
                 '--spark-pool-name {spark-pool}',
                 checks=[
                     self.check('sessions[0].jobType', 'SparkSession')
                 ])

        # reset spark session's timeout time
        self.cmd('az synapse spark session reset-timeout --livy-id {session-id} --workspace-name {workspace} '
                 '--spark-pool-name {spark-pool}')

        # create a spark session statement job
        statement = self.cmd('az synapse spark statement invoke --session-id {session-id} '
                             '--workspace-name {workspace} --spark-pool-name {spark-pool} '
                             '--code {code} --language {language}',
                             checks=[
                                 self.check('state', 'waiting')
                             ]).get_output_in_json()
        self.kwargs['statement-id'] = statement['id']
        time.sleep(10)

        # get a spark session statement
        self.cmd('az synapse spark statement show --livy-id {statement-id} --session-id {session-id} '
                 '--workspace-name {workspace} --spark-pool-name {spark-pool}',
                 checks=[
                     self.check('state', 'running')
                 ])

        # list all spark session statements under a specific spark session
        self.cmd('az synapse spark statement list --session-id {session-id} '
                 '--workspace-name {workspace} --spark-pool-name {spark-pool}',
                 checks=[
                     self.check('statements[0].state', 'running')
                 ])

        # cancel a spark session statement
        self.cmd('az synapse spark statement cancel --livy-id {statement-id} --session-id {session-id} '
                 '--workspace-name {workspace} --spark-pool-name {spark-pool}  --yes',
                 checks=[
                     self.check('msg', 'canceled')
                 ])

        # delete/cancel a spark session
        self.cmd('az synapse spark session cancel --livy-id {session-id} --workspace-name {workspace} '
                 '--spark-pool-name {spark-pool} --yes')
        import time
        time.sleep(120)
        self.cmd('az synapse spark session show --livy-id {session-id} --workspace-name {workspace} '
                 '--spark-pool-name {spark-pool}',
                 checks=[
                     self.check('state', 'killed')
                 ])

    @record_only()
    def test_access_control(self):
        self.kwargs.update({
            'workspace': 'clitestsynapseworkspace',
            'role': 'Synapse Contributor',
            'userPrincipal': 'username@contoso.com',
            'servicePrincipal': 'testsynapsecli',
            'scopeName': 'workspaces/{workspaceName}/bigDataPools/{bigDataPoolName}',
            'itemType': 'bigDataPools',
            'item': 'testitem'})

        self.cmd(
            'az synapse role scope list --workspace-name {workspace} ',
            checks=[
                self.check("contains([], '{scopeName}')", True)
            ]
        )

        self.cmd(
            'az synapse role definition list --workspace-name {workspace}',
            checks=[
                self.check('[0].name', 'Synapse Administrator')
            ])

        # get role definition
        role_definition_get = self.cmd(
            'az synapse role definition show --workspace-name {workspace} --role "{role}" ',
            checks=[
                self.check('name', self.kwargs['role'])
            ]).get_output_in_json()

        self.kwargs['roleId'] = role_definition_get['id']

        # create role assignment
        role_assignment_create = self.cmd(
            'az synapse role assignment create --workspace-name {workspace} --role "{role}" '
            '--assignee  {servicePrincipal} --assignment-id 0550e787-7841-4669-9ac8-a8176e900002',
            checks=[
                self.check('roleDefinitionId', self.kwargs['roleId'])
            ]).get_output_in_json()
        self.kwargs['roleAssignmentId'] = role_assignment_create['id']
        self.kwargs['roleId'] = role_assignment_create['roleDefinitionId']
        self.kwargs['principalId'] = role_assignment_create['principalId']

        # create role assignment at scope
        self.cmd(
            'az synapse role assignment create --workspace-name {workspace} --role "{role}" '
            '--assignee  {servicePrincipal} --item-type {itemType} --item {item} '
            '--assignment-id 0333e787-7841-4669-9ac8-a8176e900002',
            checks=[
                self.check('roleDefinitionId', self.kwargs['roleId']),
                self.check('scope', 'workspaces/{workspace}/{itemType}/{item}')
            ])

        # get role assignment
        self.cmd(
            'az synapse role assignment show --workspace-name {workspace} --id {roleAssignmentId} ',
            checks=[
                self.check('roleDefinitionId', self.kwargs['roleId']),
                self.check('principalId', self.kwargs['principalId'])
            ])

        # list role assignment by role and scope
        self.cmd(
            'az synapse role assignment list --workspace-name {workspace} --role "{role}" --item-type {itemType} --item {item}',
            checks=[
                self.check("length([])", 2)
            ])

        # list role assignment by servicePrincipal
        self.cmd(
            'az synapse role assignment list --workspace-name {workspace} --assignee {servicePrincipal} ',
            checks=[
                self.check("length([])", 2)
            ])

        # list role assignment by object_id
        self.cmd(
            'az synapse role assignment list --workspace-name {workspace} --assignee-object-id {principalId} ',
            checks=[
                self.check("length([])", 2)
            ])

        # delete role assignment
        self.cmd(
            'az synapse role assignment delete --workspace-name {workspace} --ids {roleAssignmentId} -y ')
        self.cmd(
            'az synapse role assignment show --workspace-name {workspace} --id {roleAssignmentId} ',
            expect_failure=True)

    def _create_workspace(self, *additional_create_params):
        self.kwargs.update({
            'workspace': self.create_random_name(prefix='clitest', length=16),
            'location': self.location,
            'file-system': 'testfilesystem',
            'login-user': 'cliuser1',
            'login-password': self.create_random_name(prefix='Pswd1', length=16)
        })

        # Create adlsgen2
        # self._create_storage_account()

        # Wait some time to improve robustness
        if self.is_live or self.in_recording:
            import time
            time.sleep(60)

        # create synapse workspace
        self.cmd(
            'az synapse workspace create --name {workspace} --resource-group {rg} --storage-account {storage-account} '
            '--file-system {file-system} --sql-admin-login-user {login-user} '
            '--sql-admin-login-password {login-password}'
            ' --location {location} ' + ' '.join(additional_create_params), checks=[
                self.check('name', self.kwargs['workspace']),
                self.check('type', 'Microsoft.Synapse/workspaces'),
                self.check('provisioningState', 'Succeeded')
            ])

    def _create_storage_account(self):
        self.kwargs.update({
            'location': self.location,
            'storage-account': self.create_random_name(prefix='adlsgen2', length=16)
        })

        # Wait some time to improve robustness
        if self.is_live or self.in_recording:
            import time
            time.sleep(60)

        # create storage account
        self.cmd(
            'az storage account create --name {storage-account} --resource-group {rg} --enable-hierarchical-namespace true --location {location}',
            checks=[
                self.check('name', self.kwargs['storage-account']),
                self.check('type', 'Microsoft.Storage/storageAccounts'),
                self.check('provisioningState', 'Succeeded')
            ])

    def _create_workspace_eastus(self, *additional_create_params):
        self.kwargs.update({
            'workspace': self.create_random_name(prefix='clitest', length=16),
            'location': 'eastus',
            'file-system': 'testfilesystem',
            'login-user': 'cliuser1',
            'login-password': self.create_random_name(prefix='Pswd1', length=16)
        })

        # Create adlsgen2
        self._create_storage_account_eastus()

        # Wait some time to improve robustness
        if self.is_live or self.in_recording:
            import time
            time.sleep(60)

        # create synapse workspace
        self.cmd(
            'az synapse workspace create --name {workspace} --resource-group {rg} --storage-account {storage-account} '
            '--file-system {file-system} --sql-admin-login-user {login-user} '
            '--sql-admin-login-password {login-password}'
            ' --location {location} ' + ' '.join(additional_create_params), checks=[
                self.check('name', self.kwargs['workspace']),
                self.check('type', 'Microsoft.Synapse/workspaces'),
                self.check('provisioningState', 'Succeeded')
            ])

    def _create_storage_account_eastus(self):
        self.kwargs.update({
            'location': 'eastus',
            'storage-account': self.create_random_name(prefix='adlsgen2', length=16)
        })

        # Wait some time to improve robustness
        if self.is_live or self.in_recording:
            import time
            time.sleep(60)

        # create storage account
        self.cmd(
            'az storage account create --name {storage-account} --resource-group {rg} --enable-hierarchical-namespace true --location {location}',
            checks=[
                self.check('name', self.kwargs['storage-account']),
                self.check('type', 'Microsoft.Storage/storageAccounts'),
                self.check('provisioningState', 'Succeeded')
            ])

    @record_only()
    @ResourceGroupPreparer(name_prefix='synapse-cli', random_name_length=16)
    @StorageAccountPreparer(name_prefix='adlsgen2', length=16, location=location, hns=True, key='storage-account')
    def test_linked_service(self):
        self.kwargs.update({
            'name': 'linkedservice',
            'file': os.path.join(os.path.join(os.path.dirname(__file__), 'assets'), 'linkedservice.json')
        })

        # create a workspace
        self._create_workspace()
        # create firewall rule
        self.cmd(
            'az synapse workspace firewall-rule create --resource-group {rg} --name allowAll --workspace-name {workspace} '
            '--start-ip-address 0.0.0.0 --end-ip-address 255.255.255.255', checks=[
                self.check('provisioningState', 'Succeeded')
            ]
        )
        import time
        time.sleep(20)

        # create linked service
        self.cmd(
            'az synapse linked-service create --workspace-name {workspace} --name {name} --file @"{file}"',
            checks=[
                self.check('name', self.kwargs['name'])
            ])

        # get linked service
        self.cmd(
            'az synapse linked-service show --workspace-name {workspace} --name {name}',
            checks=[
                self.check('name', self.kwargs['name'])
            ])

        # list linked service
        self.cmd(
            'az synapse linked-service list --workspace-name {workspace}',
            checks=[
                self.check('[0].type', 'Microsoft.Synapse/workspaces/linkedservices')
            ])

        # delete linked service
        self.cmd(
            'az synapse linked-service delete --workspace-name {workspace} --name {name} -y')
        self.cmd(
            'az synapse linked-service show --workspace-name {workspace} --name {name}',
            expect_failure=True)

    @record_only()
    @ResourceGroupPreparer(name_prefix='synapse-cli', random_name_length=16)
    @StorageAccountPreparer(name_prefix='adlsgen2', length=16, location=location, hns=True, key='storage-account')
    def test_dataset(self):
        self.kwargs.update({
            'name': 'dataset'})

        # create a workspace
        self._create_workspace()
        # create firewall rule
        self.cmd(
            'az synapse workspace firewall-rule create --resource-group {rg} --name allowAll --workspace-name {workspace} '
            '--start-ip-address 0.0.0.0 --end-ip-address 255.255.255.255', checks=[
                self.check('provisioningState', 'Succeeded')
            ]
        )
        import time
        time.sleep(20)

        self.kwargs['file'] = ('{\\"properties\\":{\\"linkedServiceName\\":{\\"referenceName\\":\\"' + self.kwargs[
            'workspace'] + '-WorkspaceDefaultStorage\\",'
                           '\\"type\\":\\"LinkedServiceReference\\"},\\"type\\":\\"Orc\\",\\"typeProperties\\":{\\"location\\":{\\"type\\":\\"AzureBlobFSLocation\\"}}}}')

        # create dataset
        self.cmd(
            'az synapse dataset create --workspace-name {workspace} --name {name} --file {file}',
            checks=[
                self.check('name', self.kwargs['name'])
            ])

        # get dataset
        self.cmd(
            'az synapse dataset show --workspace-name {workspace} --name {name}',
            checks=[
                self.check('name', self.kwargs['name'])
            ])

        # list dataset
        self.cmd(
            'az synapse dataset list --workspace-name {workspace}',
            checks=[
                self.check('[0].type', 'Microsoft.Synapse/workspaces/datasets')
            ])

        # delete dataset
        self.cmd(
            'az synapse dataset delete --workspace-name {workspace} --name {name} -y')
        self.cmd(
            'az synapse dataset show --workspace-name {workspace} --name {name}',
            expect_failure=True)

    @record_only()
    def test_pipeline(self):
        self.kwargs.update({
            'workspace': 'testsynapseworkspace',
            'name': 'pipeline',
            'file': os.path.join(os.path.join(os.path.dirname(__file__), 'assets'), 'pipeline.json')
        })

        # create pipeline
        self.cmd(
            'az synapse pipeline create --workspace-name {workspace} --name {name} --file @"{file}"',
            checks=[
                self.check('name', self.kwargs['name'])
            ])

        # get pipeline
        self.cmd(
            'az synapse pipeline show --workspace-name {workspace} --name {name}',
            checks=[
                self.check('name', self.kwargs['name'])
            ])

        # list pipeline
        self.cmd(
            'az synapse pipeline list --workspace-name {workspace}',
            checks=[
                self.check('[0].type', 'Microsoft.Synapse/workspaces/pipelines')
            ])

        # create pipeline run
        pipeline_run = self.cmd(
            'az synapse pipeline create-run --workspace-name {workspace} --name {name}').get_output_in_json()
        self.kwargs['runId'] = pipeline_run['runId']

        # cancel pipeline run
        self.cmd(
            'az synapse pipeline-run cancel --workspace-name {workspace} --run-id {runId} -y')
        import time
        time.sleep(20)

        # get pipeline run by run id
        self.cmd(
            'az synapse pipeline-run show --workspace-name {workspace} --run-id {runId}',
            checks=[
                self.check('status', 'Cancelled')
            ])

        # get pipeline run by workspace
        self.cmd(
            'az synapse pipeline-run query-by-workspace --workspace-name {workspace} '
            '--last-updated-after 2020-09-01T00:36:44.3345758Z --last-updated-before 2020-10-16T00:36:44.3345758Z')

        # get acticity run
        self.cmd(
            'az synapse activity-run query-by-pipeline-run --workspace-name {workspace} --name {name} --run-id {runId} '
            '--last-updated-after 2020-09-01T00:36:44.3345758Z --last-updated-before 2020-10-16T00:36:44.3345758Z')

        # delete pipeline
        self.cmd(
            'az synapse pipeline delete --workspace-name {workspace} --name {name} -y')
        self.cmd(
            'az synapse pipeline show --workspace-name {workspace} --name {name}',
            expect_failure=True)

    @record_only()
    def test_trigger(self):
        self.kwargs.update({
            'workspace': 'testsynapseworkspace',
            'name': 'trigger',
            'event-trigger': 'EventTrigger',
            'tumbling-window-trigger': 'TumblingWindowTrigger',
            'run-id': '08586024051698130326966471413CU40',
            'file': os.path.join(os.path.join(os.path.dirname(__file__), 'assets'), 'trigger.json')
        })

        # create trigger
        self.cmd(
            'az synapse trigger create --workspace-name {workspace} --name {name} --file @"{file}"',
            checks=[
                self.check('name', self.kwargs['name'])
            ])

        # get trigger
        self.cmd(
            'az synapse trigger show --workspace-name {workspace} --name {name}',
            checks=[
                self.check('name', self.kwargs['name'])
            ])

        # list trigger
        self.cmd(
            'az synapse trigger list --workspace-name {workspace}',
            checks=[
                self.check('[0].type', 'Microsoft.Synapse/workspaces/triggers')
            ])

        # delete trigger
        self.cmd(
            'az synapse trigger delete --workspace-name {workspace} --name {name} -y')
        self.cmd(
            'az synapse trigger show --workspace-name {workspace} --name {name}',
            expect_failure=True)

        # subscribe to event
        self.cmd(
            'az synapse trigger subscribe-to-event --workspace-name {workspace} --name {event-trigger}',
            checks=[
                self.check('status', 'Provisioning')
            ])
        import time
        time.sleep(20)

        # get event subscription status
        self.cmd(
            'az synapse trigger get-event-subscription-status --workspace-name {workspace} --name {event-trigger}',
            checks=[
                self.check('status', 'Enabled')
            ])

        # unsubscribe from event
        self.cmd(
            'az synapse trigger unsubscribe-from-event --workspace-name {workspace} --name {event-trigger}',
            checks=[
                self.check('status', 'Deprovisioning')
            ])

        # start a trigger
        self.cmd(
            'az synapse trigger start --workspace-name {workspace} --name {tumbling-window-trigger}')

        # get trigger run by workspace
        self.cmd(
            'az synapse trigger-run query-by-workspace --workspace-name {workspace} '
            '--last-updated-after 2020-09-01T00:36:44.3345758Z --last-updated-before 2020-10-01T00:36:44.3345758Z')

        # rerun a trigger
        self.cmd(
            'az synapse trigger-run rerun --workspace-name {workspace} --name {tumbling-window-trigger} --run-id {run-id}')

        # stop a trigger
        self.cmd(
            'az synapse trigger stop --workspace-name {workspace} --name {tumbling-window-trigger}')

    @record_only()
    @unittest.skip('(InvalidTokenIssuer) Token Authentication failed with SecurityTokenInvalidIssuerException')
    def test_data_flow(self):
        self.kwargs.update({
            'workspace': 'testsynapseworkspace',
            'name': 'dataflow',
            'file': os.path.join(os.path.join(os.path.dirname(__file__), 'assets'), 'dataflow.json')
        })

        # create data flow
        self.cmd(
            'az synapse data-flow create --workspace-name {workspace} --name {name} --file @"{file}"',
            checks=[
                self.check('name', self.kwargs['name'])
            ])

        # get data flow
        self.cmd(
            'az synapse data-flow show --workspace-name {workspace} --name {name}',
            checks=[
                self.check('name', self.kwargs['name'])
            ])

        # list data flow
        self.cmd(
            'az synapse data-flow list --workspace-name {workspace}',
            checks=[
                self.check('[0].type', 'Microsoft.Synapse/workspaces/dataflows')
            ])

        # delete data flow
        self.cmd(
            'az synapse data-flow delete --workspace-name {workspace} --name {name} -y')
        self.cmd(
            'az synapse data-flow show --workspace-name {workspace} --name {name}',
            expect_failure=True)

    @record_only()
    @ResourceGroupPreparer(name_prefix='synapse-cli', random_name_length=16)
    @StorageAccountPreparer(name_prefix='adlsgen2', length=16, location=location, hns=True, key='storage-account')
    def test_notebook(self):
        self.kwargs.update({
            'workspace': 'testsynapseworkspace',
            'name': 'notebook',
            'spark-pool': 'testpool',
            'spark-version': '2.4',
            'file': os.path.join(os.path.join(os.path.dirname(__file__), 'assets'), 'notebook.ipynb')
        })

        # create a workspace
        self._create_workspace()

        # create firewall rule
        self.cmd(
            'az synapse workspace firewall-rule create --resource-group {rg} --name allowAll --workspace-name {workspace} '
            '--start-ip-address 0.0.0.0 --end-ip-address 255.255.255.255', checks=[
                self.check('provisioningState', 'Succeeded')
            ]
        )

        # create spark pool
        self.cmd('az synapse spark pool create --name {spark-pool} --spark-version {spark-version}'
                 ' --workspace {workspace} --resource-group {rg} --node-count 3 --node-size Medium',
                 checks=[
                     self.check('name', self.kwargs['spark-pool']),
                     self.check('type', 'Microsoft.Synapse/workspaces/bigDataPools'),
                     self.check('provisioningState', 'Succeeded')
                 ]).get_output_in_json()

        # create notebook
        self.cmd(
            'az synapse notebook create --workspace-name {workspace} --name {name} --file @"{file}" '
            '--spark-pool-name {spark-pool}',
            checks=[
                self.check('name', self.kwargs['name'])
            ])

        # get notebook
        self.cmd(
            'az synapse notebook show --workspace-name {workspace} --name {name}',
            checks=[
                self.check('name', self.kwargs['name'])
            ])

        # list notebook
        self.cmd(
            'az synapse notebook list --workspace-name {workspace}',
            checks=[
                self.check('[0].type', 'Microsoft.Synapse/workspaces/notebooks')
            ])

        # export notebook
        self.kwargs['output-folder'] = os.getcwd()
        self.cmd(
            'az synapse notebook export --workspace-name {workspace} --name {name} '
            '--output-folder "{output-folder}"')
        file_path = os.path.join(self.kwargs['output-folder'], self.kwargs['name'] + '.ipynb')
        self.assertTrue(os.path.isfile(file_path))
        os.remove(file_path)

        # delete notebook
        self.cmd(
            'az synapse notebook delete --workspace-name {workspace} --name {name} -y')
        self.cmd(
            'az synapse notebook show --workspace-name {workspace} --name {name}',
            expect_failure=True)

    @record_only()
    def test_integration_runtime(self):
        self.kwargs.update({
            'rg': 'chayang-test-rg',
            'workspace': 'zes0219test',
            'name': 'integrationruntime',
            'type': 'Managed',
            'selfhosted-integration-runtime': 'IntegrationRuntime0219selfhosted0507',
            'node': 'MININT-Q3EGQJ8'})

        # create integration runtime
        self.cmd(
            'az synapse integration-runtime create --resource-group {rg} --workspace-name {workspace} --name {name} --type {type}',
            checks=[
                self.check('name', self.kwargs['name'])
            ])

        # get integration runtime
        self.cmd(
            'az synapse integration-runtime show --resource-group {rg} --workspace-name {workspace} --name {name}',
            checks=[
                self.check('name', self.kwargs['name'])
            ])

        # list integration runtime
        self.cmd(
            'az synapse integration-runtime list --resource-group {rg} --workspace-name {workspace}',
            checks=[
                self.check('[0].type', 'Microsoft.Synapse/workspaces/integrationruntimes')
            ])

        # delete integration runtime
        self.cmd(
            'az synapse integration-runtime delete --resource-group {rg} --workspace-name {workspace} --name {name} -y')
        self.cmd(
            'az synapse integration-runtime show --resource-group {rg} --workspace-name {workspace} --name {name}',
            expect_failure=True)

        # upgrade self-hosted integration runtime
        self.cmd(
            'az synapse integration-runtime upgrade --resource-group {rg} --workspace-name {workspace} --name {selfhosted-integration-runtime}')

        # get keys for a self-hosted integration runtime
        key = self.cmd(
            'az synapse integration-runtime list-auth-key --resource-group {rg} --workspace-name {workspace} --name {selfhosted-integration-runtime}').get_output_in_json()
        assert key['authKey1'] is not None
        assert key['authKey2'] is not None

        # regenerate self-hosted integration runtime key
        key = self.cmd(
            'az synapse integration-runtime regenerate-auth-key --resource-group {rg} --workspace-name {workspace} --name {selfhosted-integration-runtime} '
            '--key-name authKey1').get_output_in_json()
        assert key['authKey1'] is not None
        assert key['authKey2'] is None

        # get metric data for a self-hosted integration runtime
        self.cmd(
            'az synapse integration-runtime get-monitoring-data --resource-group {rg} --workspace-name {workspace} --name {selfhosted-integration-runtime}',
            checks=[
                self.check('name', self.kwargs['selfhosted-integration-runtime'])
            ])

        # get self-hosted integration runtime node information
        self.cmd(
            'az synapse integration-runtime-node show --resource-group {rg} --workspace-name {workspace} --name {selfhosted-integration-runtime} '
            '--node-name {node}',
            checks=[
                self.check('nodeName', self.kwargs['node'])
            ])

        # update self-hosted integration runtime node
        self.cmd(
            'az synapse integration-runtime-node update --resource-group {rg} --workspace-name {workspace} \
            --name {selfhosted-integration-runtime} --node-name {node} --auto-update On --update-delay-offset PT03H',
            checks=[
                self.check('nodeName', self.kwargs['node'])
            ])

        # get self-hosted integration runtime node ip
        self.cmd(
            'az synapse integration-runtime-node get-ip-address --resource-group {rg} --workspace-name {workspace} --name {selfhosted-integration-runtime} '
            '--node-name {node}')

        # sync credentials among integration runtime nodes
        self.cmd(
            'az synapse integration-runtime sync-credentials --resource-group {rg} --workspace-name {workspace} --name {selfhosted-integration-runtime}')

        # get connection info
        self.cmd(
            'az synapse integration-runtime get-connection-info --resource-group {rg} --workspace-name {workspace} --name {selfhosted-integration-runtime}')

        # get status
        self.cmd(
            'az synapse integration-runtime get-status --resource-group {rg} --workspace-name {workspace} --name {selfhosted-integration-runtime}',
            checks=[
                self.check('name', self.kwargs['selfhosted-integration-runtime'])
            ])

    def _get_storage_endpoint(self, storage_account, resource_group):
        return self.cmd('az storage account show -g {} -n {}'
                        ' --query primaryEndpoints.blob'
                        .format(resource_group, storage_account)).get_output_in_json()


    def _get_storage_key(self, storage_account, resource_group):
        return self.cmd('az storage account keys list -g {} -n {} --query [0].value'
                        .format(resource_group, storage_account)).get_output_in_json()

    @record_only()
    @ResourceGroupPreparer(name_prefix='synapse-cli', random_name_length=16)
    def test_managed_private_endpoints(self):
        self.kwargs.update({
            'workspace': 'testsynapseworkspacepe',
            'name': 'AzureDataLakeStoragePE',
            'privateLinkResourceId': '/subscriptions/051ddeca-1ed6-4d8b-ba6f-1ff561e5f3b3/resourceGroups/bigdataqa/providers/Microsoft.Storage/storageAccounts/hozhao0917gen2',
            'groupId': 'dfs'})

        # create managed private endpoint
        self.cmd(
            'az synapse  managed-private-endpoints create --workspace-name {workspace} --pe-name {name} --resource-id {privateLinkResourceId} --group-Id {groupId}',
            checks=[
                self.check('name', self.kwargs['name'])
            ])

        # wait some time to improve robustness
        if self.is_live or self.in_recording:
            import time
            time.sleep(90)
        # get managed private endpoint
        self.cmd(
            'az synapse  managed-private-endpoints show --workspace-name {workspace} --pe-name {name}',
            checks=[
                self.check('name', self.kwargs['name'])
            ])

        # list managed private endpoint
        self.cmd(
            'az synapse  managed-private-endpoints list --workspace-name {workspace}',
           checks=[
                self.check('[0].type', 'Microsoft.Synapse/workspaces/managedVirtualNetworks/managedPrivateEndpoints')
            ])
        
        # delete managed private endpoint
        self.cmd(
            'az synapse  managed-private-endpoints delete --workspace-name {workspace} --pe-name {name} -y')
        if self.is_live or self.in_recording:
            import time
            time.sleep(60)    
        self.cmd(
            'az synapse managed-private-endpoints show --workspace-name {workspace} --pe-name {name}',
            expect_failure=True)
