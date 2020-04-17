from aws_cdk import core
import aws_cdk.aws_ec2 as _ec2
import aws_cdk.aws_directoryservice as _ds


class DirectoryServiceStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, vpc, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        
