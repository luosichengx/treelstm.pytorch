import pickle
from query_to_tree import QT
with open("gnucore_dev", "rb")as f:
    qt_list = pickle.load(f)
for qt in qt_list:
    print(qt_list)
