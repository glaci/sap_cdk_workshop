from aws_cdk import core
import aws_cdk.aws_ec2 as _ec2
import aws_cdk.aws_iam as _iam
import aws_cdk.aws_lambda as _lambda
import aws_cdk.aws_cloudformation as _cf
import aws_cdk.aws_secretsmanager as _sm

class PrepVpcStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        _domain_user = self.node.try_get_context("source")['domain_user']

        # Create a Secret Manager Secret to set default Password
        _sm.Secret(
            self, "SecretForADConnector",
            generate_secret_string = _sm.SecretStringGenerator(
                generate_string_key = "password",
                secret_string_template = "{\"username\": ""\""+_domain_user+"\"""}"
            )
        )


        # Create IAM Policy for LambdaFunction: Accept RAM Invitation
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
                    "ram:AcceptResourceShareInvitation",
                    "ram:GetResourceShareInvitations",
                    "ram:DisassociateResourceShare",
                    "ram:DisassociateResourceSharePermission"
                    ],
                    resources = [ "*" ]
                )
            ]
        )

        # Creare a IAM Role for Lambda
        lambdarole = _iam.Role(
            self,"LambdaRoleToAcceptRAMInvitation",
            assumed_by = _iam.ServicePrincipal('lambda.amazonaws.com'),
            inline_policies = { "LambdaAcceptRAM": lambdapolicy },
            role_name = "Lambda_Accept_RAM_Invitation"
        )

        # Create a Lambda function to Register Directory Service on WorkSpaces
        ramlambda = _lambda.Function(
            self, "LambdaStackForRAM",
            runtime = _lambda.Runtime.PYTHON_3_7,
            handler = "ramreceiver.handler",
            role = lambdarole,
            code=_lambda.Code.asset('lambda/ram'),
            environment={
                "ACCOUNT_ID": self.account
            },
            timeout = core.Duration.seconds(120),
            function_name = "accept_ram_invitation"
        )
        # Create a customResource to trigger Lambda function after Lambda function is created
        _cf.CfnCustomResource(
            self, "InvokeLambdaFunction",
            service_token = ramlambda.function_arn
        )
