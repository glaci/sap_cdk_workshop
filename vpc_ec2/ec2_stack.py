from aws_cdk import core
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_ssm as _ssm 
import aws_cdk.aws_iam as _iam


class CdkVpcEc2Stack(core.Stack):
    
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # parameters should be extracted
        vpc_id = "vpc-ba535ddd"  # Import an Exist VPC
        ec2_type = "t2.medium"
        key_name = "keyWorkspace" #TODO
        directoryId = "d-956712d519"
        directoryName = "test.lab"
        dnsIpAddresses1 = "10.0.3.193"
        dnsIpAddresses2 = "10.0.4.102"

        linux_ami = ec2.GenericLinuxImage({
            "cn-northwest-1": "AMI-ID-IN-cn-northwest-1-REGION",  # Refer to an Exist AMI
            "eu-west-1": "AMI-ID-IN-eu-west-1-REGION"
        })
        windows_ami = ec2.WindowsImage(ec2.WindowsVersion.WINDOWS_SERVER_2019_ENGLISH_FULL_BASE)

        # with open("./user_data/user_data.sh") as f:
        #     user_data = f.read()

        # The code that defines your stack goes here
        vpc = ec2.Vpc.from_lookup(self, "VPC", vpc_id=vpc_id)

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


        host = ec2.Instance(self, "myEC2",
                            instance_type=ec2.InstanceType(
                                instance_type_identifier=ec2_type),
                            instance_name="myAdHost",
                            machine_image=windows_ami,
                            vpc=vpc,
                            role=ssmrole,
                            key_name=key_name,
                            vpc_subnets=ec2.SubnetSelection(
                                subnet_type=ec2.SubnetType.PUBLIC)
                            # user_data=ec2.UserData.custom(user_data)
                            )

        # # ec2.Instance has no property of BlockDeviceMappings, add via lower layer cdk api:
        # host.instance.add_property_override("BlockDeviceMappings", [{
        #     "DeviceName": "/dev/xvda",
        #     "Ebs": {
        #         "VolumeSize": "10",
        #         "VolumeType": "io1",
        #         "Iops": "150",
        #         "DeleteOnTermination": "true"
        #     }
        # }, {
        #     "DeviceName": "/dev/sdb",
        #     "Ebs": {"VolumeSize": "30"}
        # }
        # ]) 
        # by default VolumeType is gp2, VolumeSize 8GB

        host.connections.allow_from_any_ipv4(ec2.Port.tcp(3389), "Allow RDP from internet")

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