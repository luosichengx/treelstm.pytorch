from __future__ import division
from __future__ import print_function

import os
import pickle
import random
import logging

import torch
import torch.nn as nn
import torch.optim as optim

# IMPORT CONSTANTS
from mytreelstm import Constants
# NEURAL NETWORK MODULES/LAYERS
from mytreelstm import TreeLSTM
# DATA HANDLING CLASSES
from mytreelstm import Vocab
# DATASET CLASS FOR SICK DATASET
from mytreelstm import query_to_tree
# METRICS CLASS FOR EVALUATION
from mytreelstm import Metrics
# UTILITY FUNCTIONS
from mytreelstm import utils
# TRAIN AND TEST HELPER FUNCTIONS
from mytreelstm import myTrainer
# CONFIG PARSER
from myconfig import parse_args
from mytreelstm import varTree as myTree


# MAIN BLOCK
def main():
    global args
    args = parse_args()
    # global logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s:%(name)s:%(message)s")
    # file logger
    fh = logging.FileHandler(os.path.join(args.save, args.expname)+'.log', mode='w')
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    # console logger
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    # argument validation
    args.cuda = args.cuda and torch.cuda.is_available()
    device = torch.device("cuda:0" if args.cuda else "cpu")
    if args.sparse and args.wd != 0:
        logger.error('Sparsity and weight decay are incompatible, pick one!')
        exit()
    logger.debug(args)
    torch.manual_seed(args.seed)
    random.seed(args.seed)
    if args.cuda:
        torch.cuda.manual_seed(args.seed)
        torch.backends.cudnn.benchmark = True
    if not os.path.exists(args.save):
        os.makedirs(args.save)

    print(device)
    args.data = "data/angr"
    train_dir = os.path.join(args.data, 'train/')
    dev_dir = os.path.join(args.data, 'dev/')
    test_dir = os.path.join(args.data, 'test/')

    # write unique words from all token files
    # sick_vocab_file = os.path.join(args.data, 'sick.vocab')
    # if not os.path.isfile(sick_vocab_file):
    #     token_files_b = [os.path.join(split, 'b.toks') for split in [train_dir, dev_dir, test_dir]]
    #     token_files_a = [os.path.join(split, 'a.toks') for split in [train_dir, dev_dir, test_dir]]
    #     token_files = token_files_a + token_files_b
    #     sick_vocab_file = os.path.join(args.data, 'sick.vocab')
    #     utils.build_vocab(token_files, sick_vocab_file)

    # get vocab object from vocab file previously written
    # vocab = Vocab(filename=sick_vocab_file,
    #               data=[Constants.PAD_WORD, Constants.UNK_WORD,
    #                     Constants.BOS_WORD, Constants.EOS_WORD])
    # logger.debug('==> SICK vocabulary size : %d ' % vocab.size())

    smt_vocab_file = os.path.join(args.data, 'smt.vocab')
    smt_vocab = Vocab(filename=smt_vocab_file,
                  data=[Constants.PAD_WORD, Constants.UNK_WORD,
                        Constants.BOS_WORD, Constants.EOS_WORD])
    logger.debug('==> smt vocabulary size : %d ' % smt_vocab.size())

    # load SICK dataset splits
    # train_file = os.path.join(args.data, 'sick_train.pth')
    # if os.path.isfile(train_file):
    #     train_dataset = torch.load(train_file)
    # else:
    #     train_dataset = SICKDataset(train_dir, smt_vocab, args.num_classes)
    #     torch.save(train_dataset, train_file)
    # logger.debug('==> Size of train data   : %d ' % len(train_dataset))
    # dev_file = os.path.join(args.data, 'sick_dev.pth')
    # if os.path.isfile(dev_file):
    #     dev_dataset = torch.load(dev_file)
    # else:
    #     dev_dataset = SICKDataset(dev_dir, smt_vocab, args.num_classes)
    #     torch.save(dev_dataset, dev_file)
    # logger.debug('==> Size of dev data     : %d ' % len(dev_dataset))
    # test_file = os.path.join(args.data, 'sick_test.pth')
    # if os.path.isfile(test_file):
    #     test_dataset = torch.load(test_file)
    # else:
    #     test_dataset = SICKDataset(test_dir, smt_vocab, args.num_classes)
    #     torch.save(test_dataset, test_file)
    # logger.debug('==> Size of test data    : %d ' % len(test_dataset))
    train_file = os.path.join(args.data, 'gnucore_train')
    dev_file = os.path.join(args.data, 'gnucore_dev')
    test_file = os.path.join(args.data, 'gnucore_test')
    if os.path.isfile(train_file):
        # train_dataset = torch.load(dev_file)
        # dev_dataset = train_dataset
        # test_dataset = train_dataset
        train_dataset = torch.load(train_file)
        dev_dataset = torch.load(dev_file)
        test_dataset = torch.load(test_file)
    else:
        train_dataset, dev_dataset, test_dataset = query_to_tree.generate_dataset(os.path.join(args.data,'query'))
        torch.save(train_dataset, train_file)
        torch.save(dev_dataset, dev_file)
        torch.save(test_dataset, test_file)
    # logger.debug('==> Size of train data   : %d ' % len(train_dataset))

    # initialize model, criterion/loss_function, optimizer
    model = TreeLSTM(
        smt_vocab.size(),
        args.input_dim,
        args.mem_dim,
        args.hidden_dim,
        args.num_classes,
        args.sparse,
        args.freeze_embed)
    criterion = nn.KLDivLoss()

    # for words common to dataset vocab and GLOVE, use GLOVE vectors
    # for other words in dataset vocab, use random normal vectors
    emb_file = os.path.join(args.data, 'smt.pth')
    if os.path.isfile(emb_file):
        emb = torch.load(emb_file)
    else:
        # load glove embeddings and vocab
        emb = torch.zeros(smt_vocab.size(), smt_vocab.size(), dtype=torch.float, device=device)
        # zero out the embeddings for padding and other special words if they are absent in vocab
        for word in smt_vocab.labelToIdx.keys():
            emb[smt_vocab.getIndex(word)][smt_vocab.getIndex(word)] = 1
        torch.save(emb, emb_file)
    # plug these into embedding matrix inside model
    model.childsumtreelstm.emb.weight.data.copy_(emb)

    model.to(device), criterion.to(device)
    if args.optim == 'adam':
        optimizer = optim.Adam(filter(lambda p: p.requires_grad,
                                      model.parameters()), lr=args.lr, weight_decay=args.wd)
    elif args.optim == 'adagrad':
        optimizer = optim.Adagrad(filter(lambda p: p.requires_grad,
                                         model.parameters()), lr=args.lr, weight_decay=args.wd)
    elif args.optim == 'sgd':
        optimizer = optim.SGD(filter(lambda p: p.requires_grad,
                                     model.parameters()), lr=args.lr, weight_decay=args.wd)
    metrics = Metrics(args.num_classes)

    # create trainer object for training and testing
    trainer = myTrainer(args, model, criterion, optimizer, device, smt_vocab)

    best = -float('inf')
    for epoch in range(args.epochs):
        train_loss = trainer.train(train_dataset)
        train_loss, train_pred, train_label = trainer.test(train_dataset)
        dev_loss, dev_pred, dev_label = trainer.test(dev_dataset)
        test_loss, test_pred, test_label = trainer.test(test_dataset)

        train_accuracy = metrics.accuracy(train_pred, train_label)
        logger.info('==> Epoch {}, Train \tLoss: {}\tAccuracy: {}'.format(
            epoch, train_loss, train_accuracy))
        dev_accuracy = metrics.accuracy(dev_pred, dev_label)
        logger.info('==> Epoch {}, Dev \tLoss: {}\tAccuracy: {}'.format(
            epoch, dev_loss, dev_accuracy))
        test_accuracy = metrics.accuracy(test_pred, test_label)
        logger.info('==> Epoch {}, Test \tLoss: {}\tAccuracy: {}'.format(
            epoch, test_loss, test_accuracy))

        if best < test_accuracy:
            best = test_accuracy
            checkpoint = {
                'model': trainer.model.state_dict(),
                'optim': trainer.optimizer,
                'pearson': test_accuracy,
                'args': args, 'epoch': epoch
            }
            logger.debug('==> New optimum found, checkpointing everything now...')
            torch.save(checkpoint, '%s.pt' % os.path.join(args.save, args.expname))

        # train_pearson = metrics.pearson(train_pred, train_dataset.labels)
        # train_mse = metrics.mse(train_pred, train_dataset.labels)
        # logger.info('==> Epoch {}, Train \tLoss: {}\tPearson: {}\tMSE: {}'.format(
        #     epoch, train_loss, train_pearson, train_mse))
        # dev_pearson = metrics.pearson(dev_pred, dev_dataset.labels)
        # dev_mse = metrics.mse(dev_pred, dev_dataset.labels)
        # logger.info('==> Epoch {}, Dev \tLoss: {}\tPearson: {}\tMSE: {}'.format(
        #     epoch, dev_loss, dev_pearson, dev_mse))
        # test_pearson = metrics.pearson(test_pred, test_dataset.labels)
        # test_mse = metrics.mse(test_pred, test_dataset.labels)
        # logger.info('==> Epoch {}, Test \tLoss: {}\tPearson: {}\tMSE: {}'.format(
        #     epoch, test_loss, test_pearson, test_mse))
        #
        # if best < test_pearson:
        #     best = test_pearson
        #     checkpoint = {
        #         'model': trainer.model.state_dict(),
        #         'optim': trainer.optimizer,
        #         'pearson': test_pearson, 'mse': test_mse,
        #         'args': args, 'epoch': epoch
        #     }
        #     logger.debug('==> New optimum found, checkpointing everything now...')
        #     torch.save(checkpoint, '%s.pt' % os.path.join(args.save, args.expname))


if __name__ == "__main__":
    main()
