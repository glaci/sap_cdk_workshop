import json
import boto3
import os
import cfnresponse
import logging
import threading

sm_client = boto3.client('secretsmanager')
ds_client = boto3.client('ds')
responseStr = {'Status' : {}}

def handler(event, context):

    status = cfnresponse.SUCCESS
    try:
        if event['RequestType'] == 'Delete':
            response = ds_client.describe_directories()
            ds_client.delete_directory(
                DirectoryId = response['DirectoryDescriptions'][0]['DirectoryId']
            )       
            responseStr['Status']['LambdaFunction'] = "Delete AD Connector"
        else:
            response = sm_client.get_secret_value(
            SecretId = os.environ['SM_DOMAIN_PASSWORD']
            )

            username = json.loads(response['SecretString'])['username']
            password = json.loads(response['SecretString'])['password']

            ds_client.connect_directory(
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
            responseStr['Status']['LambdaFunction'] = "Create AD Connector"

    except Exception as e:
        logging.error('Exception: %s' % e, exc_info=True)
        print (str(e))
        responseStr['Status']['LambdaFunction'] = str(e)
        status = cfnresponse.FAILED

    finally:
        cfnresponse.send(event, context, status, {'Status':json.dumps(responseStr)}, None)
