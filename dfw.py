import torch
from torch.optim import Optimizer
import torch
import torch.optim as optim
from torch.optim.optimizer import required
from collections import defaultdict


class DFW1(optim.Optimizer):
    def __init__(self, params, lr=required, momentum=0.9, weight_decay=0, eps=1e-5):
        if lr is not required and lr <= 0.0:
            raise ValueError("Invalid eta: {}".format(lr))
        if momentum < 0.0:
            raise ValueError("Invalid momentum value: {}".format(momentum))
        if weight_decay < 0.0:
            raise ValueError("Invalid weight_decay value: {}".format(weight_decay))

        defaults = dict(lr=lr, momentum=momentum, weight_decay=weight_decay)
        super(DFW1, self).__init__(params, defaults)
        self.eps = eps

        for group in self.param_groups:
            if group['momentum']:
                for p in group['params']:
                    self.state[p]['momentum_buffer'] = torch.zeros_like(p.data, requires_grad=False)

    @torch.autograd.no_grad()
    def step(self, closure):
        loss = float(closure())

        w_dict = defaultdict(dict)
        for group in self.param_groups:
            wd = group['weight_decay']
            for param in group['params']:
                if param.grad is None:
                    continue
                w_dict[param]['delta_t'] = param.grad.data
                w_dict[param]['r_t'] = wd * param.data

        self._line_search(loss, w_dict)

        for group in self.param_groups:
            lr = group['lr']
            mu = group['momentum']
            for param in group['params']:
                if param.grad is None:
                    continue
                state = self.state[param]
                delta_t, r_t = w_dict[param]['delta_t'], w_dict[param]['r_t']
                param.data -= lr * (r_t + self.gamma * delta_t)

                if mu:
                    z_t = state['momentum_buffer']
                    z_t *= mu
                    z_t -= lr * self.gamma * (delta_t + r_t)
                    param.data += mu * z_t

    @torch.autograd.no_grad()
    def _line_search(self, loss, w_dict):
        """
        Computes the line search in closed form.
        """
        num = loss
        denom = 0

        for group in self.param_groups:
            lr = group['lr']
            for param in group['params']:
                if param.grad is None:
                    continue
                delta_t, r_t = w_dict[param]['delta_t'], w_dict[param]['r_t']
                num -= lr * torch.sum(delta_t * r_t)
                denom += lr * delta_t.norm() ** 2

        self.gamma = float((num / (denom + self.eps)).clamp(min=0, max=1))


# import torch
# from torch.optim.optimizer import Optimizer, required

# class DFW1(Optimizer):
#     def __init__(self, params, lr=required, momentum=0.9, weight_decay=0, eps=1e-6):
#         if lr is not required and lr <= 0.0:
#             raise ValueError("Invalid learning rate: {}".format(lr))
#         if momentum < 0.0:
#             raise ValueError("Invalid momentum value: {}".format(momentum))
#         if weight_decay < 0.0:
#             raise ValueError("Invalid weight_decay value: {}".format(weight_decay))
        
#         defaults = dict(lr=lr, momentum=momentum, weight_decay=weight_decay, eps=eps)
#         super(DFW1, self).__init__(params, defaults)
#         self.gamma = 0.1  # Initialize gamma as a starting value

#     def step(self, aggregated_gradients, loss, w_dict):
#         """Perform a single optimization step."""
#         self._line_search(loss, w_dict)  # Update gamma using the line search method

#         for group in self.param_groups:
#             momentum = group['momentum']
#             lr = group['lr']

#             for p, grad in zip(group['params'], aggregated_gradients):
#                 if p.grad is None:
#                     continue

#                 # Apply momentum
#                 param_state = self.state[p]
#                 if 'momentum_buffer' in param_state:
#                     buf = param_state['momentum_buffer']
#                     buf.mul_(momentum).add_(grad)
#                     grad = buf

#                 # Update parameter
#                 p.data.add_(-lr * self.gamma, grad)

#     @torch.no_grad()
#     def _line_search(self, loss, w_dict):
#         """
#         Computes the line search in closed form to update gamma.
#         """
#         num = loss
#         denom = 0

#         for group in self.param_groups:
#             lr = group['lr']
#             for param in group['params']:
#                 if param.grad is None:
#                     continue
#                 delta_t = w_dict[param]['delta_t']
#                 r_t = w_dict[param]['r_t']
#                 num -= lr * torch.sum(delta_t * r_t)
#                 denom += lr * (delta_t.norm() ** 2)

#         self.gamma = float((num / (denom + self.eps)).clamp(min=0, max=1))
