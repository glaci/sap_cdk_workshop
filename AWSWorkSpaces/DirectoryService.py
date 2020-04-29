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

        # Import Data from cdk.json
        _doamin_name = self.node.try_get_context("source")['doamin_name']
        _doamin_server_ips = self.node.try_get_context("source")['dnsips']
        _domain_user = self.node.try_get_context("source")['domain_user']
        _sm_domain_password = self.node.try_get_context("source")['sm_domain_password']
        _ec2_type = self.node.try_get_context("target")['ec2_type']
        _key_name = self.node.try_get_context("target")['key_name']

        # Import Resource Stack (VPC, Subnet)
        _subnet1 = _ec2.Subnet.from_subnet_attributes(
            self, "PublicSubnet1",
            subnet_id = vpc.get_vpc_subnets()[0].ref,
            availability_zone = vpc.get_vpc_subnets()[0].availability_zone
        )

        _subnet2 = _ec2.Subnet.from_subnet_attributes(
            self, "PublicSubnet2",
            subnet_id = vpc.get_vpc_subnets()[1].ref,
            availability_zone = vpc.get_vpc_subnets()[1].availability_zone
        )

        _vpc = _ec2.Vpc.from_vpc_attributes(
            self, "VPC",
            vpc_id = vpc.get_vpc_stack().ref,
            availability_zones = [ _subnet1.availability_zone, _subnet2.availability_zone ]
        )

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
                "VPC_ID": _vpc.vpc_id,
                "SUBNETID1": _subnet1.subnet_id,
                "SUBNETID2": _subnet2.subnet_id,
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

        # The code that defines your stack goes here


         # Create a security group for RDP access on Windows EC2JoinDomain (EC2)
        rdpsg = _ec2.SecurityGroup(
            self, "SGForRDP",
            vpc = _vpc,
            description = "The Secrurity Group from local environment to Windows EC2 Instance"
        )

        rdpsg.add_ingress_rule(
            peer = _ec2.Peer.ipv4("0.0.0.0/0"),
            connection = _ec2.Port.tcp(3389)
        )

        # create windows ec2 instance
        host = _ec2.Instance(
           self, "myEC2",
           instance_type = _ec2.InstanceType(
              instance_type_identifier = _ec2_type ),
           instance_name = "myAdHost",
           machine_image = windows_ami,
           vpc = _vpc,
           role = ssmrole,
           key_name = _key_name,
           security_group = rdpsg,
           vpc_subnets = _ec2.SubnetSelection(
              subnets = [ _subnet1, _subnet2 ] )
        )


        # Create SSM Document to join Window EC2 into AD
        ssmdocument = _ssm.CfnDocument(
            self, "SSMDocumentJoinAD",
            document_type = "Command",
            name = "SSMDocumentJoinAD",
            content =
            {
                "description": "Run a PowerShell script to domain join a Windows instance securely",
                "schemaVersion": "2.0",
                "mainSteps": [
                    {
                        "action": "aws:runPowerShellScript",
                        "name": "runPowerShellWithSecureString",
                        "inputs": {
                            "runCommand": [
                            "# Example PowerShell script to domain join a Windows instance securely",
                            "# Adopt the document from AWS Blog Join a Microsoft Active Directory Domain with Parameter Store and Amazon EC2 Systems Manager Documents",
                            "",
                            "$ErrorActionPreference = 'Stop'",
                            "",
                            "try{",
                            "    # Parameter names"
                            "    $domainJoinPasswordParameterStore = \"{}\"".format(_sm_domain_password),
                            "",
                            "    # Retrieve configuration values from parameters",
                            "    $ipdns = \"{}\"".format(_doamin_server_ips[0]),
                            "    $domain = \"{}\"".format(_doamin_name),
                            "    $username = ((Get-SECSecretValue -SecretId $domainJoinPasswordParameterStore ).SecretString | ConvertFrom-Json ).username",
                            "    $password = ((Get-SECSecretValue -SecretId $domainJoinPasswordParameterStore ).SecretString | ConvertFrom-Json ).password | ConvertTo-SecureString -asPlainText -Force ",
                            "",
                            "    # Create a System.Management.Automation.PSCredential object",
                            "    $credential = New-Object System.Management.Automation.PSCredential($username, $password)",
                            "",
                            "    # Determine the name of the Network Adapter of this machine",
                            "    $networkAdapter = Get-WmiObject Win32_NetworkAdapter -Filter \"AdapterType = 'Ethernet 802.3'\"",
                            "    $networkAdapterName = ($networkAdapter | Select-Object -First 1).NetConnectionID",
                            "",
                            "    # Set up the IPv4 address of the AD DNS server as the first DNS server on this machine",
                            "    netsh.exe interface ipv4 add dnsservers name=$networkAdapterName address=$ipdns index=1",
                            "",
                            "    # Join the domain and reboot",
                            "    Add-Computer -DomainName $domain -Credential $credential",
                            "    Restart-Computer -Force",
                            "}",
                            "catch [Exception]{",
                            "    Write-Host $_.Exception.ToString()",
                            "    Write-Host 'Command execution failed.'",
                            "    $host.SetShouldExit(1)",
                            "}"
                            ]
                        }
                   }
               ]
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
