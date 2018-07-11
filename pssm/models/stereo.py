# -*- coding: utf-8 -*-
# @Author: lidong
# @Date:   2018-03-20 18:01:52
# @Last Modified by:   yulidong
# @Last Modified time: 2018-07-11 11:11:39

import torch
import numpy as np
import torch.nn as nn
import math
from math import ceil
from torch.autograd import Variable
from torch.nn.function import cosine_similarity as cosine_s
from rsden import caffe_pb2
from rsden.models.utils import *
rsn_specs = {
    'scene': 
    {
         'n_classes': 9,
         'input_size': (540, 960),
         'block_config': [3, 4, 23, 3],
    },

}


def convbn(in_planes, out_planes, kernel_size, stride, pad, dilation):

    return nn.Sequential(nn.Conv2d(in_planes, out_planes, kernel_size=kernel_size, stride=stride, padding=dilation if dilation > 1 else pad, dilation = dilation, bias=False),
                         nn.BatchNorm2d(out_planes))
class BasicBlock(nn.Module):
    expansion = 1
    def __init__(self, inplanes, planes, stride, downsample, pad, dilation):
        super(BasicBlock, self).__init__()

        self.conv1 = nn.Sequential(convbn(inplanes, planes, 3, stride, pad, dilation),
                                   nn.ReLU(inplace=True))

        self.conv2 = convbn(planes, planes, 3, 1, pad, dilation)

        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        out = self.conv1(x)
        out = self.conv2(out)

        if self.downsample is not None:
            x = self.downsample(x)

        out += x

        return out
class feature_extraction(nn.Module):
    def __init__(self):
        super(feature_extraction, self).__init__()
        self.inplanes = 32
        self.firstconv = nn.Sequential(convbn(3, 32, 3, 1, 1, 1),
                                       nn.ReLU(inplace=True),
                                       convbn(32, 32, 3, 1, 1, 1),
                                       nn.ReLU(inplace=True),
                                       convbn(32, 32, 3, 1, 1, 1),
                                       nn.ReLU(inplace=True))

        self.layer1 = self._make_layer(BasicBlock, 32, 3, 1,1,1)
        self.layer2 = self._make_layer(BasicBlock, 64, 16, 1,1,1) 
        self.layer3 = self._make_layer(BasicBlock, 128, 3, 1,1,1)
        self.layer4 = self._make_layer(BasicBlock, 128, 3, 1,1,2)

        self.branch1 = nn.Sequential(nn.AvgPool2d((64, 64), stride=(64,64)),
                                     convbn(128, 32, 1, 1, 0, 1),
                                     nn.ReLU(inplace=True))

        self.branch2 = nn.Sequential(nn.AvgPool2d((32, 32), stride=(32,32)),
                                     convbn(128, 32, 1, 1, 0, 1),
                                     nn.ReLU(inplace=True))

        self.branch3 = nn.Sequential(nn.AvgPool2d((16, 16), stride=(16,16)),
                                     convbn(128, 32, 1, 1, 0, 1),
                                     nn.ReLU(inplace=True))

        self.branch4 = nn.Sequential(nn.AvgPool2d((8, 8), stride=(8,8)),
                                     convbn(128, 32, 1, 1, 0, 1),
                                     nn.ReLU(inplace=True))

        self.lastconv = nn.Sequential(convbn(320, 128, 3, 1, 1, 1),
                                      nn.ReLU(inplace=True),
                                      nn.Conv2d(128, 32, kernel_size=1, padding=0, stride = 1, bias=False))

    def _make_layer(self, block, planes, blocks, stride, pad, dilation):
        downsample = None
        if stride != 1 or self.inplanes != planes * block.expansion:
           downsample = nn.Sequential(
                nn.Conv2d(self.inplanes, planes * block.expansion,
                          kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(planes * block.expansion),)

        layers = []
        layers.append(block(self.inplanes, planes, stride, downsample, pad, dilation))
        self.inplanes = planes * block.expansion
        for i in range(1, blocks):
            layers.append(block(self.inplanes, planes,1,None,pad,dilation))

        return nn.Sequential(*layers)

    def forward(self, x):
        output      = self.firstconv(x)
        output      = self.layer1(output)
        output_raw  = self.layer2(output)
        output      = self.layer3(output_raw)
        output_skip = self.layer4(output)


        output_branch1 = self.branch1(output_skip)
        output_branch1 = F.upsample(output_branch1, (output_skip.size()[2],output_skip.size()[3]),mode='bilinear')

        output_branch2 = self.branch2(output_skip)
        output_branch2 = F.upsample(output_branch2, (output_skip.size()[2],output_skip.size()[3]),mode='bilinear')

        output_branch3 = self.branch3(output_skip)
        output_branch3 = F.upsample(output_branch3, (output_skip.size()[2],output_skip.size()[3]),mode='bilinear')

        output_branch4 = self.branch4(output_skip)
        output_branch4 = F.upsample(output_branch4, (output_skip.size()[2],output_skip.size()[3]),mode='bilinear')

        output_feature = torch.cat((output_raw, output_skip, output_branch4, output_branch3, output_branch2, output_branch1), 1)
        output_feature = self.lastconv(output_feature)

        return output_feature

class feature_extraction2(nn.Module):
    def __init__(self):
        super(feature_extraction2, self).__init__()
        self.inplanes = 32
        self.firstconv = nn.Sequential(convbn(3, 32, 3, 1, 1, 1),
                                       nn.ReLU(inplace=True),
                                       convbn(32, 32, 3, 1, 1, 1),
                                       nn.ReLU(inplace=True),
                                       convbn(32, 32, 3, 1, 1, 1),
                                       nn.ReLU(inplace=True))

        self.layer1 = self._make_layer(BasicBlock, 32, 3, 1,1,1)

    def _make_layer(self, block, planes, blocks, stride, pad, dilation):
        downsample = None
        if stride != 1 or self.inplanes != planes * block.expansion:
           downsample = nn.Sequential(
                nn.Conv2d(self.inplanes, planes * block.expansion,
                          kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(planes * block.expansion),)

        layers = []
        layers.append(block(self.inplanes, planes, stride, downsample, pad, dilation))
        self.inplanes = planes * block.expansion
        for i in range(1, blocks):
            layers.append(block(self.inplanes, planes,1,None,pad,dilation))

        return nn.Sequential(*layers)

    def forward(self, x):
        output      = self.firstconv(x)
        output      = self.layer1(output)


        return output

class aggregation(nn.Module):
    def __init__(self):
        super(aggregation, self).__init__()
        self.s_conv = nn.Sequential(convbn(33, 32, 3, 1, 1, 1),
                                       nn.ReLU(inplace=True),
                                       convbn(32, 32, 3, 1, 1, 1),
                                       nn.ReLU(inplace=True),
                                       convbn(32, 1, 3, 1, 1, 1)
                                       )
        self.l_conv = nn.Sequential(convbn(33, 32, 3, 1, 1, 1),
                                       nn.ReLU(inplace=True),
                                       convbn(32, 32, 3, 1, 1, 1),
                                       nn.ReLU(inplace=True),
                                       convbn(32, 1, 3, 1, 1, 1))



    def forward(self, s,l,x):
        s_var      = self.s_conv(torch.cat([s,x]))+x
        l_var      = self.l_conv(torch.cat([l,x]))+x
        return s_var,l_var

class ss_argmin(nn.Module):
    def __init__(self):
        super(ss_argmin, self).__init__()
        self.softmax = nn.Softmax(dim=-1)



    def forward(self,x,min,max):
        x=self.softmax(x)
        index=torch.ones_like(x)*torch.range(min,max+1)
        return torch.sum(x*index,dim=-1)

class EDSNet(nn.Module):


    def __init__(self, 
                 P,
                 pre,
                 n_classes=9, 
                 block_config=[3, 4, 6, 3], 
                 input_size= (480, 640), 
                 version='scene'):

        super(EDSNet, self).__init__()
        self.feature_extraction=feature_extraction()
        self.feature_extraction2=feature_extraction2()
        self.aggregation=aggregation()    
        self.ss_argmin=ss_argmin()
        self.P=P
        #0 l to r,1 min,2 max
        self.pre=pre                                                                                
    def forward(self, l,r):
        l_mask=P[:,:,3]-P[:,:,0]
        s_mask=P[:,:,0]
        l_lf=self.feature_extraction(l)
        l_sf=self.feature_extraction2(l)
        r_lf=self.feature_extraction(r)
        r_sf=self.feature_extraction2(r)
        #reshape the mask to batch and channel
        feature=l_lf(l)*l_mask+self.l_sf(l)*s_mask
        disparity=torch.zeros([540,960])
        one=torch.ones(1)
        zero=torch.zeros(1)
        #promotion
        #we can segment with bounding box and divide the whole image into many parts
        #each single bounding box will be managed through network not the whole image
        for i in range(torch.max(self.P[:,:,1]).type(torch.int32)+1):
            min_d=torch.where(P[:,:,1]==i,self.pre[:,:,1],-1)
            max_d=torch.where(P[:,:,1]==i,self.pre[:,:,2],-1)
            object_mask=torch.where(P[:,:,1]==i,one,zero)
            s_mask_o=object_mask*s_mask
            l_mask_o=object_mask*l_mask
            s_l_o=feature*s_mask_o
            l_l_o=feature*l_mask_o
            s_r_o=r_sf*object_mask
            l_r_o=r_lf*object_mask
            cost_s=[]
            cost_l=[]
            for i in range(min_d,max_d+d):
                s_r_o_t=torch.cat(s_r_o[:,i:,:],s_r_o[:,i:,:])
                cost_s.append(torch.where(s_mask_o==1,cosine_s(s_l_o,s_r_o_t),zero))
            cost_s=torch.stack(cost_s,-1)
            for i in range(min_d,max_d+d):
                l_r_o_t=torch.cat(l_r_o[:,i:,:],l_r_o[:,i:,:])
                cost_l.append(torch.where(l_mask_o==1,cosine_s(l_l_o,l_r_o_t),zero))
            cost_l=torch.stack(cost_l,-1)
            cost_volume=cost_s+cost_l
        #aggregation
        for i in range(torch.max(self.P[:,:,1]).type(torch.int32)+1):
            a_volume=torch.zeros_like(cost_volume[i])
            object_r=torch.where(P[:,:,1]==i,self.P[:,:,2],zero)
            max_r=torch.max(object_r)
            object_r=torch.where(P[:,:,1]==i,self.P[:,:,2],max_r+1)
            min_r=torch.min(object_r)
            for j in range(min_r,max_r+1):
                plane_mask=torch.where(object_r==j,one,zero)
                plane=cost_volume[i]*plane_mask
                for m in range(planes.shape[-1])
                    s_var,l_var=self.aggregation(l_sf,l_lf,plane[...,m])
                    plane[...,m]=s_var*s_mask+l_var*l_mask
                a_volume+=plane
            cost_volume[i]=a_volume
        for i in range(torch.max(self.P[:,:,1]).type(torch.int32)+1):
            min_d=torch.where(P[:,:,1]==i,self.pre[:,:,1],-1)
            max_d=torch.where(P[:,:,1]==i,self.pre[:,:,2],-1)
            disparity+=ss_argmin(cost_volume[i],min_d,max_d)
        

        return x


