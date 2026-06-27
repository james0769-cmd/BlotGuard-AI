"""Inference classifier extracted from the detector training workspace."""

import torch.nn as nn


class FCN_Classifier(nn.Module):
    def __init__(self, num_classes):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(256, 128, 3, padding=1, bias=False),
            nn.BatchNorm2d(128),
            nn.LeakyReLU(0.1),
            nn.Conv2d(128, 64, 3, padding=1, bias=False),
            nn.BatchNorm2d(64),
            nn.LeakyReLU(0.1),
            nn.Conv2d(64, 32, 3, padding=1),
        )
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Linear(32, num_classes)
        self._init_weights()

    def _init_weights(self):
        for module in self.modules():
            if isinstance(module, nn.Conv2d):
                nn.init.kaiming_normal_(
                    module.weight,
                    mode="fan_out",
                    nonlinearity="leaky_relu",
                    a=0.1,
                )
            elif isinstance(module, nn.Linear):
                nn.init.uniform_(module.weight, -0.1, 0.1)
                nn.init.constant_(module.bias, 0.0)

    def forward(self, inputs):
        features = self.features(inputs)
        pooled = self.pool(features).flatten(1)
        return self.fc(pooled)
