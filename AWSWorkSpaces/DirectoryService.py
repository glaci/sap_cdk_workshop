from aws_cdk import core
import aws_cdk.aws_ec2 as _ec2
import aws_cdk.aws_directoryservice as _ds
import aws_cdk.aws_iam as _iam
import aws_cdk.aws_lambda as _lambda
import aws_cdk.aws_cloudformation as _cf
import aws_cdk.aws_ssm as _ssm


class DirectoryServiceStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, vpc, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        #Import Data
        _vpc = vpc.get_vpc_stack()
        _subnet = vpc.get_vpc_subnets()
        _doamin_name = self.node.try_get_context("source")['doamin_name']
        _doamin_server_ips = self.node.try_get_context("source")['dnsips']
        _domain_user = self.node.try_get_context("source")['domain_user']
        _sm_domain_password = self.node.try_get_context("source")['sm_domain_password']

        # Create Policy to workspaces_DefaultRole Role
        wsdefaultpolicy = _iam.PolicyDocument(
            statements = [
                _iam.PolicyStatement(
                    actions = [
                    "ec2:CreateNetworkInterface",
                    "ec2:DeleteNetworkInterface",
                    "ec2:DescribeNetworkInterfaces"
                    ],
                    resources = [ "*" ]
                ),
                _iam.PolicyStatement(
                    actions = [
                    "workspaces:RebootWorkspaces",
                    "workspaces:RebuildWorkspaces",
                    "workspaces:ModifyWorkspaceProperties"
                    ],
                    resources = [ "*" ]
                )
            ]
        )

        # Create role workspaces_DefaultRole for later WorkSpaces API usage
        wsrole = _iam.Role(
            self, "WorkSpacesDefaultRole",
            assumed_by = _iam.ServicePrincipal('workspaces.amazonaws.com'),
            inline_policies = { "WorkSpacesDefaultPolicy": wsdefaultpolicy },
            role_name = "workspaces_DefaultRole"
        )

        # Create IAM Policy for LambdaFunction: Create AD Connector
        lambdapolicy = _iam.PolicyDocument(
            statements = [
                _iam.PolicyStatement(
                    actions = [ "logs:CreateLogGroup" ],
                    resources = [ "arn:aws:logs:{}:{}:*".format(self.region,self.account) ]
                ),
                _iam.PolicyStatement(
                    actions = [
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    resources = [ "arn:aws:logs:{}:{}:log-group:/aws/lambda/*".format(self.region,self.account) ]
                ),
                _iam.PolicyStatement(
                    actions = [
                        "ds:ConnectDirectory",
                        "ds:DescribeDirectories",
                        "ds:DeleteDirectory",
                        "ds:AuthorizeApplication",
                        "ds:UnauthorizeApplication",
                        "workspaces:RegisterWorkspaceDirectory",
                        "workspaces:DeregisterWorkspaceDirectory",
                        "iam:GetRole",
                        "ec2:AuthorizeSecurityGroupEgress",
                        "ec2:AuthorizeSecurityGroupIngress",
                        "ec2:CreateNetworkInterface",
                        "ec2:CreateSecurityGroup",
                        "ec2:CreateTags",
                        "ec2:DescribeNetworkInterfaces",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeVpcs",
                        "ec2:DescribeInternetGateways",
                        "ec2:DescribeRouteTables",
                        "ec2:DescribeAvailabilityZones",
                        "ec2:DeleteSecurityGroup",
                        "ec2:DeleteNetworkInterface",
                        "ec2:RevokeSecurityGroupIngress",
                        "ec2:RevokeSecurityGroupEgress",
                        "ec2:DeleteTags",
                        "kms:Decrypt"
                    ],
                    resources = [ "*" ]
                ),
                _iam.PolicyStatement(
                    actions = [
                        "secretsmanager:GetSecretValue",
                        "secretsmanager:DescribeSecret"
                    ],
                    resources = [ "arn:aws:secretsmanager:{}:{}:secret:{}*".format(self.region,self.account,_sm_domain_password) ]
                ),
                _iam.PolicyStatement(
                    actions = [
                        "ssm:PutParameter",
                        "ssm:LabelParameterVersion",
                        "ssm:DeleteParameter",
                        "ssm:GetManifest"
                    ],
                    resources = [ "arn:aws:ssm:{}:{}:parameter/*".format(self.region,self.account) ]
                )
            ]
        )

        # Creare a IAM Role for Lambda
        lambdarole = _iam.Role(
            self,"LambdaRoleToCreateADConnector",
            assumed_by = _iam.ServicePrincipal('lambda.amazonaws.com'),
            inline_policies = { "LambdaCreateADConnector": lambdapolicy },
            role_name = "Lambda_Create_ADConnector"
        )

        # Create a Lambda function to Register Directory Service on WorkSpaces
        adlambda = _lambda.Function(
            self, "LambdaStackForAD",
            runtime = _lambda.Runtime.PYTHON_3_7,
            handler = "adconnector.handler",
            role = lambdarole,
            code=_lambda.Code.asset('lambda/adconnector'),
            environment={
                "DOMAIN_NAME": _doamin_name,
                "SM_DOMAIN_PASSWORD": _sm_domain_password,
                "VPC_ID": _vpc.ref,
                "SUBNETID1": _subnet[0].ref,
                "SUBNETID2": _subnet[1].ref,
                "DNSIP1": _doamin_server_ips[0],
                "DNSIP2": _doamin_server_ips[1],
            },
            timeout = core.Duration.seconds(900),
            function_name = "create_adconnector"
        )
        
        # Create a customResource to trigger Lambda function after Lambda function is created
        _cf.CfnCustomResource(
            self, "InvokeLambdaFunction",
            service_token = adlambda.function_arn
        )

    # def get_ad(self):
    #     return self.ssm_directory_service.string_value
