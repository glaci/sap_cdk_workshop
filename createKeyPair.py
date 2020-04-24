#!/usr/bin/env python3
import boto3

boto3.setup_default_session(profile_name='security1')

ec2 = boto3.client('ec2')



new_keypair = ec2.create_key_pair(KeyName='keyWorkspace')

with open('./key_workspace.pem', 'w') as file:
    file.write(new_keypair.get('KeyMaterial'))

print(new_keypair.get('KeyMaterial'))
