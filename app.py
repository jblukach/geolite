#!/usr/bin/env python3
import os

import aws_cdk as cdk

from geolite.geolite_download import GeoliteDownload
from geolite.geolite_searchuse1 import GeoliteSearchUSE1
from geolite.geolite_searchusw2 import GeoliteSearchUSW2

app = cdk.App()

GeoliteDownload(
    app, 'GeoliteDownload',
    env = cdk.Environment(
        account = os.getenv('CDK_DEFAULT_ACCOUNT'),
        region = 'us-east-2'
    ),
    synthesizer = cdk.DefaultStackSynthesizer(
        qualifier = 'lukach'
    )
)

use1 = GeoliteSearchUSE1(
    app, 'GeoliteSearchUSE1',
    env = cdk.Environment(
        account = os.getenv('CDK_DEFAULT_ACCOUNT'),
        region = 'us-east-1'
    ),
    synthesizer = cdk.DefaultStackSynthesizer(
        qualifier = 'lukach'
    )
)

usw2 = GeoliteSearchUSW2(
    app, 'GeoliteSearchUSW2',
    env = cdk.Environment(
        account = os.getenv('CDK_DEFAULT_ACCOUNT'),
        region = 'us-west-2'
    ),
    synthesizer = cdk.DefaultStackSynthesizer(
        qualifier = 'lukach'
    )
)

cdk.Tags.of(app).add('Alias','geolite')
cdk.Tags.of(app).add('GitHub','https://github.com/jblukach/geolite')
cdk.Tags.of(app).add('Org','lukach.io')

app.synth()