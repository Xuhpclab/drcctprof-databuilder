from collections import deque
import os
from re import L
import numpy as np
import sys
sys.path.append('./hatchet')
import hatchet as ht
from pathlib import Path
from hatchet import GraphFrame
import drcctprof_data_builder as ddb
from anytree import Node, RenderTree

root = None
check = True
ID = 0 # manually assign the id number
all = [] # all paths with id, name, file, line, and start line

class TreeNode:
    def __init__(self, name, parent, file, line, start_line):
        global ID
        self.parent = parent
        self.name = name
        self.children = []
        self.id = ID
        ID += 1
        self.file = file
        self.line = line
        self.start_line = start_line
    
    def add_child(self, node):
        self.children.append(node)
        return node

    def get_children(self):
        return self.children

    def __str__(self, level=0):
        ret = "\t"*level+repr(self.name)+", id:"+str(self.id)+", line:"+str(self.line)+", startline:"+str(self.start_line)+"\n"
        for child in self.children:
            ret += child.__str__(level+1)
        return ret
    
    def __repr__(self):
        return self.name
    
def has_child(node):
    return node.children is not None

def return_all_paths(node, paths):
    global all
    if node is None:
        return
    paths.append((node.name, node.id, node.file, node.line, node.start_line))
    if has_child(node):
        #print(list(reversed(paths)))
        all.append(list(paths))
    for i in node.children:
        return_all_paths(i, paths)
    paths.pop()

def build_tree(node, parent):
    global root
    if not parent:
        root = Node(str(node), parent=parent)
        return root
    
    a = str(node)
    a = Node(a, parent=parent)
    return a

def main(tau_profile_dir, output):
    global root
    global check
    #parent = root
    
    
    builder = ddb.Builder()
    gf = ht.GraphFrame.from_tau(str(tau_profile_dir))
    df = gf.dataframe
    metric_num = 0
    units = []
    contextid_dict, id = {}, 0
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

        sumvalue = 0
        metricMsgList = []
        
        contextMsgList = []
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
            if not parent and check:
                root = TreeNode(name, None, file, line, startline)
                parent = root
                check = False
            elif name in parent.name:
                parent = root
            else:
                if not parent: 
                    child = root.add_child(TreeNode(name, root, file, line, startline))
                else:
                    child = parent.add_child(TreeNode(name, parent, file, line, startline))
                parent = child
                
            #print(parent.name)
            if name in contextid_dict:
                contextMsgList.append(ddb.ContextMsg(int(contextid_dict[name]), file, name, name, startline, line))
            else:
                contextid_dict[name] = id
                id += 1
                contextMsgList.append(ddb.ContextMsg(int(contextid_dict[name]), file, name, name, startline, line))
             
        for idx in range(metric_num):
            if units[idx]:
                metricMsgList.append(ddb.MetricMsg(0, int(row[8 + idx * 2]*1000000), ""))
            else:
                metricMsgList.append(ddb.MetricMsg(0, int(row[8 + idx * 2]), ""))
            if metricMsgList[idx].uintValue > 0:
                sumvalue += 1
        if sumvalue < 1:
            continue
        
        #contextMsgList[:] = contextMsgList[::-1]
        #builder.addSample(contextMsgList, metricMsgList)
    """
    use print(root) to see the whole tree
    """
    #print(root)
    
    paths = tuple()
    return_all_paths(root, path)
    for each_path in all:
        contextMsgList = []
        for each_node in each_path:
            contextMsgList.append(ddb.ContextMsg(each_node[1], each_node[2], each_node[0], each_node[0], each_node[4], each_node[3]))
        builder.addSample(contextMsgList, metricMsgList)
    
    builder.generateProfile(output)
        

if __name__ == "__main__":

    # check the number of arguments.
    
    if len(sys.argv[1:]) != 2:
        sys.exit("Invalid Inputs.\nHow to run this file:\npython3 tau-converter.py 'input name' 'output name'")

    input, output = sys.argv[1:]
    if not input or not output:
        sys.exit("Reenter the command again.")

    # check the output format: 
    # if the file contains '.drcctprof' and if the file is end with .drcctprof
    idx = (output.find('.drcctprof'))
    if '.drcctprof' not in output or len(output[idx:]) != 10:
        sys.exit("Output format should be .drcctprof")

    # check the input file
    if not Path(input).is_dir():
        sys.exit("Input path doesn't exist.")
    
    main(input, output)
    
        #print("Unexpected Error")