from torch import nn
from reed_wsd.util import cudaify

def inv_abstain_prob(output_tensor):
    return (1. - output_tensor[:,-1])
    
def max_nonabstain_prob(output_tensor):
    return output_tensor[:,:-1].max(dim=1).values

def max_prob(output_tensor):
    return output_tensor[:,:-1].max(dim=1).values

class BasicFFN(nn.Module): 
 
    def __init__(self, 
                 input_size = 784, 
                 hidden_sizes = [128, 64], 
                 output_size = 10,
                 confidence_extractor = max_prob):
        super().__init__()
        self.confidence_extractor = confidence_extractor
        self.dropout = nn.Dropout(p=0.2)        
        self.linear1 = cudaify(nn.Linear(input_size, hidden_sizes[0]))
        self.linear2 = cudaify(nn.Linear(hidden_sizes[0], hidden_sizes[1]))
        self.final = cudaify(nn.Linear(hidden_sizes[1], output_size))
        self.softmax = cudaify(nn.Softmax(dim=1))
        self.relu1 = nn.ReLU()
        self.relu2 = nn.ReLU()

    def initial_layers(self, input_vec):
        nextout = cudaify(input_vec)
        nextout = self.linear1(nextout)
        nextout = self.dropout(nextout)
        nextout = self.relu1(nextout)
        nextout = self.linear2(nextout)
        nextout = self.relu2(nextout)
        nextout = self.dropout(nextout)
        return nextout
    
    def final_layers(self, input_vec):
        nextout = self.final(input_vec)
        nextout = nextout.clamp(min=-25, max=25)
        nextout = self.softmax(nextout)
        return nextout, self.confidence_extractor(nextout)

    def forward(self, input_vec):
        nextout = self.initial_layers(input_vec)
        result, confidence = self.final_layers(nextout)
        return result, confidence
    
class AbstainingFFN(BasicFFN): 
 
    def __init__(self, 
                 input_size = 784, 
                 hidden_sizes = [128, 64], 
                 output_size = 10,
                 confidence_extractor = 'inv_abs'):
        assert(confidence_extractor in ['inv_abs', 'max_non_abs'])
        super().__init__(input_size, hidden_sizes, output_size, confidence_extractor)
        if confidence_extractor == 'inv_abs':
            self.confidence_extractor = inv_abstain_prob
        if confidence_extractor == 'max_non_abs':
            self.confidence_extractor = max_nonabstain_prob
        self.final = cudaify(nn.Linear(hidden_sizes[1], output_size + 1))


class ConfidentFFN(BasicFFN): 
 
    def __init__(self, 
                 input_size = 784, 
                 hidden_sizes = [128, 64], 
                 output_size = 10):
        super().__init__(input_size, hidden_sizes, output_size)
        self.confidence_layer = cudaify(nn.Linear(hidden_sizes[1], 1))

    def final_layers(self, input_vec):
        nextout = self.final(input_vec)
        nextout = self.softmax(nextout)
        return nextout, self.confidence_layer(input_vec)
    
    
