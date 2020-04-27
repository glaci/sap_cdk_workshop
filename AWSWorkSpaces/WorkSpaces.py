from aws_cdk import core
import aws_cdk.aws_directoryservice as _ds
import aws_cdk.aws_workspaces as _ws
import aws_cdk.aws_ec2 as _ec2
import aws_cdk.aws_ssm as _ssm


class AWSWorkSpaces(core.Stack):

    def __init__(self, scope: core.Construct, id: str, directory, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # The code that defines your stack goes here
        _user = self.node.try_get_context("target")['workspacesuser']
        _windows = self.node.try_get_context("target")['workspacesbundle']

        # Import SSM Paratemer for Directory Service
        dsid = _ssm.StringParameter.from_string_parameter_name(
             self, "ImportSSMParameterDSID",
             string_parameter_name = "DirectoryServiceID"
        )

        #build up a workspaces based on windows 10 bundle_id
        ws = _ws.CfnWorkspace(
            self,"WorkSpaces",
            bundle_id = _windows,
            directory_id = dsid.string_value,
            user_name = _user
        )
