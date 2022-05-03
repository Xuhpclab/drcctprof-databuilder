#!/usr/bin/env python3

import sys
sys.path.insert(0, './hatchet')
import hatchet as ht
from pathlib import Path
import drcctprof_data_builder as ddb

roots = []
ID = 0 # manually assign the id number

"""
lists in a list. 
each list in a list presents a path.
each list contains multiple tuples.
a tuple means a node, consists of id, name, file, start line, and rows respectively.
Example:
[
    [(name1, id, file, line, start_line, rows)], 
    [(name1, id, file, line, start_line, rows), (name2, id, file, line, start_line, rows)], 
    [(name1, id, file, line, start_line, rows), (name3, id, file, line, start_line, rows)]
]
"""
all_paths = []


class TreeNode:
    def __init__(self, name, parent, file, line, start_line):
        global ID
        self.parent = parent
        self.name = name
        self.children = []
        self.parents = []
        self.id = ID
        ID += 1
        self.file = file
        self.line = line
        self.start_line = start_line
        self.rows = set()
        
        """
        fill the list of self.parents, 
        if two nodes have exact same parents and names of two nodes are same, 
        then consider they are same one.
        """
        p = self.parent
        while p:
            self.parents.append(p.name)
            p = p.parent
    
    def add_child(self, node):
        self.children.append(node)
        return node
    
    def add_row(self, row):
        self.rows.add(row)
        
    def __str__(self, level=0):
        # print all_paths info except row
        
        ret = "\t"*level+repr(self.name)+", id:"+str(self.id)+", line:"+str(self.line)+", startline:"+str(self.start_line)+", rows:"+str(len(self.rows)) +"\n"
        #ret = "\t"*level+repr(self.name)+",rows: "+prt_rows+"\n"
        
        for child in self.children:
            ret += child.__str__(level+1)
        return ret
    
    def __repr__(self):
        return self.name

# check if the node has child(ren)
def has_child(node):
    return node.children is not None


def return_all_paths(node, paths):
    global all_paths
    if node is None:
        return
    paths.append((node.name, node.id, node.file, node.line, node.start_line, node.rows))
    if has_child(node):
        all_paths.append(list(paths))
    for i in node.children:
        return_all_paths(i, paths)
    paths.pop()


def main(tau_profile_dir, output):
    global root
    
    builder = ddb.Builder()
    gf = ht.GraphFrame.from_tau(str(tau_profile_dir))
    # print(gf.tree())
    df = gf.dataframe
    multiRank = False
    multiThread = False
    if len(df.index.names) == 2:
        if df.index.names[1] == 'thread':
            multiThread = True
        else:
            multiRank = True
    elif len(df.index.names) == 3:
        multiThread = True
        multiRank = True
    
    metric_num = 0
    units = []
    """
    Add Metric Type: builder.addMetricType()
    """
    for idx, column in enumerate(df.columns.values):
        if "(I)" in column:
            continue
        if "(E)" in column:
            column = column.replace("(E)", "")
            temp = column.rsplit("(", 1)
            des = temp[0].strip()
            unit = ''
            if len(temp) == 2:
                unit = temp[1].split(")")[0].strip()
            units.append([idx, unit == "sec"])
            metric_num += 1
            builder.addMetricType(1, unit, des)
            # break

    nodes = []
    sample_map = {} #key is name, value is the number of samples
    last_row_name, sample_num = None, 0
    rows = gf.dataframe.itertuples()
    for row in rows:
        if multiRank and multiThread:
            node = row[0][0]
            rank = row[0][1]
            thread = row[0][2]
        elif multiRank and not multiThread:
            node = row[0][0]
            rank = row[0][1]
            thread = -1
        elif not multiRank and multiThread:
            node = row[0][0]
            rank = -1
            thread = row[0][1]
        else:
            node = row[0]
            rank = -1
            thread = -1

        if last_row_name is None:
            sample_num = 1
        elif last_row_name == node:
            sample_num += 1
        else:
            last_row_name = None
            sample_num = 1
        last_row_name = node
        
        path = []
        for cur in node.path():
            path.append(cur)
        
        if node.frame.get('type') != 'function' and node.frame.get('type') != 'statement':
            continue
        
        

        curNode = node
        contextMsgDic = {}
        parent = None
        for idx, val in enumerate(path):
            if idx >= len(path):
                break
            curNode = val
            try:
                if thread > -1 and rank > -1:
                    contextMsgDic = dict(gf.dataframe.loc[(curNode, rank, thread)])
                elif rank > -1:
                    contextMsgDic = dict(gf.dataframe.loc[(curNode, rank)])
                elif thread > -1:
                    contextMsgDic = dict(gf.dataframe.loc[(curNode, thread)])
                else:
                    contextMsgDic = dict(gf.dataframe.loc[curNode])
            except:
                continue

            file, name, line, startline = contextMsgDic['file'], contextMsgDic['name'], int(contextMsgDic['line']), contextMsgDic['line']
            if file == None or str(file) == '0':
                file = "[unknown]"
            if name in sample_map: sample_map[name] = max(sample_num, sample_map[name])
            else:sample_map[name] = sample_num
            # building a tree named root
            
            if parent == None:
                for root in roots:
                    if root.name == name and root.file == file and root.line == line:
                        parent = root
                        break
                if parent == None:
                    parent = TreeNode(name, parent, file, line, startline)
                    roots.append(parent)
            else:
                tree_node = None
                for node in parent.children:
                    if node.name == name and node.file == file and node.line == line:
                        tree_node = node
                        break
                if tree_node == None:
                    tree_node = TreeNode(name, parent, file, line, startline)
                    parent.add_child(tree_node)
                parent = tree_node
                
        if parent != None:
            parent.add_row(row)
    """
    use print(root) to see the whole tree
    """
    for root in roots:
        # print(root)
        paths = []
        return_all_paths(root, paths)

    #print(all_paths)
    for each_path in all_paths:
        sumvalue = 0
        contextMsgList = []
        for each_node in each_path:
            contextMsgList.append(ddb.ContextMsg(each_node[1], each_node[2], each_node[0], each_node[0], each_node[4], each_node[3]))
        # print(each_node[0])
        for r in each_node[5]:
            metricMsgList = []
            for idx in range(metric_num):
                metricValue = 0
                if units[idx][1]:
                    metricValue = int(r[units[idx][0]+1]*1000000)    
                else:
                    metricValue = int(r[units[idx][0]+1])
                # print(metricValue)
                metricMsgList.append(ddb.MetricMsg(0, metricValue, ""))
                if metricMsgList[idx].uintValue > 0:
                    sumvalue += 1
            if sumvalue < 1:
                continue        
            builder.addSample(contextMsgList, metricMsgList)
            
    builder.generateProfile(output)
        
DEBUG_MOED = False
def debug():
    main("./tests/data/tau_data", "tau.debug.drcctprof")
    # main("./tau_test", "tau.drcctprof")

if __name__ == "__main__":
    
    if DEBUG_MOED == True:
        debug()
        exit()

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
    
    main(input, output)