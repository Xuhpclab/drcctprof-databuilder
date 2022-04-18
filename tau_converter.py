import os
from re import L
import numpy as np
import sys
sys.path.append('./hatchet')
import hatchet as ht
from pathlib import Path
from hatchet import GraphFrame
import drcctprof_data_builder as ddb

root = None
check = True
ID = 0 # manually assign the id number

"""
lists in a list. 
each list in a list presents a path.
each list contains multiple tuples.
a tuple means a node, consists of id, name, file, start line, and row respectively.
Example:
[
    [('.TAU application', 0, '[unknown]', 0, 0)], 
    [('.TAU application', 0, '[unknown]', 0, 0), ('MPI_Bcast()', 1, '[unknown]', 0, 0)], 
    [('.TAU application', 0, '[unknown]', 0, 0), ('MPI_Comm_rank()', 2, '[unknown]', 0, 0)], 
    [('.TAU application', 0, '[unknown]', 0, 0), ('MPI_Comm_size()', 3, '[unknown]', 0, 0)]
]
"""
all = []


class TreeNode:
    def __init__(self, name, parent, file, line, start_line, row):
        global ID
        self.parent = parent
        self.name = name
        self.children = []
        self.id = ID
        ID += 1
        self.file = file
        self.line = line
        self.start_line = start_line
        self.row = row # use a row to get the time
    
    def add_child(self, node):
        self.children.append(node)
        return node

    def get_children(self):
        return self.children

    def __str__(self, level=0):
        # print all info except row
        ret = "\t"*level+repr(self.name)+", id:"+str(self.id)+", line:"+str(self.line)+", startline:"+str(self.start_line)+"\n"
        for child in self.children:
            ret += child.__str__(level+1)
        return ret
    
    def __repr__(self):
        return self.name

# check if the node has child(ren)
def has_child(node):
    return node.children is not None

def return_all_paths(node, paths):
    global all
    if node is None:
        return
    paths.append((node.name, node.id, node.file, node.line, node.start_line, node.row))
    if has_child(node):
        all.append(list(paths))
    for i in node.children:
        return_all_paths(i, paths)
    paths.pop()

def main(tau_profile_dir, output):
    global root
    global check
    
    builder = ddb.Builder()
    gf = ht.GraphFrame.from_tau(str(tau_profile_dir))
    df = gf.dataframe
    metric_num = 0
    units = []
    #print(gf.tree())
    """
    Add Metric Type: builder.addMetricType()
    """
    for column in df.columns.values:
        if "(I)" in column:
            continue
        if "(E)" in column:
            column = column.replace("(E)", "")
            temp = column.rsplit("(", 1)
            des = temp[0].strip()
            unit = ''
            if len(temp) == 2:
                unit = temp[1].split(")")[0].strip()
            units.append(unit == "sec")
            metric_num += 1
            builder.addMetricType(1, unit, des)
            # break

    list_node = []
    for row in gf.dataframe.itertuples():
        # the form of index is (node, rank) / (node, rank, thread)
        node = row[0][0]
        path = []
        if str(node.path()) not in list_node and not node.children:
            for cur in node.path():
                path.append(cur)
                list_node.append(str(node.path()))
        
        if node.frame.get('type') != 'function' and node.frame.get('type') != 'statement':
            continue
        rank = row[0][1]
        thread = -1
        if len(row[0]) == 3:
            thread = row[0][2]

        curNode = node
        contextMsgDic = {}
        
        parent = root
        for idx, val in enumerate(path):
            if idx >= len(path):
                break
            curNode = val
            if thread > -1:
                contextMsgDic = gf.dataframe.loc[(curNode, rank, thread)].to_dict()
            else:
                contextMsgDic = dict(gf.dataframe.loc[(curNode, rank)])

            file, name, line, startline = "[unknown]", contextMsgDic['name'], int(contextMsgDic['line']), contextMsgDic['line']
            
            # building a tree named root
            if not parent and check: # create one at the beginning
                root = TreeNode(name, None, file, line, startline, row)
                parent = root
                check = False
            elif name in parent.name:
                continue
            else:
                child = parent.add_child(TreeNode(name, parent, file, line, startline, row))
                parent = child
    """
    use print(root) to see the whole tree
    """
    #print(root)
    
    paths = tuple()
    return_all_paths(root, path)
    #print(all)
    for each_path in all:
        sumvalue = 0
        contextMsgList, metricMsgList = [], []
        for each_node in each_path:
            contextMsgList.append(ddb.ContextMsg(each_node[1], each_node[2], each_node[0], each_node[0], each_node[4], each_node[3]))
            for idx in range(metric_num):
                if units[idx]:
                    metricMsgList.append(ddb.MetricMsg(0, int(each_node[5][8 + idx * 2]*1000000), ""))
                else:
                    metricMsgList.append(ddb.MetricMsg(0, int(each_node[5][8 + idx * 2]), ""))
                if metricMsgList[idx].uintValue > 0:
                    sumvalue += 1
                if sumvalue < 1:
                    continue
        builder.addSample(contextMsgList, metricMsgList)
    builder.generateProfile(output)
        

if __name__ == "__main__":
    if len(sys.argv[1:]) != 2:
        sys.exit("Invalid Inputs.\nHow to run this file:\npython3 tau-converter.py 'input name' 'output name'")

    input, output = sys.argv[1:]
    if not input or not output:
        sys.exit("Reenter the command again.")

    idx = (output.find('.drcctprof'))
    if '.drcctprof' not in output or len(output[idx:]) != 10:
        sys.exit("Output format should be .drcctprof")

    if not Path(input).is_dir():
        sys.exit("Input path doesn't exist.")
    
    try:
        main(input, output)
    except:
        sys.exit("Unexpected error")