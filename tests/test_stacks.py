import unittest
import aws_cdk as cdk
from aws_cdk.assertions import Template

from geo.geo_download import GeoDownload
from geo.geo_search_use1 import GeoSearchUSE1
from geo.geo_search_use2 import GeoSearchUSE2
from geo.geo_search_usw2 import GeoSearchUSW2
from geo.geo_stack import GeoStack


class StackTests(unittest.TestCase):

    def setUp(self):
        self.app = cdk.App()
        self.env = cdk.Environment(account="123456789012", region="us-east-2")
        self.download_stack = GeoDownload(
            self.app,
            "GeoDownload",
            env=self.env,
            synthesizer=cdk.DefaultStackSynthesizer(qualifier="lukach"),
        )
        self.search_use1 = GeoSearchUSE1(
            self.app,
            "GeoSearchUSE1",
            env=cdk.Environment(account="123456789012", region="us-east-1"),
            synthesizer=cdk.DefaultStackSynthesizer(qualifier="lukach"),
        )
        self.search_usw2 = GeoSearchUSW2(
            self.app,
            "GeoSearchUSW2",
            env=cdk.Environment(account="123456789012", region="us-west-2"),
            synthesizer=cdk.DefaultStackSynthesizer(qualifier="lukach"),
        )
        self.search_use2 = GeoSearchUSE2(
            self.app,
            "GeoSearchUSE2",
            env=cdk.Environment(account="123456789012", region="us-east-2"),
            synthesizer=cdk.DefaultStackSynthesizer(qualifier="lukach"),
        )
        self.geo_stack = GeoStack(
            self.app,
            "GeoStack",
            env=cdk.Environment(account="123456789012", region="us-east-1"),
            synthesizer=cdk.DefaultStackSynthesizer(qualifier="lukach"),
        )

        self.download_stack.add_stack_dependency(self.search_use1)
        self.download_stack.add_stack_dependency(self.search_usw2)
        self.download_stack.add_stack_dependency(self.search_use2)
        self.download_stack.add_stack_dependency(self.geo_stack)

    def test_download_stack_has_trigger_custom_resource(self):
        template = Template.from_stack(self.download_stack)
        # Custom::Trigger resource should be synthesized by TriggerFunction
        template.has_resource_properties(
            "Custom::Trigger",
            {
                "ExecuteOnHandlerChange": True,
                "InvocationType": "RequestResponse",
            },
        )

    def test_download_stack_dependencies(self):
        dependencies = self.download_stack.dependencies
        dep_stack_names = {dep.stack_name for dep in dependencies}
        self.assertIn("GeoSearchUSE1", dep_stack_names)
        self.assertIn("GeoSearchUSW2", dep_stack_names)
        self.assertIn("GeoSearchUSE2", dep_stack_names)
        self.assertIn("GeoStack", dep_stack_names)


if __name__ == "__main__":
    unittest.main()
