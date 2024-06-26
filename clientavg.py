import torch
import torch.nn as nn
import numpy as np
import copy
import time
from flcore.clients.clientbase import Client
from utils.privacy import *
from flcore.optimizers.fedoptimizer import DFW, DINSGD
from flcore.optimizers.dfw import DFW1
from flcore.optimizers.dfw_din import DFWDin
import torch.distributed as dist
from flcore.optimizers.sls import Sls
from torch.optim.optimizer import required
import numpy as np
import torch

   

class clientAVG(Client):
    def __init__(self, args, id, train_samples, test_samples,enable_memory_management=True, **kwargs):
        super().__init__(args, id, train_samples, test_samples, **kwargs)
        nprocs = torch.cuda.device_count()
        self.round_counter = 0
        self.loss = nn.CrossEntropyLoss()
        self.optimizer = DFW1(self.model.parameters(), lr=self.learning_rate, weight_decay=self.weight_decay)
        #self.scheduler = torch.optim.lr_scheduler.StepLR(self.optimizer, step_size=1, gamma=0.98)  # Example scheduler
        self.mu = args.mu
        self.memory_management = enable_memory_management
        self.global_params = copy.deepcopy(list(self.model.parameters()))

        


    def train(self):
        #print("Client Training")
        trainloader = self.load_train_data()        #i got batches for 5 clients divided into a batch of 32
        start_time = time.time()
        self.model.train()
        
        # differential privacy
        if self.privacy:
            model_origin = copy.deepcopy(self.model)
            self.model, self.optimizer, trainloader, privacy_engine = \
                initialize_dp(self.model, self.optimizer, trainloader, self.dp_sigma)
                
        max_local_steps = self.local_epochs
        if self.train_slow:
            max_local_steps = np.random.randint(1, max_local_steps // 2)

        for step in range(max_local_steps):
            for i, (x, y) in enumerate(trainloader):
                if type(x) == type([]):
                    x[0] = x[0].to(self.device)
                else:
                    x = x.to(self.device)
                y = y.to(self.device)
                if self.train_slow:
                    time.sleep(0.1 * np.abs(np.random.rand()))                    
                self.optimizer.zero_grad()
                output = self.model(x)
                loss = self.loss(output, y)                    
                loss.backward()
                #torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1)  # Gradient clipping
                self.optimizer.step(lambda:float(loss))
                    
                
                    
            # if self.memory_management:  # Assuming a flag to control this behavior
            #      torch.cuda.empty_cache()
                 
            # self.scheduler.step()
            
        self.train_time_cost['num_rounds'] += 1
        self.train_time_cost['total_cost'] += time.time() - start_time

        if self.privacy:
            res, DELTA = get_dp_params(self.optimizer)
            print(f"Client {self.id}", f"(ε = {res[0]:.2f}, δ = {DELTA}) for α = {res[1]}")


# class clientAVG(Client):
#     def __init__(self, args, id, train_samples, test_samples, enable_memory_management=True, **kwargs):
#         super().__init__(args, id, train_samples, test_samples, **kwargs)
#         self.loss = nn.CrossEntropyLoss()
#         self.optimizer = DFW1(self.model.parameters(), lr=self.learning_rate, weight_decay=self.weight_decay)
#         self.memory_management = enable_memory_management
        
#     def compute_gradients(self):
#         trainloader = self.load_train_data()
#         self.model.train()
#         total_loss = 0
#         aggregated_gradients = {param: torch.zeros_like(param.data) for param in self.model.parameters()}
#         w_dict = {}

#         for i, (x, y) in enumerate(trainloader):
#             x = x.to(self.device)
#             y = y.to(self.device)
#             self.optimizer.zero_grad()
#             output = self.model(x)
#             loss = self.loss(output, y)
#             loss.backward()
#             loss_val = loss.item()
#             total_loss += loss_val * y.size(0)

#             for param in self.model.parameters():
#                 if param.grad is not None:
#                     aggregated_gradients[param] += param.grad.clone() / len(trainloader)  # Average gradients

#         # Setup w_dict for all parameters after the loop
#         for param in self.model.parameters():
#             if param.grad is not None:
#                 w_dict[param] = {'delta_t': aggregated_gradients[param], 'r_t': torch.zeros_like(param.grad)}

#         average_loss = total_loss / len(trainloader.dataset)
#         return list(aggregated_gradients.values()), average_loss, w_dict

#     def train(self):
#         gradients, loss, w_dict = self.compute_gradients()
#         return gradients, loss, w_dict
