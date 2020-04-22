import json
import boto3
import os
import cfnresponse
import logging
import threading

client = boto3.client('ram')
responseStr = {'Status' : {}}

def handler(event, context):

    status = cfnresponse.SUCCESS
    try:
        response = client.get_resource_share_invitations()

        if event['RequestType'] == 'Delete':
            client.disassociate_resource_share(
            resourceShareArn = response['resourceShareInvitations'][0]['resourceShareArn'],
            principals = [ os.environ['ACCOUNT_ID'] ]
            )
            responseStr['Status']['LambdaFunction'] = "Disassociate Share Resource"

        else:
            client.accept_resource_share_invitation(
            resourceShareInvitationArn = response['resourceShareInvitations'][0]['resourceShareInvitationArn']
            )
            responseStr['Status']['LambdaFunction'] = "Accept Share Resource"

    except Exception as e:
        logging.error('Exception: %s' % e, exc_info=True)
        print (str(e))
        responseStr['Status']['LambdaFunction'] = str(e)
        status = cfnresponse.FAILED

    finally:
        cfnresponse.send(event, context, status, {'Status':json.dumps(responseStr)}, None)
