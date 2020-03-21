import os
import random
import sys
sys.setrecursionlimit(1000000)
from collections import defaultdict
from .Tree import varTree as Tree
import re
import pickle


op = ["forall","exists","and","or","not","distinct","implies","iff","symbol","function","real_constant",
      "bool_constant","int_constant","str_constant","plus","minus","times","le","lt","equals",
      "ite","toreal","bv_constant","bvnot","bvand","bvor","bvxor","concat","extract","rotation",
      "extend","zero_extend","sign_extend","bvult","bvule","bvuge","bvugt","bvneg","bvadd","bvsub","bvmul","bvudiv",
      "bvurem","bvlshl","bvlshr","bvrol","bvror","bvzext","bvsext","bvslt","bvsle","bvcomp","bvsdiv",
      "bvsrem","bvashr","str_length","str_concat","str_contains","str_indexof","str_replace","str_substr",
      "str_prefixof","str_suffixof","str_to_int","int_to_str","str_charat","select","store","value",
      "div","pow","algebraic_constant","bvtonatural","_to_fp","=","unknown"]

# op = ["not","bvadd","bvule","extract","ite","and","or","distinct","bvmul","concat","bvashr",
#       "bvuge","bvugt","bvnot","bvor","bvsle","bvsub","bvsgt","zero_extend","bvshl","bvsge","bvlshr","sign_extend",
#       "bvurem","bvudiv","bvxor","bvand"]

si_op = ["extract","zero_extend","sign_extend","_to_fp"]

tri_op = ["ite"]

bv_constant = "constant"
bool_constant = "constant"

# class Tree:
#     def __init__(self, operator, left= None, mid= None, right= None):
#         if operator not in op:
#             raise ValueError
#         self.operator = operator
#         if left in op or mid in op or right in op:
#             raise ValueError
#         self.left = left
#         self.mid = mid
#         self.right = right
#         self.name = None
#
#     def set_name(self, name):
#         self.name = name
#
# class varTree(Tree):
#     def __init__(self, operator, left= None, mid= None, right= None):
#         super(varTree,self).__init__(operator, left= None, mid= None, right= None)
#         self.var = set()
#         self.depth = 0
#         self.compress_depth = 0
#         if self.operator == "concat":
#             self.reduce_concat()
#             self.compress_depth -= 1
#         for i in [left, mid, right]:
#             if not i:
#                 i = varTree(None)
#         if left == None:
#             self.depth = 0
#             self.compress_depth = 0
#         else:
#             self.depth = max(left.depth, mid.depth, right.depth) + 1
#             self.compress_depth = max(left.compress_depth, mid.compress_depth, right.compress_depth) + 1
#         for i in [left, mid, right]:
#             if i.startwiths("var"):
#                 self.var.add(i)
#             elif isinstance(i, Tree):
#                 self.var.add(i.var)
#
#     def reduce_concat(self):
#         if not self.left:
#             raise ValueError
#         if not self.mid:
#             raise ValueError
#         if self.right:
#             raise  ValueError
#         if self.left.var.issubset(self.mid.var):
#             self.left = self.mid.left
#             self.right = self.mid.right
#             self.mid = self.mid.mid
#         elif self.mid.var.issubset(self.left.var):
#             self.right = self.mid.right
#             self.mid = self.mid.mid
#             self.left = self.mid.left
#         elif self.left.depth > self.mid.depth:
#             self.right = self.mid.right
#             self.mid = self.mid.mid
#             self.left = self.mid.left
#         else:
#             self.left = self.mid.left
#             self.right = self.mid.right
#             self.mid = self.mid.mid


class QT:
    def __init__(self, logic_tree, timeout):
        self.logic_tree = logic_tree
        self.timeout = timeout

class query_tree:
    def __init__(self):
        self.filename = None
        self.sol_time = 0
        self.tree_list = []
        self.logic_tree = None
        self.val_list = []
        self.val_dic = {}
        self.mid_val = {}
        self.timeout = None

    def load(self, input):
        with open(input) as f:
            data = f.read()
        data_list = data.split("\n")
        try:
            if data_list[0].startswith("filename"):
                self.filename = data_list[0].split("/")[-1]
            else:
                self.filename = input.split("/")[-1]
        except:
            pass
        for i in range(len(data_list)):
            if "declare-fun" in data_list[i]:
                self.val_list.append(data_list[i].split(" ")[1])
                self.val_dic[data_list[i].split(" ")[1]] = "var" + str(len(self.val_list))
            elif "assert" in data_list[i]:
                self.str_to_tree_list(data.split("(assert\n")[1:])
                break
        self.generate_logic_tree()

    def generate_logic_tree(self):
        tl = self.tree_list
        while len(tl) != 1:
            new_tl = []
            if len(tl) % 3 != 0:
                tl.append(None)
            if len(tl) % 3 != 0:
                tl.append(None)
            for i in range(0, len(tl), 3):
                new_tl.append(Tree("and", tl[i], tl[i + 1], tl[i + 2]))
            tl = new_tl
        self.logic_tree = tl[0]

    def str_to_tree_list(self, assertions):
        # assertion
        for assertion in assertions:
            data_lines = assertion.split("\n")
            # one line
            for data_line in data_lines:
                if data_line == "(check-sat)" or data_line == "":
                    continue
                data_list = data_line.split(" ")
                stack = []
                if "time:" in data_line:
                    self.sol_time = data_list[-1]
                    self.timeout = float(self.sol_time) > 300
                    break
                else:
                    try:
                        for da in data_list:
                            if len(stack) != 0 and da.startswith("("):
                                for i in range(da.count("(")):
                                    stack.append("(")
                            d = da.replace("(", "")
                            d = d.replace(")", "")
                            if d == '' or d == '_' or d == "let":
                                continue
                            elif d.startswith("?x") or d.startswith("$x"):
                                if len(stack) == 0 and d in self.mid_val.keys():
                                    break
                                elif len(stack) != 0 :
                                    stack.append(self.mid_val[d])
                                else:
                                    stack.append(d)
                            elif d.isdigit():
                                pass
                            elif re.match("bv[0-9]+", d):
                                stack.append(Tree(bv_constant))
                            elif d == "true" or d == "false":
                                stack.append(Tree(bool_constant))
                            elif d in self.val_list:
                                stack.append(Tree(self.val_dic[d]))
                            elif d in op:
                                stack.append(d)
                            res = da.count(")")
                            while(res != 0 and "(" in stack):
                                stack_rev = stack[::-1]
                                i = stack_rev.index("(")
                                tree_val = stack[-i:] + [None] * 3
                                if len(stack[-i:]) == 1:
                                    self.mid_val["val"] = stack[-i:][0]
                                else:
                                    self.mid_val["val"] = Tree(tree_val[0], tree_val[1], tree_val[2], tree_val[3])
                                stack = stack[:-i - 1]
                                res -= 1
                                stack.append(self.mid_val["val"])
                        if len(stack) != 0:
                            stack = stack + [None] * 3
                            if "let" in data_line and isinstance(stack[1], Tree):
                                self.mid_val[stack[0]] = stack[1]
                                stack[1].set_name(stack[0])
                                # print("let", stack[1])
                            else:
                                self.tree_list.append(Tree(stack[0], stack[1], stack[2], stack[3]))
                                print("assert", self.tree_list[-1])
                    except:
                        with open("parse_error.txt", "w") as f:
                            f.write(data_line + "\n")
                        data_line = data_line.replace("(", "")
                        data_line = data_line.replace(")", "")
                        data_list = data_line.split(" ")
                        stack = []
                        for d in data_list:
                            if d.startswith("?x") or d.startswith("$x"):
                                if len(stack) == 0 and d in self.mid_val.keys():
                                    break
                                elif "let" not in data_line or len(stack) != 0:
                                    stack.append(self.mid_val[d])
                                else:
                                    stack.append(d)
                            elif re.match("bv[0-9]+", d):
                                stack.append(Tree(bv_constant))
                            elif d == "true" or d == "false":
                                stack.append(Tree(bool_constant))
                            elif d in self.val_list:
                                stack.append(Tree(self.val_dic[d]))
                        if len(stack) != 0:
                            stack = stack + [None]*3
                            if "let" in data_line:
                                tree = Tree("unknown", stack[1], stack[2], stack[3])
                                tree.set_name(stack[0])
                                self.mid_val[stack[0]] = tree
                            else:
                                self.tree_list.append(Tree("unknown", stack[0], stack[1], stack[2]))


def count_data(input):
    print(input)
    qt_list = []
    if os.path.isdir(input):
        for root, dirs, files in os.walk(input):
            for file in files:
                print(file)
                querytree = query_tree()
                querytree.load(os.path.join(input, file))
                qt = QT(querytree.logic_tree, querytree.timeout)
                qt_list.append(qt)
                print(len(qt_list))
                # if len(qt_list) > 1:
                #     break
    else:
        i = 0
        input_file = input + str(i)
        while(os.path.exists(input_file)):
            qt = query_tree()
            query_tree.load(qt,input)
            qt_list.append(qt)
            i += 1
            input_file = input + str(i)
    return qt_list

def split_train_test(qt_list):
    random.shuffle(qt_list)
    td = int(len(qt_list) * 0.5)
    dt = int(len(qt_list) * 0.6)
    return qt_list[:td], qt_list[td:dt], qt_list[dt:]


def generate_dataset(input):
    qt_list = count_data(input)
    return split_train_test(qt_list)

