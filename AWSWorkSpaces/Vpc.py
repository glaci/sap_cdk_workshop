from aws_cdk import core
import aws_cdk.aws_ec2 as _ec2


class AwsVpcStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # The code that defines your stack goes here
        vpc_workspaces = _ec2.Vpc(
            self, "VPCWorkSpaces",
            cidr = ,
            
        )
