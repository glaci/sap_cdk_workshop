#!/usr/bin/env python3

from aws_cdk import core

from AWSWorkSpaces.Vpc import AwsVpcStack


env_workspaces = core.Environment(
    account = app.node.try_get_context("account"),
    region = app.node.try_get_context("region")
)

app = core.App()

Vpc = AwsVpcStack(
    app, "NewVPC",
    env = env_workspaces
)

app.synth()
