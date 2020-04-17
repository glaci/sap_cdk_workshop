from aws_cdk import core
import aws_cdk.aws_ec2 as _ec2


class AwsVpcStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Import vars from cdk.json context
        _vpc_cidr = self.node.try_get_context("vpc_cidr")
        _subnet1_cidr = self.node.try_get_context("subnet1_cidr")
        _subnet2_cidr = self.node.try_get_context("subnet2_cidr")
        _transitgw_id = self.node.try_get_context("transitgw_id")
        _ad_cidr = self.node.try_get_context("ad_cidr")

        # Create detaul DHCP Option
        vpc_dhcp = _ec2.CfnDHCPOptions(
            self, "DefaultDHCPOption",
            domain_name = "{}.compute.internal".format(self.region),
        )

        # Create new VPC
        vpc_workspaces = _ec2.CfnVPC(
            self, "VPCWorkSpaces",
            cidr_block = _vpc_cidr
        )

        # Attach DHCP to this VPC
        _ec2.CfnVPCDHCPOptionsAssociation(
            self, "DHCPOptionAttachment",
            dhcp_options_id = vpc_dhcp.ref,
            vpc_id = vpc_workspaces.ref
        )

        # Create Public Subnet 1
        subnet1 = _ec2.CfnSubnet(
            self, "PublicSubnet1",
            cidr_block = _subnet1_cidr,
            vpc_id = vpc_workspaces.ref,
            availability_zone = self.availability_zones[0]
        )

        # Create Public Subnet 2
        subnet2 = _ec2.CfnSubnet(
            self, "PublicSubnet2",
            cidr_block = _subnet2_cidr,
            vpc_id = vpc_workspaces.ref,
            availability_zone = self.availability_zones[1]
        )

        # Create Public Subnet RouteTable
        public_subnet_route = _ec2.CfnRouteTable(
            self, "PublicRouteTable",
            vpc_id = vpc_workspaces.ref
        )

        # Create Transit GW Attachment to this VPC
        transitGWattachment = _ec2.CfnTransitGatewayAttachment(
            self, "CreateTransitGWAttachment",
            transit_gateway_id = _transitgw_id,
            vpc_id = vpc_workspaces.ref,
            subnet_ids = [ subnet1.ref, subnet2.ref ]
        )

        # Attach RouteTable to Public Subnet1
        _ec2.CfnSubnetRouteTableAssociation(
            self, "PublicRouteTableAssociationPublic1",
            route_table_id = public_subnet_route.ref,
            subnet_id = subnet1.ref
        )

        # Attach RouteTable to Public Subnet2
        _ec2.CfnSubnetRouteTableAssociation(
            self, "PublicRouteTableAssociationPublic2",
            route_table_id = public_subnet_route.ref,
            subnet_id = subnet2.ref
        )

        # Add route from transitGW to AD Env
        public_route = _ec2.CfnRoute(
            self, "CreateRouteFromTransitGWtoAD",
            route_table_id = public_subnet_route.ref,
            destination_cidr_block = _ad_cidr,
            transit_gateway_id = _transitgw_id
        )

        public_route.add_depends_on(transitGWattachment)
