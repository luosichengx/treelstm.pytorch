import torch
import torch.nn as nn
import torch.nn.functional as F

from . import Constants


# module for childsumtreelstm
class ChildSumTreeLSTM(nn.Module):
    def __init__(self, vocab_size, in_dim, mem_dim, sparsity, freeze):
        super(ChildSumTreeLSTM, self).__init__()
        self.in_dim = in_dim
        self.mem_dim = mem_dim
        self.ioux = nn.Linear(self.in_dim, 3 * self.mem_dim)
        self.iouh = nn.Linear(self.mem_dim, 3 * self.mem_dim)
        self.fx = nn.Linear(self.in_dim, self.mem_dim)
        self.fh = nn.Linear(self.mem_dim, self.mem_dim)
        self.emb = nn.Embedding(vocab_size, in_dim, padding_idx=Constants.PAD, sparse=sparsity)
        if freeze:
            self.emb.weight.requires_grad = False

    def node_forward(self, inputs, child_c, child_h):
        child_h_sum = torch.sum(child_h, dim=0, keepdim=True)

        iou = self.ioux(inputs) + self.iouh(child_h_sum)
        i, o, u = torch.split(iou, iou.size(1) // 3, dim=1)
        i, o, u = F.sigmoid(i), F.sigmoid(o), F.tanh(u)

        f = F.sigmoid(
            self.fh(child_h) +
            self.fx(inputs).repeat(len(child_h), 1)
        )
        fc = torch.mul(f, child_c)

        c = torch.mul(i, u) + torch.sum(fc, dim=0, keepdim=True)
        h = torch.mul(o, F.tanh(c))
        return c, h

    def forward(self, tree):
        children = []
        if hasattr(tree, "state"):
            return tree.state
        if tree.left:
            children.append(tree.left)
        if tree.mid:
            children.append(tree.mid)
        if tree.right:
            children.append(tree.right)
        for child in children:
            self.forward(child)

        if len(tree.val.shape) == 1:
            tree.val = self.emb(tree.val)
        if len(children) == 0:
            child_c = tree.val.detach().new(1, self.mem_dim).fill_(0.).requires_grad_()
            child_h = tree.val.detach().new(1, self.mem_dim).fill_(0.).requires_grad_()
        else:
            child_c, child_h = zip(* map(lambda x: x.state, children))
            child_c, child_h = torch.cat(child_c, dim=0), torch.cat(child_h, dim=0)

        tree.state = self.node_forward(tree.val, child_c, child_h)
        return tree.state

#
# module for distance-angle similarity
class Activate(nn.Module):
    def __init__(self, mem_dim, hidden_dim, num_classes):
        super(Activate, self).__init__()
        self.mem_dim = mem_dim
        self.hidden_dim = hidden_dim
        self.num_classes = num_classes
        self.wh = nn.Linear(self.mem_dim, self.hidden_dim)
        self.wp = nn.Linear(self.hidden_dim, self.num_classes)

    def forward(self, vec_dist):
        out = F.sigmoid(self.wh(vec_dist))
        out = F.log_softmax(self.wp(out), dim=1)
        return out


# putting the whole model together
class TreeLSTM(nn.Module):
    def __init__(self, vocab_size, in_dim, mem_dim, hidden_dim, num_classes, sparsity, freeze):
        super(TreeLSTM, self).__init__()
        self.childsumtreelstm = ChildSumTreeLSTM(vocab_size, in_dim, mem_dim, sparsity, freeze)
        self.Activate = Activate(mem_dim, hidden_dim, num_classes)

    def forward(self, tree):
        state, hidden = self.childsumtreelstm(tree)
        output = self.Activate(state)
        return output
