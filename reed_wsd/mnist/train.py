"""
Code adapted from:
https://towardsdatascience.com/handwritten-digit-mnist-pytorch-977b5338e627

"""

import torch
import copy
from time import time
from torch import optim
from reed_wsd.util import cudaify
from collections import defaultdict
from reed_wsd.plot import PYCurve, plot_curves
from reed_wsd.mnist.networks import AbstainingFFN, ConfidentFFN
from reed_wsd.train import validate_and_analyze, Trainer
from reed_wsd.train import Decoder
from tqdm import tqdm

class MnistDecoder(Decoder):
    
    def __call__(self, net, data):
        net.eval()
        for images, labels in data:
            for i in range(len(labels)):
                img = images[i].view(1, 784)
                # Turn off gradients to speed up this part
                with torch.no_grad():
                    ps, conf = net(cudaify(img))                
                ps = ps.squeeze(dim=0)
                c = conf.squeeze(dim=0).item()
                pred = ps.argmax(dim=0).item()
                gold = labels[i].item()
                yield {'pred': pred, 'gold': gold, 'confidence': c}


def decoder(net, data):
    net.eval()
    for images, labels in data:
        for i in range(len(labels)):
            img = images[i].view(1, 784)
            # Turn off gradients to speed up this part
            with torch.no_grad():
                ps, conf = net(cudaify(img))                
            ps = ps.squeeze(dim=0)
            c = conf.squeeze(dim=0).item()
            pred = ps.argmax(dim=0).item()
            gold = labels[i].item()
            yield {'pred': pred, 'gold': gold, 'confidence': c}
    


class PairwiseTrainer(Trainer):
         
    def _epoch_step(self, model):
        running_loss = 0.
        denom = 0
        for img_x, img_y, lbl_x, lbl_y in tqdm(self.train_loader, total=len(self.train_loader)):
            self.optimizer.zero_grad()                           
            output_x, conf_x = model(cudaify(img_x))
            output_y, conf_y = model(cudaify(img_y))
            loss = self.criterion(output_x, output_y, cudaify(lbl_x),
                                  cudaify(lbl_y), conf_x, conf_y)
            loss.backward()
            self.optimizer.step()                                                                                                 
            running_loss += loss.item()
            denom += 1
        return running_loss / denom
     
class SingleTrainer(Trainer):

    def _epoch_step(self, model):
        running_loss = 0.
        denom = 0
        for images, labels in tqdm(self.train_loader, total=len(self.train_loader)):
            self.optimizer.zero_grad()                       
            output, conf = model(cudaify(images))
            loss = self.criterion(output, conf, cudaify(labels))
            loss.backward()
            self.optimizer.step()                   
            running_loss += loss.item()
            denom += 1
        return running_loss / denom


def plot_saved_models(val_loader, 
                      filenames = ['saved/pair_baseline.pt', 
                                   'saved/pair_neg_abs.pt']):
    curves = []
    for filename in filenames:
        net_base = AbstainingFFN()
        net_base.load_state_dict(torch.load(filename, map_location=torch.device('cpu')))
        decoded = list(decoder(net_base, val_loader))
        pyc_base = PYCurve.from_data(decoded)
        curves.append((pyc_base, filename))
    plot_curves(*curves)
