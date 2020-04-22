import json
import boto3
import os
import cfnresponse
import logging
import threading

client = boto3.client('ds')
responseStr = {'Status' : {}}

def handler(event, context):

    status = cfnresponse.SUCCESS
    try:
        if event['RequestType'] == 'Delete':
            client.describe_directories()
            client.delete_directory()

            responseStr['Status']['LambdaFunction'] = "Delete AD Connector"

        else:
            client.connect_directory(
                Name = os.environ['DIRECTORY_ID'],
                Password = os.environ['DIRECTORY_ID'],
                Size = 'Small',
                ConnectSettings = {
                    'VpcId': os.environ['DIRECTORY_ID'],
                    'SubnetIds': [ os.environ['DIRECTORY_ID'], os.environ['DIRECTORY_ID']],
                    'CustomerDnsIps': [ os.environ['DIRECTORY_ID'],os.environ['DIRECTORY_ID'] ],
                    'CustomerUserName': os.environ['DIRECTORY_ID']
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
