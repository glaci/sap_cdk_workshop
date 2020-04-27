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
        # parameters should be extracted
        vpc_id = "vpc-ba535ddd"  # Import an Exist VPC
        ec2_type = "t2.medium"
        key_name = "keyWorkspace" 
        directoryId = "d-956712d519"
        directoryName = "test.lab"
        dnsIpAddresses1 = "10.0.3.193"
        dnsIpAddresses2 = "10.0.4.102"


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

    

        # =========
        #   EC2
        # =========
        windows_ami = _ec2.WindowsImage(_ec2.WindowsVersion.WINDOWS_SERVER_2019_ENGLISH_FULL_BASE)

        # The code that defines your stack goes here
        vpc = _ec2.Vpc.from_lookup(self, "VPC", vpc_id=vpc_id)

        # Create role "EC2JoinDomain" to apply on Windows EC2JoinDomain (EC2)
        ssmrole = _iam.Role(
            self,"SSMRoleforEC2",
            assumed_by = _iam.ServicePrincipal('ec2.amazonaws.com'),
            managed_policies = [
                _iam.ManagedPolicy.from_managed_policy_arn(
                    self,"AmazonSSMManagedInstanceCore",
                    managed_policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
                ),
                _iam.ManagedPolicy.from_managed_policy_arn(
                    self,"AmazonSSMDirectoryServiceAccess",
                    managed_policy_arn = "arn:aws:iam::aws:policy/AmazonSSMDirectoryServiceAccess"
                )
            ],
            role_name = "EC2JoinDomain"
        )

        # create windows ec2 instance
        host = _ec2.Instance(self, "myEC2",
                            instance_type=_ec2.InstanceType(
                                instance_type_identifier=ec2_type),
                            instance_name="myAdHost",
                            machine_image=windows_ami,
                            vpc=vpc,
                            role=ssmrole,
                            key_name=key_name,
                            vpc_subnets=_ec2.SubnetSelection(
                                subnet_type=_ec2.SubnetType.PUBLIC)
                            # user_data=ec2.UserData.custom(user_data)
                            )

        host.connections.allow_from_any_ipv4(_ec2.Port.tcp(3389), "Allow RDP from internet")

        core.CfnOutput(self, "Output", value=host.instance_public_ip)

        # Create SSM Document to join Window EC2 into AD
        ssmdocument = _ssm.CfnDocument(
            self, "SSMDocumentJoinAD",
            document_type = "Command",
            name = "SSMDocumentJoinAD",
            content =
            {
                "schemaVersion": "1.0",
                "description": "Automatic Domain Join Configuration created by EC2 Console.",
                "runtimeConfig": {
                    "aws:domainJoin": {
                        "properties": {
                            "directoryId": directoryId,
                            "directoryName": directoryName,
                            "dnsIpAddresses": [
                                dnsIpAddresses1,
                                dnsIpAddresses2
                            ]
                        }
                    }
                }
            }
        )

        # Create SSM Associate to trigger SSM doucment to let Windows EC2JoinDomain (EC2) join Domain
        ssmjoinad = _ssm.CfnAssociation(
            self,"WindowJoinAD",
            name = ssmdocument.name,
            targets = [{
                "key": "InstanceIds",
                "values": [ host.instance_id ]
            }]
        )

        ssmjoinad.add_depends_on(ssmdocument)

# def get_ad(self):
    #     return self.ssm_directory_service.string_value