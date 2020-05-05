#!/usr/bin/env python3
import boto3,sys

profile=sys.argv[1]

boto3.setup_default_session(profile_name=profile)

#create key pair
ec2 = boto3.client('ec2')
new_keypair = ec2.create_key_pair(KeyName='keyWorkspace')

# save to local
with open('./key_workspace.pem', 'w') as file:
    file.write(new_keypair.get('KeyMaterial'))

#print(new_keypair.get('KeyMaterial'))
