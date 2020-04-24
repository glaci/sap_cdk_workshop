#!/usr/bin/env python3

from aws_cdk import core
from AWSWorkSpaces.PrepVpc import PrepVpcStack
from AWSWorkSpaces.Vpc import VpcStack
from AWSWorkSpaces.DirectoryService import DirectoryServiceStack
from vpc_ec2.ec2_stack  import CdkVpcEc2Stack

app = core.App()
env_workspaces = core.Environment(
    account = app.node.try_get_context("target")['account'],
    region = app.node.try_get_context("target")['region']
)

Prep = PrepVpcStack(
    app, "PrepStack",
    env = env_workspaces
)

Vpc = VpcStack(
    app, "NewVPC",
    env = env_workspaces
)

CdkVpcEc2Stack(app, "vpc-ec2", env=env_workspaces)


AD = DirectoryServiceStack(
    app, "NewADConnector", Vpc,
    env = env_workspaces
)

app.synth()
