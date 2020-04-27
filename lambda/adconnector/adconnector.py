import json
import boto3
import os
import cfnresponse
import logging
import threading
import time

sm_client = boto3.client('secretsmanager')
ds_client = boto3.client('ds')
ssm_client = boto3.client('ssm')
ws_client = boto3.client('workspaces')

responseStr = {'Status' : {}}

def handler(event, context):

    status = cfnresponse.SUCCESS
    try:
        if event['RequestType'] == 'Delete':
            response = ds_client.describe_directories()

            ws_client.deregister_workspace_directory(
                DirectoryId = response['DirectoryDescriptions'][0]['DirectoryId']
            )

            ds_client.delete_directory(
                DirectoryId = response['DirectoryDescriptions'][0]['DirectoryId']
            )

            ssm_client.delete_parameter(
                Name = 'DirectoryServiceID'
            )

            responseStr['Status']['LambdaFunction'] = "Delete AD Connector"
        else:
            response = sm_client.get_secret_value(
            SecretId = os.environ['SM_DOMAIN_PASSWORD']
            )

            username = json.loads(response['SecretString'])['username']
            password = json.loads(response['SecretString'])['password']

            dsresponse = ds_client.connect_directory(
                Name = os.environ['DOMAIN_NAME'],
                Password = password,
                Size = 'Small',
                ConnectSettings = {
                    'VpcId': os.environ['VPC_ID'],
                    'SubnetIds': [ os.environ['SUBNETID1'], os.environ['SUBNETID2'] ],
                    'CustomerDnsIps': [ os.environ['DNSIP1'],os.environ['DNSIP2'] ],
                    'CustomerUserName': username
                }
            )

            result = ds_client.describe_directories(
                    DirectoryIds= [ dsresponse['DirectoryId'] ]
            )['DirectoryDescriptions'][0]['Stage']

            while result != 'Active':
                time.sleep(30)
                result = ds_client.describe_directories(
                        DirectoryIds= [ dsresponse['DirectoryId'] ]
                )['DirectoryDescriptions'][0]['Stage']
                if result == 'Failed':
                    break

            if result == 'Active':
                ws_client.register_workspace_directory(
                    DirectoryId = dsresponse['DirectoryId'],
                    EnableWorkDocs = False
                )

            ssm_client.put_parameter(
                Name = 'DirectoryServiceID',
                Description = 'AD Connector ID',
                Value = dsresponse['DirectoryId'],
                Type = 'String'
            )

            responseStr['Status']['LambdaFunction'] = "Create AD Connector"

    except Exception as e:
        logging.error('Exception: %s' % e, exc_info=True)
        print (str(e))
        responseStr['Status']['LambdaFunction'] = str(e)
        status = cfnresponse.FAILED

    finally:
        cfnresponse.send(event, context, status, {'Status':json.dumps(responseStr)}, None)
