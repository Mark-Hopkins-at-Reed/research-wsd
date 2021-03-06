"""
Code adapted from:
https://towardsdatascience.com/handwritten-digit-mnist-pytorch-977b5338e627

"""

import torch
import torch.nn.functional as F
from reed_wsd.util import cudaify, ABS
from reed_wsd.train import Trainer, Decoder
from tqdm import tqdm
import numpy as np

class MnistSimpleDecoder(Decoder):
    def __call__(self, net, data, trust_model):
        net.eval()
        for images, labels in tqdm(data, total=len(data)):
            with torch.no_grad():
                output, conf = net(cudaify(images))
                ps = F.softmax(output.clamp(min=-25, max=25), dim=1)
            preds = ps.argmax(dim=1)
            if trust_model is not None:
                trust_score = trust_model.get_score(images.cpu().numpy(), 
                                                    preds.cpu().numpy())
                trust_score = trust_score.astype(np.float64)
                trust_score = torch.from_numpy(trust_score)
            else:
                trust_score = [None] * labels.shape[0]
            for element in zip(preds, labels, conf, trust_score):
                p, g, c, t = element
                if t is not None:
                    yield {'pred': p.item(), 'gold': g.item(), 'confidence': t.item(), 'abstained': False}
                else:
                    yield {'pred': p.item(), 'gold': g.item(), 'confidence': c.item(), 'abstained': False}
                    

class MnistAbstainingDecoder(Decoder):
    
    def __call__(self, net, data, trust_model=None):
	# note that trust_model here is a dummy argument
	# a correct usage of the function should not pass values other than None to trust_model
        net.eval()
        for images, labels in tqdm(data, total=len(data)):
            output, conf = net(cudaify(images))
            ps = F.softmax(output.clamp(min=-25, max=25), dim=1)
            abs_i = output.shape[1] - 1
            max_weight_class = ps.argmax(dim=-1)
            is_abs = (max_weight_class == abs_i)
            preds = ps[:, :-1].argmax(dim=-1)
            for e in zip(preds, labels, conf, is_abs):
                pred, gold, c, abstained = e
                result = {'pred': pred.item(), 'gold': gold.item(), 'confidence': c.item(), 'abstained': abstained.item()} 
                yield result

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
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1)
            self.optimizer.step()                   
            running_loss += loss.item()
            denom += 1
        return running_loss / denom


