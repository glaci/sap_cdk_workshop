#!/usr/bin/env python3

from aws_cdk import core

from AWSWorkSpaces.Vpc import VpcStack
from AWSWorkSpaces.DirectoryService import DirectoryServiceStack

app = core.App()

env_workspaces = core.Environment(
    account = app.node.try_get_context("account"),
    region = app.node.try_get_context("region")
)

Vpc = VpcStack(
    app, "NewVPC",
    env = env_workspaces
)

AD = DirectoryServiceStack(
    app, "NewADConnector", Vpc
    env = env_workspaces
)

app.synth()
