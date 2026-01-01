import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from torchinfo import summary


class ConvLayer(nn.Module):

    def __init__(self,
                 in_channels,
                 out_channels,
                 kernel_size,
                 stride,
                 padding=0):
        super().__init__()

        conv = nn.Conv2d(in_channels,
                         out_channels,
                         kernel_size,
                         stride=stride,
                         padding=padding)
        batch_norm = nn.BatchNorm2d(out_channels)
        relu = nn.LeakyReLU(0.1)

        self.layers = nn.Sequential(conv, batch_norm, relu)

    def forward(self, x):
        x = self.layers(x)
        return x


class ResidualBlock(nn.Module):

    def __init__(self, in_channels):
        super(ResidualBlock, self).__init__()

        conv_block1 = ConvLayer(in_channels, in_channels // 2, 1, 1, padding=0)
        conv_block2 = ConvLayer(in_channels // 2, in_channels, 3, 1, padding=1)
        self.layers = nn.Sequential(conv_block1, conv_block2)

    def forward(self, x):
        return x + self.layers(x)


class ConvLayerStack(nn.Module):

    def __init__(self, in_channels, mid_channels, out_channels):
        super(ConvLayerStack, self).__init__()
        layers = []
        layers.append(ConvLayer(in_channels, out_channels, 1, 1, padding=0))
        layers.append(ConvLayer(out_channels, mid_channels, 3, 1, padding=1))
        layers.append(ConvLayer(mid_channels, out_channels, 1, 1, padding=0))
        layers.append(ConvLayer(out_channels, mid_channels, 3, 1, padding=1))
        layers.append(ConvLayer(mid_channels, out_channels, 1, 1, padding=0))

        self.layer_seq = nn.Sequential(*layers)

    def forward(self, x):
        return self.layer_seq(x)


class OutputLayer(nn.Module):

    def __init__(self, in_channels, num_anchors=3, num_classes=2):
        super(OutputLayer, self).__init__()
        self.final_block = ConvLayer(in_channels,
                                     in_channels * 2,
                                     3,
                                     1,
                                     padding=1)
        self.bounding_box_conv = nn.Conv2d(in_channels * 2,
                                           num_anchors * (num_classes + 5), 1)

    def forward(self, x):
        return self.bounding_box_conv(self.final_block(x))


class SaveLayer(nn.Module):

    def __init__(self):
        super(SaveLayer, self).__init__()

    def forward(self, x):
        return x


class YOLO(nn.Module):

    def __init__(self, num_anchors=3, num_classes=2):
        super(YOLO, self).__init__()
        layers = []

        layers.append(ConvLayer(3, 32, 3, 1, padding=1))
        layers.append(ConvLayer(32, 64, 3, 2, padding=1))
        layers.append(ResidualBlock(64))
        layers.append(ConvLayer(64, 128, 3, 2, padding=1))
        for i in range(2):
            layers.append(ResidualBlock(128))
        layers.append(ConvLayer(128, 256, 3, 2, padding=1))
        for i in range(8):
            layers.append(ResidualBlock(256))
        layers.append(SaveLayer())
        layers.append(ConvLayer(256, 512, 3, 2, padding=1))
        for i in range(8):
            layers.append(ResidualBlock(512))
        layers.append(SaveLayer())
        layers.append(ConvLayer(512, 1024, 3, 2, padding=1))
        for i in range(4):
            layers.append(ResidualBlock(1024))

        #First Predicition Layer (Big Objects)
        layers.append(ConvLayerStack(1024, 1024, 512))
        layers.append(
            OutputLayer(512, num_anchors=num_anchors, num_classes=num_classes))

        #Connectors
        layers.append(ConvLayer(512, 256, 1, 1, padding=0))
        layers.append(nn.Upsample(scale_factor=2))

        #Second Predicition Layer (Medium Objects)
        layers.append(ConvLayerStack(512 + 256, 512, 256))
        layers.append(
            OutputLayer(256, num_anchors=num_anchors, num_classes=num_classes))

        #Connectors
        layers.append(ConvLayer(256, 128, 1, 1, padding=0))
        layers.append(nn.Upsample(scale_factor=2))

        #Third Predicition Layer (Small Objects)
        layers.append(ConvLayerStack(256 + 128, 256, 128))
        layers.append(
            OutputLayer(128, num_anchors=num_anchors, num_classes=num_classes))

        self.module_layers = nn.ModuleList(layers)

    def forward(self, x):
        outputs = []
        saved_layers = []
        for l in self.module_layers:
            if isinstance(l, OutputLayer):
                outputs.append(l(x))
                continue

            x = l(x)

            #Save layers or pop and concat layers as needed
            if isinstance(l, SaveLayer):
                saved_layers.append(x)
            elif isinstance(l, nn.Upsample):
                x = torch.cat([x, saved_layers[-1]], dim=1)
                saved_layers.pop()

        return outputs


if __name__ == "__main__":
    model = YOLO()
    # Sample input tensor with batch size of 1 and image size 416x416
    x = torch.randn(1, 3, 416, 416)
    output = model(x)
    print(output[0].shape)
    print(output[1].shape)
    print(output[2].shape)
    summary(model, input_size=(1, 3, 416, 416))
