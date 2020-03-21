from tqdm import tqdm

import torch
from .Tree import varTree
from . import utils


class myTrainer(object):
    def __init__(self, args, model, criterion, optimizer, device, vocab):
        super(myTrainer, self).__init__()
        self.args = args
        self.model = model
        self.criterion = criterion
        self.optimizer = optimizer
        self.device = device
        self.epoch = 0
        self.vocab = vocab

    # helper function for training
    def train(self, dataset):
        self.model.train()
        self.optimizer.zero_grad()
        total_loss = 0.0
        indices = torch.randperm(len(dataset), dtype=torch.long, device='cpu')
        for idx in tqdm(range(len(dataset)), desc='Training epoch ' + str(self.epoch + 1) + ''):
            qt = dataset[idx]
            if qt.timeout == True:
                target = torch.Tensor([[1, 0]])
            else:
                target = torch.Tensor([[0, 1]])
            # qt.logic_tree = varTree("and", varTree("var1"), varTree("constant"))
            self.val_to_tensor(qt.logic_tree, self.device, self.vocab)
            # input = input.to(self.device)
            target = target.to(self.device)
            output = self.model(qt.logic_tree)
            loss = self.criterion(output, target)
            total_loss += loss.item()
            # loss.backward()
            loss.backward(retain_graph=True)
            if idx % self.args.batchsize == 0 and idx > 0:
                self.optimizer.step()
                self.optimizer.zero_grad()
        self.epoch += 1
        return total_loss / len(dataset)

    # helper function for testing
    def test(self, dataset):
        self.model.eval()
        with torch.no_grad():
            total_loss = 0.0
            predictions = torch.zeros(len(dataset), dtype=torch.float, device='cpu')
            labels = torch.zeros(len(dataset), dtype=torch.float, device='cpu')
            indices = torch.arange(0, 2, dtype=torch.float, device='cpu')
            for idx in tqdm(range(len(dataset)), desc='Testing epoch  ' + str(self.epoch) + ''):
                qt = dataset[idx]
                if qt.timeout == True:
                    target = torch.Tensor([[1, 0]])
                    labels[idx] = torch.Tensor([0])
                else:
                    target = torch.Tensor([[0, 1]])
                    labels[idx] = torch.Tensor([1])
                self.val_to_tensor(qt.logic_tree, self.device, self.vocab)
                # input = input.to(self.device)
                target = target.to(self.device)
                output = self.model(qt.logic_tree)
                loss = self.criterion(output, target)
                total_loss += loss.item()
                output = output.squeeze().to('cpu')
                if torch.dot(indices, torch.exp(output)) > 0.5:
                    predictions[idx] = torch.Tensor([1])
                else:
                    predictions[idx] = torch.Tensor([0])
        return total_loss / len(dataset), predictions, labels

    def val_to_tensor(self, tree, device, vocab):
        if tree:
            try:
                if not isinstance(tree.val, torch.Tensor):
                    tree.val = torch.tensor([vocab.labelToIdx[tree.val]], dtype=torch.long, device=device)
                else:
                    return
            except:
                tree.val = torch.tensor([1], dtype=torch.long, device=device)
            self.val_to_tensor(tree.left, device, vocab)
            self.val_to_tensor(tree.mid, device, vocab)
            self.val_to_tensor(tree.right, device, vocab)